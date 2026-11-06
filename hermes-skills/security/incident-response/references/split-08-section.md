## 七、恶意样本分析

### 7.1 静态分析
```bash
# 基础信息
file sample
strings -a -n 6 sample | head -100
sha256sum sample
ssdeep sample                      # 模糊Hash（变种聚类）

# PE分析
python -m pefile sample.exe        # 导入表/资源/节区（不常见的节名如.upx=加壳）
sigcheck -a sample.exe             # 签名/版本信息（VS)
# 加壳检测：DIE(Detect It Easy)、UPX、检查导入表密度

# 恶意文档
python -m oletools.olevba sample.doc        # 宏代码提取
python -m oletools.oleid sample.doc         # OLE结构风险标识
# 恶意PDF：pdfid、peepdf

# YARA规则匹配
yara -r rules/ sample               # 使用 MalwareBazaar/YARA-Forge 社区规则集
# 在线：VirusTotal、Hybrid Analysis（上传前确认样本无敏感信息）

# 配置提取（勒索/远控家族）
# 使用公开解密工具：如 DragonBuster 等勒索解密工具、通用C2配置提取器
```

### 7.2 动态分析
```
沙箱环境（必隔离）：
- Any.Run（在线交互式，可看进程树+网络）
- Joe Sandbox（在线深度报告）
- Cuckoo/CAPE Sandbox（本地自动化）
- 本地VM（禁用共享/快照回滚/仅主机网络+NAT代理）

监控项（对照记录）：
- 进程创建/注入（进程树形态）
- 文件操作（创建/修改/删除，重点自启动路径）
- 注册表操作（RunKeys/服务/WMI）
- 网络通信（DNS/HTTP/TCP，抓包分析C2协议）
- 互斥量/管道（去重与家族识别）
- 持久化机制（重启后是否存活）

行为结论输出：文件hash、C2域名/IP、家族归属、持久化点、窃取数据清单
```

### 7.3 快速判定流程（10分钟出结论）
```
1. VT/沙箱多引擎：命中数>10 → 高度恶意（先看家庭/行为标签）
2. 签名+加壳：未签名+加壳+高熵 → 可疑（提取静态配置）
3. 网络行为：主动外连非常规端口/域名 → 恶意概率大增
4. 持久化行为：写入自启动 → 确认恶意
5. 输出：该样本是"已知家族变种"还是"新型"，决定后续溯源与规则发布
```

### 7.4 逆向分析基础
```
Ghidra（免费）/ IDA Pro：静态反编译定位关键逻辑
x64dbg / WinDbg：动态调试（需在隔离环境）
分析重点：C2字符串、解密密钥、加密算法（勒索）、外传目标
进阶：脱壳（unpack）、混淆还原、行为指纹提取（用于YARA）
```

