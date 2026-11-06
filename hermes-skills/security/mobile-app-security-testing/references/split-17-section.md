## 十六、修复建议

### 16.1 客户端基础加固
- [ ] 关闭 `android:debuggable`、`android:allowBackup`、`usesCleartextTraffic`；配置 `networkSecurityConfig` 仅信任系统证书
- [ ] 全量使用 HTTPS + 证书固定（Pinning），定期轮换备份 pin
- [ ] 禁止硬编码密钥/云凭据：使用 Keystore/Keychain + 服务端动态下发短期 Token（JWT），密钥生命周期最小化
- [ ] 敏感数据加密存储（EncryptedSharedPreferences / Keychain），避免明文 SQLite/日志
- [ ] 开启 ProGuard/R8/Dart 混淆（Flutter 需 `flutter build --obfuscate`），关键逻辑下沉 Native 并加 VMP
- [ ] 禁用/最小化 WebView JS 桥暴露面：仅对可信域开放 `addJavascriptInterface`、校验来源与参数、设置 scheme 白名单

### 16.2 运行时对抗
- [ ] 分层 root/越狱/模拟器检测（文件+属性+传感器+Play Integrity API 组合，检测点分散分布）
- [ ] 加固 + Frida 检测（文件/端口/D-Bus/内存特征扫描），检测失败即退出而非继续运行
- [ ] 完整性校验（签名/文件/内存段 hash+HMAC，密钥服务端下发）防重打包与篡改
- [ ] 反调试（ptrace/sysctl 检测）与防 Hook（关键校验函数内联汇编化）

### 16.3 组件与 IPC
- [ ] 非必要组件一律 `android:exported="false"`；导出的 Provider/Service 做权限校验与 URI 白名单
- [ ] Provider 输入参数白名单校验（防 SQL 注入/路径穿越），不依赖 grantUriPermissions 放开授权
- [ ] 深链使用 App Links（`android:autoVerify`）/ Universal Links 并校验来源与参数；敏感动作强制二次认证
- [ ] 所有 Intent 转发前校验来源与目标组件（防 Intent Redirection）

### 16.4 服务端与云
- [ ] 全接口鉴权（含隐藏/内部接口），服务端做最终越权校验（IDOR 根本防线在服务端）
- [ ] JWT 使用 RS256 并校验算法头；Token 过期/刷新链加固；敏感操作二次验证
- [ ] GraphQL 关闭 introspection、限制查询深度与数据量
- [ ] 速率限制/验证码防爆破；服务端参数白名单校验
- [ ] 云凭据最小权限+定期轮换+密钥管理服务（KMS/Secret Manager）；存储桶默认私有并审计 ACL
- [ ] 供应链：锁定依赖版本+漏洞扫描（OSV/Snyk/Trivy），审计第三方 SDK 权限与外发行为，警惕依赖混淆

### 16.5 AI 应用专项
- [ ] 端侧模型完整性校验（签名/哈希）防替换投毒
- [ ] AI 输出与外部输入严格隔离：对模型输入做来源标注（provenance-aware prompting），拒绝处理 UI/截图文本中的指令
- [ ] Agent 权限最小化：禁止未确认跨 App 动作、高危操作强制人工确认；命令拼接层禁用 shell 或做参数白名单（防 RCE）
- [ ] 不记录/最小化记录用户 prompt 与 AI 输出（防隐私泄露）；向量库/RAG 内容做可信度分级
- [ ] 参考 OWASP LLM Top 10 定期对 AI 功能做提示注入与数据泄露专项测试

### 16.6 测试流程与基线
- [ ] 参照 MASVS L1/L2 建立常态化测试基线，CI/CD 接入 MobSF 等自动扫描
- [ ] 每季度跟踪行业情报（OWASP Mobile Top 10、MASVS、NVD 移动 CVE）更新技能库
- [ ] AI 辅助开发代码强制安全评审（vibe coding 风险控制）

