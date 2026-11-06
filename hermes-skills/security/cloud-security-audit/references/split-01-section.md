## 概述

云环境是现代化基础设施的核心，攻击面横跨IaaS/PaaS/SaaS多层。本技能系统化覆盖**云资产枚举→身份滥用→权限提升→横向移动→数据窃取→持久化→痕迹清理**完整攻击链，覆盖AWS/Azure/GCP/阿里云四大平台，并深度融入2025-2026最新威胁情报：OIDC信任滥用、AI辅助攻击、云上AI服务攻击面、云供应链与容器逃逸新漏洞。

| 邻域 | 走 |
|------|-----|
| 云元数据 / IMDS / SSRF 打 169.254 | `cloud-metadata-harvesting`（配合 `ssrf-testing`） |
| Android / IPA / Frida / 证书固定 | `apk-recon` · `ios-pentest` · `mobile-reverse` |
| IoT 固件 / UART / JTAG / MQTT | `firmware-pentest` · `ot-ics` · `hardware-security` |
| 容器 / K8s 逃逸 | `container-security-testing` · `linux-privilege-escalation` |

### 核心概念
- **共享责任模型**：云厂商负责"云的安全"（物理/虚拟化/控制平面），租户负责"云中的安全"（IAM/数据/网络/配置）——绝大多数可被利用的漏洞都在租户侧
- **控制平面 vs 数据平面**：控制平面是云API/IAM（如sts:AssumeRole、ec2:RunInstances），数据平面是资源内部（如VM内命令执行）。云攻击的本质是"控制平面攻击"，一次API调用即等同于传统渗透的一次RCE
- **身份即边界**：2025年Google Cloud报告显示**身份妥协占云妥协事件的83%**，IAM已成为云上新的内核——"没有漏洞利用链，只有权限滥用"
- **Living-off-the-cloud (LOTC)**：不落地恶意软件，纯用云API与合法云服务完成C2/数据窃取/横向移动，流量与正常业务无法区分
- **攻击链模型**：初始凭据/入口 → 枚举（我有什么权限）→ 权限提升 → 横向移动 → 数据窃取 → 持久化 → 对抗（日志清理/规避检测）

### 2025-2026 云威胁态势（时效性情报）
| 威胁趋势 | 关键情报 | 攻防启示 |
|---------|---------|---------|
| 身份攻击主导 | 身份妥协占83%；钓鱼转向vishing（语音钓鱼）+第三方SaaS令牌窃取 | 审计重点从端口转向身份与信任关系 |
| AI压缩攻击时间 | Sysdig实测：AI辅助攻击8分钟内从凭据窃取到管理员权限（19个AWS主体、6个IAM角色） | 传统"小时级"响应已失效，需近实时检测 |
| OIDC信任滥用 | UNC6426：s1ngularity npm供应链+宽松GitHub→AWS OIDC信任策略，72小时实现AWS管理员接管；275+ AWS账户存在同类缺陷 | CI/CD身份信任关系是最高价值攻击面 |
| 容器逃逸新漏洞 | Leaky Vessels(CVE-2024-21626)、NVIDIAScape(CVE-2025-23266,CVSS 9.0)、runc三漏洞(CVE-2025-31133/52565/52881) | GPU容器/AI基础设施成为逃逸新战场 |
| 云上AI服务被攻击 | AWS Bedrock 8条IAM攻击向量、LLMjacking单日成本达$46,000、向量库未授权（Milvus CVE-2025-64513 CVSS 9.3） | AI服务自身就是新的高价值攻击面 |
| 供应链攻击常态化 | 2025年供应链攻击+93%；TanStack事件首次产出带有效SLSA L3的恶意包；tj-actions影响23,000+仓库 | 镜像/依赖/CI/CD第三方组件必须纳入审计 |
| 检测规避升级 | T1562.008禁用云日志；PutBucketLifecycle短过期删CloudTrail日志；ATT&CK v18新增K8s/CI/CD/云数据库覆盖 | 日志完整性与抗篡改成为防御基石 |

