---
name: admin-auth-middleware-bypass
description: "Use when admin login is hardened: attack the middleware."
version: 1.0.0
tags: [admin-backend, auth-middleware, bearer-prefix, spring-boot, knife4j, unauthenticated, data-dump]
---

# 管理后台鉴权中间件绕过（admin-auth-middleware-bypass）

**一句话**：登录口打不动，不代表后台进不去 —— **先拆中间件，再拆密码**。
国产自研后台最常见的洞不是弱口令，是「中间件只判断了个格式」。

**触发**：后台接口稳定回 `401` / `token认证失败`；登录有 AES 参数加密或 2FA；
账号枚举 / SQLi / 弱口令全阴；`/doc.html` 或 `/v2/api-docs` 居然能打开；
响应包是 `{"code":..,"message":..,"success":..,"total":..}` 这种带 total 的中式包装。

## 何时用 / 何时不用

**用**：管理端连得上、接口存在、但每条都 401；想在不碰密码的情况下确认鉴权到底跑没跑。

**不用**（有专卡，先走专卡）：
- JWT 伪造 / alg 混淆 / kid 注入 → `jwt-bypass-pentest`、`jwt-attacks`
- 登录 oracle（2FA 前置、锁定窗口、假封禁）→ `admin-auth-oracle-triage`
- 某几条路由漏鉴权（422 vs 401）→ `unauthenticated-admin-api`
- RuoYi / satoken 等具体框架 → `ruoyi-admin-console-attack`、`satoken-session-hijack`
- 找后台在哪 → `admin-console-discovery`

**本卡只管一件事**：鉴权**中间件本身**有缺陷（前缀校验、过滤器顺序、白名单过宽）导致的整面绕过。

---

## 一、顺序铁律：文档面 → 中间件 → 登录面

```text
① 文档面     /doc.html /v2/api-docs /swagger-resources /openapi.json
② 中间件     Authorization 头名 + 前缀极端值 十秒探针
③ 登录面     枚举 / SQLi / 弱口令（此时才轮到，且 10-20 发封顶）
④ 泄露面     持票人 / 内网服务 / 配置里的第三方 key
```

**为什么这个顺序**：本案 `/admin/login` 对 `admin'--`、`or 1=1`、12 个弱口令**全阴性**并带 AES 参数加密，
但中间件一枪就穿。先爆破 = 白烧配额 + 触发锁定 + 留痕 + 可能封 IP，回报却是零。

---

## 二、★ 前缀校验缺失：`Authorization: Bearer <任意值>`

### 判据现场（2026-10 奥恩 Spring Boot）
```text
GET /account/list                            → 401 {"code":401,"message":"token认证失败","success":false,"total":0}
GET /account/list   Authorization: Bearer x  → 200 {"success":true,"code":200,"data":[{"id":1,...}]}
```
中间件等价于 `if (!auth.startsWith("Bearer ")) return 401;` ——
之后的解析、验签、Redis 比对、过期与吊销检查**全部缺失**。
`Bearer null` / `Bearer 1` / `Bearer x` 一律 200。

### 十秒探针（复制即用）
```bash
# 1) 头名定位：只有正确头名才会让错误文案发生变化
for h in Authorization token X-Token X-Auth-Token satoken access_token navboxauth jwt sid; do
  printf '%-14s ' "$h"
  curl -s -H "$h: 1" http://T/api/account/list | head -c 70; echo
done

# 2) 前缀极端值：很多实现把字符串 "null"/"undefined" 当成合法非空串
for v in x 1 0 null undefined true admin "Bearer null" "Bearer 0"; do
  printf '%s  ' "$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $v" http://T/api/account/list)"
  echo "Bearer $v"
done
```

### 读结果
| 现象 | 结论 |
|---|---|
| 任何 `Bearer <非 JWT>` 返回 200 | **前缀校验缺失 = 超管等价权限** ⇒ 立刻停爆破，转全量 dump |
| 只有 `Bearer ` 前缀生效、裸值无效 | 确实在读前缀 ⇒ 别改头名，改值 |
| 换头名后文案变了（如 `token已过期`） | 头名对了 ⇒ 该头名 + 伪造/泄露值继续 |
| 所有头名同一句 `token认证失败` | 可能头名不在候选里 ⇒ 从 SPA bundle 抄 axios 调用点 |

### 同类变体（顺带一起测，成本近乎零）
- **X-Forwarded-For / X-Real-IP 白名单**：`127.0.0.1`、`localhost`、内网段
- **过滤器路径白名单过宽**：`/api/admin/../admin/list`、`;.js`、`%2e%2e/`、大小写、末尾 `/`
- **空值当通过**：`Authorization: Bearer`（无值）、`Bearer `（仅空格）

