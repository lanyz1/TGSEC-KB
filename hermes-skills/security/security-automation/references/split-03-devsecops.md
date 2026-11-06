## 一、DevSecOps 全流程与安全左移

### 1.1 安全左移模型
```
Plan阶段:   威胁建模(STRIDE) → 安全需求 → 安全设计评审 → 攻击面分析
Code阶段:   IDE安全插件 → Pre-commit Hook(密钥/格式) → 代码审计(SAST)
Build阶段:  SAST → SCA → 依赖漏洞 → 许可证合规 → 构建产物签名
Test阶段:   DAST → IAST → 渗透测试 → Fuzzing → API安全测试
Deploy阶段: 容器扫描 → IaC审计 → 配置合规 → 供应链校验(SBOM)
Run阶段:    RASP → WAF → 运行时监控(Falco) → 漏洞管理 → 自动化应急响应
```

### 1.2 安全管道架构（GitLab CI 示例）
```yaml
stages:
  - security-scan

sast:
  stage: security-scan
  image: semgrep/semgrep
  script:
    - semgrep --config=auto --json -o sast-results.json .
  artifacts:
    reports:
      sast: sast-results.json

dependency-scan:
  stage: security-scan
  image: aquasec/trivy
  script:
    - trivy fs --format json -o deps-results.json .

container-scan:
  stage: security-scan
  image: aquasec/trivy
  script:
    - trivy image --format json -o container-results.json $CI_REGISTRY_IMAGE

secret-scan:
  stage: security-scan
  image: zricethezav/gitleaks
  script:
    - gitleaks detect --source . --report-format json --report-path secrets.json

iac-scan:
  stage: security-scan
  image: bridgecrew/checkov
  script:
    - checkov -d terraform/ -o json > iac-results.json
```

### 1.3 全链路安全门禁（Gate）
```bash
# 门禁原则：扫描发现 X 级漏洞 → 阻断发布；Y 级漏洞 → 放行+缺陷登记+限时修复
# 示例：Semgrep 阻断严重级
if grep -q '"severity": "ERROR"' sast-results.json; then
  echo "检测到严重级SAST漏洞，阻断流水线"
  exit 1
fi

# 示例：Trivy 高危漏洞阈值阻断（支持 --exit-code --severity 直接内嵌）
trivy image --exit-code 1 --severity CRITICAL,HIGH --ignore-unfixed $IMAGE
```
- **硬门禁**：CRITICAL/HIGH 直断；**软门禁**：MEDIUM/LOW 放行但自动创建缺陷单并追踪 SLA
- 门禁参数建议统一由 `security-config` 仓库管理，扫描器只读配置，避免各团队自行放水

### 1.4 度量与指标
| 指标 | 含义 | 建议目标 |
|------|------|---------|
| 漏洞密度 | 每千行代码漏洞数 | 持续下降趋势 |
| MTTR | 平均修复时间（漏洞/告警） | 按 SLA 分级 |
| 修复率 | 周期内修复/新增 | ≥90% |
| 门禁拦截率 | 流水线被安全阻断比例 | 反映左移生效度 |
| 误报率 | 确认误报/总告警 | <30% 持续优化 |
| 覆盖率 | 扫描资产/全量资产 | ≥95% |

