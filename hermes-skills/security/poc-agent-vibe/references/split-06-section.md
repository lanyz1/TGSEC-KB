## 执行流程

执行主线：读取指纹 `tech_stack` → 搜索 POC（本地优先，联网须用户授权）→ 候选来源审计生成待验证**变体**清单 → 解析构造请求（无害化优先，OOB 走 dnslog 闭环）→ 逐变体发包、按 matcher 闭环评估 → 仅回填闭环确认的漏洞与无法无害化的低风险提醒，"不适用"不写入 findings。

### 第一步：读取指纹并搜索 POC

#### 1.1 提取 BaseURL 和 RootURL

读取 `workspace/fingerprint.json`，遍历每个 JSON key（目标 URL）及其 `tech_stack` 列表。

| 变量 | 规则 | 示例（key = `http://192.168.1.133:8080/jenkins/`） | 示例（key = `http://target.com/`） |
|------|------|--------------------------------------------------|----------------------------------|
| `{{BaseURL}}` | key 去掉末尾斜杠，**保留路径部分** | `http://192.168.1.133:8080/jenkins` | `http://target.com` |
| `{{RootURL}}` | 仅保留 `scheme://host:port`，**去掉路径部分** | `http://192.168.1.133:8080` | `http://target.com` |

> 大多数情况下 key 是根 URL，此时 BaseURL 与 RootURL 相同。

#### 1.2 提取指纹关键字

从 `tech_stack` 数组中每个条目提取 `/` 前的名称作为关键字，合并去重后用于 POC 搜索。例如：
- `Jenkins/2.138` → `Jenkins`
- `SpringBoot` → `SpringBoot`
- `Alibaba Druid` → `Alibaba Druid`

#### 1.3 搜索本地 POC

执行 `python {SKILL_ROOT}/scripts/poc_search.py search --keywords "k1,k2,k3"`，传入全部关键字列表，脚本会同时搜索内容和文件名，输出候选清单。

#### 1.4 联网搜索 POC（仅在用户明确允许时）

默认不联网搜索。用户明确允许时，在完成本地搜索后，使用以下来源补充：

