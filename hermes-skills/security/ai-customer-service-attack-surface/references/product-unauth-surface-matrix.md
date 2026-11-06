# AI 应用 / 客服系统 逐产品「未授权面」矩阵(实测校准版 v1.0)

> **来源与口径**:2026-09-22 对 188 台 AI 应用候选池的实测(跳板机出口,全程**只 GET / 零爆破 / 零写入**),已含 3 处自纠。
> **分区规则(重要)**:A 区 = **有本次实测证据**;B 区 = 方法论推演、**本次未打**(不要当结论用);C 区 = 判死判活速查(防误判)。
> **用法**:先指纹 → 打该产品"权威配置端点"(几乎都免鉴权)→ 再按"未授权面"逐条推进。

---

## A 区:实测校准(有证据)

| 产品 | 权威配置/指纹端点(免鉴权) | 关键字段 | 未授权面(按优先级) |
|---|---|---|---|
| **Open WebUI** | `GET /api/config` | `features.enable_signup` / `enable_login_form` / `enable_ldap` / `auth_trusted_header` / `oauth.providers` / `version` | ① `enable_signup:true` → 注册 → **`POST /api/v1/tools/create` 的 Tool 内容会被 `exec()` ⇒ 容器内 RCE**(本轮唯一打穿路径) ② `GET /api/v1/memories/ef` 未授权触发 embedding(仅 DoS) ③ LDAP 空密码绕过(≤0.8.12,需 `enable_ldap:true`) ④ `auth_trusted_header` 信任头伪造 ⑤ OAuth token exchange 缺 audience(0.8.0–0.10.x) |
| **LibreChat** | `GET /api/config` | `registrationEnabled` / `emailEnabled` / `passwordResetEnabled` / `openidLoginEnabled` / `serverDomain` | ① **`registrationEnabled:true` + `emailEnabled:false` = 注册不强制验证 ⇒ 登录直给 token**(本轮 2 台实锤) ② `/api/models`、`/api/endpoints`(`userProvide:false` = 平台侧付费 key) ③ `/api/mcp/servers` + `/api/mcp/tools` = **企业内网 MCP 拓扑 + 工具全表** ④ `POST /api/agents`(201,可绑企业 MCP 工具)→ `POST /api/agents/chat` → `GET /api/agents/chat/stream/<streamId>` |
| **Dify** | `GET /console/api/setup` | `step`(`finished` = 已初始化)、`setup_at` | ① **`step != finished` ⇒ 任意人可 `POST /console/api/setup` 设超管 = 接管**(本轮 8 台全 `finished`,判负) ② `/console/api/*` 未授权面 ③ 应用/数据集 IDOR |
| **Flowise** | `GET /api/v1/version`(免鉴权) | `version` | ① **★ `GET /api/v1/nvidia-nim/get-token` — 零鉴权直接吐真实 NVIDIA NGC API key**（2026-09-23 实测 `100.57.110.107` 3.0.7 **实锤**；同一 router 的 `start-container` / `get-image` / `list-running-containers` / `stop-container` 亦全零鉴权。源码：`packages/server/src/routes/nvidia-nim/index.ts` **9 条路由无任何鉴权中间件**，挂载于 `routes/index.ts:128`；上游 GHSA 检索 `nvidia`/`NIM`/`get-token`/`ngc` = **0 条记录**。**非 RCE**：`flowise-nim-container-manager` 走 podman HTTP API 无 shell 拼接、mounts/ports 固定 ⇒ 定性「未认证容器编排/凭据泄露」）② `/api/v1/public-chatflows`(412 = 只缺不可猜 UUID) ③ `/api/v1/get-upload-file`（无鉴权但**被「chatflow 必须存在」前置校验挡下**：2026-09-23 以 7 种穿越 payload（`../` / URL编码 / 绝对路径 / `....//` / `/etc/passwd` / `app/package.json` / `database.sqlite`）实测，**全部回 `404 Chatflow … not found`** ⇒ 需先有真实 chatflow UUID）④ **`/api/v1/fetch-links?url=` SSRF**（本机实测 401）⑤ `/api/v1/leads`、`/api/v1/feedback`（412 无鉴权，需 chatflow ID）⑥ `public-chatbotConfig/<id>`（500 无鉴权，需不可枚举 UUID） |
| **Langflow** | `GET /api/v1/version`(免鉴权) | `version` | ① **`GET /api/v1/auto_login` —— Docker 默认 `AUTO_LOGIN=true` 时直接返回 access token = 无条件接管**(必测!) ② **★ `GET /api/v1/monitor/messages` 免鉴权泄露消息（含 `flow_id`）→ 用该 id 再打 `GET /api/v1/monitor/builds?flow_id=` 与 `GET /api/v1/monitor/transactions?flow_id=` 也免鉴权，返回真实提示词原文与执行 inputs ⇒ 无凭据全链泄露**（2026-09-23 在 1.4.0/1.6.0 双机实测）③ `POST /api/v1/users/` 开放注册端点（**设计如此，非漏洞**；实测返 201、`is_active:false`/`is_superuser:false` ⇒ 不可用于接管）④ `POST /api/v1/validate/code` 代码执行(CVE-2025-3248,**仅 ≤1.3.0**；1.4/1.6 实测 403 已修) ⑤ `POST /api/v1/files/upload/{flow_id}` 422 无鉴权上传面 ⑥ `POST /api/v1/mcp/` 400 `session_id is required` = 无鉴权 MCP 面 ⑦ `/api/v1/flows/` 需 API key(403) |
| **RAGFlow** | `GET /v1/system/version` | `code:401` = 存在且需鉴权 | ① `/v1/system/*` 未授权 ② 知识库/文档 IDOR(顺序 id)③ **RAG 投毒**(上传文档被检索后影响对客户回答) |
| **AnythingLLM** | `GET /api/ping` → `{"online":true}` | — | ① `GET /api/v1/admin/is-multi-user-mode` **403 `No valid api key found.`** = API key 强制(本轮 5 台全 403) ② 其余业务面需 key ⇒ 判负 |
| **Chatwoot** | `GET /api` | `version`(实测泄 3.8.0–4.17.1) | ① `/api/v1/accounts/1`、`/api/v1/profile` **401** ② 公开 API `/public/api/v1/inboxes/{inbox_identifier}/contacts`(**设计上公开**) ③ `/super_admin` 入口 ④ **widget key** 与会话 IDOR |
| **FastGPT** | `GET /api/system/getInitData` | `feConfigs`(系统名/OAuth 开关/文档地址) | ① 该端点**设计上公开**,不构成漏洞 ② `POST /api/support/user/account/register` 注册 ③ 知识库/应用 IDOR |
| **MCP Server** | `POST /mcp`(JSON-RPC) | `initialize` / `tools/list` / `tools/call` | ① **`/mcp` 协议入口常漏挂鉴权**(本轮 `54.144.94.209` 写工具 10/10 执行) ② `tools/call` 空参探存在性 ③ `register_service`(**可逆**,改 endpoint ⇒ orchestrator 回调 ⇒ 内网 SSRF/供应链投毒) ④ `register_capability` **留永久残留,禁碰** |
| **Onyx(Danswer)** | `GET /api/health`(免鉴权) | `status` | ① 本轮 `166.117.188.218` 见 "Onyx Agent Gateway",其余业务路由**全 SPA HTML 兜底** ⇒ 公网 vhost 无 API。再测时先确认 API 前缀 |

