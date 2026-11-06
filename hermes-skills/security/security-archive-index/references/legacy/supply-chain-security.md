<!-- archived from /root/.hermes/skills/security/supply-chain-security/SKILL.md on 2026-10-21 -->

---
name: supply-chain-security
description: 软件供应链安全测试：依赖投毒、包镜像劫持、CI/CD 管道、构建/发布环节、上游库漏洞利用面。触发关键词：供应链、依赖投毒、CI/CD安全、软件供应链。
---

> 归档卡：原目录 `/root/.hermes/skills/security/supply-chain-security`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/supply-chain-security/…')`，不要相对 `references/legacy/` 解析。

# Supply Chain Security Testing

## 本仓探针

```bash
python3 tools/ops/supply_chain_probe.py drive --path <仓根> --case <案>
```

L2=安装脚本或未钉死 Action / 未钉死 pip。证据进案卷 `测绘/`。

## ACTION REQUIRED（读完后立刻执行）

1. `NOW`: 确认本次任务目标是用户明确提供的授权目标（RoE）；未授权目标立即停止，不执行
2. `NOW`: 确认当前任务是否命中本 skill 的适用范围
3. `NEXT`: 用 shell 检查工具可用性（`which`/`where`），缺工具用 `pip install` 或系统包管理器安装，不猜路径
4. `NEXT`: 缺工具时调用 bootstrap，不要猜路径
5. `ACT`: 进入"工作流"第一步并执行，不要停在确认状态

> SBOM / SCA / CI/CD 管道 / 依赖溯源
> 法规驱动：美国行政令 SBOM、中国国标、EU CRA

## 适用场景

- 软件供应链安全评估
- 开源依赖漏洞扫描与验证
- CI/CD 管道安全审计
- 容器镜像安全分析
- 第三方组件合规审查
- 构建产物溯源与完整性验证

## 六层供应链治理框架

```text
Layer 1: 源码信任评估 → 上游仓库/维护者/发布历史审查
Layer 2: 构建管道集成 → CI/CD 安全门禁、签名验证
Layer 3: 制品分发完整性 → 签名、校验和、SBOM 附加
Layer 4: 运行时保护 → 容器扫描、准入控制
Layer 5: 持续监控 → CVE 实时追踪、漏洞可达性分析
Layer 6: 事件响应 → 供应链攻击应急、回滚策略
```

## 工作流

### 1. SBOM 生成与审计

```text
生成 SBOM：
□ CycloneDX 格式: cdxgen → bom.json
□ SPDX 格式: sbom-tool generate
□ Syft: syft <image|dir> -o spdx-json

审计要点：
□ 是否存在未知/未授权的依赖
□ 是否存在已废弃/停止维护的包
□ 许可证冲突检测
□ 直接依赖 vs 传递依赖清单
□ 每个组件的发布时间线和维护者状态
```

### 2. 软件组成分析（SCA）

```bash
# OSV-Scanner（免费、Google 维护）
osv-scanner scan -r . --format json

# OWASP Dependency-Track（企业级持续监控）
docker run -p 8080:8080 dependencytrack/apiserver
# → 上传 SBOM → 自动匹配 NVD/OSV/GitHub Advisory

# Snyk（商业）
snyk test --all-projects
snyk monitor # 持续监控

# Trivy（容器 + 依赖 + IaC）
trivy fs . # 文件系统扫描
trivy image nginx # 容器镜像
trivy config . # IaC 配置
```

### 3. 漏洞可达性验证

```text
SCA 告警 ≠ 实际风险！大多数 SCA 工具只有 ~15% 的告警是实际可达的。

验证步骤：
1. 用 Dependency-Track 或 Trivy 获取 CVE 列表
2. 筛选 CVSS ≥ 7.0 的漏洞
3. 对有 PoC 的 CVE 做可达性分析
 - Code Property Graph 切片: 追踪用户输入到漏洞函数的路径
 - DEPTEX 方法: EPD (Execution Path Dominance) + LLM 语义验证
4. 在隔离环境中验证 PoC
5. 对可达的漏洞按实际影响排序修复优先级
```

工具参考：
- CodeQL: GitHub 代码查询 → 数据流分析
- Snyk Code: 可达性标记
- DEPTEX: LLM 辅助上下文感知风险评估

### 4. CI/CD 管道安全

