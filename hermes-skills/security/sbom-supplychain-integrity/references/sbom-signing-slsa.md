# SBOM / 签名 / SLSA 来源证明 工程参考

> 配套技能卡 `sbom-supplychain-integrity`。约定:未标注 = 已对官方文档/仓库核对;标 **未验证** = 未逐版本核对,升级后请重验。
> 上游素材:`HiFullHouse-CyberSecurity-Skills/25-供应链安全-SupplyChainSecurity/skills/{SBOM生成与验证, 代码签名与供应链完整性, 软件依赖与开源合规审计}.md`、`33-容器安全-ContainerSecurity/skills/容器镜像安全与漏洞扫描.md`、`18-安全开发运维-DevSecOps/skills/软件供应链安全.md`。

## 1. 生成 SBOM(真实命令)

### Syft(Anchore)
```bash
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
syft alpine:latest -o cyclonedx-json=sbom.cdx.json      # "格式=文件" 一步落盘(已验证)
syft dir:. -o spdx-json=sbom.spdx.json
syft file:app.tar.gz -o syft-json=sbom.syft.json
```
- 输出格式:`cyclonedx-json / cyclonedx-xml / spdx-json / spdx-tag-value / syft-json / table`;源前缀 `dir: file: image: registry: oci-dir: oci-archive: docker-archive: sbom:`。
- `syft-json` 是原生格式(Grype 能直读),不是行业交换格式 —— 对外交付一律 CycloneDX/SPDX。
- 上游的 `syft packages <target>` 与 `--scope all-layers` 是 syft 0.x 用法;1.x 把 `packages` 降为兼容别名、默认扫全层。**未验证**:两代 `--scope` 的精确语义差异。

### Trivy(顺路出 SBOM + 漏洞)
```bash
trivy image --format cyclonedx --output sbom.cdx.json nginx:latest     # 已验证
trivy image --format spdx-json --output sbom.spdx.json nginx:latest
trivy fs --format cyclonedx -o sbom.cdx.json .
trivy image --scanners vuln,misconfig,secret,license nginx:latest
trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 nginx:latest
trivy sbom sbom.cdx.json --severity CRITICAL,HIGH     # 消费第三方 SBOM(见 §9)
trivy config Dockerfile                               # 配置/IaC 面, 详见 devsecops-scan-chain.md
```
坑:Trivy 的 SPDX 格式名是 `spdx-json`,与 Syft 的 `spdx-tag-value` 不同名;CycloneDX 两家都叫 `cyclonedx*` 但规范版本可能不同,入库前按 §3 校验。

### cdxgen(CycloneDX 官方生成器,Java/多模块依赖解析最准)
```bash
npm install -g @cyclonedx/cdxgen
cdxgen -t maven -o sbom.json                          # 省略 -t 则自动探测
cdxgen -r /app -o sbom.json                           # -r/--recurse 递归多模块
docker run --rm -v "$PWD:/app" -w /app ghcr.io/cyclonedx/cdxgen:latest -r /app -o /app/sbom.json
FETCH_LICENSE=true cdxgen -t npm -o sbom.json          # 联网解析许可证(默认关, 慢)
```
- `-t` 常见值:`maven / gradle / npm / python(pip、poetry 为别名) / golang / csharp / php / ruby`。**未验证**:完整清单以 `cdxgen --help` 为准;上游的 `--deep`、`--generate-key` **未验证**是否仍存在(签名请走 §4)。

## 2. CycloneDX vs SPDX(交付选型)
| 维度 | CycloneDX | SPDX |
|:---|:---|:---|
| 主管 | OWASP | Linux Foundation(ISO/IEC 5962) |
| 强项 | 漏洞/VEX/服务/ML 组件,贴合 Dependency-Track、Grype 生态 | 许可证与版权字段最完整,法务合规首选 |
| 版本 | 1.0–1.7(JSON/XML/protobuf/CSV) | 2.2 / 2.3(tag-value/JSON/YAML/RDF/XML) |
| 互转 | `cyclonedx-cli convert` 支持 `spdxjson` 双向 | 同左,**但会丢字段**(SPDX→CDX→SPDX 常报 `license_info_in_file is mandatory`) |
结论:流水线内用 CycloneDX(直接喂 Dependency-Track/Grype);对外法务交付另出 SPDX(Syft 一次扫两种格式最省事)。

