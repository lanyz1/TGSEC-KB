## 十一、免杀与C2

### 11.1 免杀思路（攻防对抗核心）
```
# 检测维度: 静态特征/行为特征/内存特征/流量特征
# 免杀分层:
# 1) 源码层: 加密/混淆payload、变量重命名、字符串拆分、控制流平坦化
# 2) 加载层: Shellcode Loader(无文件)、进程注入(远程线程/APC/QueueUserAPC)、
#            模块隐藏、无新内存页特征
# 3) 传输层: HTTPS/HTTP2/WS加密流量、域前置、CDN中转、流量伪装(JA3指纹)
# 4) 执行层: 白利用(LOLBins: mshta/rundll32/regsvr32/certutil)、
#            签名程序加载、DLL劫持(白名单DLL)、内存DLL(Reflective)
# 常用技术: 分离免杀(C2远程加载)/ 加密shellcode(AES/XOR) / 沙箱对抗(延时/交互检测) /
#           AMSI/ETW Patch / Syscall直接调用(绕过EDR hook)
# 工具: shellcode loader模板 / Nim/Go/Rust加载器 / ScareCrow(签名+LOLBin)
```

### 11.2 C2基础设施
```
# Cobalt Strike / Sliver / Havoc / Metasploit / 商业化(MSFvenom+handler)
# 配置要点:
# - 仅使用HTTPS listener(HTTP明文易检测)
# - Malleable C2 Profile: 修改流量指纹(UA/JA3/请求路径/响应包)
# - 域前置/云函数/CDN: 隐藏真实C2地址
# - 证书伪装: 使用与目标业务相近的TLS证书
# - 多级C2: 边界listener → 内网redirector → 真实C2(内网不出网场景)
# - 反沙箱: 检测VM/沙箱环境延时执行
# 内网不出网: 通过已建立的隧道走C2流量(见第四章)
```

### 11.3 AI辅助免杀（大模型赋能攻防）
```
# 1) 代码生成: 让LLM生成多种语言的shellcode加载器变体
#    (C/C#/Go/Rust/Nim/Python,含XOR/AES加密+动态解密)
# 2) 混淆增强: LLM对PowerShell/C#载荷做变量重命名、字符串拆分、
#    逻辑扁平化、插入无用代码, 打散静态特征
# 3) 检测对抗: 把loader源码丢给LLM, 让它标注可能的检测点
#    (CreateRemoteThread等API调用、内存属性RXW、可疑字符串)
#    并给出替代实现(如异步回调/进程镂空/无新线程)
# 4) 变体生成: 每次上线生成不同变体, 降低AV/EDR误报学习效率
# 5) 流量混淆: LLM辅助生成Malleable C2 Profile变体与HTTPS请求样式
# 注意: 所有免杀载荷须在隔离环境/靶场验证, 遵守授权与合规边界
```

