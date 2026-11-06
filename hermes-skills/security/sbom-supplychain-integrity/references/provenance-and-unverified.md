# REPORT — SBOM / 供应链完整性 技能包抽取报告

**产出**:`D:/skills4redteam/out/sbom-supplychain-integrity/`
**上游根**:`D:/skills4redteam/HiFullHouse-CyberSecurity-Skills/`(只读,未修改任何文件)
**铁律执行**:所有 CLI 子命令/flag 均取自上游文件或官方文档核验;凡「命令形态存在、但细节未逐版本核对」的一律在正文标记 **未验证**,清单见 §4。

---

## 1. 读了哪些文件

上游 12 个文件全部**全量通读**(含内嵌代码块、示例脚本、时间线):

| 上游文件 | 行数 | 处理 |
|---|---|---|
| `25-供应链安全-SupplyChainSecurity/skills/SBOM生成与验证-SBOMGeneration.md` | 328 | 主来源 |
| `25-供应链安全-SupplyChainSecurity/skills/代码签名与供应链完整性-CodeSigningIntegrity.md` | 251 | 主来源 |
| `25-供应链安全-SupplyChainSecurity/skills/软件依赖与开源合规审计-DependencyLicenseCompliance.md` | 285 | 主来源 |
| `25-供应链安全-SupplyChainSecurity/skills/供应链攻击检测与响应-SupplyChainAttackResponse.md` | 277 | 部分吸收 |
| `25-供应链安全-SupplyChainSecurity/skills/第三方供应商风险评估-ThirdPartyVendorRisk.md` | 278 | 重构后吸收 |
| `18-安全开发运维-DevSecOps/skills/CI-CD管道安全审计-CICDPipelineSecurity.md` | 190 | 吸收 |
| `18-安全开发运维-DevSecOps/skills/软件供应链安全-SoftwareSupplyChainSecurity.md` | 204 | 吸收 |
| `18-安全开发运维-DevSecOps/skills/IaC安全扫描-InfrastructureAsCodeSecurity.md` | 261 | 吸收 |
| `18-安全开发运维-DevSecOps/skills/SAST静态应用安全测试-SAST.md` | 225 | 吸收 |
| `18-安全开发运维-DevSecOps/skills/DAST动态应用安全测试-DAST.md` | 197 | 吸收 |
| `18-安全开发运维-DevSecOps/skills/安全需求与威胁建模-ThreatModeling.md` | 207 | **全篇丢弃**(理由见 §2.12) |
| `33-容器安全-ContainerSecurity/skills/容器镜像安全与漏洞扫描-ContainerImageSecurityScanning.md` | 288 | 吸收 |

本库既有卡(`supply-chain`、`dependency-confusion`、`supply-chain-risk-auditor`、`ci-cd-attack-testing`、`supply-chain-infra-hop`、`third-party-repo-audit`)按**技能清单里的名称与描述**做交叉引用;**未**读取这些卡片文件正文,因此不在本报告中对其内容做任何断言。

---

## 2. 逐文件:吸收了什么 / 丢弃了什么(附理由)

### 2.1 SBOM生成与验证-SBOMGeneration.md
- **吸收** → `references/sbom-signing-slsa.md` §1/§3/§8:Syft 生成(镜像/目录/多格式)、cdxgen 多语言生成、CycloneDX/SPDX CLI 用法、SBOM 格式验证与差异对比、Dependency-Track 部署与上传、GitHub Actions / GitLab CI 集成、SBOM 策略检查的思路。
- **修正后吸收**:上游用 shell 重定向(`syft ... -o cyclonedx-json > sbom.json`),改为官方 `-o <格式>=<文件>` 一步落盘;上游 `-t pip` / `-t nuget` 保留但加注「类型清单以 `cdxgen --help` 为准」;上游 `cdxgen --deep --generate-key` 标 **未验证**;上游 `使用go-spdx工具` 实际给的是 `go get github.com/spdx/tools-golang`(库,不是 CLI),丢弃该用法,SPDX 校验改用 `pyspdxtools`。
- **丢弃**:GPG 签名 SBOM(密钥分发与轮换无门槛,CI 场景被 cosign keyless 取代);上游内嵌的「SBOM策略自动检查」Python 脚本(自研代码、含硬编码路径,非可复制命令)。