## 3. 校验与 diff(生成 ≠ 有效)
```bash
# CycloneDX 官方 CLI(.NET 单文件, CI 友好)
cyclonedx validate --input-file sbom.json --input-format json --input-version v1_6 --fail-on-errors
cyclonedx convert  --input-file sbom.json --output-format spdxjson --output-file sbom.spdx.json
cyclonedx diff     old-sbom.json new-sbom.json        # 组件级差异, 可作 PR 评论
cyclonedx merge    --input-files a.json b.json --output-file merged.json
# SPDX(python spdx-tools: 默认就校验, 没有 validate/validation 子命令)
pyspdxtools -i sbom.spdx.json -o roundtrip.spdx.json  # 无效文档非 0 退出
pyspdxtools -i sbom.spdx.json --novalidation -o out.json
```
- 上游的 `cyclonedx validate --input-file ...` **子命令是真的**,但属 .NET `cyclonedx-cli`;先 `pip install cyclonedx-bom` 再调 `cyclonedx validate` 通常失败(python 包给的是 `cyclonedx-py`)。**未验证**:python 包是否也装 `cyclonedx` 入口。
- 上游的 `spdx-tools validation validate sbom.spdx` **该命令不存在**,真实入口是 `pyspdxtools`(需 `pip install spdx-tools`)。
- `cyclonedx diff` 是"供应链变更评审"的核心动作:接进 PR,新增/降级组件强制人工过目。

## 4. cosign / Sigstore(签名 + 来源证明)
```bash
# ① 密钥模式
cosign generate-key-pair
cosign sign --key cosign.key registry.corp/app:1.0
cosign verify --key cosign.pub registry.corp/app:1.0
# ② keyless(OIDC → Fulcio 短时证书 → Rekor 透明日志); CI 必须 --yes 免交互
cosign sign --yes registry.corp/app:1.0
cosign verify registry.corp/app:1.0 \
  --certificate-identity   https://github.com/ORG/REPO/.github/workflows/release.yml@refs/heads/main \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
# ③ blob(二进制/脚本/裸 SBOM 文件)
cosign sign-blob   artifact.tar.gz --bundle artifact.sigstore.json --yes
cosign verify-blob artifact.tar.gz --bundle artifact.sigstore.json \
  --certificate-identity "$ID" --certificate-oidc-issuer https://token.actions.githubusercontent.com
# ④ SBOM 的正确关联方式: in-toto attestation, 不是 attach
cosign attest  --predicate sbom.cdx.json --type cyclonedx registry.corp/app:1.0
cosign verify-attestation --type cyclonedx registry.corp/app:1.0 \
  --certificate-identity "$ID" --certificate-oidc-issuer "$ISSUER"
cosign download attestation registry.corp/app:1.0 | jq -r .payload | base64 -d | jq .predicate
cosign tree registry.corp/app:1.0          # 列镜像上的签名/attestation
```
- `--type` 合法值:`slsaprovenance | slsaprovenance02 | slsaprovenance1 | link | spdx | spdxjson | cyclonedx | vuln | openvex | custom`(已验证)。
- **`cosign attach sbom` 已废弃**(官方称 2024-02-22 后不久的版本移除),且它**不签名**;`--type` 只接受 `spdx|cyclonedx|syft`。→ 统一用 `cosign attest`。
- 上游 `cosign verify-attestation --type cyclonedx <img>` 单独用**在 keyless 下会失败**:v2+ 强制 identity/issuer,否则任何人都能签个冒充的 attestation。
- 气隙:`cosign initialize`(拉 Sigstore TUF root)→ `cosign save <img> --dir ./img` → `cosign verify --local-image ./img --offline=true --trusted-root ~/.sigstore/root/tuf-repo-cdn.sigstore.dev/targets/trusted_root.json`。
- 透明日志:`rekor-cli search --sha sha256:<digest>`、`rekor-cli get --log-index <n> --format json`。**未验证**:旧写法 `rekor-cli search --artifact` 是否仍可用。

