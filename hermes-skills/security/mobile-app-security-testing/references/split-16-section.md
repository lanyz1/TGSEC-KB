## 十五、测试检查清单

### 15.1 信息收集与资产梳理
- [ ] 获取目标 APK/IPA（官方商店/三方市场/客户提供）
- [ ] 识别框架指纹（原生/Flutter/React Native/uni-app/加固壳）
- [ ] 提取 API 域名/端口/子域名清单（静态+抓包交叉验证）
- [ ] 确认测试环境（真机/模拟器、越狱/root 状态、能否对抗检测）

### 15.2 Android 静态与组件
- [ ] APK 解包反编译（apktool+jadx）
- [ ] Manifest 审计（debuggable/allowBackup/exported/usesCleartextTraffic/networkSecurityConfig）
- [ ] 硬编码密钥扫描（AWS AKIA/私钥/API key/LLM key）
- [ ] Native so 逆向（关键算法/校验逻辑）
- [ ] Content Provider 六入口测试（query/insert/update/delete/openFile/call + 路径穿越）
- [ ] 插件化/动态加载 DEX 来源与校验审计
- [ ] 深链/Intent Redirection/Intent 注入测试
- [ ] 权限过度申请（短信/通讯录/无障碍/悬浮窗）

### 15.3 Android 动态与对抗
- [ ] Frida 环境搭建与存活验证（spawn+attach 双模式）
- [ ] Frida 特征检测识别与绕过（文件/进程/端口/D-Bus/maps/ptrace）
- [ ] Root 检测绕过（Magisk DenyList + hook 组合）
- [ ] 模拟器检测绕过（Build/QEMU/传感器/IMEI）
- [ ] 加密函数 Hook（Cipher/密钥/IV/Base64 抓取）
- [ ] 组件动态触发（am start/startservice/broadcast/content query）
- [ ] 加固壳识别与脱壳（frida-dexdump/FART/BlackDex）
- [ ] 壳反脱壳对抗（pthread_create 阻断/完整性等式化替换）

### 15.4 iOS 深度测试
- [ ] IPA 解包与 Mach-O 分析（LC_ENCRYPTION_INFO/段/符号）
- [ ] class-dump/ObjC 类方法枚举与敏感方法定位
- [ ] Info.plist/entitlements 审计（ATS/URL Scheme/keychain-access-groups）
- [ ] LLDB 动态调试（断点/寄存器/表达式执行）
- [ ] 越狱检测识别与绕过（文件/进程/dylib/sysctl）
- [ ] 证书固定绕过（objection/SecTrustEvaluate/TrustKit）
- [ ] 砸壳与重签名（frida-ios-dump/codesign）
- [ ] Keychain/NSUserDefaults/Data Protection 等级审计

### 15.5 抓包与流量
- [ ] 代理搭建与证书信任（Android 7+ 系统证书/ iOS 完全信任）
- [ ] SSL Pinning 绕过后可正常抓包
- [ ] mTLS 双向认证绕过（证书提取+Burp 配置）
- [ ] 非 HTTP 流量分析（TLS 解密/protobuf/WebSocket/DNS）
- [ ] 敏感数据泄露检查（URL 参数/日志/响应体明文）

### 15.6 存储与密钥
- [ ] SharedPreferences/SQLite/内部外部存储明文检查
- [ ] EncryptedSharedPreferences/Keystore 密钥可提取性验证
- [ ] iOS Keychain kSecAttrAccessible 等级审计
- [ ] 硬编码密钥动态验证（提取的 AWS/云密钥最小化验证）
- [ ] adb backup 数据可导出性验证

### 15.7 WebView 与 IPC
- [ ] WebView JS 开关/JS 桥方法审计（RCE 面）
- [ ] shouldOverrideUrlLoading/onReceivedSslError 处理审计
- [ ] 深链劫持/参数注入/Universal Link 校验
- [ ] Intent Redirection 转发链审计

### 15.8 跨平台
- [ ] Flutter：libapp.so 提取+Blutter 还原+SSL 函数绕过
- [ ] React Native：bundle/Hermes 提取审计
- [ ] uni-app/Cordova：www 资源审计+桥方法
- [ ] 小程序：wxapkg 解包+云函数鉴权+跳转注入

### 15.9 AI 应用攻击面
- [ ] 端侧模型文件提取/替换/逆向
- [ ] AI 助手提示注入测试（直接/间接信道）
- [ ] 移动 Agent 截图竞态/隐形文本/命令注入测试
- [ ] 系统提示泄露/敏感信息泄露测试
- [ ] AI 功能权限最小化验证（跨应用动作/隐私数据访问）

### 15.10 API 与后端云
- [ ] API 端点枚举与未授权访问测试
- [ ] 认证/Token 测试（JWT 算法/过期/刷新链/OAuth 劫持）
- [ ] IDOR 越权遍历（对象 ID 篡改）
- [ ] 参数篡改（价格/数量/角色重放）
- [ ] 速率限制/爆破枚举测试
- [ ] GraphQL introspection/过度查询
- [ ] 服务端注入（SQL/NoSQL/SSRF）
- [ ] 云凭据泄露验证与存储桶权限检查
- [ ] 供应链：第三方 SDK 权限/外发域名/依赖 CVE 审计

### 15.11 完整攻击链验证
- [ ] 单点漏洞已复现并有证据（截图/日志/数据）
- [ ] 尝试串联攻击链（App→API→后端→云）评估实际影响
- [ ] 输出结构化报告（复现步骤/影响/修复建议/危害评级）

