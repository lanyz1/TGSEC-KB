## 十一、工具链

### 11.1 钓鱼演练平台

```bash
# 开源
GoPhish               # 开源钓鱼平台（发送/模板/落地页/统计一站式）
King Phisher          # 钓鱼框架（Kali内置）
SET                   # Social Engineering Toolkit（邮件/网页/电话社工）
BeEF                 # 浏览器利用框架（XSS钩子）

# 商业（SaaS，功能更全）
KnowBe4 / Proofpoint Security Awareness / PhishLabs / Cofense / Hoxhunt
```

### 11.2 高级仿真工具

```bash
# AiTM中间人钓鱼（授权演练用，见第四章红线）
git clone https://github.com/kgretzky/evilginx2.git && cd evilginx2 && make
sudo ./bin/evilginx

# 其他同类
Modlishka            # Go写的高级代理钓鱼框架
phishmonger          # 交互式AiTM钓鱼（支持OAuth/多因素）
GoPhish + Evilginx2  # 组合：GoPhish发信 + Evilginx2收割会话行为数据

# 语音/深度伪造检测（防御侧）
# 微软Video Authenticator / Intel FakeCatcher / Resemble.ai Deepfake检测类
# 开源音频分析: Pytorch TorchAudio + 声纹比对工具
```

### 11.3 培训平台与靶场

```bash
# Web安全培训
OWASP WebGoat         # Web安全交互式培训
DVWA                  # 漏洞练习平台
OWASP Juice Shop      # 现代Web漏洞靶场（贴近真实业务）
PortSwigger Web Security Academy  # 免费在线Web安全课程+实验室

# 综合靶场
HackTheBox            # 渗透靶场
TryHackMe             # 引导式学习（含安全意识路径）
VulnHub               # 离线靶场镜像
自建靶场              # 内部漏洞环境（隔离网络）

# 安全意识平台
LMS（Moodle/SAP Litmos等）+ 安全意识课程包
```

### 11.4 评估与数据工具

```bash
# 演练数据统计
GoPhish Campaigns报表  # 导出CSV/JSON做二次分析
Python/pandas + matplotlib  # 趋势图/部门对比/聚类分析

# 行为问卷（参考实现）
HAIS-Q (Human Aspects of Information Security Questionnaire)
SeBIS (Security Behavior Intentions Scale)
企业自研问卷（Knowledge/Attitude/Behavior三维）

# 威胁情报源（培训内容更新）
APWG季度趋势报告 / KnowBe4行业基准报告 / Verizon DBIR / Microsoft数字防御报告
ENISA威胁态势报告 / 国内: 奇安信/深信服/绿盟年度报告
```

### 11.5 AI辅助工具

```bash
# LLM辅助（受管环境，注意数据红线）
企业私有化部署LLM（本地/专网）用于教材/试题/演练内容生成
# 提示词模板库（见第十章10.1/10.2示例）
# 演练数据分析脚本（Python+LLM报告生成）
# 提示注入测试工具（红队评估AI应用: Garak / PyRIT等）
```