## 5. SLSA 等级与落地
- **口径两套,别混**:v0.2 有 1–4 级;v1.0(现行)只有 **Build L1/L2/L3**,L4 已移除。上游表格里的 "SLSA 4" 属旧口径。L1=构建有文档化/自动化流程并产出 provenance;L2=跑在托管构建服务上、provenance 由服务签名;L3=构建环境隔离防篡改、provenance 不可伪造(需受信 builder)。
- 落地顺序(性价比):① 制品 `cosign sign` keyless;② CI 出 SBOM 并 `cosign attest`;③ 用受信 builder 生成 provenance;④ 部署侧只放行验证通过的制品。
```yaml
# GitHub 受信 builder: digest 必填 —— 不传就有 TOCTOU 窗口
jobs:
  build:
    permissions: { contents: read, id-token: write, packages: write }
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v1.9.0
    with: { image: ghcr.io/${{ github.repository }}, digest: ${{ needs.build.outputs.digest }} }
```
**未验证**:`@v1.9.0`、`.github/workflows/builder_go_slsa3.yml` 的具体 tag(上游写 v1.9.0/v1.4.0)是否仍是最新。
```bash
# 消费侧验证(锁 digest, 不锁 tag)
go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@latest
IMAGE="registry.corp/app@$(crane digest registry.corp/app:1.0)"
slsa-verifier verify-image "$IMAGE" --source-uri github.com/ORG/REPO --source-tag v1.0.0 \
  --builder-id "https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@refs/tags/v1.9.0"
slsa-verifier verify-artifact app_linux_amd64 --provenance-path app.intoto.jsonl \
  --source-uri github.com/ORG/REPO --source-tag v1.0.0 --print-provenance | jq .
```
退出码 0/1 是唯一可信信号;`--print-provenance` 出的 in-toto statement 可再喂策略引擎比对 commit SHA。GitHub 原生签发:`gh attestation verify <file> --repo ORG/REPO [--signer-workflow ORG/REPO/.github/workflows/release.yml] [--predicate-type https://slsa.dev/provenance/v1]`。**未验证**:该子命令 flag 全集。

## 6. in-toto(步骤级元数据)
```bash
pip install in-toto
in-toto-run --step-name build --key alice.pub --materials src/ --products dist/app -x 'make build'
in-toto-record start --step-name build --key alice.pub --materials src/
in-toto-record stop  --step-name build --key alice.pub --products dist/app
in-toto-verify --layout root.layout --verification-keys owner.pub --link-dir .
in-toto-sign   --key alice.pub -f root.layout
```
- 上游的 `in-toto-keygen` 与 `in-toto-attestation` **不是现行 CLI 子命令**(前者 1.0 前后移除,后者只是 python 模块 `in_toto.attestation`)。密钥用 `openssl genpkey -algorithm ed25519 -out alice.pem`;**未验证**:`in-toto-verify --layout-keys`(旧名)与 `--verification-keys` 的版本边界。上游 `--key my-project.private-key` 也是旧写法:现代版本按 `.pub` 后缀配对找私钥,照抄易报错。
- 谓词类型白名单:`https://slsa.dev/provenance/v1`、`https://in-toto.io/attestation/link/v0.3`、`.../release/v0.1`、`.../vulns/v0.1`、SCAI `.../scai/attribute-report/v0.2`。策略里写死 predicateType,别信 `_type`。

## 7. TUF(更新框架:要点是信任模型不是命令)
- 四角色密钥隔离:`root`(签其他角色密钥)→ `targets`(签目标清单)→ `snapshot`(签 targets 版本)→ `timestamp`(高频签,唯一可在线)。大仓库用 delegated targets 分权。
- 三条不可省的纪律:① **root 密钥离线/HSM**,轮换靠版本递增 + 新旧 root 双签过渡;② **过期时间必设且短**,客户端过期即拒更新(timestamp 小时~1 天);③ 客户端内嵌起点 root 防降级,抵御 freeze/rollback/mix-and-match 三类攻击。
```python
from tuf.api.metadata import Metadata, Root, Targets, Snapshot, Timestamp  # 构造/签名
from tuf.ngclient import Updater                                          # 客户端拉取
updater = Updater(metadata_dir=..., metadata_base_url=..., target_base_url=...)
info = updater.get_targetinfo("app.tar.gz"); updater.download_target(info)
```
**未验证**:`Updater` 构造参数签名在 python-tuf 各 minor 版本间有调整,以 `help(Updater)` 为准;`tuf.repository_tool` 是已弃用旧 API。Sigstore 自身即用 TUF 分发信任根(`cosign initialize` / Go `sigstore/tuf` / `go-tuf`),私有部署可把该 root 做内网镜像。

