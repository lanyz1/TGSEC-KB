## 十三、工具链

```bash
# ── 云安全审计/合规 ──
prowler                     # AWS/Azure/GCP/阿里云(community) 安全审计，CIS基准
ScoutSuite                  # 多云安全审计（AWS/Azure/GCP/阿里云）
CloudSploit                 # AWS配置审计
Steampipe + Powerpipe       # 用SQL做多云资产与合规查询（适合LLM结合审计）
kubeaudit / kube-bench      # K8s集群/基线审计

# ── 身份枚举与攻击 ──
pacu                        # AWS攻击框架（iam__bruteforce_permissions等模块）
enumerate-iam               # AWS权限盲测枚举
aws-consoler                # AK/SK转Console登录
BloodHound + AzureHound     # Azure/Entra ID 提权路径图
Stormspotter                # Azure资源关系图谱
GCPwn                       # GCP攻击工具集
gcp-iam-collector           # GCP IAM分析
aliyun_ram_checker          # 阿里云RAM审计（社区工具）

# ── 枚举/测绘 ──
CloudBrute                  # 云资产枚举
cloud_enum                  # 多云资源枚举
cartography                  # 资产图谱（Neo4j）
Shodan/FOFA/Quake           # 公网暴露面
cloudlist                   # 多云资产清单
OSS_Scanner                 # 多厂商OSS存储桶扫描（阿里云/腾讯云/华为云/AWS）

# ── 容器/K8s ──
kube-hunter                 # K8s渗透测试
peirates                    # K8s渗透工具集
kdigger                     # 容器环境探测（逃逸前置侦察）
deepce                      # 容器逃逸辅助
trivy                       # 镜像/仓库/K8s漏洞扫描
cdk (Container Dunk Kit)    # 容器逃逸工具箱
falconhound / falco         # 运行时检测（防御侧）

# ── 元数据/SSRF ──
trufflehog / gitleaks       # 凭据扫描
Cloud Metadata Toolkit      # 元数据服务探测
ssrfmap                     # SSRF自动化利用

# ── AI安全 ──
garak                       # LLM漏洞扫描（提示注入/越狱）
promptmap                   # LLM红队
pyrit / llm-guard           # AI安全测试框架
vectordb审计：Chroma/Milvus/Pinecone 官方CLI + 未授权探测脚本
# 模拟工具：imagetragick、恶意模型检测（picklescan）

# ── 取证/检测（防御视角） ──
CloudTrail Insights         # AWS异常行为检测
GuardDuty / Sentinel / Chronicle / 阿里云态势感知
Sigma规则库（云检测）        # ATT&CK映射检测规则
```

