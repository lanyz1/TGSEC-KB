# 漏洞类型测试清单（12 维威胁建模 + 探针矩阵）

> 对每个功能模块先过 12 维威胁建模，再按类型打探针。本文件是「思维框架 + 探针索引」；每类的深度细节见对应 `xxx-test.md`。
> 原则：不是扫漏洞模式，是理解代码意图后找到开发者的认知盲区。先差分后结论，状态码 200 不算漏洞。

## 12 维威胁建模（每个接口/模块过一遍）

| # | 维度 | 问什么 |
|---|------|--------|
| 1 | 数据流 | 这个输入进了哪条链路？终端是谁（DB/ES/文件/消息队列/第三方）？ |
| 2 | 权限边界 | 谁在什么角色下能调？鉴权在网关还是业务层？接口级还是数据级？ |
| 3 | 资源归属 | 返回的资源是谁的？id 是全局还是租户内？资源前面有没有 owner 检查？ |
| 4 | 状态变更 | 写操作改了哪些字段？状态机能不能跳步/回退/并发翻转？ |
| 5 | 客户端可控值 | body/query/header/cookie/path 里哪个值能影响服务端行为？ |
| 6 | 并发场景 | 券/库存/积分/余额/签到：有没有非原子操作？竞态窗口多大？ |
| 7 | 输出展示 | 回显点在哪个上下文（HTML/JS/JSONP/CSS/附件名/下载头）？ |
| 8 | 认证与会话 | 会话怎么签发/校验？能不能伪造/复用/不换绑？token 里有什么？ |
| 9 | 服务端请求 | 有没有 URL/回调/导入/预览/SSRF 面？出网策略如何？ |
| 10 | 注入面 | 参数进了哪类解释器？（SQL/NoSQL/模板/表达式/命令/XML/XPath） |
| 11 | 文件操作 | 上传/下载/解压/预览/导出：路径可控吗？内容被解释吗？ |
| 12 | 业务逻辑 | 流程可以乱序/重放/跳过校验吗？金额/数量/身份可篡改吗？ |

## 按价值排序的 6 大优先类

### 1. 越权 / IDOR（`idor-test.md`）
- **基线法**：本租户 total/条数 → 换 id/租户字段后差分
- **id 枚举**：邻号、回包 id、`0`/`-1`/空、UUID 可预测段、密文 id（找明文序号，用 JS 公钥自加密邻号，见 `打野短表`）
- **对象归属**：详情/附件/导出接口是否校验资源 owner
- **跨租户**：`appId`/`tenantId`/`orgId` 试 `0`/`-1`/空/他租户；哨兵租户
- **差分即证据**：总条数/他人字段变化才叫洞，200 ≠ 漏洞

### 2. 认证绕过 / 账号接管（`authbypass.md`）
- 未登录打业务接口（omit Cookie/无 token）
- 重置/改绑/换票链：验证码不绑号、重置换用户、回包带码
- JWT：alg 混淆、弱密钥、过期验证缺失、kid 注入（`oauth-jwt-test.md`）
- OAuth：redirect_uri 校验、state 缺失、code 复用（`oauth-jwt-test.md`）
- 发码接口：体验票/演示号/写死产品号 JWT（见 `打野短表`）

### 3. 注入（`injection-test.md` 按栈选探针）
| 栈 | 探针 | 差分判断 |
|----|------|---------|
| SQL | `'`、`1 AND 1=1` vs `1 AND 1=2`、时间盲注、报错类函数 | total/时间/报错内容差分 |
| NoSQL | `{"$ne":null}`、`{"$gt":""}`、`[$ne]=` | 返回条数变化 |
| ES | `{"query_string":{"query":"*"}}`、数组注入 | total 海量 |
| HQL/JPA | `' or '1'='1`、`${}` | 语义差分 |
| SpEL/OGNL | `${7*7}`、`T(java.lang.Runtime)` 回显 | 表达式求值回显 |
| SSTI | `{{7*7}}`、`${7*7}`、`<%=7*7%>` | 49 回显 |
| XXE | 带外 DNS/HTTP 检测（`xxe-test.md`） | 外带收到 |
| 命令 | `;id`、`|id`、`$(id)`、反引号 | 命令输出回显 |

### 4. SSRF（`ssrf-test.md`）
- 入口：URL/回调/webhook/import/preview/图片代理/PDF 生成
- 回环对照 → 内网探测 → 云元数据（169.254.169.254，各厂商路径差）
- 出网验证：DNSLOG / 自己的 VPS；先证明能出网再谈利用
- 走私/重定向绕过：`@`、编码、302 跳转、DNS rebinding（`dns-rebinding-test.md`）

