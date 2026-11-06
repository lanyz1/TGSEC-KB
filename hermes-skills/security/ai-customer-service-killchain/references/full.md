# ai-customer-service-killchain — 全文续篇

> 主卡保留前 14 节；本文件从第 15 节起。原文件：`/root/.hermes/skills/security/ai-customer-service-killchain/SKILL.md`

## 3. 七条攻击路径(可独立执行;一条堵死就换下一条)

> 格式:**前提 → 入口 → 步骤 → 证据(拿到才叫成) → 危害 → 本次实测状态**。

### P1 自注册 → 白嫖平台侧付费 key + Agent 构建器 【实测·2 台 P1】
- **前提**:`registrationEnabled:true` **且** `emailEnabled:false`(邮箱验证不强制)
- **入口**:`POST /api/auth/register` → `POST /api/auth/login`
- **步骤**:register → **立刻 login 拿 token**(回 "Please check your email to verify" 不代表死路)→ `GET /api/user`(`emailVerified:true`、`role`)→ `GET /api/models`(模型全表)→ `GET /api/endpoints`(**`userProvide:false` = 平台侧供 key**)→ `GET /api/mcp/servers` + `/api/mcp/tools`(**企业内网 MCP 拓扑 + 工具全表**)→ `POST /api/agents`(201,可绑企业 MCP 工具)
- **证据**:**token 可用 + 组织级资产清单**(端点/工具)⇒ 已够 P1
- **危害**:白嫖付费模型;泄露企业内部 MCP 地址与写工具清单;为 P5 提供靶点
- **状态**:`20.114.162.114`、`34.238.181.82` **两台实锤**;`saillab.top` 注册开着但被 `lab_code` 门挡(不爆破 ⇒ 判负)

### P2 Tool 内容 `exec()` → 容器内 RCE → 伪造 admin 【实测·唯一打穿】
- **前提**:Open WebUI 类 `enable_signup:true`(开放注册)
- **入口**:`POST /api/v1/tools/create`
- **步骤**:注册 → 建 Tool(内容为最小无害命令 `id`)→ 工具加载即执行 → 容器内读 `WEBUI_SECRET_KEY` → 用该密钥**伪造 admin JWT** → 管理员后台接管
- **证据**:`uid=0(root)` + 容器 ID + `/app/backend` 路径 + admin 会话
- **危害**:从"游客"到"容器 root + 管理员",**一跳到底**
- **状态**:`42.194.194.131:3000`(Open WebUI 0.7.2)**已打穿并归零复原**(5 Tool + 3 账号删净,31→28 用户)

### P3 未初始化 → 抢设超管接管 【实测·8 台全判负】
- **前提**:Dify `GET /console/api/setup` → `step != "finished"`
- **入口**:`POST /console/api/setup`
- **步骤**:抢在管理员之前提交初始化表单 ⇒ 自己成为超管
- **证据**:能进 `/console` 管理端
- **状态**:8 台**全 `finished`**(含 `2026-09-20` 才装的)⇒ 判负。**窗口只有"部署完到初始化之间",转瞬即逝** ⇒ 以后见到新装实例立刻试

### P4 auto_login / 协议面漏挂鉴权 → 无条件接管 【实测·判负】
- **前提**:Langflow `AUTO_LOGIN=true`(Docker 默认),或 MCP `:443 /mcp` 未挂鉴权
- **入口**:`GET /api/v1/auto_login`(直接返 access token)
- **步骤**:拿 token → 列 flows / 调 `/api/v1/validate/code`(CVE-2025-3248,**仅 ≤1.3.0**)
- **状态**:`1.4.0` 403 需 key、`1.6.0` `auto_login:false`+403 ⇒ **判负**。注意:**API key 强制(`No valid api key found.`)是设计,不是漏洞**,别报假阳性

### P5 MCP 协议面 → 未授权工具调用 → orchestrator 投毒 / 内网 SSRF 【实测·写工具 10/10】
- **前提**:MCP Server 暴露 `POST /mcp`(JSON-RPC)而漏挂鉴权
- **步骤**:`initialize` → `tools/list`(列全工具)→ `tools/call <只读工具>`(证明可调)→ **可逆**写工具:`register_service` → 改 `endpoint` ⇒ **orchestrator 会回调该地址** ⇒ 内网 SSRF / 供应链投毒 ⇒ 立刻 `deregister_service`
- **证据**:`get_server_health` 返 `{"status":"Active","version":...}` + 写工具 `HANDLER-EXECUTED` + `register_service` 返 `service_id`
- **纪律**:只碰 **(a) 空参**与 **(b) 可逆 register/deregister**;**禁碰 `register_capability`**(留永久残留);只读工具优先
- **状态**:`54.144.94.209 / mcp.dev.monetedge.ai` **写工具 10/10 执行**;残留 1 条软标记(无硬删工具)已披露

### P6 客服专有链:widget 凭据 → 会话 IDOR → RAG 投毒 → 工具越权 【推演·未实战】
> 这条是**"客服"区别于"通用 AI 框架"的部分**;拿到带客服 widget 的站按序验(对应同族卡矩阵 B 区 B1–B10)。