```text
安全检查点：
□ 代码提交 → pre-commit hook: gitleaks (密钥扫描)
□ PR 阶段 → SCA 扫描 (Trivy/OSV-Scanner)
□ 构建阶段 → 制品签名 (cosign)
□ 推送阶段 → SBOM 附加 (syft + attest)
□ 部署阶段 → 准入控制 (OPA/Kyverno + 镜像扫描)
□ 运行时 → 持续漏洞监控 (Dependency-Track)

管道自身安全：
□ Pipeline as Code 审计（GitHub Actions / GitLab CI 配置注入）
□ Runner 隔离（防止恶意构建突破容器）
□ 密钥管理（Actions Secrets / Vault，禁止硬编码）
□ 第三方 Action 审查（锁定 commit SHA，非 tag）
```

### 5. 容器镜像安全

```bash
# Dockerfile 审计
hadolint Dockerfile

# 镜像扫描（多层：OS + 应用依赖 + 配置）
trivy image --severity HIGH,CRITICAL nginx:latest

# 最小基础镜像
# 优先: distroless → alpine → slim → 避免 latest
docker scout quickview nginx:latest

# 镜像签名
cosign sign --key cosign.key myimage:tag
cosign verify --key cosign.pub myimage:tag
```

### 6. 第三方依赖审查

```text
新增依赖 Checklist：
□ 维护状态：最近 6 个月有提交？维护者活跃度？
□ 安全历史：过去有无被植入恶意代码？
□ 依赖树：引入后新增多少传递依赖？
□ 许可证：与项目许可证兼容？
□ 替代方案：有无更安全的替代（Snyk Advisor / Socket.dev 评分）？

风险评估矩阵：
 高维护 × 低依赖数 × 兼容许可证 → 低风险
 低维护 × 高依赖数 × 许可证冲突 → 高风险
```

## 工具链

| 工具 | 用途 | 获取 |
|------|------|------|
| OWASP Dependency-Track | 企业级持续 SCA | `docker pull dependencytrack/apiserver` |
| OSV-Scanner | 免费 SCA（OSV.dev 生态） | `go install github.com/google/osv-scanner` |
| Trivy | 镜像 + 依赖 + IaC 扫描 | `apt install trivy` |
| Syft | SBOM 生成 | `curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh` |
| cdxgen | CycloneDX SBOM 生成 | `npm install -g @cyclonedx/cdxgen` |
| Cosign | 容器签名 | `go install github.com/sigstore/cosign/v2/cmd/cosign` |
| Gitleaks | 密钥/凭证扫描 | `go install github.com/gitleaks/gitleaks/v8` |
| Snyk | 商业 SCA + 可达性 | `npm install -g snyk` |
| CodeQL | 代码查询 + 数据流 | GitHub Actions 内置 |

## 参考

- `references/sbom-sca-methodology.md` — SBOM + SCA 方法论
- `references/cicd-pipeline-security.md` — CI/CD 管道安全审计

## 任务完成自检（声称完成前 MUST 通过）

- [ ] 我是否执行了工作流中的每一步（而不是只阅读）？
- [ ] 我是否用 `which`/`where` 核对了真实工具路径？
- [ ] 我是否产出了可复现证据（命令/脚本/截图/报告）？
- [ ] 我是否完成并回写了 RULES 要求的 Checklist 项？

## 真源

- 手法：`docs/playbooks/补丁差分与Nday手法.md`
- 工具：`python3 tools/ops/nday_route.py --help`


---

## 外部库增量（2026-10-11 分享包·CJK）

## 概述
AI供应链安全涵盖模型托管、第三方API依赖、开源组件、训练数据、部署基础设施等环节的安全风险（OWASP LLM-05）。攻击者可能通过污染预训练模型、投毒训练数据、篡改推理管道等方式实施供应链攻击。本技能参照 **SLSA**、**SBOM**、**NIST SSDF**、**CNCF Software Supply Chain Best Practices** 等标准。

## 核心技能

### 1. 模型来源验证与完整性校验

```bash
# 验证模型文件的数字签名和哈希
# Hugging Face 模型验证
pip install huggingface_hub

# 下载模型并校验SHA256
curl -L -o model.safetensors https://huggingface.co/meta-llama/Llama-2-7b/resolve/main/model.safetensors
sha256sum model.safetensors > model.sha256
cat model.sha256

# 验证模型卡中的DPO签名（模型可信发布）
huggingface-cli verify-repo-signatures meta-llama/Llama-2-7b

# GPG签名验证
gpg --verify model.safetensors.asc model.safetensors
```

