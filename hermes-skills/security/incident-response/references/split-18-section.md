## 十七、工具链

### 17.1 主机取证与采集
```bash
# Windows
KAPE                   # 自动化工件采集与解析
Velociraptor           # 大规模远程取证/狩猎
winpmem / DumpIt / Magnet RAM Capture   # 内存采集
MFTECmd / EvtxECmd / Timeline Explorer  # EZ 工具家族
Sysinternals Suite     # sigcheck/process explorer/strings等
LogParser / EvtxECmd   # Windows日志解析

# Linux
LiME                   # 内存采集内核模块
avml                   # 快速内存采集
UAC                    # Linux自动化三线采集
Autopsy/Sleuth Kit     # 磁盘取证
```

### 17.2 内存与恶意样本
```bash
Volatility 3           # 内存分析（windows.*/linux.*插件）
Ghidra / IDA / x64dbg  # 逆向与调试
YARA                  # 规则匹配
CyberChef             # 编解码/混淆还原
Any.Run / Joe Sandbox / CAPE   # 动态沙箱
oletools              # 恶意文档分析
DIE / pefile          # 加壳与PE分析
```

### 17.3 日志与SIEM
```bash
ELK Stack / Splunk / Sentinel / XSIAM   # 日志聚合与SIEM
Timesketch            # 取证时间线
Sigma CLI             # 检测规则转换(sigma convert -t splunk)
Osquery / Elastic Defend   # 主机遥测
```

### 17.4 云与容器
```bash
aws cli / az cli / gcloud      # 云审计与快照
Falco / Tetragon / tracee-ebpf # 运行时检测
Sysdig Inspect / dive / trivy  # 容器镜像与运行时取证
kubectl / crictl / docker      # K8s取证基础命令
hubble (Cilium)                # 服务网格流量
```

### 17.5 响应编排与情报
```bash
TheHive / Cortex      # 事件管理与分析编排
MISP                  # 威胁情报共享（STIX/TAXII）
BloodHound            # AD攻击路径（反向防御用法）
Velociraptor          # 狩猎与远程采集
Dradis / XMind        # 调查记录与思维导图
AI助手(LLM/SOAR)      # 告警分诊与报告生成（见十三章）
```