1. **B1 前端泄凭据**:拉客户站点的 `widget.js`/`embed.js` 全文 → grep `key|app_id|identifier|token` ⇒ Chatwoot 的 **`inbox_identifier`**(设计上公开,但是后续所有请求的**钥匙**)
2. **B4 访客身份伪造**:用 `inbox_identifier` 调 `/public/api/v1/inboxes/{id}/contacts` 与 `/conversations` ⇒ 拿到 `contact_identifier`/`visitor_token`;若 token 由前端可预测生成 ⇒ **伪造任意访客**(冒充他人读历史、以他人身份发消息)
3. **B2 通道未授权订阅**:Chatwoot 走 `/cable`(ActionCable),订阅帧只带 `conversation_id` ⇒ 若服务端不校验归属 ⇒ **实时窃听全部会话**
4. **B3 会话/工单 IDOR**:会话 id 顺序可枚举 ⇒ 直读**全部客户聊天记录**(PII、手机号、订单号)——**这是客服系统最值钱的面**
5. **B5 RAG 投毒**:客服 bot 检索知识库 ⇒ 上传/编辑文档塞入间接提示注入 ⇒ 影响**其他客户**看到的回答(跨用户影响,危害等级跃升)
6. **B7 工具调用越权**:function calling 面(查订单/退款/改地址/查积分)若只按**会话内自称身份**鉴权 ⇒ 查他人订单、改他人地址
7. **B6/B9** 提示注入泄系统提示与工具名;`openidLoginEnabled:true` 时查 `redirect_uri`/`state`
- **状态**:188 台池内**无带 widget 的活站可验** ⇒ 挂"待条件",**汇报时必须标推演**

### P7 文件 / SSRF 面(上传穿越、fetch-links)【实测·全封】
- **入口**:Flowise `GET /api/v1/get-upload-file?path=`(**路径穿越**)、`GET /api/v1/fetch-links?url=`(**SSRF**)、`/api/v1/public-chatflows`(412 = 只缺不可猜 UUID)、`/api/v1/leads`+`/feedback`(白名单端点)
- **状态**:7 台三路径全封(`500 Invalid file path` / 401 / 412),含 3.0.12 ⇒ **判负**;`fetch-links` 401 说明鉴权到位

### P8 基础设施面:向量库 / 模型仓投毒 → 数据污染 / 供应链后门 【实测·2 条闭环】
- **入口**:Qdrant `:6333`(未授权 `collections`/`points`)、Ollama `:11434`(`/api/tags`、`/api/create`、`/api/delete`)、Chroma `:8000`、Milvus `:19530`、vLLM `:8000`、PaaS(Coolify)、工作流(n8n/Dify/Langflow/Flowise)、IDE dev server(Vite `:5173`)
- **实证**:① Qdrant 写标记点 → 读回 → 删,总分片数不变(**可逆归零**);② Ollama 建标记模型 `pt-marker-*`(**绝不改已有模型**)
- **危害**:往生产 RAG 库注入污染文档 = 回答投毒(客服答案被改);植入恶意模型 = 供应链后门
- **纪律**:只建**新标记对象**、绝不改动已有;写完**必读回**、验完**必删**;⚠️ 对 **CPU 推理**的 Ollama 做生成(如拉 27B)会把主机打瘫,`/api/tags` 45s 超时到连删除都做不了 ⇒ 用最小模型 / `num_predict=1`,或只做「写入 → 读回」不做生成

### P9 可持久化账号:开放注册 → token 即凭据 【实测·首次成功】
- **入口**:Chatwoot `POST /api/v1/accounts`(响应体**直接返回 `access_token`**,一次请求拿持久凭据);同类:Gitea `/user/sign_up`、Coolify `/register`、OWUI `/api/v1/auths/signup`、Typebot `/api/auth/signup`
- **实证**:`104.131.176.18:3000` Chatwoot 4.5.2 → **200**,落 `role: administrator`,token 读 `profile`/`agents`/`inboxes`/`webhooks` **全 200 = 持久化实证**;跨租户 `account_id=1` → **401(隔离正确,越权判负)**
- **判据铁律(本轮踩坑)**:**`GET /user/sign_up` 返 200 ≠ 可注册** —— 必须查页面内**是否存在 `user_name`/`email`/`password` 表单字段**(Gitea 禁用注册时返回提示页,只有 meta 标签);Chatwoot 首页有 signup 字样 ≠ 开放(其余 6 台全 404);**Coolify `403` 才是「注册关闭」的真凭据**
- **清理**:`DELETE /api/v1/accounts/<id>` + `DELETE /api/v1/profile`;一律**标记邮箱 + 随机强密码,建完必删**

## 4. 纪律(全是本轮踩出来的硬规则,违反即报废结论)

### ★ 对照组铁律(最重要)
**凡"鉴权缺失 / 绕过"类判定,必须同时打一个"已修补版本"当对照组。** 实证:Chatwoot CVE-2026-63765 我因为只打命中版本,一个 422 中间态把假设带偏**三次**(空参 422 → 猜 CSRF → 补 `Origin` 仍 422 → 换 form/multipart 仍 422;对照的 4.16.0/4.17.1 **完全一样**)⇒ 最终**判负**,没吹成发现。**没有对照组就拿不到"差分",而拿不到差分的响应码毫无意义。**