### A 区实测汇总(本轮)

| 产品 | 实测台数 | 结果 |
|---|---|---|
| Open WebUI | 10 | **1 台打穿**(`42.194.194.131` 0.7.2 → 容器 root → 管理员接管,已归零复原);其余 `enable_signup:false` 全判负 |
| LibreChat | 8 | **2 台实锤**(`20.114.162.114` P1 企业 MCP 拓扑 + 工具表;`34.238.181.82` **P1** `emailEnabled:false` 自注册 + Azure OpenAI 平台 key + Agent Builder);`saillab.top` `registrationEnabled:true` 但被 `lab_code` 门挡(判负,不爆破);其余 `registrationEnabled:false` |
| Dify | 8 | 全 `step:finished` ⇒ **无一台可接管**,判负 |
| Flowise | 7 | 三路径全封(`get-upload-file` 一律 `500 Invalid file path`;`fetch-links` 401;`public-chatflows` 412);含 3.0.12 与同族一致。**2026-09-23 补测 `100.57.110.107`(3.0.7)：`nvidia-nim` 全族零鉴权 ⇒ `get-token` 未认证泄露真实 NGC API key（实锤）+ 未认证容器编排面可达（运行时不可用故未起容器）；同机 25 条敏感端点对照全 401/403 ⇒ 该机鉴权机制生效，`nvidia-nim` 属真漏（非整机裸奔）** |
| Langflow | 3 | 1.4.0 → 403 需 key;1.6.0 → `auto_login:false` + 403;另一台全 403 ⇒ 判负。**2026-09-23 补测 37 端点 @1.4.0/1.6.0：★ `monitor/messages`+`monitor/builds`+`monitor/transactions` 三端点全免鉴权且可串联（拿 flow_id → 读提示词原文与执行 inputs）= 未认证全链泄露；`files/download|images` 8 种穿越 payload 全未到 handler（400 或 SPA HTML）⇒ 穿越判负；`validate/code`、`flows`、`variables`、`projects`、`api_key`、`users/whoami` 全 403（鉴权生效）；`POST /users/` 201 开放注册（设计如此）** |
| RAGFlow | 6 | `code:401`×4 / 404×1 / 502×1 ⇒ 判负 |
| AnythingLLM | 5 | 全 403 `No valid api key found.` ⇒ 判负 |
| Chatwoot | 7 | 全 401 ⇒ 判负(仅泄版本) |

