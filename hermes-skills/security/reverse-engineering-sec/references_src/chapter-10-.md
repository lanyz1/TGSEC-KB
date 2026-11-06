## 10. 测试检查清单

```
AI辅助逆向 (§1)
□ 安装GhidrAssist/GEPETTO/VulChatGPT到Ghidra
□ 使用PyGhidra构建自动化分析管道
□ 测试Binary Ninja Sidekick的交互式AI分析
□ 使用BinaryAI进行函数相似性搜索识别库函数
□ 用VulChatGPT自动标记可疑函数进行漏洞分类

移动应用逆向 (§2)
□ 使用JADX反编译APK并搜索硬编码凭据
□ 用Frida Hook Root检测/SSL Pinning/加密函数
□ 使用Objection一键绕过安全控制
□ 分析Native库(.so)中的JNI函数
□ iOS: class-dump导出头文件+Frida Hook Objective-C方法

二进制分析 (§3)
□ 使用angr进行符号执行探索路径
□ 用静态分析增强AFL模糊测试(覆盖率驱动)
□ 识别高风险函数(strcpy/sprintf/system等)及其交叉引用
□ 测试SysFuSS系统级固件模糊测试
□ 用Bangr在Binary Ninja中集成angr符号执行

固件逆向 (§4)
□ 使用binwalk提取固件文件系统
□ 测试SWD/JTAG调试端口是否激活(OpenOCD)
□ 脱焊SPI Flash + CH341A读取固件
□ SPI嗅探捕获固件加载过程(逻辑分析仪)
□ 使用Ghidra分析ARM/MIPS固件二进制

反混淆 (§5)
□ 使用Squanchy反混淆WASM模块
□ 用SiMBA++/GAMBA简化MBA表达式
□ 使用angr进行控制流反平坦化
□ 绕过ptrace反调试(LD_PRELOAD/Frida Hook)
□ 捕获运行时动态AES密钥生成

WASM逆向 (§6)
□ 使用wasm-objdump查看模块节信息
□ wasm2wat转换为可读WAT文本格式
□ wasm2c提升到C进行深入分析
□ 测试SeeWasm符号执行
□ 检查WASM模块是否包含反机器人逻辑

加密协议逆向 (§7)
□ 使用CryptoLyzer分析TLS/SSH配置
□ 检测CVE-2026-3142(OpenSSL HollowByte)
□ 检测CVE-2026-0947(MCP证书链绕过)
□ 使用testssl.sh全面TLS审计
□ 测试后量子密码套件支持(Kyber/Dilithium)

硬件逆向 (§8)
□ 使用ChipWhisperer进行SPA/DPA攻击AES
□ 测试电压毛刺绕过Secure Boot
□ 使用JTAGulator发现JTAG接口
□ 用Saleae逻辑分析仪嗅探UART/SPI通信
□ 验证常量时间比较防御是否正确实现
```

---

