---
name: sbom-supplychain-integrity
description: "Use when 供应链/SBOM面:Syft、cosign签名、SLSA、CI依赖混淆。"
---

# SBOM / 供应链完整性 / 依赖合规

把「我们到底装了什么、它是否被篡改、许可证能不能用」变成流水线里可自动验证的工程动作。
攻击面(依赖混淆、CI 管道投毒)见 `dependency-confusion`、`ci-cd-attack-testing`;本卡只管**把攻击面关掉**的工程面。

## 何时用
- 要软件物料清单(SBOM)或客户/审计要求交付 CycloneDX/SPDX。
- 要签名制品、验证镜像来源、上 SLSA 等级/来源证明(in-toto、provenance)。
- 要许可证合规(AGPL/SSPL 风险、PR 许可证门禁)、第三方依赖风险持续监控。
- 要验收外部交付物(镜像/二进制/SBOM)是否真的出自声称的仓库与流水线。
- 要在 CI 里串 SBOM/漏洞/许可证/签名四件事,或排查线上"装到脏包"。
- 组织/项目要落地 TUF 更新框架或 Dependency-Track。

## 工作流
1. **定范围与格式**:生产流水线用 CycloneDX(能直喂 Dependency-Track/Grype);对外法务交付另出 SPDX。先确认要扫的是镜像、源码目录还是已发布的 SBOM。
2. **生成**:镜像用 `syft`/`trivy image`;Java 多模块用 `cdxgen -r`;已有 SBOM 用 `trivy sbom` / `grype sbom:` 消费。生成后立刻校验格式,别把非法 JSON 往制品库里塞。
3. **签名与归属**:制品与 SBOM 都 `cosign sign`(keyless,CI 里 `--yes`);SBOM 用 `cosign attest --type cyclonedx` 挂成 attestation。禁止用 `cosign attach sbom`(已废弃且不签名)。
4. **验证(消费侧)**:`cosign verify` / `cosign verify-blob` **必须给 `--certificate-identity` 与 `--certificate-oidc-issuer`**;镜像锁 `digest`;有 provenance 就用 `slsa-verifier verify-image --source-uri --builder-id` 或 `gh attestation verify`。
5. **归集与持续监控**:CI 把 BOM `POST /api/v1/bom` 进 Dependency-Track(`autoCreate=true`),让新披露的 CVE 能回溯命中已有项目;许可证策略(禁止/需审批/允许三档)与 PR 门禁(`dependency-review-action`)同时开。
6. **门禁与基线**:所有扫描器一律先跑 baseline/`--soft-fail` 观测,再开 `--exit-code`/`--error` 卡新增;SBOM 用 `cyclonedx diff` 做变更评审。

## 命令速查
```bash
# 生成
syft dir:. -o cyclonedx-json=sbom.cdx.json ; syft alpine:latest -o spdx-json=sbom.spdx.json
trivy image --format cyclonedx -o sbom.cdx.json nginx:latest
cdxgen -r /app -o sbom.json                        # Java/多模块
# 校验 / 差异
cyclonedx validate --input-file sbom.cdx.json --input-format json --fail-on-errors
cyclonedx diff old-sbom.json new-sbom.json
pyspdxtools -i sbom.spdx.json -o roundtrip.spdx.json      # SPDX 校验(python spdx-tools)
# 签名 / 来源证明
cosign sign --yes registry.corp/app:1.0
cosign verify registry.corp/app:1.0 --certificate-identity "$ID" --certificate-oidc-issuer "$ISSUER"
cosign attest --predicate sbom.cdx.json --type cyclonedx registry.corp/app:1.0
slsa-verifier verify-image "$IMG@$DIGEST" --source-uri github.com/ORG/REPO --builder-id "$BID"
# 消费与合规
trivy sbom sbom.cdx.json --severity CRITICAL,HIGH --exit-code 1
grype sbom:./sbom.cdx.json --fail-on high --only-fixed
osv-scanner scan -L sbom.cdx.json --format json
trivy fs --scanners license --severity HIGH,CRITICAL .
# 归集
curl -sf -X POST "$DTRACK_URL/api/v1/bom" -H "X-Api-Key: $DTRACK_API_KEY" \
  -F autoCreate=true -F projectName="$CI_PROJECT_PATH" -F projectVersion="$CI_COMMIT_TAG" -F bom=@sbom.cdx.json
```

## Pitfalls
- **`cosign verify` 不带 identity/issuer 等于没验**:keyless 下任何人的签名都能过。同理 `verify-attestation` 必须带 `--certificate-identity`。
- **`cosign attach sbom` 已废弃**:它不签名、只挂文件;要可信就用 `cosign attest`。
- **SLSA 口径**:v1.0 只有 Build L1/L2/L3(L4 已移除);别照抄旧文里的"SLSA 4"。验证镜像必须锁 digest,锁 tag 有 TOCTOU。
- **SBOM ≠ 漏洞清单**,也 ≠ 完整清单:SBOM 只记录打包进制品的组件,漏掉构建期工具与动态下载内容;动态语言(Go 的 `-trimpath`、musl 混淆)还会认错版本。生成器换一个结果就变,入库前要校验并留生成器名+版本。
- **格式名坑**:Trivy 的 SPDX 叫 `spdx-json`,Syft 是 `spdx-tag-value`;`pip install cyclonedx-bom` 提供的是 `cyclonedx-py`(只生成),`cyclonedx validate/diff` 来自 .NET `cyclonedx-cli`。
- **in-toto 没有 `in-toto-keygen`/`in-toto-attestation` 子命令**,现代用 `in-toto-run`/`in-toto-record`/`in-toto-verify`;attestation 是 python 模块不是 CLI。
- **许可证扫描误报高**:`licensecheck`/`trivy license` 对双许可、文件头与 SPDX 元数据解释不一致,必须人工复核清单,豁免要带 approver 与到期日。
- **`extra-index-url`(pip)/ 无 scope 的私有包名 是依赖混淆入口**,客户端只配单一 `index-url` + `--require-hashes` + `--ignore-scripts`。
- **Token 别写死在 CI 变量**:用 OIDC 短时凭据;TUF root 密钥离线;私有 registry 关匿名读。
- **离线环境漏洞库更新不了**时报"无发现"是假的;`--exit-code` 前先确认 DB 已同步。
- 本卡不覆盖对抗利用(投毒/绕过),需要时切 `dependency-confusion`、`ci-cd-attack-testing`、`supply-chain-infra-hop`。

## 参考文件
- `references/sbom-signing-slsa.md` —— Syft/Trivy/cdxgen 生成、CycloneDX vs SPDX、校验与 diff、cosign/sigstore keyless、SLSA 与 slsa-verifier、in-toto、TUF、Dependency-Track 部署与 CI YAML、许可证合规、CI 漏洞扫描。
- `references/devsecops-scan-chain.md` —— IaC/SAST/DAST 真实命令与 CI 串联、CI/CD 管道攻击面审计命令、依赖混淆防护配置(pip/npm/yarn/Maven/NuGet/Cargo/Go)。
- `references/provenance-and-unverified.md`：来源核对（哪些命令搬自上游 / 哪些是补充 / 未验证清单）。
- 相关卡:`supply-chain`、`dependency-confusion`、`supply-chain-risk-auditor`、`ci-cd-attack-testing`、`supply-chain-infra-hop`、`third-party-repo-audit`。
