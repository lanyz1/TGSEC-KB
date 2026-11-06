---
name: vendor-doc-default-credentials
description: "触发: 厂商公开 API 文档/Swagger/api/docs。先试文档示例凭据(运营方照抄默认值)。"
version: 1.0.0
license: MIT

---

# 厂商文档示例凭据 = 第一顺位默认口令

## When to Use

目标暴露出**它自己产品的接口文档**时立刻跑本技能:`/api/docs`、`/swagger`、`/api-json`、`/docs`、README、`.well-known/`、厂商官网的「API 文档」页。

**核心断言**:厂商写文档时会在示例里放 `your_client_id` / `YOUR_ACCESS_TOKEN` / 一串示例 key,并常在旁边标注「生产请勿使用」。**部署这套产品的运营方照抄文档是常态**——那句警告经常没人读。所以文档示例值不是「演示垃圾」,是**排序第一的默认口令候选**。

这是**测默认凭据**,不是爆破:一发请求,零风险,不需要字典。

## 实测战果(2026-09,某 WhatsApp 网关)

`GET /` 直接自报家门:

```json
{"status":200,"message":"Welcome to the Evolution API, it is working!","version":"2.3.7",...}
```

`/instance/fetchInstances` 无 key → **401**(说明路由存在、鉴权生效)。把**官方文档里的示例 `AUTHENTICATION_API_KEY` 值原样填进 `apikey` 头**:

```bash
curl -s https://<host>/instance/fetchInstances -H 'apikey: <文档示例值>'
# → 200，返回实例列表(id / name / connectionStatus / ownerJid / token)
```

**全局管理员到手。** 官方文档原文就写着:

> `AUTHENTICATION_API_KEY=<示例值>` … **Never use the example key above.**

运营方就是没读那句。这套产品本身还有 `/manager` 管理 SPA,未授权可达。

## 步骤

### 1. 找文档端点(先于任何路径字典)

```
/api/docs   /api/docs/   /docs   /swagger   /swagger-ui   /api-json
/api-docs  /openapi.json  /redoc  /robots.txt  /sitemap.xml  /.well-known/
```
`/robots.txt` 和 `/sitemap.xml` 也常把内部路由/后台路径一起列出来——**动字典之前先把这两条读了**。

### 2. 判读鉴权:401 与 404 是两个世界

| 响应 | 含义 | 动作 |
|---|---|---|
| `401` + 业务文案(`Invalid client_id or client_secret.`) | **路由存在,鉴权生效** | 去找凭据(本文档示例值 / 前端 JS / 租户 `.env` / 厂商站) |
| `404` + `{"status":"error","message":"Route not found."}`(约 47B) | **路由不存在** | 别在同一 host 继续枚举这条路由;先核对 base URL 与 vhost |
| `200` + 内容与全站 catch-all **字节数相同** | SPA 兜底页,不是命中 | 见 §5 基线法 |
| `405` | 路由存在但方法不对(如 GET 打了个只收 POST 的登录口) | 直接用对的 method 再打 |

### 3. 试文档示例值

把文档里出现的**每一个字面量**都当候选:示例 key、示例 `client_id/secret`、示例 token、示例账号密码、示例 `.env` 片段。⚠️ 试之前确认目标确实是**厂商自己的部署**(白标/二次分发),否则示例值无意义。

### 4. 栈指纹:决定还要不要继续投注入

先花一发确认后端栈,再决定投入方向:

- **JSON schema 严格校验**:对象/数组当字符串传 → `400/500 Invalid value` ≈ **Fastify(+Prisma)**。
- 这类栈是**参数化查询**:`client_id: "' OR 1=1-- "` 只会得到**普通 401**;NoSQL 类型混淆(`{"$ne":null}`)会被类型校验挡下。
- 结论:**立刻停止注入投入**,把时间全押在「找凭据」上。这是本技能最大的时间节省点。

### 5. 基线法:200/404 都可能骗你

批量扫路径前,先请求一个**保证不存在**的路径拿 catch-all 基线(记下字节数)。之后**只有长度不等于基线的响应才是候选命中**。同模板多租户站点对所有未知路径返回同一个 `index.html`,长度逐路径完全一致——不设基线就会刷出满屏假阳性(把「注册开着」这类结论建立在 catch-all 上)。

### 6. 文档 base URL ≠ 你打的这台

文档 head 常写上游厂商域(例:`https://node.<厂商域>`),而**实际 API 挂在你正打的这台机器上**。所以:

