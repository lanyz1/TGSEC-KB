## 输出格式

将发现回填到预先生成的 `workspace/findings/poc-agent.json`。骨架中的示例值仅为占位内容，必须按真实结果覆写；如发现多个漏洞，在 `findings` 中继续追加对象，`vuln_id` 按 `POC-001`、`POC-002` 递增。

回填要求：
- `http_interactions[].request.headers` 必须尽量保留真实请求头，至少保留对复现有帮助的头：`Content-Type`、`Cookie`、`Authorization`、`Origin`、`Referer`、自定义鉴权头、代理头、版本头等；不要无意义地统一写成空对象
- `http_interactions[].request.body` 必须尽量保留真实请求体；不要无意义地统一写成 `null`
- `confidence` 为 `confirmed` 或已成功利用时，必须在 `http_test_commands` 中至少记录 1 条可直接回放的 `http_test.py` 命令；命令应尽量保留真实参数，并包含 `--show-command --show-summary --include-headers --allow-insecure --timeout 15`；`command` 字段中的脚本路径必须写成当前环境下的完整绝对路径，例如 `python "d:/vibe_pentest/scripts/http_test.py" ...`，不要保留 `{SKILL_ROOT}` 占位符。没有对应实际执行过的 `http_test.py` 命令时，不得将 POC 标记为 `confirmed` 或 `likely`。
- `http_interactions[].request.url` 必须尽量保留真实探测参数、变体 payload 和关键编码细节
- 若请求中包含动态值或敏感值，可做最小必要脱敏，但必须保留可用于人工复验的结构、字段名、参数名、payload 形态和关键取值
- 若为 GET/HEAD 等通常无请求体的方法，可保留 `body: null`；但如果实际发起时存在 body，则必须按真实内容回填
- `http_interactions[].response.headers`、`response.body` 也应尽量保留关键证据
- 当漏洞验证使用了 OOB / DNS 回连方式时，必须在对应 `http_interactions` 条目中填写 `oob_evidence` 字段：`platform` 为反连平台名称（如 dnslog.cn），`domain` 为当前 POC / CVE / payload 专属反连域名，`record_count` 为 DNS 记录数量，`records` 为 `[域名, IP, 时间]` 数组，`time_correlation` 说明 DNS 记录时间与请求时间的关联；同时必须说明该域名与当前 payload 的唯一标识、基线 record_count、增量 record_count。若原始 matcher 要求 `interactsh_protocol: http`，但本环境仅能获得 DNS 记录，应在 `oob_evidence` 中说明这是 DNS 解析回连等价证据以及 dnslog 平台无法展示 HTTP 请求详情，不得因此把已满足时间相关性和唯一标识条件的漏洞降级为“无法确认”。未使用 OOB 验证时可省略该字段
- `RepairSuggestions` 必须结合本次发现撰写针对性整改建议（1-3 条，用 `；` 分隔）：须点明具体整改措施，并引用与本发现直接相关的组件与版本、CVE 编号、受影响路径；禁止照抄通用模板
- 回填说明性文本字段（如：`title`、`description`、`http_interactions[].label`），默认回填为中文，但不得翻译路径、参数名、字段名、payload、状态码、URL 中的技术片段
- 低风险提醒条目（因无法无害化验证而跳过的 POC）必须复用已有字段写入 `findings`：`severity: "low"`、`confidence: "potential"`、`title` 前缀 `【低风险提醒·未验证】`、`description` 说明跳过原因及漏洞可能真实存在建议人工复验、`http_interactions` 与 `http_test_commands` 填空数组；不得新增顶层字段
- 回填全部完成后，最终 JSON 文件在语法上须保持有效

格式参考：

```json
{
  "agent": "poc-agent",
  "coverage": ["rce", "sqli", "lfi", "information_disclosure", "file_upload"],
  "checked_fingerprints": 5,
  "findings": [
    {
      "vuln_id": "POC-001",
      "title": "CVE-2018-1000861 - Jenkins 远程命令注入",
      "type": "rce",
      "type_zh": "远程代码执行",
      "severity": "critical",
      "confidence": "confirmed",
      "authenticated": false,
      "target_url": "http://192.168.1.133:8080/securityRealm/user/admin/descriptorByName/...",
      "description": "通过指纹识别发现 Jenkins/2.138，匹配 POC CVE-2018-1000861 验证存在远程命令注入漏洞。",
      "RepairSuggestions": "1. 升级 Jenkins 到最新安全版本；2. 限制 descriptorByName 路径的访问权限",
      "http_test_commands": [
        {
          "label": "POC 验证回放命令",
          "command": "python \"d:/vibe_pentest/scripts/http_test.py\" --url \"http://192.168.1.133:8080/securityRealm/user/admin/descriptorByName/...\" --method GET --include-headers --show-summary --response-max-lines 100 --allow-insecure --timeout 15",
          "expected_evidence": "响应体包含 package#vulntest 且状态码为 200"
        }
      ],
      "http_interactions": [
        {
          "seq": 1,
          "label": "POC CVE-2018-1000861 验证请求",
          "request": {
            "method": "GET",
            "url": "http://192.168.1.133:8080/securityRealm/user/admin/descriptorByName/...",
            "headers": {},
            "body": null
          },
          "response": {
            "status_code": 200,
            "headers": {"Content-Type": "text/html"},
            "body": "...package#vulntest..."
          }
        },
        {
          "seq": 2,
          "label": "OOB POC 验证 - DNS 回连确认漏洞触发",
          "request": {
            "method": "GET",
            "url": "http://192.168.1.133:8080/api/ssrf?url=http://abc123.dnslog.cn",
            "headers": {},
            "body": null
          },
          "response": {
            "status_code": 200,
            "headers": {"Content-Type": "text/html"},
            "body": ""
          },
          "oob_evidence": {
            "platform": "dnslog.cn",
            "domain": "abc123.dnslog.cn",
            "record_count": 1,
            "records": [
              ["abc123.dnslog.cn", "1.2.3.4", "2025-01-01 12:00:00"]
            ],
            "time_correlation": "DNS 记录时间与验证请求时间一致，确认 SSRF 漏洞触发"
          }
        }
      ]
    },
    {
      "vuln_id": "POC-002",
      "title": "【低风险提醒·未验证】CVE-XXXX-XXXXX - 某产品远程命令执行",
      "type": "rce",
      "type_zh": "远程代码执行",
      "severity": "low",
      "confidence": "potential",
      "authenticated": false,
      "target_url": "http://192.168.1.133:8080/xxx",
      "description": "目标存在对应组件与接口，匹配 POC CVE-XXXX-XXXXX，但验证依赖执行破坏性命令/写入生产数据，无法通过无害 payload 替换或 OOB 外带完成无害化验证，故未实际验证。漏洞可能真实存在，建议人工复验。",
      "RepairSuggestions": "在隔离测试环境中人工复验，并将受影响组件升级到安全版本",
      "http_test_commands": [],
      "http_interactions": []
    }
  ]
}
```

