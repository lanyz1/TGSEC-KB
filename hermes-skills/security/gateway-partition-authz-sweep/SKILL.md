---
name: gateway-partition-authz-sweep
description: "Use for /{gw}/{svc}/ microservice gateway authz sweeps."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
---
# 网关服务分区越权扫描（`/{gw}/{svc}/` 型微服务）

## 触发条件
- 路径形如 `/gtw/{ply,mer,sys,prv,dc,auth}/...` 或 `/api/{svc}/...`，一个网关后面挂多个微服务。
- 前端 Next.js/SPA，后端 Spring Boot（报错泄 `java.time.LocalDateTime` / `jakarta.validation` 即坐实）。
- **玩家/用户身份面已经打不动**（JWT 伪造被拒、改密/找回密码都 self-scope），但业务上有钱、有流水、有 KYC。

## 核心心法

> 同一个网关下，不同微服务的鉴权强度天差地别。
> **身份面做死的平台，读面（资金/流水/结算）往往整片塌陷。**

所以不要死磕「登录成他」。先回答一个问题：**哪个服务信任客户端传的 `usrnm` / `id`？**
找到它，战果就是「任意账号的金融身份 + 全部资金数据」，实战价值高于拿一个登录态。

## 五步流程

### 1. api-docs 全服务摸一遍（第一步，不是最后一步）

```
GET /{gw}/{svc}/v3/api-docs
```

逐服务试 `ply/mer/sys/prv/dc/auth`，常零鉴权。实测一次拿到 5 份、**1,255 个端点**，还顺带泄内网：
`prod-eai.<vendor>.local`、`10.74.x.x`、`<vendor>-gateway-service.default.svc.cluster.local`。

**服务名要接着字典往下打**，同一个命名空间常还有：

```
usr (用户/商户/股东管理)   job (调度)   aff (联盟商)   bethis
bo/api   img (对象存储代理)   auth   dc
```

实测扩到 **9 份文档、~1,450 端点**。但见 §6 的铁律：**文档里有 ≠ 路由挂着**。

auth 服务常 401 → 带你已有的 Bearer 再试一次。
**五份 JSON 先落盘**，后面所有必填项、枚举值、字段名都从这里查。

### 2. 差集 = 攻击面

```python
new = set(openapi["paths"]) - set(前端 chunk 抽出的端点)
```

实测 84（JS）vs 1255（文档）→ 差集里 38 个玩家作用域端点，**越权全在里面**。
前端没调过 = 没人测过 = 权限注解最容易漏。

优先级：命名含 `get-by-id` / `{id}` / `ls-page` / `balance` / `withdraw` / `trf` / `reset` 的。

### 3. schema 的 `required` 打败猜测

```python
def deref(doc, node, depth=0):
    if depth > 4 or not isinstance(node, dict): return node
    if "$ref" in node:
        cur = doc
        for k in node["$ref"].lstrip("#/").split("/"): cur = cur.get(k, {})
        return deref(doc, cur, depth+1)
    return node
```

只看 `required` 数组 + `properties` 字段名。别靠报错一个一个试，差十倍时间。
**重点：optional 字段往往是分支开关。** 实测某重置端点 `eml` 可选 —— 传了走「用户名+邮箱双匹配」分支，不传走「按用户名找 OTP」分支，两条完全不同的逻辑。

### 4. 服务层鉴权差分

| 服务角色 | 典型强度 | 表现 |
|---|---|---|
| `ply`（玩家面） | 硬 | 传 `usrnm`/`plyId` 被忽略；改密只认 token 用户 |
| `prv`（provider/EAI/资金面） | **塌** | 直接信任请求里的 `usrnm`；`get-by-id/{id}` 零归属校验 |
| `mer`（商户） | 部分裸 | `/mer/public/*` 明文无鉴权，泄管理员名与商户开关 |
| `sys` / `dc` | BO 专属 | 低权 token → `999970 Invalid oauth2 client id` |

**战术：拿最低权 token，只打 `prv`。打 `ply` 是浪费时间。**

### 5. 两种可复用越权形态

**A. 数字 ID 顺序枚举（IDOR）**

```http
GET /{gw}/prv/prtl/wlt-dpo-wd/get-by-id/390800
Authorization: Bearer <任意低权 token>
```

零归属校验 + 自增 ID。批量打一段区间，命中率本身就是证据：

```python
recs = []
for i in range(BASE, BASE+N):
    d = json.loads(call("/.../get-by-id/%d" % i, None, "GET", extra=AUTH)).get("data")
    if d: recs.append(d)
    time.sleep(0.2)
print("hit %d/%d players=%d amt=%.2f" % (len(recs), N, len({x.get("usrnm") for x in recs}), sum(float(x.get("amt") or 0) for x in recs)))
```

**B. `usrnm` 受信（BOLA）—— 对照实验判定**

```
?usrnm=<victim>  → total = 103252   ← 真实数据
?usrnm=<self>    → total = 0        ← 自己
```

总数不同 = 服务端信了参数（漏洞）；总数相同 = 参数被忽略（self-scope，换下一个）。
这比逐字段比对快得多，且能直接当报告里的一行铁证。