## 8. Dependency-Track(把 SBOM 变成持续监控)
上游自建 compose 骨架(apiserver 收 BOM,frontend 出报表,Postgres 外置):
```yaml
services:
  apiserver: { image: dependencytrack/apiserver, ports: ["8081:8080"], volumes: ["dtrack-data:/data"],
               environment: [ALPINE_DATABASE_MODE=external, ALPINE_DATABASE_URL=jdbc:postgresql://postgres:5432/dtrack,
                             ALPINE_DATABASE_DRIVER=org.postgresql.Driver, ALPINE_DATABASE_USERNAME=dtrack, ALPINE_DATABASE_PASSWORD=dtrack] }
  frontend:  { image: dependencytrack/frontend, ports: ["8080:8080"], environment: ["API_BASE_URL=http://localhost:8081"] }
  postgres:  { image: postgres:16-alpine, volumes: ["postgres-data:/var/lib/postgresql/data"],
               environment: [POSTGRES_DB=dtrack, POSTGRES_USER=dtrack, POSTGRES_PASSWORD=dtrack] }
```
**未验证**:镜像 tag 与 `ALPINE_DATABASE_*` 变量名随版本变化(官方亦支持 `ALPINE_DATABASE_MODE=embedded`);首次登录的初始 admin 密码按官方文档取,别硬编码。API Key 从 Automation 团队创建,调用带 `X-Api-Key`。
```bash
# 自动建项目(CI 最常用)
curl -sf -X POST "$DTRACK_URL/api/v1/bom" -H "X-Api-Key: $DTRACK_API_KEY" \
  -F autoCreate=true -F projectName="$CI_PROJECT_PATH" -F projectVersion="$CI_COMMIT_TAG" -F bom=@sbom.cdx.json
# 已知项目 UUID(JSON + base64;单次载荷上限约 20,000,000 字符)
curl -sf -X PUT "$DTRACK_URL/api/v1/bom" -H "X-Api-Key: $DTRACK_API_KEY" -H "Content-Type: application/json" \
  -d "{\"project\":\"$UUID\",\"bom\":\"$(base64 -w0 sbom.cdx.json)\"}"
curl -s -H "X-Api-Key: $DTRACK_API_KEY" "$DTRACK_URL/api/v1/bom/cyclonedx/project/$UUID" -o roundtrip.json ; curl -s -H "X-Api-Key: $DTRACK_API_KEY" "$DTRACK_URL/api/v1/vulnerability/project/$UUID" | jq .   # 取回 BOM / 查漏洞
```
```yaml
# GitHub Actions: 生成 → 校验 → 签名 → 归集
permissions: { contents: read, id-token: write, packages: write }
steps:
  - uses: actions/checkout@v4
  - uses: anchore/sbom-action@v0   # with: {format: cyclonedx-json, output-file: sbom.cdx.json}
  - run: cyclonedx validate --input-file sbom.cdx.json --input-format json --fail-on-errors
  - uses: sigstore/cosign-installer@v3
  - run: cosign sign-blob sbom.cdx.json --bundle sbom.cdx.sigstore.json --yes
  - env: { DTRACK_API_KEY: ${{ secrets.DTRACK_API_KEY }} }
    run: curl -sf -X POST "$DTRACK_URL/api/v1/bom" -H "X-Api-Key: $DTRACK_API_KEY" -F autoCreate=true -F projectName="$GITHUB_REPOSITORY" -F projectVersion="$GITHUB_REF_NAME" -F bom=@sbom.cdx.json
```
```yaml
# GitLab CI: 用官方 cyclonedx 制品类型, 让 GitLab 自出依赖清单
sbom:
  image: anchore/syft:latest
  script: [syft dir:. -o cyclonedx-json=sbom.cdx.json]
  artifacts: { reports: { cyclonedx: sbom.cdx.json }, paths: [sbom.cdx.json] }
scan-and-gate:
  image: aquasec/trivy:latest
  needs: [sbom]
  script: [trivy sbom sbom.cdx.json --severity CRITICAL,HIGH --exit-code 1]
```
**未验证**:`anchore/sbom-action`、`aquasecurity/trivy-action` 的输入名随大版本变动(如 `format`/`output-file` vs `sbom-format`),用前查该 action 的 `action.yml`。