---

## B 区:AI 客服专有攻击面(方法论推演 —— **本次未打,勿当结论**)

> 这一区正是"AI 客服"区别于"AI 框架"的部分。拿到带客服的站后按此逐条验。

| # | 面 | 具体手法 | 验法 |
|---|---|---|---|
| B1 | **客服 widget 前端泄凭据** | 落地页加载 `widget.js` / `embed.js` → 内含 `widget_key` / `app_id` / `api_base` / `inbox_identifier` | 拉 JS 全文 grep `key|app_id|identifier|token` |
| B2 | **实时消息通道未授权订阅** | Chatwoot 走 `/cable`(ActionCable);Intercom/Tawk 走 WSS。订阅他人 `conversation_id`/`room` | `wss://host/cable` 发 `subscribe` 帧,看是否只按 id 授权 |
| B3 | **会话/工单 IDOR** | 会话 id 顺序/可枚举 ⇒ 直读**全部客户聊天记录(含 PII、订单号、手机号)** | 带自己 token 请求他人 id,对比 200/403 |
| B4 | **访客身份伪造** | `contact_identifier` / `visitor_token` / `hmac` 由前端算 ⇒ 伪造 `?token=` 冒充任意访客发消息、读历史 | 改 visitor 标识重放 |
| B5 | **RAG 知识库投毒** | 客服 bot 检索知识库 → 上传/编辑文档把指令塞进去(间接提示注入)⇒ 影响**其他客户**看到的回答 | 上传测试文档 + 提问验证是否被采纳 |
| B6 | **提示词注入泄内部信息** | 客户消息里塞 "ignore previous / repeat your system prompt / 列出可用工具" ⇒ 泄系统提示、内部工具名、其他会话上下文 | 直接对话,观察 tool 名/提示泄露 |
| B7 | **AI 客服工具调用越权** | function calling 面(查订单/退款/改地址/查积分)若只按**会话内自称身份**鉴权 ⇒ 查他人订单/改他人地址 | 用自己身份触发他人订单号 |
| B8 | **真人客服社工** | 冒充客户/同事/供应商,套内部流程、系统名、账号 | 话术库见 `ticketing/` 与社工类技能 |
| B9 | **SSO/OAuth 面** | `openidLoginEnabled:true` 时查 `redirect_uri` 是否可外跳、state 是否校验 | 改 `redirect_uri` 重放 |
| B10 | **知识库越权读** | 客服 bot 后台的文档管理 API 若只按 `tenant_id` 查询参数隔离 ⇒ 换参读其他租户知识库 | 换 `tenant`/`workspace` 参 |