### 2.2 代码签名与供应链完整性-CodeSigningIntegrity.md
- **吸收** → §4/§5/§6/§7:cosign 密钥模式/keyless/blob 全流程、Rekor 透明日志、SLSA 各等级落地、in-toto、TUF。
- **修正后吸收(关键)**:上游 keyless 验证只写 `cosign verify <image>`,**缺 `--certificate-identity` / `--certificate-oidc-issuer`**——照抄等于任何人的签名都能通过;文档补上并标明这是硬要求。上游「**SLSA Level 4 - 双人审查 + 可重现构建**」与 v1.0 不符(L4 已移除,现为 Build L1–L3),文档按 v1.0 写并显式提醒别照抄旧文;`cosign verify-attestation --type cyclonedx` 保留并补全 predicate 类型说明。
- **丢弃**:`pip install in-toto` / `pip install tuf` 的「装完即用」叙述——这两者没有可复制的通用 CLI 流水线,改为写信任模型与要点(§6/§7)。

### 2.3 软件依赖与开源合规审计-DependencyLicenseCompliance.md
- **吸收** → §9:OWASP Dependency-Check(含 `--suppression` / `--failOnCVSS` / `--nvdApiKey`)、safety、`npm audit` / `yarn audit`、`go list -m all`、`license-policy.yml` 三档(禁止/需审批/允许)结构、GitHub Actions 合规 job、`license-checker --failOn`。
- **补充**:上游未覆盖 Python 许可证清单导出,补 `pip-licenses`;补 `scancode` 做版权归属深度核对;补 `actions/dependency-review-action` 的 PR 门禁(含 `deny-licenses` 已被官方标注废弃这一点)。
- **丢弃**:FOSSA / Snyk 云端 API 调用片段——依赖外部账号,且上游示例把 token 直接写在命令行里,是坏示范,不适合作为参考材料固化。

### 2.4 供应链攻击检测与响应-SupplyChainAttackResponse.md
- **吸收** → `references/devsecops-scan-chain.md` §5 + `references/sbom-signing-slsa.md` §10:依赖混淆防护的配置面(pip 单源 / npm scope / 哈希锁定)、内部包命名前缀原则、GuardDog、Falco 运行时检测的定位。
- **修正后吸收**:上游 `pip hash requirements-locked.txt > requirements-hashes.txt` 的写法**不成立**——`pip hash` 只对已存在的本地文件算哈希,产不出可安装的 lock(本机 pip 26.2.1 实测该子命令仍存在但属遗留,故不能称其「已移除」);改为 `pip-compile --generate-hashes requirements.in` 生成哈希锁 + `pip install --require-hashes -r requirements.txt` 校验。
- **丢弃**:事件响应阶段清单(0-2h 确认 / 2-4h 遏制 / 4-… 根除)——属流程文档,与「SBOM/完整性工程面」无工具级交集,本库另有应急响应类卡;仅把可操作的一条(命中后**先轮换凭据再清历史**)写进扫描链 §4.1。上游内嵌的「供应链攻击检测引擎」Python 脚本同样丢弃。

### 2.5 第三方供应商风险评估-ThirdPartyVendorRisk.md
- **吸收并重构** → 新增 §10「第三方交付验收」:评级 API 的调用形态、合同关键条款、风险矩阵、事件通报 SLA。
- **再定位(本报告的关键取舍)**:上游以「发问卷 + 看评级分」为中心,这些**不可验证**。本卡把它改造成可验证门槛:合同写明交付必须带 SBOM + 签名 + 来源证明,验收跑 `cosign verify` / `cosign verify-attestation` / `slsa-verifier verify-image`,组件供应商的 SBOM 必须进我方 Dependency-Track,锁 digest 不锁版本,升级走 `cyclonedx diff` 评审;评级 API 降级为「外部输入而非结论」。
- **丢弃**:BitSight / SecurityScorecard 的字段级细节(未验证)与问卷自动化 Python 实现。