- 某条文档路由在你打的 host 返回 `Route not found` **不代表整条线断了**——可能只是这台只挂了部分路由(如只挂 `/api/auth/login` + `/api/docs`)。
- 反过来:文档里公开的 `clientCallbackUrl` 之类**由调用方指定**的参数,等于「服务端会主动发起请求」= **SSRF 面**。拿到凭据后优先看这类参数,它常是打进同机 `127.0.0.1` 内部服务的通道。

## 价值上限判定(重要:别把 PoV 当数据面)

拿到全局 key / 管理员后,**先看它到底能读到什么数据,再决定怎么汇报**:

- 网关类产品(WhatsApp 网关、消息队列、支付网关)的管理权限,价值**取决于实例状态**。
- 例:实例 `connectionStatus: close/connecting` 且 `ownerJid: null` = **从未配对成功** → 消息历史为空。
- 此时正确的定性是:**「未授权访问 PoV + 运营方运维卫生画像」,不是「已进入数据层」**。
- 但它同时是**极高价值的横向情报**:证明该运营方会用文档默认值 → 立刻把同一套默认值/同源字符串拿去横向试它其它资产(面板登录、邮件、SSH、上游网关)。

## Pitfalls

1. **别跳过文档直接上字典**。文档端点常在 `/api/docs` 明文摆着,读它比跑 5000 条字典便宜几个数量级。
2. **文档里的示例值要「原样」填**,不要自作聪明地规范化大小写/去掉连字符——默认凭据就是逐字节匹配。
3. **401 的文案要逐字读**:它常直接告诉你参数名(`client_id / client_secret`),省掉猜字段名的一轮。
4. **注入失败要认**:严格类型校验 + 参数化查询是「这条路本来就不通」,不是「payload 不够好」。继续加 payload 是纯浪费。
5. **不要把 catch-all 的 200 写成「端点存在」**。见 §5。
6. **不要用示例值去猜生产主站的登录口**(那是拿默认值撞真账号)。本技能限定在「厂商自己部署的那套产品」的 API 凭据面。

## 关联

| 技能 | 定位 |
|---|---|
| `middleware-unauth-family` | 中间件未授权家族(Nacos/XXL-JOB/Doris/etcd/Redis 等) |
| `api-security` | API 面测试方法论 |
| `site-recon-bypass` | 边界/源站测绘总纲(响应判读、同 IP 归组) |
| `card-shop-pentest` / `open-source-faka-pentest` | 卡密/发卡站(常带公开 API 文档与默认凭据) |

细节(逐条实测请求与响应报文)见 `references/evolution-api-doc-default-key.md`。


---

## 外部库增量（2026-10-11 分享包）

## ★ 升级路径:厂商**骨架/源码仓**比文档更肥(实测定型)

文档只给示例值;**厂商的 GitHub 骨架仓**能一次交出三件套,且都能直接落地为攻击面:

```
① 真路由表   → internal/adapter/handler/*_routes.go / cmd/api/main.go 的 Group("...") 注册
               ★ 用途:拿真路由去打目标(不要猜路径);含免认证探针(如 /api/v1/health)当判决式正控
② 种子凭据   → migrations/*_seed_*.up.sql  里的 bcrypt 哈希(离线破解,零请求)
               例:INSERT INTO admin_users VALUES('admin','$2a$10$...','super_admin') ⇒ 破出 admin/admin123
③ 部署默认值 → deployments/docker-compose.yml 的 ${DB_ROOT_PASSWORD:-root123456}
               configs/.env.example 的 JWT_SECRET=your_jwt_secret_change_in_production
               infrastructure/config/config.go 的 v.SetDefault("jwt.secret", "...")
               ★ **代码里的默认值最易被忽略、却最常生效**:容器/k8s 部署**常常根本不注入该 env** ⇒ 活体跑的就是代码默认值;
                 与「运营方照抄文档示例值」是同一类失误。三处默认值(代码 / env.example / compose)合并去重后一起当候选。
```

**种子哈希反推(bcrypt 也别放弃)** —— 默认口令的价值在于「好记」,不在于「抗爆破」,生成式生态词表几千条即可:

```python
import bcrypt, itertools
base = ['<产品名>', '<组织名>', 'admin', 'root', 'wallet', 'bot']   # 从源码/README/品牌词/证书 CN 抓
suf  = ['', '123', '1234', '12345', '123456', '888', '@123', '@2024', '@2025', '2026', '!', '@', '#']
for c in sorted({b + s for b, s in itertools.product(base, suf)}):
    if bcrypt.checkpw(c.encode(), target_hash.encode()): print('HIT', c); break
```