```python
# 模型完整性校验自动化
import hashlib
import requests
from typing import Dict, Optional

class ModelIntegrityVerifier:
    """模型文件完整性验证器"""
    
    def __init__(self):
        self.trusted_registries = [
            "huggingface.co",
            "github.com",
            "pytorch.org",
            "tensorflow.org",
        ]
    
    def verify_model_hash(self, model_path: str, expected_hash: str, 
                          algorithm: str = "sha256") -> bool:
        """验证模型文件哈希"""
        h = hashlib.new(algorithm)
        with open(model_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        actual_hash = h.hexdigest()
        return actual_hash == expected_hash
    
    def check_model_registry(self, model_url: str) -> Dict:
        """检查模型来源是否可信"""
        risk_assessment = {
            "url": model_url,
            "trusted": False,
            "risks": []
        }
        
        # 检查来源
        if not any(registry in model_url for registry in self.trusted_registries):
            risk_assessment["risks"].append("非可信模型托管平台")
        
        # 检查HTTPS
        if not model_url.startswith("https://"):
            risk_assessment["risks"].append("不使用HTTPS传输")
        
        # 检查是否包含版本锁定
        if "@" not in model_url and "v" not in model_url.split("/")[-1]:
            risk_assessment["risks"].append("未锁定版本，易受恶意更新攻击")
        
        risk_assessment["trusted"] = len(risk_assessment["risks"]) == 0
        return risk_assessment
```

### 2. SBOM (AI Bill of Materials) 生成与分析

```python
import json
from datetime import datetime
from typing import List, Dict

class AISBOMGenerator:
    """AI供应链SBOM生成器（基于CycloneDX格式）"""
    
    def generate_model_sbom(self, model_info: Dict) -> Dict:
        """生成模型SBOM"""
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "component": {
                    "type": "application",
                    "name": model_info.get("name"),
                    "version": model_info.get("version"),
                    "model": model_info.get("model_type"),
                    "description": "AI Model Supply Chain Bill of Materials"
                }
            },
            "components": self._collect_components(model_info)
        }
        return sbom
    
    def _collect_components(self, model_info: Dict) -> List[Dict]:
        """收集所有供应链组件"""
        components = []
        
        # 训练框架
        components.append({
            "type": "framework",
            "name": model_info.get("framework", "unknown"),
            "version": model_info.get("framework_version", "unknown")
        })
        
        # 训练数据集
        for dataset in model_info.get("datasets", []):
            components.append({
                "type": "data",
                "name": dataset.get("name"),
                "version": dataset.get("version"),
                "licenses": dataset.get("license"),
                "evidence": dataset.get("source_url")
            })
        
        # Python依赖
        for dep in model_info.get("dependencies", []):
            components.append({
                "type": "library",
                "name": dep.get("name"),
                "version": dep.get("version"),
                "purl": dep.get("purl")  # Package URL
            })
        
        # 基础模型（如果是微调模型）
        if model_info.get("base_model"):
            components.append({
                "type": "model",
                "name": model_info["base_model"]["name"],
                "version": model_info["base_model"]["version"],
                "bundled": True
            })
        
        return components
```

### 3. 依赖漏洞扫描

```bash
# Python ML依赖安全扫描
pip install safety
safety check

# 扫描requirements.txt
safety check -r requirements.txt --full-report

# Trivy - 容器和依赖扫描
trivy fs --severity HIGH,CRITICAL --exit-code 1 /path/to/project

# Snyk - AI项目依赖扫描
snyk test --all-projects --severity-threshold=high

# GitHub Dependabot配置 (.github/dependabot.yml)
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels:
      - "security"
      - "dependencies"
```

### 4. 训练数据投毒检测