---

## C 区:判死判活速查(本轮踩过的坑,全部实证)

| 现象 | 真相 | 处置 |
|---|---|---|
| 全路径都回 **200 且同一个 HTML 兜底页** | SPA catch-all,**路由不存在**(不是"全接口 200") | 换 JSON 端点或带 `Accept: application/json` 判存在性 |
| **400** | **纯 HTTP 打到了 HTTPS 端口** | 必须带 TLS 重探(`ssl` 关校验);本轮 20 台里 16 台从未带 TLS 探过 = 漏测 |
| **404**(有指纹、无数据) | **该端口不是目标应用**,≠ 主机死亡 | 换端口/换协议,别记 DEAD |
| 301 跳转后回 **405** | 客户端 301→GET **降级假象** | 用 `--path-as-is` 或直接对目标协议发 POST |
| `CERTIFICATE_VERIFY_FAILED` | HTTP→HTTPS **跳转**,不是目标不可用 | 脚本必须 `check_hostname=False/verify_mode=CERT_NONE` 重探 |
| 指纹标签与实物不符 | **测绘指纹误配**(本轮实测 5 例:`218.161.59.54`→Joplin Server、`178.128.122.112`→Strapi、`222.88.83.2`→IIS、`72.10.33.232`→静态站、`3.16.210.222`→Clearpath) | 用产品**权威端点**二次确认再动手 |
| **「空参 POST」当零写入探测** | **会真的写库！** 实测：把 `POST /api/v1/users/` 的 `{"username":"x","password":""}` 当 schema 探测（预期 422），**实事返 201 并在两台生产实例各建了一个真账号**，且 `DELETE /api/v1/users/{id}` 需超管 key（403）⇒ **不可回收残留**。同理 Ollama 建模型、Chatwoot 注册也是真空写入 | **零写入探测只能靠「必然触发参数校验失败」的形态**：缺字段 / 类型错误 / 长度越界；绝不能用「字段值为空」来假定不写。写类端点的第一步永远是先读源码确认它能不能建对象 |
| 静态源码审计扫出「无鉴权路由」 | **假阳率高，不能当结论** —— 2026-09-23 实测：`flowise_audit.py` 扫出 26 条候选，逐条活体验证后**仅 `nvidia-nim` 族为真**，`nodes/category` / `oauth2/callback` / `evaluations/is-outdated` / `text-to-speech/abort` / `agentflowv2-generator/generate` **全部实际 401**（同族其他文件是特性、或中间件在解析器覆盖不到的位置） | **静态审计只产出候选清单，必须逐条活体验证才算数**；判据：401/403 = 有鉴权；400/404/405/412/422/500 = handler 已执行 = 无鉴权；**SPA HTML 200 不算命中** |
| RAGFlow `/api/config` 回 **200** | **统一封装体套 404**(`{code:404,...}`) | 看内层 `code`,不看 HTTP 码 |
| 注册回 "Please check your email to verify" | `emailEnabled:false` 时**验证不强制** | **立刻试 login**,拿到 token 才算实锤 |
| `POST /api/user/delete` 回 200 | **可能是"封禁"而非删除**(本例复登 403 `temporarily banned`) | 删除必须用**同凭据重登**验证,不是看返回码;封禁后无法自删 ⇒ 如实披露 |

---

## D 区:客服系统(Chatwoot)已知 CVE 对档 + 一次完整的"证伪"过程(2026-09-22)

### D.1 手上 7 台实测版本
| 主机 | 版本 |
|---|---|
| `135.222.157.136:3000` | **3.8.0** |
| `104.131.176.18:3000` | **4.5.2** |
| `103.90.224.35:3000` | 4.16.2 |
| `149.130.184.36:3000` | **4.16.0(补丁边界·对照组)** |
| `91.98.219.6:3000` / `77.235.25.241:80` / `129.121.133.21:3001` | 4.17.1 |