实测 **4,139 条候选命中出厂管理员口令**(零请求、成本≈0)。顺带一条省时间的判据:
`git log --oneline | wc -l` 只要 1 条(squash 过的仓)⇒ **无历史配置泄露可挖**,直接改从**迁移种子 + compose 默认值**两条线取,别在 git 历史上耗。

**同源判据(比字符串更像判据)**:比**错误码约定**。实测目标返回 `40701 登录状态无效`,骨架的契约文档写 `4xxxx` 家族 ⇒ 同血统;再叠 `/api/v1` + `/api/miniapp/v1` 命名空间 ⇒ 可判同源骨架。

★ **第二条同源判据 =「活体可读的配置值域」对 seed 值域(比错误码硬,且不依赖路由存在)**:
厂商 seed 迁移里的阈值/费率(如 `finance_min/max=10/500000`、年化率、PIN 试错锁定策略、提现自动审核门槛、链上确认数)
与**活体 UI 自己报出来的区间**(余额宝 10~500,000、年化 5%、限红 1~1000)对照 ⇒ **区间同、比例被后台改过 = 同源且活体是更新版**。
它同时修正一个关键读法:**拿骨架路由表打目标全 404 时有两种成因**,必须都验、别只取一种:
(a) **管理 API 在独立端口/服务上**(见下节);(b) **活体已升版、路由集合变了** —— 此时配置值域仍然同源。
取 (a) 就去找端口/命名空间,取 (b) 就改从**版本差分**入手;
拿一个读法下结论会把「活体新版本」误写成「骨架假设不成立」而丢掉整条出厂凭据线。
★ **实作栈不同不构成否证**:实测厂商开源版是 `Go/Gin + React`、客户站是 `Java/JFinal` —— 同一产品的两个分支。
**按产品契约比对**(默认凭据 / 管理 API 路径 / 参数名 / 错误码族),**不按框架指纹比对**;
因「框架指纹对不上」就丢掉开源版 = 白丢整条产品线的出厂口令。

### 先找「供应商在哪」——没文档、没镜像残留时走 TG 生态(零额外足迹)

产品型白标的供应商**不在 GitHub 上营销,在 TG 上卖**。固定链路:

```text
目标自己的客服号 / 官方 bot 菜单
  → 客服 bio、bot 菜单里的同族 bot（源码商铺、代搭建、兑币、群管）
  → 商铺频道 / 技术群历史消息（产品名、更新日志、演示站、报价）
  → 供应商 GitHub org + 产品仓库 → 白盒源码
```

Telethon **只读**(不进群、不发消息、不加好友),关键词过滤历史而不是拉全量:

```python
KEY = re.compile(r'钱包|后台|管理|源码|搭建|演示|授权|部署|服务器|主控|面板|成品', re.I)
for m in client.iter_messages(channel, limit=1500):
    if KEY.search(m.message or ''): print(m.id, (m.message or '')[:200])
```

- ★ **被引用的原帖是金矿**:商铺转帖常带 `t.me/<频道>/<id>` ⇒ `client.get_messages(entity, ids=[<id>])`
  精确读那一条(实测原始帖就是开源作者自述「我要 1:1 复刻 <产品>」+ 仓库地址)。
- ★ **bot 菜单就是生态拓扑图**:`/start` 返回的按钮 URL 指向同族其它 bot/服务,顺着走能到源码商铺。
- ⚠️ **落盘会崩在 markup**:`reply_markup` 里的对象含 `bytes`,`json.dump` 直接抛异常 ⇒
  一律 `json.dump(..., default=str)`(或先把 markup `str()` 化),否则整轮侦察白跑。

### 真路由表打全 404 时怎么读(重要)

拿真路由表打目标,结果 **`/api/v1/*` 全 `404 page not found`(含免认证的 `/api/v1/health`)** ⇒ **不要**判「骨架假设错」,正确读法:

- 骨架的 `configs/.env.example` 常把 **Admin API 写成独立服务**:`port: 8080` ⇒ **管理 API/面板不在 443/nginx 上**。
- 这也解释了为什么此前的**路径字典(974/772)、vhost 枚举(130)、信任 IP 头矩阵(54)全部落空**——打错端口/服务了。
- 于是剩余路径 = **拿 origin 内网可达性(SSRF / 同网段 / 内网跳板)**,此时上面三件套**立即变现**:`admin/admin123` 进后台、`root/root123456` 进 MySQL、默认 JWT 密钥伪造管理票。
- 纪律:骨架默认值**只在目标确为同源部署时才用**;对非同源站用示例值撞登录 = 违反本技能边界。