```python
import numpy as np
from typing import List, Tuple

class DataPoisoningDetector:
    """训练数据投毒检测"""
    
    def __init__(self, clean_data_sample: np.ndarray):
        self.clean_stats = self._compute_statistics(clean_data_sample)
    
    def _compute_statistics(self, data: np.ndarray) -> Dict:
        return {
            "mean": np.mean(data, axis=0),
            "std": np.std(data, axis=0),
            "min": np.min(data),
            "max": np.max(data)
        }
    
    def detect_outliers(self, suspicious_data: np.ndarray, 
                        threshold: float = 3.0) -> np.ndarray:
        """检测异常数据点（潜在投毒）"""
        z_scores = np.abs(
            (suspicious_data - self.clean_stats["mean"]) / self.clean_stats["std"]
        )
        return np.any(z_scores > threshold, axis=1)
    
    def detect_label_flipping(self, features: np.ndarray, 
                              labels: np.ndarray) -> List[int]:
        """检测标签翻转攻击"""
        from sklearn.ensemble import IsolationForest
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        
        # 特征-标签组合检测
        X_combined = np.concatenate([features, labels.reshape(-1, 1)], axis=1)
        anomalies = iso_forest.fit_predict(X_combined)
        
        return np.where(anomalies == -1)[0].tolist()
```

### 5. 供应链攻击场景

```text
# AI供应链攻击典型场景

## 场景1：模型权重投毒
攻击者在公开模型权重中植入后门
→ 当输入包含特定触发器时，模型执行恶意行为
→ 防御：校验模型哈希、使用可信源、权重签名验证

## 场景2：Python依赖劫持
攻击者注册与流行ML库相似的恶意包（Typosquatting）
例如：tensorfl0w (数字0代替o)
→ 防御：锁定依赖版本、使用private PyPI镜像、包名验证

## 场景3：Hugging Face恶意模型
攻击者上传含恶意代码的模型
→ 模型加载时执行任意代码（利用了pickle反序列化漏洞）
→ 防御：使用safetensors格式、模型沙箱加载、审查模型代码

## 场景4：训练数据污染
攻击者向公开数据集注入含毒样本
→ 模型在特定输入下产生预设的错误输出
→ 防御：数据来源验证、离群值检测、差分隐私训练

## 场景5：CI/CD管道劫持
攻击者通过篡改CI/CD配置注入恶意模型
→ 每次部署都自动加载被篡改的模型
→ 防御：CI/CD配置签名、SBOM验证、部署审批流程
```

### 6. 安全配置检查清单

```text
# AI供应链安全配置检查清单

## 模型获取
[ ] 模型来源是否来自可信注册表？
[ ] 是否校验模型文件哈希和签名？
[ ] 是否使用safetensors而非pickle格式？
[ ] 是否对模型进行了安全审计？

## 依赖管理
[ ] 是否使用requirements.lock / poetry.lock锁定版本？
[ ] 是否定期扫描依赖漏洞？
[ ] 是否使用private PyPI / conda镜像？
[ ] 是否移除了不必要的依赖？

## 部署安全
[ ] 模型是否运行在沙箱/隔离环境中？
[ ] 推理API是否有速率限制和鉴权？
[ ] 是否实施了模型完整性运行时监控？
[ ] 是否启用了模型访问审计日志？

## 持续监控
[ ] 是否实施了SBOM自动生成？
[ ] 是否有依赖变更告警机制？
[ ] 是否定期审查第三方模型行为？
[ ] 是否有供应链安全事件响应计划？
```

## 常用工具

| 工具 | 用途 | 链接 |
|:---|:---|:---|
| Trivy | 容器/依赖漏洞扫描 | https://github.com/aquasecurity/trivy |
| Safety | Python依赖安全扫描 | https://github.com/pyupio/safety |
| Snyk | 开源依赖安全 | https://snyk.io/ |
| CycloneDX | SBOM标准化工具 | https://github.com/CycloneDX |
| Hugging Face Hub | 模型托管（有安全检查） | https://huggingface.co/ |
| PickleScan | 检测恶意pickle文件 | https://github.com/mmaitre314/picklescan |
| SLSA Framework | 供应链安全级别框架 | https://slsa.dev/ |

## 参考资源

- [OWASP LLM Top 10 — LLM05: Supply Chain Vulnerabilities](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [SLSA — Supply-chain Levels for Software Artifacts](https://slsa.dev/)
- [NIST SSDF — Secure Software Development Framework](https://csrc.nist.gov/publications/detail/sp/800-218/final)
- [CNCF Software Supply Chain Best Practices](https://github.com/cncf/tag-security/tree/main/supply-chain-security)
- [Hugging Face Security Policy](https://huggingface.co/docs/hub/security)
- [OpenSSF Scorecard](https://securityscorecards.dev/)