### 5. XSS（`xss-test.md`）
- 反射点：URL 参数 → HTML/JS/属性上下文
- 存储点：评论/昵称/富文本/文件名 → 管理后台盲打
- 上传 XSS：SVG/HTML 文件 + 存储桶 Content-Type（`dangling-markup-test.md`）
- 兜底链：XSS → CSRF → 改密/改绑的高危闭环

### 6. 文件上传 / RCE（`file-upload-test.md`）
- 后缀/Content-Type/Magic 三重校验绕过；解析差异（`shell.php.jpg` 等要看具体中间件）
- 上传不落地 → 对象存储/云函数；STS 通配覆盖（见 `打野短表`）
- 拿到 RCE → `webshell.md` 授权 PoC 流程（无害命令证明 → 唯一标记 → 清理）

## 其他类型速查索引

| 类型 | 文件 | 一句话要点 |
|------|------|-----------|
| 401/403 绕过 | `401-403-bypass.md` | 方法切换/路径变异/头伪造/认证类型差 |
| API 网关 | `api-gateway-test.md` | 鉴权在网关可以绕过直打业务源 |
| 缓存投毒 | `cache-poisoning-test.md` | 未验证头进缓存，毒化他人响应 |
| 点击劫持 | `clickjacking-test.md` | 缺少 X-Frame-Options/CSP frame-ancestors |
| CORS | `cors-test.md` | Origin 反射 + 凭证位，跨站读接口 |
| CRLF | `crlf-injection-test.md` | 注入响应头/Set-Cookie |
| CSP 绕过 | `csp-bypass-test.md` | 白名单内的可控端点做跳板 |
| CSRF | `csrf-test.md` | 无 token/弱校验 + XSS 闭环 |
| CSV 公式注入 | `csv-formula-injection-test.md` | 导出开头 `=`/`+` 等公式前缀 |
| 悬挂标记 | `dangling-markup-test.md` | 反射尖括号受限时的数据窃取兜底 |
| 依赖混淆 | `dependency-confusion-test.md` | 内部包名推到公共源 |
| 反序列化 | `deserialization-test.md` | 客户端二进制 → 服务端 gadget |
| EL 注入 | `el-injection-test.md` | 表达式函数回显 |
| 邮件头注入 | `email-header-injection-test.md` | `\r\n` 注入 Bcc/发信人 |
| 请求走私 | `http-smuggling-test.md` | CL.TE / TE.CL 前后端解析差异 |
| HTTP/2 | `http2-attacks-test.md` | h2 降级/头混淆走私 |
| Host 头 | `http-host-header-test.md` | 密码重置链接注入/缓存分割 |
| 信息泄露 | `info-leak-test.md` | 报错/源码/备份/git 泄露/云凭证 |
| 不安全仓库 | `insecure-scm-test.md` | .git/.svn 拖库、历史提交里的密钥 |
| JNDI | `jndi-injection-test.md` | log4j 系 `${jndi:ldap://}` |
| LLM 安全 | `llm-security-test.md` | 提示注入/越权工具调用 |
| 逻辑漏洞 | `logic-test.md` | 金额/状态/流程/阈值边界 |
| GraphQL | `graphql-test.md` | introspection、批量、嵌套 DoS |
| HTTP 参数污染 | `hpp-test.md` | 重复参数取哪个值 |
| 开放重定向 | `open-redirect-test.md` | 跳转参数校验；配合 OAuth/钓鱼 |
| 路径穿越 | `path-traversal-lfi-test.md` | `../` 编码变体、本地文件包含 |
| 原型污染 | `prototype-pollution-test.md` | `__proto__`/`constructor` 覆盖 |
| 竞态 | `race-condition-test.md` | 并发窗口：券/库存/限额 |
| 子域接管 | `subdomain-takeover-test.md` | 悬挂 CNAME → 抢注 |
| 类型混淆 | `type-juggling-test.md` | `0` vs `"0"`、MD5 弱比较 `0e` |
| WebSocket | `websocket-test.md` | 升级头鉴权缺失/消息注入 |
| XSLT | `xslt-injection-test.md` | 样式表注入/文件读取 |
| XXE | `xxe-test.md` | 文档解析外部实体 |
| 云 IDE/RCE 链 | `cloud-ide-codex-rce-chain.md` | 沙箱逃逸/工具链滥用 |
| 依赖/供应链 | `dependency-confusion-test.md` | 私有包名抢注 |
| 壳/混淆 | `ghost-bits-cast-test.md` | 魔改加密流量识别 |

## 探针纪律

1. **有差分面的口必须真打**：注入/SSRF/XSS/RCE 四件套，按栈选探针，不打 N/A 要写明原因
2. **每日空窗检查**：连续作战日不能出现「今日四件套未测」
3. **基线先行**：每个探针前先记录正常值/空/非法值基线
4. **工具辅助不替代**：sqlmap/nuclei 结果必须手工复核，禁止直接当结论
5. **中危升链**：同一对象先升链（写 → 跨用户 → 接管 → 可执行），别急着换站