**C. 读即证写（安全且有力）**

`eai/trf/balance` 与 `eai/trf/withdraw` 共用同一 DTO、同一服务、同一鉴权路径。
**`balance` 返回 `suc:true` 就足以论证 `withdraw` 的 `usrnm` 同样受信**，不必真的动钱。
报告写明「读已实测、写未执行，避免真实资金损失」。

## 错误码字典（Spring Boot 网关族）

| code | 含义 | 处置 |
|---|---|---|
| `999999` | 泛化 Unknown Error（NPE） | **不是「端点死」**：前缀错 / method 错 / 缺必填字段 |
| `999984` | `Hitting error when converting JSON String to Object` | 明文体被拒 → **必须加密**（`x-e: TRUE` + 加密体） |
| `999970` | `Invalid oauth2 client id` | BO 专属端点，低权 token 无权，放弃或换 client |
| `20006` | `Your account access has changed. Please log in again.` | **token 已失效** → 重新取 token |
| `20007` | 账号锁定 | 失败计数到阈值，别再试 |
| `30021` | `Current password not matched` | 改密时 `crntPw` 对 token 用户，不看 `usrnm` |
| `30010` | `Player Not Found` | 用户名+邮箱配对不匹配 |
| `30015` | `Link not found/expired` | 重置链接 token 无效 |
| `170002` | `Member Otp Not Found` | 无 OTP 记录（未发码/已过期） |
| `20005` | 缺登录态 | 有路由，需任意有效 token |
| `20001` | `Incorrect Agent/Username/Password` | **用户存在、密码错** = 枚举 oracle |
| `500` | Spring Cloud Gateway 无路由（原生错误体带 `timestamp`/`requestId`） | **端点没挂**，不是鉴权问题 |
| `190026` | `Invalid Recaptcha Token` | Turnstile，须在受信域名内用真浏览器渲染 |
| `80038` | `phnNum Invalid Phone number` | 格式：`telCode=+60` + 11 开头 10 位 |
| `60003` | `Payment Provider Not Found` | 该商户没启用这条通道 |
| `40046`/`40048` | 商户开关未开 | SSRF 类功能被业务开关挡死 |
| `70067` | `Real name verification is required` | 提现前置 KYC 未做 |

## 6. ★ 文档全 ≠ 路由通 —— 500 是「网关没挂路由」，不是「鉴权失败」

文档聚合器会把**没有挂到网关上的内部服务**也一起吐出来：`/usr/**`、`/job/**` 直调全部
`500`，而 `/gtw/usr/v3/api-docs` 照样 200。

判别三连：

- `500` + Spring 原生错误体 → **网关无路由**，端点根本不存在于这张网关上
- `20005` → 有路由、缺登录态
- `999970` → 有路由、oauth2 client 不匹配（见 §7）

所以「文档里有」最多算 L1 情报。报告里写成「已发现但未挂路由」，别写成「已攻破/已排除」。

## 7. ★ 后台的 oauth2 client 写死在自己的前端 bundle 里 —— 这是换分区的钥匙

`999970 Invalid oauth2 client id` 不是终点，是提示你「去把那个 client 找出来」。管理端 SPA
主 bundle 里通常明写：

```js
username: "<vendor>-bo-app", password: "<32 位随机串>"
```

拿到它 → `Authorization: Basic base64(user:pass)` 打同一个 `/gtw/auth/oauth2/token`，人就进
**后台分区**了。同一个 client 通常生产/UAT 共用（UAT bundle 里是同一串）。

**半扇门（当探针用）**：只加 `Authorization: Basic <bo-client>` 而 **不带合法 BO token** 时，
错误码会从 `999970` 掍成 `20005` —— 说明 client 校验只认这层 Basic 头，真正的墙是 token
的 `aud`/client 类型。所以「999970 → 20005」= **你这个 Basic client 选对了**，剩下的就是拿
一个该 client 的 token（而这正好是密码/锁号/SSRF 要解决的那一段）。

反向：token 里塞 `client_id`/`clientId`/`aud`/`x-client-id` 这些 **header 都不管用**，
别浪费请求。

**UAT 是陷阱**：UAT 往往共用/克隆生产用户库（同一个 `admin` 在生产、UAT 响应一模一样，
连错误码都一样），所以 UAT 上的锁号会传导到生产。**UAT 不能当爆破靶场，只能当配置差异样本。**

拿到 BO client 后解锁的端点（文档里有、玩家 token 打不动）：

| 端点 | 能力 |
|---|---|
| `PUT /usr/mer/upd-usr-pw {usrnm,pw}` | **改任意用户密码，不要旧密码** = 账号接管原语 |
| `POST /usr/shd/crt` | 建股东/一级管理员，密码自填 |
| `POST /job/job-exc-cfg/crt {jobCfgId,jobPrm,jobCronExprs}` | RuoYi 式定时任务 → RCE 候选 |
| `POST /usr/public/two-fa-auth {username,password}` | 回 `twoFaQrCodeUrl`，URL 里 `secret=` 即 TOTP 种子（仅未完成绑定时） |

## 8. ★ `/gtw/img/` 图片代理常匿名可写 —— 双域存储型 XSS

