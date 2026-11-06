## 五、安全工具链集成实战（nuclei/SAST/DAST/漏洞管理平台联动）

### 5.1 扫描器→漏洞平台全链路联动
```
CI流水线/调度器
  ├─ Semgrep(SAST) ──┐
  ├─ Trivy(SCA/镜像) ─┤→ 结果归一化 → DefectDojo/ThreadFix → 指派修复 → 复扫验证
  ├─ Nuclei(DAST) ───┤
  └─ Checkov(IaC) ───┘        ↑
                        回归/去重/加噪
```

### 5.2 Nuclei 实战（模板驱动快速扫描）
```bash
# 单资产扫描
nuclei -u https://target.com -severity high,critical -jsonl -o nuclei.jsonl

# 资产列表批量扫描（并发控制，遵守授权）
nuclei -l targets.txt -c 20 -stats -jsonl -o nuclei.jsonl

# 指定模板分类
nuclei -u https://target.com -t cves/ -t exposures/ -t misconfiguration/

# 与漏洞平台联动：nuclei -jsonl 输出 → jq 提取 → 导入 DefectDojo
jq -c '{scan_type:"Nuclei Scan", ...}' nuclei.jsonl
```

### 5.3 结果归一化示例（Python 单文件）
```python
# 将 nuclei JSONL → DefectDojo 期望字段（示意）
import json, sys
out = []
for line in sys.stdin:
    d = json.loads(line)
    out.append({
        "title": d.get("info", {}).get("name", d.get("template-id")),
        "severity": d.get("info", {}).get("severity", "info"),
        "cwe": (d.get("info", {}).get("classification") or {}).get("cwe-id", []),
        "description": d.get("info", {}).get("description", ""),
        "matched_at": d.get("matched-at"),
        "tags": d.get("info", {}).get("tags", []),
    })
print(json.dumps(out, ensure_ascii=False, indent=2))
```

### 5.4 ZAP 自动化（DAST 入 CI）
```bash
# ZAP 全量扫描并出报告
docker run -t ghcr.io/zaproxy/zaproxy zap-baseline.py \
  -t https://target.com -r zap-report.html -J zap-report.json

# 结合 -x 导出 XML 供 DefectDojo "ZAP Scan" 类型导入
```

