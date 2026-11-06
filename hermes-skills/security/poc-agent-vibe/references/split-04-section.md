## 使用工具

### HTTP 发包工具（强制）

**所有 HTTP 请求必须使用 `{SKILL_ROOT}/scripts/http_test.py`。**
开始使用工具前应先读取：
`{SKILL_ROOT}/references/http-test-usage.md`
后续优先复用已获取的用法信息，除非遇到新的场景或参数。
核心调用模板：

```bash
python {SKILL_ROOT}/scripts/http_test.py --url "<URL>" --method <METHOD> \
  --data '<PAYLOAD>' --headers '{"Key":"Val"}' --cookies "<COOKIE>" \
  --response-filter '<REGEX>' --response-filter-mode line \
  --response-max-lines 80 --show-command --show-summary --include-headers \
  --allow-insecure --timeout 15
```

关键规则：
- PowerShell 环境下必须参考 `http-test-usage.md` 的 PowerShell 兼容说明；复杂正则优先使用 `--response-filter-file`，请求体较长、包含二进制/换行优先使用 `--data-file`，避免受 shell 转义影响。遇到复杂 Header、复杂 URL、编码、Cookie、重定向或动态参数问题时，也必须优先通过 `http_test.py` 的参数、URL 编码、临时 payload/filter 文件解决；仍无法表达时，将该变体标记为“工具能力受限/未验证”，不得改用自定义脚本、curl、wget、浏览器自动化或其他 HTTP 客户端发包。
- 保持默认开启 `--show-command --show-summary --include-headers`，确保输出满足证据回填要求；仅在非取证探测且确无需要时才使用 `--no-*` 关闭。
- 报错型和回显型检测优先使用 `--response-filter` 提取关键证据；需要数据库错误、唯一标识、命令回显、SSRF 服务响应或 XXE 文件内容特征时，按需参考 `http-test-usage.md` 的"常用证据过滤模板"。
- 大 HTML 响应必须用 `--response-max-lines 80`（或更小）限制输出。
- 表单字段优先使用 `--form`；需精确控制原始文本请求体时使用 `--data`；请求体较长、包含二进制/换行，或易受 shell 转义影响时使用 `--data-file`。仅在目标本身涉及 URL 参数、表单编码或编码/解析差异时，再显式处理编码。
- Cookie 认证使用 `--cookies "key1=val1; key2=val2"` 格式。
- JSON API 使用 `--data '{"k":"v"}'` 自动识别 Content-Type。
- 禁止使用 curl 或其他工具替代。

### OOB / DNS 回连工具

当 POC 使用 `{{interactsh-url}}`、`interactsh_protocol`、`interactsh_request`、`oast`、`dnslog`，或者从 POC 语义上明显属于无回显外带验证时，需使用 `{SKILL_ROOT}/scripts/dnslog.py` 进行无回显漏洞验证。不能只靠字段名是否完全命中来判断，凡是目标会向外发起 DNS/HTTP 回连的载荷，都按 OOB 处理。

**OOB 类 POC 不允许跳过 dnslog 闭环。** 未执行 `get_domain`、基线 `get_records`、触发请求、复查 `get_records` 四步，或四步中任一步失败时，只能标记为“未验证/工具失败”，不得标记为 `confirmed`、`likely` 或“不适用”。

#### 核心 4 步流程：

1. 使用 `dnslog.py get_domain` 获取当前域名
2. **记录基线**：使用 `dnslog.py get_records <domain>` 查询当前 record_count 基线值
3. 用该域名构造 payload，并通过 `http_test.py` 发送
4. 使用 `dnslog.py get_records <domain> 5` 查询 DNS 记录，比对 `record_count` 增量与时间戳

#### OOB 防漏报规则：

- **保持原始触发语义**：必须优先按原 POC 的请求、payload、命令形式和 matcher 执行验证；只有原 POC 验证失败、运行环境不适配或无法形成 matcher/OOB 闭环时，才允许基于原漏洞语义构造低影响等价变体继续验证。若原 POC 使用 `curl` / `wget` 触发 HTTP 外带 URL，不得直接改写成 `nslookup` / `ping` 作为首选验证；HTTP 反连 URL 只替换为 `http://<dnslog-domain>/`。
- **记录必须可归因**：多个 OOB 验证应串行执行；查询结果中的实际域名必须匹配当前 payload 的专属域名，仅 `record_count` 增加但域名不匹配时不得作为当前 POC 证据。

命令示例：
```bash 
python {SKILL_ROOT}/scripts/dnslog.py get_domain
python {SKILL_ROOT}/scripts/dnslog.py get_records <domain>
python {SKILL_ROOT}/scripts/http_test.py ...
python {SKILL_ROOT}/scripts/dnslog.py get_records <domain> 5
```

注意：`dnslog.py get_domain` 与 `dnslog.py get_records` 必须复用同一会话上下文；工具会通过临时文件自动持久化 Cookie，确保同一条验证链路中的两次调用使用同一会话。

#### OOB 域名唯一性规则

- 每个 POC 条目、每次独立验证、每个 OOB payload 都必须单独调用 `dnslog.py get_domain` 获取独立域名。
- 同一 dnslog 域名只能用于同一条验证链路，严禁跨 CVE、跨 POC、跨 payload 复用。
- 多个 CVE 需要生成 XML payload、JNDI payload、XXE payload、SSRF payload 或反序列化 OOB payload 时，每个 payload 都必须嵌入当前验证专属域名。
- 如果一次验证需要尝试多个 payload 变体，每个变体应使用可区分的唯一标识；无法区分归属时，该回连记录不得作为漏洞确认依据。
- 原始 Nuclei matcher 使用 `interactsh_protocol: http` 时，允许用 `dnslog.py` 的 DNS 解析回连作为等价低限证据；但必须满足唯一域名、基线增量、时间相关性和 payload 归属清晰，并在证据中说明 dnslog 平台无法展示 HTTP 请求详情。

#### 验证成功判定标准

不得仅凭 `record_count > 0` 判定漏洞成功。必须同时满足：
1. record_count 相比基线值有增量
2. 新增记录的时间戳与当前请求时刻误差在合理范围内
3. 新增记录命中当前 payload 的唯一标识
4. 新增记录可明确回指到当前 POC / CVE / payload，不能使用其他 POC 或其他 payload 的回连结果代替

只有当以上条件全部满足时，才能作为有效运行时证据。

### 本地 POC 搜索脚本

使用 `{SKILL_ROOT}/scripts/poc_search.py` 搜索本地 POC，脚本自动定位 `pocs/public` 和 `pocs/private` 目录，同时执行内容搜索和文件名匹配，合并去重输出。

```bash
python {SKILL_ROOT}/scripts/poc_search.py search --keywords "jenkins,geoserver,druid"
```

**关键字构建规则**：将 `tech_stack` 中每个条目提取 `/` 前的名称，转换为小写后传入。例如：
- `Jenkins/2.138` → `jenkins`
- `Alibaba Druid` → `alibaba druid`
- `GeoServer` → `geoserver`

