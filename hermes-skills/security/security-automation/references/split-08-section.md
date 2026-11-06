## 六、攻防双视角自动化

### 6.1 红队自动化打点（Red 视角）
```
资产收集(子域/端口/指纹)
  → 攻击面分析(ASM: 公网暴露/影子资产)
  → 自动化漏洞探测(nuclei/自动化工具)
  → 漏洞验证(exploit-validated: 起 PoC 确认可利用性)
  → 打点成功 → 建立据点 → 横向扩展
```
```bash
# 打点自动化示例（仅授权环境）
# 1) 子域枚举
subfinder -d target.com -all -silent | sort -u > subs.txt
# 2) 存活探测
httpx -l subs.txt -silent -title -status-code -tech-detect -o alive.txt
# 3) 指纹/资产测绘（httpx 探测技术栈，nuclei -tech-detect 亦可）
httpx -l alive.txt -tech-detect -silent | tee -a tech.txt
# 4) 定向漏洞验证
nuclei -l alive.txt -t cves/ -t exposures/ -severity critical,high
# 5) 结果入库 + 人工/LLM 研判 → 确认可利用目标
```
- 攻击面管理（ASM）自动化：持续发现**影子资产/新暴露面**，与 CMDB 资产库比对找出"未登记资产"
- 红队视角关键：自动化只做"广度"，**深度利用链仍依赖专家+LLM 辅助**（结合 fastjson-exploitation 等利用技能）

### 6.2 蓝队自动检测响应（Blue 视角）
```
检测(SIEM/EDR/NDR 规则+行为分析)
  → 告警聚合/降噪(去重/关联/LLM triage)
  → 自动化调查(资产上下文/威胁情报/TTP映射)
  → 自动化响应(隔离/封禁/撤销会话 —— 高危动作 HITL)
  → 复盘与检测工程(规则调优/新规则生成)
```
```bash
# 示例：EDR/SIEM 告警 → 自动化处置脚本（示意）
# 1) 提取 IOC
# 2) 威胁情报查询（VirusTotal/AbuseIPDB/MISP）
# 3) 命中规则 → 隔离主机 / 封禁 IP / 撤销 Token
# 4) 全自动动作需白名单+审批闸门
```

### 6.3 攻击模拟与纵深防御验证
```bash
# Atomic Red Team（红蓝共用检测验证）
git clone https://github.com/redcanaryco/atomic-red-team
# 执行单一 ATT&CK 技术（模拟 T1059.001 PowerShell）
powershell -ExecutionPolicy Bypass -File ./atomics/T1059.001/T1059.001.yaml  # 或对应执行脚本

# MITRE CALDERA（自主对抗模拟平台）
# 部署 server + agent，按操作计划自动化演练

# 商业替代：SafeBreach / AttackIQ / Picus —— 持续验证检测覆盖率
```
- **检测覆盖率度量**：用攻击模拟结果反向评估"哪些 TTP 未被检测"，驱动检测工程补齐
- 攻防演练自动化：红队工具链输出 ↔ 蓝队检测覆盖矩阵（ATT&CK Navigator 热力图）自动对比

### 6.4 红蓝联动闭环
```
红队自动化发现 → 证据包(复现步骤+PoC) → 漏洞平台登记
                              ↓
蓝队检测规则(以红队 TTP 为样本生成) → 攻击模拟验证 → 上线
                              ↓
复测闭环：下轮红队验证新规则是否拦截 → 覆盖率持续提升
```