## 9. 漏洞与许可证合规扫描(CI 里真能用)
```bash
trivy sbom sbom.cdx.json --severity CRITICAL,HIGH --exit-code 1 ; grype sbom:./sbom.cdx.json --fail-on high --only-fixed   # 消费侧复扫 / 生成与扫描分离
osv-scanner scan --format json --all-packages . ; osv-scanner scan -L sbom.cdx.json   # v2 目录自动找锁文件 / 扫 SBOM(v1 的 --sbom 已废弃)
trivy fs --scanners license --severity HIGH,CRITICAL .              # 专门 license scanner
pip-licenses --format=json --with-urls --output-file py-licenses.json   # --fail-on "GPL-3.0"
scancode -clpieu --json-pp scan-result.json /path   # 深度许可证+版权归属
# OWASP Dependency-Check(自托管, 本地 NVD 库); XML 输出供 CI 解析
./dependency-check.sh --project my-app --scan . --format HTML --out ./odc \
  --suppression suppression.xml --nvdApiKey "$NVD_API_KEY" --failOnCVSS 7
```
- 许可证策略 `license-policy.yml` 三档 + 豁免(上游结构,建议照抄以留审计痕迹):`forbidden`(AGPL-3.0 / BUSL-1.1 / SSPL-1.0 / Proprietary / Facebook-Plus)、`require_approval`(GPL-2.0 / GPL-3.0 / LGPL-3.0)、`allowed`(MIT / Apache-2.0 / BSD-2-Clause / BSD-3-Clause / ISC / Unlicense / CC0-1.0 / 0BSD);每条 exemption 必须带 `component + license + reason + approved_by + expiry`。
- PR 门禁(真正的许可证合规闸):
```yaml
- uses: actions/dependency-review-action@v4
  with:
    fail-on-severity: high
    allow-licenses: MIT, Apache-2.0, BSD-3-Clause, ISC   # 与 deny-licenses 互斥, 只能给一个
    deny-packages: pkg:pypi/eventlet, pkg:npm/event-stream
    comment-summary-in-pr: on-failure                    # 需 pull-requests: write
```
  它还能输出 `dependency-changes / vulnerable-changes / invalid-license-changes / denied-changes` 供后续 job 消费;**`deny-licenses` 已被官方标注废弃**(改用 `allow-licenses` 或 `config-file`)。仅对 public repo / 开了 GHAS 的私有 repo 生效,不支持 GHES 的许可证检查。

## 10. 第三方交付验收(把供应商评估落到制品上)
- 把问卷式的供应商评估落到可验证工件:合同/SOW 写明**交付必须带 SBOM(CycloneDX 或 SPDX)+ 签名 + 来源证明**,验证命令进验收流程,拿不到就拒收。
- 最低门槛:`cosign verify --certificate-identity <对方 CI 身份> --certificate-oidc-issuer <issuer>` 过 + `cosign verify-attestation --type cyclonedx` 有 SBOM + `slsa-verifier verify-image --source-uri <对方仓库>` 过(等价于可验证的 Build L2/L3,见 §5)。
- 组件/内部库供应商:要求其 SBOM 进我方 Dependency-Track 项目并订阅 CVE;锁 digest 不锁版本号,升级走 `cyclonedx diff` 评审。
- 商业安全评级只作**外部输入不是结论**(BitSight `GET /ratings/v1/companies/portfolio`、SecurityScorecard `GET /v2/companies/portfolio`,各需自家 token;**未验证**:额度与字段稳定性)。
- 风险矩阵三维定级:能否提供 SBOM/签名、漏洞响应 SLA、是否接触生产凭据;高等级走季度复核 + 泄露 24h 内通报条款。
- 合同条款重点:数据处理与子处理者清单、漏洞披露与修复时限、SBOM 随版本交付、审计权、终止时的凭据轮换与代码/密钥交接。

## 11. 与本地技能库的分工(别重复造卡)
- 攻击面(依赖混淆投毒、typosquat、CI 管道对抗利用):`dependency-confusion`、`supply-chain`、`ci-cd-attack-testing`、`supply-chain-infra-hop`;上手前审第三方仓库后门:`third-party-repo-audit`、`opensource-backdoor-audit`。
- 依赖风险量化与供应链评级:`supply-chain-risk-auditor`(OpenSSF Scorecard 思路)。
- 本参考只负责**工程面**:生成/校验/签名/来源证明/TUF/许可证/DT 归集/交付验收 —— 即"如何把上面那些攻击面关掉"。