网关下的图片/CDN 代理是对象存储直通，读写权限经常没配：

```bash
curl -X PUT https://<brand>/gtw/img/prod/x.html --data '<script>alert(1)</script>'
# 200，且 Content-Type 由请求头决定
```

**关键一步：同一个 key 要在两个域名各 GET 一次。** 实测同一路径在品牌主域和
`prod-backoffice.<vendor>` 上都能取到 `text/html` —— 等于在**后台自己的 origin** 上托管
任意 JS，可用来偷 BO 管理员的 `tk`/`rtk`。

列桶一般 `AccessDenied`（`?prefix=` 不转发），但精确 key 可读可写；key 穿越（`../`）被
CF + nginx 双重拦。

## 三大假阴性陷阱（会浪费你半天）

### 1. 自研客户端把 HTTP method 写死

```python
r = S.post(url, data=body)   # 坑：不管传什么 method 全走 POST
```

后果：所有 PUT 端点返回同一个 `999999`，你误判「端点不可用」。
**修法**：`S.request(method, url, ...)`；并用一个已知能通的端点做对照，先证明客户端本身没问题。

### 2. 改完自己密码后继续测

改密 → 旧 token 立刻失效 → 后续越权测试全返回 `20006`，看着像「越权被拦」，其实是假阴性。
**规则：每次越权测试前重新取 token；一个脚本最多一个写操作；写操作之后的结论全部作废重测。**

### 3. OTP 爆破的可行性门

爆之前先测三件事：位数、TTL、**失败锁号阈值 —— 且锁号是按端点算的，不是账号全局**。

实测同一账号：密码校验口 3 次错即 `20007` 永久锁；而 OTP 校验口（`ver-otp-fp` /
`ver-eml-fgt-pw-otp`）**连打 8 次错码完全不锁**，恒定回 `170002 Member Otp Not Found`，
账号状态不变。所以「会不会锁」每个端点单独测：同一账号连打 5–8 次错值，看错误码/状态是否变。

**真正的门是 TTL**：6 位 + 5 分钟 + 240rps → 单窗口 7.2 万次 ≈ **7% 命中率**，期望 14 个窗口
≈ 70 分钟且全程高密度轰 auth 口（必踩 WAF/监控）。**结论：数学上不划算，放弃并写进报告。**

配套两个 o 面事实：

- **发码口常免密**。`POST /prv/public/prtl/send-eml-otp {eml}` 只要邮箱、不要密码，即可给任意
  已注册邮箱种一条 OTP。真假邮箱同回 success（无枚举差异），但 `data` 返回的就是过期时间
  （实测 = now + 5min），可白嫖 TTL。
- **重发判定**。活码未消再发回 `170001 Member Otp Exists` —— 反过来可以当「该邮箱当前有没有活码」的 oracle。

## 作业纪律
- **格式探测一律用自建小号**，绝不对目标账号试密码（锁号会切断后续所有验证）。
- **爆之前先看「有没有找回密码」**：这类管理端经常只做了提示文案、路由根本没实现（i18n 有
  `Forgot Your Password`，`/forgot` 全 404），而错密 3 次 = 永久锁（状态变 `L`，无自动解锁）。
  猜错就是替客户把管理员账号废掉。这种面直接判「不可爆」并写进报告，不赌。
- **不真执行资金划转**：读即证写。
- 长脚本别 `| head -N`：SIGPIPE 会在落盘步骤前杀掉进程，证据全丢。写文件再 `tail`。
- 限速：240 req/s 可跑，498 req/s 触发 CDN Human Verification。被挑战后本机 IP 报废，改从干净出口跑。

## 报告口径
不要把「没拿到登录」写成失败。按这个模板收尾：

> 身份面与写面做死，读面（`prv`）塌陷 —— 战果在数据与资金，不在「登录成他」。

影响定级优先级：真实姓名+银行账号 IDOR > 全量流水/余额越权 > 资金划转 `usrnm` 受信 > api-docs 全量暴露 > 用户枚举。

## 本族已实测「硬」的面（别重复劳动）
- JWT：RS256 严格校验，`alg=none` / HS256+PEM 三种混淆全 401
- `get-profile` / `get-kyc-profile`：传 `usrnm` 被忽略
- `chg-pw`：`30021`，校验 token 用户
- `fgt-pw`（找回密码）：`usrnm`+`eml` 双匹配 + OTP + 锁号
- `qck-reg` 批量赋值：`eml`/`role`/`stsCode`/`id`/`plyId`/`merCode` 全丢弃（严格 DTO）
- `/feign/*` 服务间接口：403 Access Denied
- 读 OTP 的 `mbr-otp/ls-page`：低权 token → `999970`

## 参考
- `references/gateway-apidocs-authz-sweep.md` —— 完整实战记录：五份文档清单、IDOR 字段表、对照实验输出、复现脚本清单。
- `references/bo-plane-and-panel-client.md` —— 从 api-docs 的 `servers` 泄露挖到厂商 BO 面板、
  后台 client 提取、懒加载 chunk 里的真实登录时序、锁号策略实测、双域上传验证。