- `nuclei-templates` — [https://github.com/projectdiscovery/nuclei-templates](https://github.com/projectdiscovery/nuclei-templates)
- `Awesome-POC` — [https://github.com/Threekiii/Awesome-POC](https://github.com/Threekiii/Awesome-POC)
- `Vulnerability-Wiki-PoC` — [https://github.com/SourByte05/Vulnerability-Wiki-PoC/tree/main](https://github.com/SourByte05/Vulnerability-Wiki-PoC/tree/main)
- `Exploit Database` — [https://www.exploit-db.com/](https://www.exploit-db.com/)

联网搜索规则：
- 将 `tech_stack` 关键字直接作为搜索词
- GitHub 仓库优先用 `"owner/repo" 关键词` 搜索
- 联网命中结果重点提取可用于 HTTP 验证的请求、payload 和匹配条件
- 本阶段只收集候选，不进入内容深读
- 对联网命中的高危/严重 CVE（critical/high），只要能从公开模板、复现说明、厂商通告引用或安全研究文章中提取等效 HTTP 请求、payload 和 matcher，就必须纳入最终待验证清单并实际发包验证
- 若联网命中是脚本型 POC、复现文章或非 YAML 模板，必须保留到精读阶段并读取原文；搜索摘要只能作为线索，不能替代 POC 内容
- 若联网命中仅有 CVE 描述或厂商通告，无法提取可执行 HTTP payload，则必须在收尾校验文本中列为“联网候选但未验证”，说明缺少可执行 POC / matcher；不得把这类候选写入 findings，也不得在已验证清单中遗漏说明

#### 1.5 候选去重、收敛与变体保留

将本地搜索和联网搜索得到的候选统一归并为“漏洞候选 + 来源列表 + 变体清单”，再进入精读阶段。去重时**不得丢弃任何可执行变体**，最终合并同一漏洞/同一产品的所有变体。

归并规则：
- 优先按 `CVE / 漏洞名 + 目标产品` 归一；`文件路径`、`来源 URL` 仅作为来源标识，不得作为丢弃其他来源 POC 的理由。
- 同一漏洞在本地 YAML、联网搜索、Exploit-DB、博客复现、GitHub issue / advisory 中同时命中时，如果**存在不同payload变体**，保留所有变体，作为一个漏洞候选。
- 联网命中的候选只有在精读后确认 endpoint、方法、参数位置、payload 结构、命令形式、动态值和 matcher/OOB 条件完全等价时，才允许把多个来源标记为同一变体；否则必须作为独立变体保留。
- 联网命中的非 YAML POC、脚本型 POC、复现文章不得因为已有同 CVE 本地 YAML 或 nuclei 模板就直接丢弃；即使只展示部分请求，只要包含关键差异（如 GET query 与 POST XML body、XML 属性与 XML 子元素、curl 与 nslookup、不同 typeName / namespace），也必须保留为待补全变体。

若某个漏洞候选只有 1 个变体，必须说明是否已检查其他来源、fallback、协议版本、参数位置、命令形式和等价 matcher；未说明时不得进入第三步验证阶段。

1.5 归并后的候选不得直接进入验证，必须先进入第二步执行候选来源审计与待验证变体清单生成。

### 第二步：候选来源审计与待验证变体清单生成（强制）

在开始构造请求和验证之前，必须对 1.5 形成的“漏洞候选 + 来源列表 + 初始变体清单”执行审计，并生成最终待验证变体清单。审计对象是“变体”，不是只按 CVE / POC 名称聚合后的条目。

1. **输出清单来源统计**：分别声明本地搜索命中数、联网补充数、最终待验证漏洞候选总数、最终待验证变体总数。
2. **完整读取候选来源**：对本地 YAML、pocsuite/Python/Shell 脚本、联网 YAML、博客复现、Exploit-DB 页面等，必须读取原文完整内容，不得只依赖搜索摘要或只读取第一个命中来源。
3. **逐一列出全部待验证变体**：按 `漏洞候选 / CVE -> variant_id` 展开列出，不得只列 CVE 名称；每个变体必须包含 endpoint、HTTP 方法、参数位置、payload/命令形式、fallback、动态值提取、matcher/OOB/时间差验证方式。
4. **展开脚本型 POC 分支**：对脚本型 POC 中的循环、数组、fallback、条件分支必须展开为变体清单。例如 `payloads=[nslookup,curl]`、`all_data=[data1,data2]`、多个 `typeName`、多个 endpoint 均需列入待验证清单。
5. **联网候选首轮深读审计**：联网命中超过 10 条时，按“指纹匹配度 → 路径/接口特征匹配度 → 风险等级 → 发布时间”排序，优先深入读取前 10 条（仅为首轮深读上限，不是最终清单上限）；首轮深读后仍必须保留所有可执行变体，不得因已有同 CVE 变体而丢弃差异请求。
6. **确定执行优先级**：先按 severity 排序（`critical` > `high` > `medium` > `low`/`info`），同一漏洞候选内再按低影响优先原则排序变体（回显/状态码 → 时间差 → OOB → 明显有副作用的命令）。
7. **变体验证方式多样性检查**：涉及命令执行或外带回连的 POC，必须先按原 POC 提供的验证方式执行；只有原 POC 验证失败、运行环境不适配或无法形成 matcher/OOB 闭环时，才补充等价低影响方式，如 HTTP 外带、时间差、命令回显或原文提供的其他命令形式；若无法补充，必须说明限制原因。
8. **生成完整待验证变体清单**：整理所有变体的名称、来源、优先级、matcher 摘要和验证方式（如回显 / OOB / 状态码 / 时间差）。
9. **变体计数校验**：逐个漏洞候选声明 `source_count`、`variant_count`、`endpoint_count`、`parameter_location_count`、`matcher_type_count`；若 `variant_count = 1`，必须说明为何没有其他来源、fallback、协议版本、参数位置、命令形式或等价 matcher 可测。
10. **严禁选择性执行**：清单中每个 `variant_id` 都必须经历第三步及后续完整验证流程；任一变体确认成功后，可停止同一漏洞候选的剩余变体，除非用户要求全量验证。若所有变体均失败，才允许将该漏洞候选标记为“不适用/未验证”。

### 第三步：解析 POC 并构造验证请求

#### 3.1 解析 POC 定义

- **本地 Nuclei YAML**：按 `{SKILL_ROOT}/references/nuclei-templates-usage.md` 解析 Path 格式、Raw 格式、关键字段和匹配器
- **联网非 YAML POC**：从模板、脚本或复现说明中提取等效 HTTP 请求、payload、关键 Header、请求体和成功判定条件；脚本中的循环、数组、fallback 和动态探测逻辑必须按第二步的变体清单审计要求展开
- **失败原因分析与变体重构（强制）**：验证失败时不得只记录“失败”并结束；必须先判断失败层级，再按同一安全影响重构等价变体。
  1. **请求构造层失败**：路径、方法、Content-Type、XML 命名空间、参数位置、命令构造兼容（不同操作系统或不同版本的命令构造语法）、编码、版本号、上下文路径等错误，应根据 POC 原文、目标能力接口和响应错误修正后重试；出现缺少参数、未知操作/方法、路由不到处理器、版本不支持、请求体解析失败等现象时，优先按本类复盘。
  2. **表达式解析层失败**：如 `No such attribute: exec(...)`、`No such property`、表达式原文被当作属性名、函数名未识别、payload 未进入调用语义，应标记为“表达式未被执行/仅按属性名解析”，并优先切换表达式入口、参数位置、语法形式、协议版本或 typeName。
  3. **payload 执行层失败**：命令不可用、无回显、无 OOB、运行时依赖错误、类加载失败、外部二进制不存在、出站网络受限等，应保持原漏洞语义，改用回显、时间差、HTTP/DNS 外带、文件读取、不同 XML 入口或不同参数位置等方式继续验证。
  4. 变体应从 POC 原文、脚本分支、模板 matcher、目标能力接口、响应错误和协议语义中推导；不得机械固定为某一个命令、端点或 payload。
- **OOB/RCE/XXE 保语义规则**：涉及命令执行、外带回连、XML 外部实体、JNDI、SSRF 等无回显或间接验证的 POC，必须保留原始触发语义。原 POC 是 HTTP 外带时不得只改成 DNS 命令；原 POC 是 XML 实体解析时不得只验证单一 XML 入口；原 POC 是命令执行时不得只用单一系统命令作为唯一证据。
- **不适用判定前检查（强制）**：只有当已覆盖 POC 原文提供的变体、脚本分支、fallback、动态值提取结果，以及可从目标能力接口和响应错误合理推导出的等价变体后，仍无法形成原 matcher 或等价 matcher 的闭环，才能标记为“未验证/不适用”。
#### 3.2 模板变量替换

模板变量的完整替换表、Nuclei 内置函数和数学运算规则，参见：`{SKILL_ROOT}/references/nuclei-templates-usage.md`（"模板变量替换表"～"Nuclei 内置函数"章节）。

核心变量：
- `{{BaseURL}}` / `{{RootURL}}`：从第一步提取
- `{{Hostname}}`、`{{Host}}`、`{{Port}}`、`{{Scheme}}`：从 BaseURL 解析
- `{{randstr}}`、`{{randstr_N}}`：生成随机字符串
- `{{interactsh-url}}`：替换为 `dnslog.py` 获取的域名

#### 3.3 路径前缀适配

许多 POC 路径中硬编码了应用上下文前缀（如 `/geoserver/`、`/solr/`、`/jenkins/`）。当目标部署在自定义路径下时，需进行适配：

| 场景 | 处理方式 |
|------|---------|
| POC 硬编码前缀 = 实际 BasePath | 直接拼接 |
| POC 硬编码前缀 ≠ 实际 BasePath | 将硬编码前缀替换为实际 BasePath |
| POC 路径不含应用前缀，目标在非根路径 | 在路径前补上 BasePath |
| 目标部署在根路径 | 保留 POC 原路径 |
| 替换后返回 404 | 回退尝试原始路径（最多 2 种变体） |

常见硬编码前缀：`/geoserver/`、`/solr/`、`/jenkins/`、`/xxl-job-admin/`、`/nacos/`、`/admin/`、`/druid/`、`/console/`、`/imc/`、`/minio/`、`/api/`、`/confluence/`、`/rabbitmq/`、`/grafana/`、`/nexus/`、`/sonarqube/`。任何 `{{BaseURL}}` 之后的第一段路径（形如 `/xxx/` 或 `/xxx-admin/`）都可能是应用上下文前缀。

#### 3.4 反序列化 POC 处理（条件触发）

当 POC 涉及 Java 反序列化（如 Shiro `rememberMe`、WebLogic、JBoss 等）且需要动态生成 payload 时：

1. 使用 `{SKILL_ROOT}/scripts/deserialization_payload.py` 生成 ysoserial payload
2. 优先使用 `URLDNS` 等低影响 OOB 探测，配合 `dnslog.py` 验证
3. 生成 payload 后通过 `http_test.py --data-file payload.bin` 发送
4. 必须结合目标依赖选择 gadget 与输出格式，不得机械遍历全部 gadget
5. 无有效异常或 OOB 信号时必须停止

#### 3.5 构造 http_test.py 命令

**Path 格式**（`method:` + `path:`）：将 `{{BaseURL}}` 替换为实际值，拼接 path。

**Raw 格式**（`raw:`）：从请求行提取 METHOD 和 PATH，从请求头提取 Headers，从空行后提取 body。Raw 格式同样适用路径前缀适配规则。

**Raw 请求完整性规则（强制）**：Raw 请求第一行的 PATH 必须按完整 `request-target` 提取，包含 path、query string、编码字符、重复参数和参数顺序。若原始请求行包含 `?`，最终 `--url` 必须保留等价 query string；不得只截取 `?` 前的路径。发包前必须核对原始 PATH 与最终 URL 的 path+query 语义一致，不一致时必须说明适配原因。

**参数映射**：
| POC 字段 | http_test.py 参数 |
|---------|------------------|
| `redirects: true` | `--follow-redirects` |
| `cookie-reuse: true` | `--cookies "..."`（从前序响应提取） |
| `--response-filter` | 手动指定正则，仅提取 matchers 相关关键词 |

### 第四步：执行验证并评估匹配器

#### 4.1 执行规则

| 优先级 | 顺序 | severity |
|--------|------|----------|
| P0 | 最先 | critical |
| P1 | 其次 | high |
| P2 | P1 后 | medium |
| P3 | 最后 | low / info |

**清单中每个 POC 都必须验证，优先级仅决定顺序。**

**变体必须逐项发包验证。** 变体包括但不限于：请求方式、端点、参数位置、payload、fallback 值、命令形式、操作系统命令、动态值、协议/接口版本、命名空间与编码方式。执行时应从 POC 原文、脚本逻辑、目标能力接口和已获得响应中推导变体，不得只试第一个看似可用的请求。

**RCE/OOB 变体多样性提醒**：命令执行类或表达式注入类 POC 应优先使用原 POC 的验证方式。若首选方式失败、运行环境不适配或无法形成 matcher/OOB 闭环，再按 3.1 的失败层级分析补充低影响等价方式，例如 HTTP 外带、时间差或命令回显。

**失败复盘与结论门槛（强制）**：单个变体失败只能说明该变体失败，必须按 3.1 复盘并继续补验同一 POC 的其他原文变体、脚本分支、fallback、动态值和目标能力接口可推导出的等价变体。只有所有合理变体均失败，且无法形成完整 matcher/OOB 闭环时，才能标记为“未验证/不适用”；不得强行标记 `confirmed`。

**不适用判定前检查（强制）：**
- 已覆盖 POC 原文、脚本分支、fallback、动态值提取和目标能力接口可推导出的等价请求。
- 已区分运行时错误与漏洞不存在；OOB 类 POC 已完成独立域名、基线记录、触发请求、复查记录四步。

涉及 OOB / DNS 回连的 payload，按前文 OOB 域名唯一性规则执行；无法明确归属到当前 payload 的回连记录不得作为确认依据。

#### 4.2 评估匹配器

匹配器评估的详细规则参见：`{SKILL_ROOT}/references/nuclei-templates-usage.md`（"匹配器评估规则"章节）。

从 `http_test.py` 输出中检查：
- **状态码**：从 `HTTP/1.1 <状态码>` 行读取（`--include-headers`）
- **Body/Header 关键词**：直接检查响应内容
- **响应时间**：从 Meta 部分的 `Ttfb` 或 `Total` 读取（`--show-summary`）

**确认结论必须满足原 POC matcher 或等价 matcher 的完整闭环。** 服务端异常、Java 类名、文件路径错误、XML 解析错误、调用栈片段只能作为“payload 到达危险解析/执行链路”的运行时证据；除非原 POC matcher 明确以该异常为成功条件，或该异常同时证明了命令回显、外带回连、文件内容泄露等最终安全影响，否则不得仅凭异常将漏洞标记为 `confirmed`。

#### 4.3 异常响应判定

危险调用链证据（如 `ProcessImpl`、`ProcessBuilder`、外部实体解析、JNDI lookup）只能说明 payload 到达敏感链路，不能单独作为 `confirmed`。最终结论仍以 matcher/OOB 是否闭环为准：完全闭环为 `confirmed`，部分命中且有链路证据为 `likely`，所有变体失败为"不适用"。

#### 4.4 findings 写入过滤规则（防误报）

**只有匹配器全部通过、漏洞被确认存在的 POC 才能写入 findings。** 以下情况**严禁写入**：
1. 目标未部署该服务（所有变体均 404）
2. 匹配器条件未满足
3. `confidence` 为 `potential` 且无实质证据
4. 仅有“疑似命中”、版本接近、标题相似、路径相似或技术栈相似，但没有完成对应 matcher / 反连证据闭环

**"不适用"的 POC 仅在收尾校验文本输出中列出，不得写入 findings JSON。**

**唯一例外：因无法无害化验证而跳过的 POC，必须按"POC 无害化验证原则"规则 6 作为低风险提醒条目写入 findings（`severity: "low"`、`confidence: "potential"`、标题前缀 `【低风险提醒·未验证】`）；其余"不适用" POC 仍严禁写入。**

#### 4.5 执行注意事项

1. 一个 POC 可能有多个 HTTP 请求条目，每个条目必须单独测试
2. `stop-at-first-match: true` 时，任一请求匹配后即可停止
3. 请求超时时记录并继续下一个 POC