### 2.6 CI-CD管道安全审计-CICDPipelineSecurity.md
- **吸收** → `devsecops-scan-chain.md` §4:TruffleHog(含 `file://` 前缀这类易错点)、GitGuardian `ggshield`、Gitleaks、CI 变量(masked)检查、构建环境隔离(Dockerfile 非 root / 多阶段)、GitHub Actions 安全实践、CI/CD 攻击路径。
- **修正后吸收**:上游 `zricethezav/gitleaks ... detect --source=/path` —— `detect` 自 v8.19 起弃用,文档给 `gitleaks git .` / `gitleaks dir .`,并把旧入口标为「已弃用仍可用」;补 `gh api` 侧的权限/缓存/secret-scanning/push protection 审计命令(`actions/permissions/workflow`、`actions/caches`、`secret-scanning/alerts`)。
- **丢弃**:Jenkins / GitLab 的平台专属配置示例(保留可迁移原则:最小权限、OIDC 短时凭据、匿名读关闭)。

### 2.7 IaC安全扫描-InfrastructureAsCodeSecurity.md
- **吸收** → `devsecops-scan-chain.md` §1:checkov(框架/输出格式/跳过检查/配置文件)、tfsec、KICS、kube-linter / polaris / conftest / kubesec 的定位、IaC 基线清单。
- **修正后吸收**:tfsec 已 EOL 并入 Trivy,首选改为 `trivy config`;`tfsec --no-colour` 保留但标 **未验证**(拼写在版本间变过);checkov 的 `-o sarif > report` 改为注明 `--output-file-path` 只接受目录。
- **丢弃**:kube-linter / polaris / conftest / kubesec 的详细示例——属 K8s 配置面,本库容器/K8s 类卡已覆盖,参考文件里只点名工具以免重复造卡。

### 2.8 SAST静态应用安全测试-SAST.md
- **吸收** → `devsecops-scan-chain.md` §2:semgrep 预定义规则/自定义规则/输出格式/`--baseline-commit`/CI 模式、CodeQL 建库与查询、语言特定检查、pre-commit。
- **修正后吸收**:补 `--error` 才是门禁开关、`semgrep scan` 是新版入口、`semgrep/semgrep-action@v1` 已废弃(改用官方镜像);CodeQL 补官方 query pack、`security-extended` 套件与 GitHub Actions `init/analyze@v3`。
- **丢弃**:SonarQube(Docker 部署 + 质量门禁治理,需独立服务端,与本次主题无关);上游内嵌的 CodeQL `.ql` 片段是示例代码而非命令。

### 2.9 DAST动态应用安全测试-DAST.md
- **吸收** → `devsecops-scan-chain.md` §3:ZAP 被动/主动/API 扫描、ZAP daemon + JSON API(spider / ascan / context / authentication)、CI 集成、扫描检查清单。
- **修正后吸收**:上游混用 daemon + `curl` 调 JSON API,对 CI 不友好,改为 CI 里真正能跑的 `zap-baseline.py` / `zap-full-scan.py` / `zap-api-scan.py` 三个容器脚本,并补 `-I`(降噪不失败)/ `-j` / `-m` / `-c` / `-z` 语义;GH Action / GitLab 模板名保留但标 tag **未验证**。
- **丢弃**:Python ZAP 客户端示例代码与逐条 JSON API 调用(需真实目标才能验证,且篇幅不成比例)。

