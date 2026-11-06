## 十、工具链

### 10.1 静态分析（SAST）

```bash
# 快速、可自定义规则、多语言
semgrep scan --config=auto --severity=ERROR,WARNING ./src
semgrep scan --config=p/owasp-top-ten ./src

# 语义级分析（自定义查询语言，跨过程污点追踪）
codeql database create ./db --language=java --source-root=./src
codeql database analyze ./db security-and-quality.qls --format=sarif-latest

# 企业级
SonarQube           # 代码质量+安全，质量门禁
Checkmarx One       # 企业治理、75+ 语言
Fortify / Veracode  # 大型企业合规

# 语言专项
bandit ./src -r                     # Python
gosec ./...                          # Go
npm audit; eslint-plugin-security    # Node.js
spotbugs / find-sec-bugs             # Java
```

### 10.2 依赖与供应链（SCA）

```bash
trivy fs --scanners vuln,secret,misconfig .   # 快、全能
grype ./                                       # Anchore
snyk test --all-projects
npm audit --json; pip audit
owasp-dependency-check.sh --scan .
syft dir:./src -o spdx-json > sbom.json        # SBOM
npx supply-chain-guard scan ./                 # 恶意包/投毒专项
```

### 10.3 密钥检测

```bash
gitleaks detect --source . --log-opts="--all"
trufflehog git https://github.com/org/repo
git-secrets --scan-history
# 注意：历史提交中的密钥需清除重写（git filter-repo），删除文件不够
```

### 10.4 反混淆与逆向

```bash
# 静态去混淆
npx js-beautify suspect.js -o clean.js
de4js / JSDetox / JStillery         # JS 去混淆
npx esprima clean.js > ast.json     # AST 分析

# Java/.NET 反编译
jadx apk/app.jar                    # Java/Android
jd-gui / CFR                        # Java
dnSpy                               # .NET
Ghidra / IDA                        # 二进制

# 动态
cuckoo / CAPE（沙箱）; Node 受控 VM; 隔离网段流量捕获
```

### 10.5 AI 辅助审计工具（2025-2026）

```bash
# 开源 AI 安全框架/技能
# Cloudflare security-audit-skill（多智能体+对抗验证）
# Capital One VulnHunter（Hunt/Fix/Verify + 反驳引擎，Claude Code skill）
# Google mantis / Trail of Bits skills（技能包）
# Vercel deepsec / raptor（SAST+LLM+fuzz 综合）

# 商业 AI SAST
# Semgrep Assistant（AI 分类/去噪）; GitHub Copilot Autofix; Snyk Code Agent Fix
# OpenAI Codex Security（2026-07 发布：identify/validate/fix 三合一 CLI）
```

