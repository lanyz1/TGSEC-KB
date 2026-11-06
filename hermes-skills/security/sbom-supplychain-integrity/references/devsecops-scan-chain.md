# DevSecOps 扫描链与管道攻击面 工程参考

> 配套技能卡 `sbom-supplychain-integrity`。未标注 = 已对官方文档核对;**未验证** = 未逐版本核对。
> 上游素材:`18-安全开发运维-DevSecOps/skills/{CI-CD管道安全审计, IaC安全扫描, SAST, DAST, 安全需求与威胁建模, 软件供应链安全}.md` + `33-容器安全-ContainerSecurity/skills/容器镜像安全与漏洞扫描.md`。
> 对抗利用面见本库 `ci-cd-attack-testing`、`supply-chain-infra-hop`、`dependency-confusion`;本文只写**扫描命令 + 加固配置 + 审计命令**。

## 1. IaC 扫描
### Trivy(现役首选:tfsec 已 EOL 并入 Trivy)
```bash
trivy config . --severity HIGH,CRITICAL --exit-code 1        # 目录递归: TF/K8s/Dockerfile/CFN
trivy config --format sarif -o iac.sarif . ; trivy fs --scanners misconfig,secret,vuln .
trivy kubernetes --scanners misconfig,secret --report summary cluster
trivy config --skip-dirs ./vendor --skip-files Dockerfile.dev .
```
`.trivyignore` 放豁免(`--ignorefile` 换路径);`--include-non-failures` 出全量。**未验证**:`--config-policy` 自定义 rego 的确切行为。
### Checkov(策略最多, 自带 secrets 与 terraform plan 模式)
```bash
pip install checkov
checkov -d . --framework terraform,terraform_plan,kubernetes,dockerfile,github_actions
checkov -d . -o sarif --output-file-path ./reports ; checkov -f main.tf --check CKV_AWS_20 --skip-check CKV_AWS_9999 --soft-fail
checkov -d . --skip-path ./examples --compact --quiet
```
**未验证**:`--output-file-path` 只接受目录(不是文件名)以及 `--download-external-modules true`。
### KICS(Checkmarx, 容器化最省心)
```bash
docker run -t -v "$PWD:/path" checkmarx/kics:latest scan -p /path -o /path/out --report-formats json,sarif,html --ignore-on-exit results
kics scan -p ./infra --exclude-paths "**/test/**"
```
`--ignore-on-exit results` = 有发现但无错误时仍返 0,便于 CI 分级。**未验证**:`--fail-on` 的取值集合。
### tfsec(已停止维护, 仅用于兼容旧流水线)
仅需 `tfsec . --format json --out tfsec.json --minimum-severity HIGH --soft-fail`;`--no-colour` / `--no-color` 拼写在版本间变过(**未验证**),新项目直接用 `trivy config`。
## 2. SAST
### Semgrep
```bash
pip install semgrep
semgrep scan --config=p/default --sarif -o semgrep.sarif --error .     # --error: 有发现即 exit 1
semgrep scan --config=p/python --config=p/secrets --json -o out.json .
semgrep scan --config=auto --exclude tests --timeout 30 --metrics=off .
semgrep scan --config=./rules/ --baseline-commit "$BASE_SHA" .         # 只报本次改动引入的问题
semgrep ci                                                             # 接 AppSec 平台(要 SEMGREP_APP_TOKEN)
```
`--error` 才是门禁开关,不加永远 exit 0;`semgrep scan` 是新版入口(`semgrep` 裸调用等价)。`semgrep/semgrep-action@v1` **已废弃**,CI 改用官方镜像 `semgrep/semgrep:latest` 跑 `semgrep ci` / `scan`。
### CodeQL(数据流最准;编译型语言要能 build)
```bash
codeql database create db --language=javascript-typescript --source-root .
codeql database create db --language=java --command="./gradlew build -x test"
codeql pack download codeql/java-queries
codeql database analyze db codeql/java-queries:codeql-suites/java-security-extended.qls --format=sarif-latest --output=codeql.sarif --threads=0
```
`--threads=0` 用满核,`--ram=4096` 调内存。**未验证**:`codeql pack download` 的离线包落盘路径。
### 语言专用
`bandit -r . -f json -o bandit.json -ll -x ./tests -s B101`(`-ll` = 中危且中置信)、`bandit -r . -c .bandit.yaml`、`gosec -fmt=json -out=gosec.json -severity high -confidence high ./...`、`gosec -include=G101,G102 -no-fail ./...`、`npx eslint . --format sarif -o eslint.sarif`。**未验证**:bandit 的 `-f sarif` 需额外安装 `bandit-sarif-formatter`。
### CI 串联
```yaml
# GitHub Actions: CodeQL 原生 + semgrep 容器
permissions: { contents: read, security-events: write, packages: read }
- uses: github/codeql-action/init@v3
  with: { languages: javascript-typescript, queries: security-extended }
- run: semgrep scan --config=p/default --sarif -o semgrep.sarif --error .
- uses: github/codeql-action/analyze@v3          # 上传 SARIF 到 Security 面板
```
```yaml
# GitLab: 官方模板一次装齐 SAST / Secret / 依赖扫描
include: [{ template: Security/SAST.gitlab-ci.yml }, { template: Security/Secret-Detection.gitlab-ci.yml }, { template: Security/Dependency-Scanning.gitlab-ci.yml }]
variables: { SAST_EXCLUDED_PATHS: "spec,test,tests,tmp" }
```
**未验证**:GitLab 17+ 迁到 CI/CD Components(`gitlab.com/components/sast/sast@main`)后旧模板的弃用时间点。
## 3. DAST
### OWASP ZAP(容器脚本三件套)
```bash
docker run -v "$PWD:/zap/wrk:rw" -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://staging.example.com -r zap.html -J zap.json -c zap.conf -I -j
docker run -v "$PWD:/zap/wrk:rw" -t ghcr.io/zaproxy/zaproxy:stable zap-full-scan.py -t https://staging.example.com -m 10 -J zap.json   # 主动扫描
docker run -v "$PWD:/zap/wrk:rw" -t ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t https://api.example.com/openapi.json -f openapi -r zap-api.html
```
- `-I` = 只报警告不失败(降噪);`-j` 启 AJAX Spider;`-m` 分钟上限;`-c` 配置文件;`-z` 透传 ZAP 参数。
- GitHub Actions 用 `zaproxy/action-baseline@v0`(另有 `action-full-scan` / `action-api-scan`,入参 `target` / `rules_file_name` / `fail_action`,**未验证**确切 tag);GitLab 用 `- { template: Security/DAST.gitlab-ci.yml }` + `DAST_WEBSITE` / `DAST_FULL_SCAN_ENABLED` / `DAST_API_OPENAPI`,登录态自行注入 cookie/header,别写进 YAML。
### Nuclei(部署后回归)
```bash
nuclei -update-templates
nuclei -u https://staging.example.com -severity critical,high,medium -jsonl -o nuclei.jsonl
nuclei -l urls.txt -t http/cves/ -tags cve,exposure -rl 50 -c 25 -timeout 10 -retries 2 -stats
nuclei -u https://target -as -silent          # -as: 按指纹自动选模板
```
只对**授权且非生产**目标跑;`-rl`(每秒请求)/`-c`(并发)必须显式压低,否则等于自伤可用性。
## 4. CI/CD 管道攻击面 → 审计命令
### 4.1 Secrets 泄露(最高频)
```bash
gitleaks git . --redact -f sarif -r gitleaks.sarif      # v8.19+ 新入口
gitleaks dir . --redact -f json -r gitleaks.json        # 未提交/本地目录
gitleaks detect --source . --verbose -r gitleaks.json   # 旧入口(已弃用, 仍可用)
trufflehog git file://. --since-commit HEAD~50 --only-verified --json > th.json   # 认 file:// 前缀
ggshield secret scan path .        # 另有 pre-commit / docker / ci 子命令
git log -p --all -S 'AKIA' -- .    # 历史里搜特征串
```
命中后先**轮换凭据**再清历史(`git filter-repo` / BFG + 强推),顺序反了等于白做。平台侧开 push protection:
```bash
gh api /repos/OWNER/REPO/secret-scanning/alerts --jq '.[] | {secret_type,state,html_url}'
gh api -X PATCH /repos/OWNER/REPO -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
```
### 4.2 自托管 runner 与工作流权限
```bash
gh api /orgs/ORG/actions/runners --jq '.runners[] | {name,os,status,labels}'
gh api /repos/OWNER/REPO/actions/permissions/workflow --jq .     # GITHUB_TOKEN 默认权限
gh api -X PUT /repos/OWNER/REPO/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
```
默认设 `read` 且禁止 Actions 自批 PR,只在需要时于 job 内逐项放开 `permissions:`。自托管 runner:public repo 一律禁用(任何人可提 PR 直打内网),不进生产网、不挂长期云凭据;主机侧盘点 `ps aux | grep -i 'Runner.Listener'` 与 `find / -path '*actions-runner*.credentials*'`(**未验证**目录/凭据文件的确切布局)。
### 4.3 缓存投毒与制品污染
```bash
gh api /repos/OWNER/REPO/actions/caches --jq '.actions_caches[] | {key,ref,size_in_bytes}'
gh api -X DELETE /repos/OWNER/REPO/actions/caches/<cache_id>     # 发现异常缓存立即清
```
`actions/cache` 的 key 跨分支可读,`restore-keys` 会命中他人分支写入的同名前缀缓存 → 上游 PR 可投毒 main 的构建。加固:只缓存可重算的中间产物(别存 `dist/` 最终制品)、制品改用 `actions/upload-artifact@v4` 并校验和、同一 job 不得既吃不可信缓存又持生产凭据。
### 4.4 危险触发与制品库权限
```bash
rg -n 'pull_request_target|workflow_run|issue_comment|\$\{\{ *github\.event\.(issue|pull_request)\.(title|body)' .github/workflows/
actionlint .github/workflows/*.yml     # 语法 + shellcheck 级静态检查
zizmor .github/workflows/              # 专查 pwn-request / 模板注入 / 凭据泄露
poutine scan -f .                      # 同类管道扫描器
```
`pull_request_target` / `workflow_run` + 检出 PR 代码 + 有 secrets = 典型 pwn request:要么删掉"检出不可信代码",要么改两段式(第一段只读、无 secrets)。
```bash
curl -s http://nexus:8081/service/rest/v1/repositories | jq .        # 匿名可读 = 全量依赖与内网包泄露
curl -s -u "$U:$P" http://nexus:8081/service/rest/v1/security/anonymous
curl -s -u "$U:$P" http://artifactory:8082/api/repositories | jq .
npm token list ; gh api /repos/OWNER/REPO/branches/main/protection --jq .
```
加固:关掉匿名读;发布权限按包/按令牌最小化(npm granular token;PyPI 用 OIDC trusted publishing 免长令牌);`.github/workflows/**` 进 CODEOWNERS 且分支保护必须过评审。
## 5. 依赖混淆防护配置
### Python
```ini
# /etc/pip.conf —— 只用单一 index-url, 不要 extra-index-url
[global]
index-url = https://nexus.corp/repository/pypi-group/simple
trusted-host = nexus.corp
```
```bash
pip config set global.index-url https://nexus.corp/repository/pypi-group/simple
pip-compile --generate-hashes requirements.in > requirements.txt   # pip-tools 生成哈希
pip install --require-hashes -r requirements.txt                   # 装包即校验哈希
pip download corp-internal --no-index --find-links ./vendor        # 内网包只走内网源
```
**`extra-index-url` 是依赖混淆的教科书入口**:私有源未命中时 pip 会去 PyPI 找同名包。正确做法是让 Nexus/Artifactory 的 group/virtual 源聚合 PyPI + 私有源,客户端只配一个 `index-url`;`--require-hashes` 作第二道闸。uv 等价写法:`[[tool.uv.index]] name="corp" url="..." explicit=true`(`explicit` = 该源只服务显式指定的包)。**未验证**:`explicit` 键的版本行为。
### Node
```ini
# .npmrc(仓库级, 提交进 VCS)
@corp:registry=https://nexus.corp/repository/npm-private/
registry=https://nexus.corp/repository/npm-group/
//nexus.corp/repository/npm-private/:_authToken=${NPM_TOKEN}
ignore-scripts=true
```
```bash
npm audit signatures ; npm install --ignore-scripts ; npm view some-pkg --json | jq '{name,version,dist}'
```
`npm audit signatures` 校验 registry 签名/provenance;`--ignore-scripts` 禁 postinstall(供应链投毒的常见载体)。`@scope` 的私有 registry **不会回落公共源**,故内部包必须带 scope;无 scope 的私有包名有被抢注的风险。yarn berry(`.yarnrc.yml`):`npmRegistryServer` + `npmScopes:` 显式列举、`enableImmutableInstalls: true`、`enableScripts: false`。
### Go / Java / .NET / Rust
```bash
export GOPRIVATE='corp.com/*' GOPROXY='https://goproxy.corp,direct' GOSUMDB='sum.golang.org' ; go mod verify
```
```xml
<!-- Maven settings.xml: mirrorOf * 让所有第三方坐标无法直连公网 -->
<mirrors><mirror><id>corp</id><mirrorOf>*</mirrorOf><url>https://nexus.corp/repository/maven-public/</url></mirror></mirrors>
```
```xml
<!-- NuGet.config: 清空默认源 + packageSourceMapping 把前缀钉到指定源 -->
<packageSources><clear/><add key="corp" value="https://nexus.corp/repository/nuget-group/index.json"/></packageSources>
<packageSourceMapping><packageSource key="corp"><package pattern="Corp.*"/><package pattern="*"/></packageSource></packageSourceMapping>
```
Cargo(`.cargo/config.toml` 用私有源替换 crates-io):`source.crates-io.replace-with = "corp"` + `source.corp.registry = "sparse+https://cargo.corp/index/"`。
## 6. 落地顺序与坑
- 顺序:① secrets 扫描 + 清历史 → ② 装包硬化(单源 index-url + require-hashes + ignore-scripts) → ③ SAST/IaC 进 PR(带 baseline, 只卡新增) → ④ SBOM + 签名(见 `references/sbom-signing-slsa.md`) → ⑤ DAST 进 nightly。
- 坑 1:上 `--error`/`--exit-code` 却不做 baseline,老代码一开几百条,团队立刻绕过 → 先 `--soft-fail` 观测两周。
- 坑 2:DAST 打生产 = 事故。ZAP 主动扫描 / nuclei 只对 staging,且压 `-rl` / `-m`。
- 坑 3:扫描器 token 明文进 CI 变量 = 新增一个泄露面;优先 OIDC 短时凭据。坑 4:漏洞库更新不了(离线环境)时报"无发现"是假的,需定期同步 trivy / grype / osv 数据库。