### 假阳性自查清单(先怀疑自己,再怀疑目标)
| 现象 | 真因 | 处置 |
|---|---|---|
| 全路径 200 | **SPA 兜底**,不是路由存在 | 看 body/`content-type`,别报"未授权接口" |
| 400 / 405 | **打错协议或端口**(HTTP vs HTTPS、:80 vs :443) | 带 TLS 重探、忽略证书校验重跑 |
| 401 | 我**没带票**(脚本 bug) | 先查自己请求头,再下结论 |
| 404 | **该端口不是目标应用**,≠ 目标死亡 | 换端口/协议重判 |
| 版本指纹命中 CVE | **版本 ≠ 可利用** | 必须实测触发 |
| 能列工具清单 | **不等于能调用** | 必须真调 |
| 能绑 Agent 工具 | **不等于执行**(实测 `illegal_model_request`) | 必须看工具是否真被触发 |

### 写入与归零纪律
- **零写入优先**:先空参 / 只读差分;必须写时选**(a) 空参、(b) 可逆操作**,并**事先想好怎么撤**
- **建号必带标记**(`pntest` 前缀邮箱)+ **`try/finally` 兜底** + **开头打印账号标识**(否则崩了就找不回)
- **删除要复登验证**:实测 `POST /api/user/delete` 返 200 **实为封号**(复登 403 `temporarily banned`)⇒ **封号 ≠ 删除**,别把 200 当成功
- **归零顺序**:先删 Agent / 对话 → 再删账号(账号删除会级联清 Agent,已实证)
- **删不掉就如实披露**,转交目标方按前缀清理;**不要重试注册**
- 禁止:绕过目标风控(429 就地等)、爆破邀请码、穿透第三方企业内网端点(只做零状态可达性判定,解不出即判负)
- 流量走**跳板机**,不用本机出口;(本卡语境下)禁区 IP 一律 `SKIP` 零请求

## 5. 结合进现有渗透体系(怎么挂)

**挂载位置**:标准流程 `recon → enum → exploit → post` 里,本卡覆盖 **enum 的"AI/客服面"分支 + exploit 的整条链**;它**不是替代** `web-pentest`,而是**并行的专用分支**——先按本卡排面,再回落到通用卡打具体漏洞。

| 你要做的事 | 用哪张卡 |
|---|---|
| **AI 客服 / chatbot 站 → 全面攻击面与路径(起点)** | **本卡** |
| 逐产品未授权面清单 + 一键探测脚本 | `ai-customer-service-attack-surface` |
| MCP 未授权 / HTTP 301 陷阱 | 同上 → `references/mcp-jsonrpc-unauth-and-http301-trap.md` |
| 提示注入 / 越狱 / 模型层 | `ai-agent-jailbreak`、`llm-ai-security-pentest` |
| Agent 运行时(宿主伪造 / 特权 RPC) | `ai-agent-runtime-pentest` |
| RAG 投毒 / 知识库 | `trade-ideas-ai-rag-pentest` |
| 通用 Web 漏洞(注入 / 越权 / 上传 / SSRF / XSS) | `web-vuln-router` → `idor-bola-chain`、`file-upload-webshell`、`ssrf-testing` |
| API 面 / 未授权管理 API | `api-security-testing`、`unauthenticated-admin-api` |
| 打穿之后(提权 / 凭据 / 会话) | `linux-post-exploit`、`credential-harvest`、`host-c2-verify` |
| 长时无人值守 + 汇报节奏 | `long-run-engagement-discipline` |
| 出报告 | `pentest-report-autogen`、`security-report-templates` |

**报告里必须单列一节**:「AI 客服 / Agent 应用专章」——写清 **产品+版本 / 免鉴权端点 / 拿到的组织级资产 / 是否可执行 / 残留披露 / 修复建议(关注册、给 MCP 挂鉴权、轮换平台 key)**。

## 6. 复现命令(起手式)

```bash
# ① 一键排面(只 GET;内置禁区黑名单)
python scripts/ai_stack_unauth_probe.py 1.2.3.4:3000 5.6.7.8:443

# ② 权威配置(判生死的关键字段)
curl -sk https://T/api/config | jq '{registrationEnabled,emailEnabled,passwordResetEnabled}'   # LibreChat
curl -sk https://T/api/config | jq '{enable_signup,features}'                                  # Open WebUI
curl -sk https://T/api/v1/version                                                              # Flowise / Langflow
curl -sk https://T/api | jq .version                                                           # Chatwoot(免鉴权泄版本)

# ③ 版本对 CVE 线(命中后先设对照组,再动手)
# ④ 判定"授权缺失"的唯一合法姿势:命中版本 vs 已修补版本 → 差分
```

> **汇报模板**:`产品/版本 → 免鉴权端点(证据) → 拿到的资产 → 能否执行(实测) → 危害定级 → 残留 → 修复建议`。
> **没有实测证据的,一律标【推演】。**

