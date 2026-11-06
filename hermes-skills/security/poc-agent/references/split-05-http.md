## HTTP 发包工具（强制）

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
- PowerShell 环境下必须参考 `http-test-usage.md` 的 PowerShell 兼容说明；复杂正则优先使用 `--response-filter-file`，请求体较长、包含二进制/换行优先使用 `--data-file`，避免受 shell 转义影响。
- 保持默认开启 `--show-command --show-summary --include-headers`，确保输出满足证据回填要求；仅在非取证探测且确无需要时才使用 `--no-*` 关闭。
- 报错型和回显型检测优先使用 `--response-filter` 提取关键证据；需要数据库错误、唯一标识、命令回显、SSRF 服务响应或 XXE 文件内容特征时，按需参考 `http-test-usage.md` 的“常用证据过滤模板”。
- 大 HTML 响应必须用 `--response-max-lines 80`（或更小）限制输出。
- 表单字段优先使用 `--form`；需精确控制原始文本请求体时使用 `--data`；请求体较长、包含二进制/换行，或易受 shell 转义影响时使用 `--data-file`。仅在目标本身涉及 URL 参数、表单编码或编码/解析差异时，再显式处理编码。
- Cookie 认证使用 `--cookies "key1=val1; key2=val2"` 格式。
- JSON API 使用 `--data '{"k":"v"}'` 自动识别 Content-Type。
- 禁止使用 curl 或其他工具替代。