---

## 三、Spring Boot / Knife4j 文档面（常与 401 并存且免鉴权）

| URL | 说明 |
|---|---|
| `GET /doc.html` | Knife4j UI；200 + 60KB 级 = 完全敞开 |
| `GET /v2/api-docs` | Swagger2 全量 JSON（本案 76KB / 89 接口） |
| `GET /swagger-resources` | 分组列表（拿去换 group 逐个拉） |
| `GET /v3/api-docs` | Springdoc 变体；`/v3/api-docs/swagger-config` 列全组 |

拿到 `/v2/api-docs` 后三件事，**比逐条 fuzz 快一个数量级**：
```bash
jq -r '.paths|keys[]' navapi.json                    # 全路由
jq -r '.definitions|keys[]' navapi.json              # 请求体字段名：建号/改密不用猜
jq -r '.paths|to_entries[]|"\(.key) \(.value[].summary)"' navapi.json   # 中文注释直接读出业务
```
`summary` 里的中文往往把业务全招了（本案读出「**劫持默认设置**」「批量生成账号」「商户域名批量添加」——
直接把平台定性从「分发」改成「流量劫持」）。

`definitions` 里的 `*VO` 字段 + 注释就是完整请求契约：
`{"account":"账号","accountKey":"登录唯一key","hackRate":"劫持比例","status":"0:启用 1:禁用"}`。

---

## 四、接管后的 dump 优先级

按价值排，前面先拿：
1. `/config/list`、`/config/getJson` —— **内网服务地址**（`http://10.x/ck.php?url=`）、第三方 key、各种 switch
2. `/account/list` —— 管理员账号（bcrypt）+ `accountKey`（常是明文登录 key，可直接复用）
3. **`/xxx/export`** —— 导出类常免鉴权且一次吐全量（本案 `/code/export` 直接给出 21 条在用劫持域名）
4. `/xxx/page?page=1&limit=500` —— 翻完所有页，**用 `total` 对账**，去重后再报数
5. `/xxx/count` —— 先拿数字定量，再决定拉多少

**对账纪律**：`total` 是硬断言。`page` 翻到空页、去重后条数与 `total` 不一致时，
必须在报告里写明差额（本案 2174 → 去重 2163，11 条重复要写出来，不能直接报 2163）。

---

## 五、写权限取证纪律（别把验证做成破坏）

- 只在**新增**方向验证（`/xxx/add`），不 update / delete 既有记录
- 建号后立刻 `/xxx/list` 读回自证：**新 id 出现在列表里才算数**，接口回 `success:true` 不算
- 报告明写「新增 1 条用于验证，未修改 / 删除任何既有数据、未停任何服务」
- **不要**为了证明能写就去改劫持比例、改别人密码、冻结客户 —— 建号已是等价证据

---

## 六、怎么摸到这个后端（源站侧）

后端常不在主域后面，而是 **裸 IP + 非标端口**。

- 从任一 CDN 外的子域（超级签 / 分发 / 上传 / 签名平台）解析真实 IP → 全端口扫 →
  找非常规端口上的 Java 响应包。**`{"code":401,"message":"token认证失败"}` 就是它。**
  ⚠ 别凭端口猜产品：本案 9000 端口我先当成 MinIO，一打才发现是 Spring Boot
- nginx 源站用 **403 vs 404 判别 `location` 规则**：403 = 该前缀未放行，404 = 放行但无此路径。
  只放行 `/clientapi/` `/mapi/` 的源站，扫一级目录就能把路由表列全
- Host 头不对时那台机器会吐**伪造的 Cloudflare 530 页**（4KB 级 CF 模板）⇒ 别当真 CF。
  换已知能命中的 vhost 做 canary（本案 `/clientapi/app/getinfo?appid=5piupt` 命中 997B 才算真源站）

详法走 `cdn-origin-tracing` / `origin-ip-discovery`。

---

## 七、红线

- 拿到超管等价权限后**先只读**，把数据面全摸清再考虑写
- 写验证一律「新增」，绝不改既有配置/账号/业务数据
- 配置里挖到的内网地址（`10.x` / `103.x` / `38.x`）只记录不主动打，除非在范围内
- `params_aes_switch=1` 的站点：正常登录要前端 AES 加密参数，别把「登录失败」当结论，已绕过就不必再攻

---

## 支持文件

| 文件 | 内容 |
|---|---|
| `references/aofen-spring-boot-bearer-bypass.md` | 奥恩劫持平台完整实录：Bearer 绕过报文、89 接口全表、9 账号 / 2174 卡密 / 101 商户域、写权限取证、源站发现路径 |
