### 23.6 2026恶意软件趋势

- **AI 辅助恶意软件**:LLM 生成多态代码(每次编译变量名、控制流不同)、自动化规避代码生成、钓鱼邮件文本生成。
- **Living-off-the-Land (LotL)**:大量使用系统自带工具(WMI、PowerShell、`certutil`、`mshta`、`rundll32` 等 LOLBins),无文件落地,传统特征检测难以覆盖。
- **无文件恶意软件**:PowerShell + .NET assembly 内存加载(Assembly.Load),通过 `System.Management.Automation` 直接调用,内存执行后不落盘。
- **Linux IoT 恶意软件**:Mirai 变种持续演进,ARM/MIPS 架构 DDoS botnet,利用弱口令与 N-day 漏洞传播,2026 年出现针对 RISC-V 设备的变种。
- **macOS 恶意软件**:针对 M1/M2 ARM64 芯片原生编译,Shadowhammer 变种窃取 Keychain,XCSSET 变种感染 Xcode 项目。
- **eBPF rootkit**:Linux 6.x 内核利用 eBPF 程序隐藏进程/文件/网络连接,绕过传统内核模块检测,需 eBPF verifier 漏洞或 root 权限加载。

---



---
📖 本切片 2/2 结束。 本章节结束。