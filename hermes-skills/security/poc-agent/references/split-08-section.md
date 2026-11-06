## 输出格式

将发现回填到预先生成的 `workspace/findings/poc-agent.json`。骨架中的示例值仅为占位内容，必须按真实结果覆写；如发现多个漏洞，在 `findings` 中继续追加对象，`vuln_id` 按 `POC-001`、`POC-002` 递增。

回填要求：
- `http_interactions[].request.headers` 必须尽量保留真实请求头，至少保留对复现有帮助的头
- `http_interactions[].request.body` 必须尽量保留真实请求体
- `confidence` 为 `confirmed` 或已成功利用时，必须在 `http_test_commands` 中至少记录 1 条可直接回放的 `http_test.py` 命令；命令应尽量保留真实参数，并包含 `--show-command --show-summary --include-headers --allow-insecure --timeout 15`；`command` 字段中的脚本路径必须写成当前环境下的完整绝对路径，例如 `python "d:/vibe_pentest/scripts/http_test.py" ...`，不要保留 `{SKILL_ROOT}` 占位符
- 若请求中包含动态值或敏感值，可做最小必要脱敏，但必须保留可用于人工复验的结构、字段名、参数名和关键取值
- `http_interactions[].response.headers`、`response.body` 也应尽量保留关键证据
- 当漏洞验证使用了 OOB / DNS 回连方式时（如 POC 中包含 `{{interactsh-url}}` 或 DSL 匹配器涉及 `interactsh_protocol`），必须在对应 `http_interactions` 条目中填写 `oob_evidence` 字段：`platform` 为反连平台名称（如 dnslog.cn），`domain` 为获取到的反连域名，`record_count` 为 DNS 记录数量，`records` 为 `[域名, IP, 时间]` 数组，`time_correlation` 说明 DNS 记录时间与请求时间的关联；未使用 OOB 验证时可省略该字段
- 回填说明性文本字段（如：`title`、`description`、`http_interactions[].label`），默认回填为中文，但不得翻译路径、参数名、字段名、payload、状态码、URL 中的技术片段
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
      "target_url": "http://192.168.1.133:8080/securityRealm/user/admin/descriptorByName/org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition/checkScriptCompile?value=@GrabConfig(...)...",
      "description": "通过指纹识别发现 Jenkins/2.138，匹配 POC CVE-2018-1000861 验证存在远程命令注入漏洞。攻击者可通过构造恶意 URL 在 Jenkins 服务器上执行任意代码。",
      "RepairSuggestions": "1. 升级 Jenkins 到最新安全版本；2. 限制 Script Console 和 descriptorByName 路径的访问权限",
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
    }
  ]
}
```

