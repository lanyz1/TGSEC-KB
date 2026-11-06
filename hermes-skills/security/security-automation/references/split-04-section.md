## 二、自动化扫描工具链

### 2.1 SAST（静态应用安全测试）
| 工具 | 语言 | 特点 |
|------|------|------|
| Semgrep | 多语言 | 规则灵活，自定义强，OSS 规则社区 |
| CodeQL | 多语言 | GitHub 集成，数据流/污点分析 |
| SonarQube | 多语言 | 代码质量+安全，质量门禁 |
| Bandit | Python | Python 专用 |
| Brakeman | Ruby | Rails 专用 |
| Gosec | Go | Go 专用 |
| ESLint Security / eslint-plugin-security | JS/TS | Node.js 安全 |
| Snyk Code / Fortify / Checkmarx | 商业 | 企业级，IDE/CI 全覆盖 |

**实战要点**：SAST 按团队细分规则集（新项目严/存量项目宽），结果按文件变更行（diff）过滤，只上报"本次改动引入"的问题，避免存量噪声淹没新问题。

### 2.2 DAST（动态应用安全测试）
| 工具 | 类型 | 特点 |
|------|------|------|
| OWASP ZAP | 开源 | CI/CD 集成，API 扫描，主动/被动模式 |
| Burp Suite CI | 商业 | 专业级，REST API 驱动 |
| Nuclei | 开源 | 模板驱动，YAML 模板生态丰富，扫描极快 |
| Nikto | 开源 | Web 服务器扫描 |
| Arachni | 开源 | 高覆盖 Web 扫描 |

### 2.3 SCA（软件成分分析）
| 工具 | 范围 | 特点 |
|------|------|------|
| Trivy | 全面 | 依赖/容器/IaC/密钥四合一 |
| Grype | 依赖/镜像 | 与 Syft SBOM 生成配套 |
| Snyk | 依赖 | 修复建议，PR 集成 |
| Dependabot / Renovate | 依赖 | 自动升级 PR |
| OWASP Dependency-Check | 依赖 | NVD 数据库 |
| OSV-Scanner | 依赖 | Google OSV 数据库 |

### 2.4 容器与 IaC 安全
| 工具 | 目标 | 特点 |
|------|------|------|
| Trivy | 镜像/依赖 | 多用途扫描，支持 SBOM 生成 |
| Hadolint | Dockerfile | Dockerfile Lint |
| Checkov | Terraform/K8s/云 | IaC 安全策略 1000+ |
| tfsec | Terraform | Terraform 安全 |
| kube-hunter | K8s | K8s 渗透测试 |
| OPA/Gatekeeper | K8s | 策略即代码（准入控制） |
| Kyverno | K8s | K8s 原生策略，无需 Rego |
| kube-bench | K8s | CIS Benchmark |

### 2.5 密钥泄露扫描与防护（Pre-commit + CI）
```bash
# gitleaks pre-commit hook（提交即拦截）
#!/bin/sh
gitleaks protect --staged
if [ $? -ne 0 ]; then
  echo "检测到密钥泄露，提交被拒绝"
  exit 1
fi
```
```yaml
# CI 全量扫描（含 Git 历史）
secret-scan:
  script:
    - gitleaks detect --source . --log-opts="--all"
    # 扫描所有 Git 历史，阻断合并请求
```
**补充**：定期（每周）对 Git 历史做深度回扫，防止已合入的密钥遗漏；检测到历史泄露时优先轮换密钥而非仅删提交。

### 2.6 供应链安全（SBOM/签名/来源）
```bash
# 生成 SBOM（CycloneDX 格式）
syft dir:. -o cyclonedx-json > sbom.json
# 或 trivy
trivy fs --format cyclonedx -o sbom.json .

# 校验 SBOM 与镜像签名
cosign verify $IMAGE --certificate-identity $IDENTITY --certificate-oidc-issuer $ISSUER

# 依赖投毒防护：锁定版本 + hash 校验（npm/pip 等）
# package-lock.json / poetry.lock 强制提交，CI 校验 lock 文件未篡改
```
供应链自动化还包括：镜像来源白名单、依赖策略（禁用已 EOL 版本）、内网镜像代理（阻断对上游的不可控拉取）。

