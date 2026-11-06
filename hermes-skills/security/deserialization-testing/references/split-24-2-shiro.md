## 2. Shiro 家族(核心决策)

### 指纹
- 响应头 `rememberMe=deleteMe`(未登录访问受限页)→ 存在 Shiro
- Cookie: `rememberMe` Base64 AES 加密序列化

### rememberMe 加密模式
- **CBC**: Shiro <1.4.2, IV=密钥前 16 字节(→ 固定 IV)
- **GCM**: Shiro ≥1.4.2, 随机 IV(更安全)
- 默认 Key: `kPH+bIxk5D2deZiIxcaaaA==`(1.2.4 前硬编码,大量沿用)

### 攻击决策
1. **密钥爆破**: 送 `rememberMe=<Base64(AES(key, serialized))>`;响应 deleteMe 变化 = 密钥对
   - 工具: shiro_attack / ShiroExploit / ysoserial 配套;高频字典 250+ 条(镜像 §3.5)
   - CBC 模式密钥不可知 → **Shiro-721 Padding Oracle**(工具: shiro_exp / shiro-721)
2. **Gadget 链**: CommonsBeanutils1(最佳经典链)→ 版本/JDK 兼容矩阵见镜像 §4.3
3. **认证绕过家族**(CVE-2020-1957 → CVE-2026-56091): URL 路径解析差异 `;/`、`..;/`、`%3b`、双写斜杠 → 未授权直达
4. **组合**: Shiro+Fastjson/Log4j、Shiro + Spring Boot 生态
5. **回显/不出网**: 错链回显、Tomcat 内存马(镜像 §5)