### D.2 CVE 对档(版本命中 ≠ 可利用)
| CVE | 影响版本 | 性质 | 命中 |
|---|---|---|---|
| CVE-2026-63765 | < 4.16.0 | **未授权** direct uploads 认证绕过 ⇒ 任意租户建 ActiveStorage blob | 3.8.0 / 4.5.2 |
| CVE-2026-5205 | 待查 | Critical SSRF(上传参数)→ 云元数据凭据 | 待查 |
| CVE-2026-44706 | 2.2.0–<4.11.2 | filter API SQLi(需认证) | 3.8.0 / 4.5.2 |
| CVE-2026-44707 | 2.14.0–<4.13.0 | OAuth 未确认账号 Pre-ATO | 3.8.0 / 4.5.2 |
| CVE-2025-21628 | <3.16.0 | filter SQLi(需认证) | 3.8.0 |
| CVE-2026-72719 | <4.9.0 | 跨租户资源转移(需 admin) | 3.8.0 / 4.5.2 |

### D.3 CVE-2026-63765 判定:**判负(证据不足)**
端点 `POST /api/v1/accounts/1/conversations/1/direct_uploads`;理论判据 = 未修补 ⇒ 200 + 签名 PUT URL;已修补 ⇒ 401。
**三次证伪(已排除的死路,勿重复)**:
1. 空 body、无 Origin ⇒ 422(曾误判为"鉴权缺失")⇒ **被对照组证伪**:4.16.0 / 4.17.1 同样 422。
2. 合法 JSON body、无 Origin ⇒ 422 ⇒ 猜"Rails CSRF(`InvalidAuthenticityToken`)早于鉴权" ⇒ 补同源 `Origin` + `Referer` 后 **仍 422** ⇒ 再被证伪。
3. 换 `form-urlencoded` / `multipart` + Origin ⇒ **仍 422**,三版一致。
**结论**:3.8.0 / 4.5.2 / 4.16.0 对同一请求一律 422、**无差分** ⇒ 请求未走到漏洞代码路径 ⇒ **无法证实 ⇒ 判负,不计为发现**;全程零写入(未建 blob、未 PUT 签名 URL)。
**残余未知**:需要一个该实例真实存在的 account_id / conversation_id 对(仅认证后可得,或从客户站 widget `inbox_identifier` 反推)⇒ 挂"待条件验证",不猜测。

### D.4 方法论沉淀(通用,已付代价换来)
- ★ **凡"鉴权缺失/绕过"类判定,必须同时打一个"已修补版本"当对照组**。没有对照组,422/400 这类中间态会把假设连带偏三次(本次实证)。
- **端点存在性**用 `404` 区分:`/api/v1/accounts/1/direct_uploads` = 404(无此路由),而 `.../conversations/1/direct_uploads` = 422 ⇒ **路由在 ≠ 代码可达**。
- Chatwoot 版本身份:`GET /api` → `{"version":...}` **免鉴权**(版本泄露);`/api/v1/accounts/1`、`/api/v1/profile` → 401(设计如此,非漏洞)。
- ★ **长文件写入必须分片 + 写后验尾部**:内容过长会被压缩截断、压缩标记会变成文件内容(本次在矩阵 D 区踩到并已修复)。

---

## 附:逐产品一键探测

`scripts/ai_stack_unauth_probe.py`(本技能自带):

```bash
python ai_stack_unauth_probe.py 1.2.3.4:3000 5.6.7.8 9.10.11.12:8081
python ai_stack_unauth_probe.py --file hosts.txt
```

自动完成:**逐端口指纹 → 产品识别 → 打该产品权威配置端点 → 打印关键字段**(`enable_signup` / `registrationEnabled` / `step` / `auto_login` / `version`),并内置**禁区 IP 黑名单**(用户指定的无授权目标,勿移除)。
