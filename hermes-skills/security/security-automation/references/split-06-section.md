## 四、漏洞管理自动化

### 4.1 漏洞管理闭环流程
```
1. 扫描发现 → 自动录入漏洞管理平台
2. 归一化 → 多扫描器结果统一格式（去重/去噪/合并同类）
3. 风险评估 → CVSS评分 × 资产权重 × 可利用性 = 优先级
4. 分配修复 → 按代码归属/资产负责人自动指派
5. 修复验证 → 自动复扫确认修复，闭环关闭
6. SLA跟踪 → 超时自动告警+升级
7. 定期报告 → 自动生成安全态势报告（周/月）
```

### 4.2 漏洞平台集成（DefectDojo 示例）
```bash
# 导入 Trivy 扫描结果
curl -X POST http://defectdojo/api/v2/import-scan/ \
  -H "Authorization: Token $TOKEN" \
  -F "scan_type=Trivy Scan" \
  -F "file=@trivy-results.json"

# 导入 Semgrep 结果
curl -X POST http://defectdojo/api/v2/import-scan/ \
  -H "Authorization: Token $TOKEN" \
  -F "scan_type=Semgrep JSON Report" \
  -F "file=@sast-results.json"
```

### 4.3 去重与聚合策略
- **多扫描器合并**：同一漏洞（如 XSS）在 SAST/DAST/人工验证中重复出现 → 以最高置信度证据为准合并，保留各来源证据链
- **指纹归一化**：CWE/CVE/资产(仓库:文件:行 / URL:参数) 三元组作为去重键
- **定期基线漂移检测**：同一资产连续 N 次扫描出现/消失的漏洞自动复核

### 4.4 SLA 与告警
```bash
# 示例：基于日期的 SLA 升级脚本（伪代码）
for vuln in open_vulnerabilities:
    if vuln.severity == "critical" and vuln.age_days > 7:
        escalate(vuln, to="安全负责人", notify="IM/邮件")
    elif vuln.severity == "high" and vuln.age_days > 14:
        escalate(vuln, to="部门负责人")
```