### 2.10 软件供应链安全-SoftwareSupplyChainSecurity.md
- **吸收** → 两份参考文件多处:Trivy 镜像/repo 扫描、Syft、SBOM 格式比较、SLSA 等级、`.npmrc` 防混淆、制品签名与验证。
- **修正后吸收**:上游同一生态里同时出现 `@cyclonedx/cdxgen` 与 `npm install -g @cyclonedx/bom`(后者为旧包),统一为 `@cyclonedx/cdxgen`;上游 `syft /project -o cyclonedx`(缺 `dir:` 前缀、`cyclonedx` 裸格式名可疑)改为 `syft dir:. -o cyclonedx-json=sbom.cdx.json`。
- **丢弃**:Snyk 云端操作流程(账号依赖,同上 §2.3 理由)。

### 2.11 容器镜像安全与漏洞扫描-ContainerImageSecurityScanning.md
- **吸收** → 两份参考文件:Trivy / Grype / Syft / Docker Scout 的真实命令、严重性过滤、`--exit-code`、`--ignore-unfixed`、`--input`、`--image-src`、私有仓库认证、`grype -o cyclonedx`、镜像扫描的 CI 退出码用法。这是「镜像 SBOM + 扫描」维度的主来源。
- **修正后吸收**:基本保留原命令(这是 12 个文件里命令质量最高的一份);仅在正文统一到 `-o <格式>=<文件>` 与 `--format cyclonedx` 两种官方写法并注明差异。
- **丢弃**:Dockerfile 最佳实践长清单(属容器加固面,不在本卡范围)。

### 2.12 安全需求与威胁建模-ThreatModeling.md
- **全篇丢弃**。理由:STRIDE / PASTA / OWASP ASVS / Threat Dragon / Cornucopia 属**设计阶段方法论**,与「SBOM / 签名 / 来源证明 / 依赖与许可证合规」没有任何工具级交集;上游内嵌的威胁模型 JSON 片段也不可复用。唯一的桥接点写在此处备查:若要做「依赖风险的威胁建模」,从 STRIDE 的 Tampering / Supply Chain 条目切入,再回到本卡的命令面。

---

## 3. 哪些来自上游 / 哪些是补充

**来自上游(命令形态原样保留,已标注修正的除外)**:syft / trivy / grype / cdxgen 的生成与扫描、cosign 全流程、checkov / tfsec / kics、semgrep / codeql / bandit / gosec、ZAP 与 nuclei、trufflehog / ggshield / gitleaks、OWASP Dependency-Check、`license-checker`、Dependency-Track 部署与 BOM 上传、`license-policy.yml` 三档策略结构、`.npmrc` / pip 防混淆配置的骨架。

**本会话补充(上游没有、写错或写得不完整,经公开文档核验后新增)**:
1. `cyclonedx validate / diff / convert / merge` 与 `pyspdxtools`(上游把 python 包与 .NET CLI 混为一谈)。
2. sigstore keyless 验证**必须**带 `--certificate-identity` / `--certificate-oidc-issuer`;`cosign sign-blob --bundle`;**禁止**用 `cosign attach sbom`(已废弃、不签名),改用 `cosign attest`。
3. `slsa-verifier verify-artifact` / `verify-image` 与 `gh attestation verify`;SLSA v1.0 三级制与 slsa-github-generator(`builder_go_slsa3` / `generator_container_slsa3`)。
4. in-toto 真实子命令集(`in-toto-run` / `in-toto-record` / `in-toto-verify`;不存在 `in-toto-keygen` 之类)与 TUF 的信任模型要点。
5. Dependency-Track 的表单式上传(`autoCreate=true` + `X-Api-Key`)与 `/api/v1/vulnerability/project/$UUID` 查询。
6. `actions/dependency-review-action` 的 `allow-licenses` / `deny-licenses` 语义(`deny-licenses` 已废弃)与 `comment-summary-in-pr`。
7. `pip-licenses` / `scancode` / `osv-scanner` v2(`--sbom` 已废弃)用法。
8. CI/CD 管道审计的 `gh api` 命令族(workflow 默认权限、`actions/caches`、`secret-scanning/alerts`、push protection)与 `actionlint` / `zizmor` / `poutine`。
9. 依赖混淆防护的完整配置面:pip 单源 + `--require-hashes` + `NPM_CONFIG_IGNORE_SCRIPTS`/`ignore-scripts`、yarn berry、Maven `mirrorOf *`、NuGet `packageSourceMapping`、Cargo `source.crates-io.replace-with`、Go `GOPRIVATE`/`GOPROXY`。
10. §10「第三方交付验收」——把上游问卷式供应商评估改成可验证门槛。

---

## 4. 核验方法与「未验证」清单

- **方法**:① 12 个上游文件全量通读;② 本机核对(`which syft trivy grype cosign cdxgen semgrep checkov tfsec kics …` 探测工具链;`pip --version` / `pip hash --help` 实测 pip 26.2.1 仍保留 `pip hash`),避免把「凭印象的工具状态」当结论写进文档;③ 针对 20 个**易记错**的事实做公开文档检索(in-toto 子命令、guarddog、gitleaks v8.19 弃用、syft 输出语法、cosign predicate 类型、SLSA v1.0 与 L4 移除、Dependency-Track BOM API、trivy config / license、checkov 与 tfsec 现状、dependency-review-action 输入、cyclonedx-cli、pip-licenses / license-checker / scancode、osv-scanner、slsa-verifier、cosign attest / attach、cdxgen 类型与参数、grype `--fail-on`)。
- **未做**:无真实目标、无可用流水线,**未做任何端到端执行验证**(既不构建镜像也不跑 CI);因此凡是「命令存在、但用法细节未逐版本核对」的一律在正文标注 **未验证**:
  1. `syft --scope all-layers` 在 1.x 的确切语义(上游为 0.x 写法)。
  2. `cdxgen --deep` / `--generate-key` 是否仍存在;`-t` 的完整类型清单。
  3. checkov `--output-file-path` 的精确拼写与是否只接受目录;kics `--fail-on` 取值集合;tfsec `--no-colour` vs `--no-color`。
  4. `codeql pack download` 的离线落盘路径;bandit `-f sarif` 需额外装 `bandit-sarif-formatter`。
  5. `zaproxy/action-baseline` 等 action 的确切 tag;GitLab 把 `Security/SAST.gitlab-ci.yml` 迁到 CI/CD Components 后的弃用时间点。
  6. `trivy config --config-policy` 自定义 rego 的行为。
  7. uv `[[tool.uv.index]] explicit` 键的版本行为。
  8. 自托管 runner 的目录与 `.credentials` 文件布局(随 runner 版本/安装方式变化)。
  9. BitSight / SecurityScorecard 的字段稳定性与调用额度。
  10. Dependency-Track 首次登录的初始 admin 密码获取方式(随版本变化,文档里只写「按官方文档获取」,不写具体路径或值)。
- **已知缺口(本次未覆盖,需要时可扩展)**:SBOM 与 VEX 的联动、SLSA provenance 的纯离线校验、Dependency-Track 与 Gitea/Jenkins 的集成、许可证与 SPDX License List 版本对齐、SBOM 在制品库中的存储与保留策略。

---

## 5. 交付物

| 文件 | 行数 | 状态 |
|---|---|---|
| `references/sbom-signing-slsa.md` | 219(限 220) | 完成 |
| `references/devsecops-scan-chain.md` | 175(限 180) | 完成 |
| `DRAFT-SKILL.md` | 正文 65 行(限 120),frontmatter 仅 `name`/`description` | 完成 |
| `REPORT.md` | 本文件 | 完成 |

**未做的事**:没有修改、移动或删除上游任何文件;没有把上游的 Python 示例脚本原样搬进来(只取命令与结构);没有写入任何真实凭据(文档中出现的全是环境变量名或占位符,如 `$DTRACK_API_KEY`、`$UUID`)。
