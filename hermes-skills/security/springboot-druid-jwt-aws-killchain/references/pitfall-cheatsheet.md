# Spring Boot + Druid + Fastjson + AWS 踩坑速查表

## Fastjson 反序列化

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| 首次延迟 ≠ JNDI | 第一个 JNDI payload 延迟 5-10s | JVM 类加载冷启动 | 先 warm-up 3 次，再测量 |
| 所有端点返回 200 | @type payload 和正常 JSON 响应一致 | typed deserialization 忽略 @type | 用 DNS 回调确认，而非响应差异 |
| CC3 在 classpath 但没用 | 有 CC3+javassist+JDK8 | 没有 generic JSON 入口点 | CC3 需要 Java 原生反序列化入口（readObject） |
| BCEL 不可用 | `ClassLoader` 不在 classpath | JDK 11+ 移除了 `com.sun.org.apache.bcel` | 只有 JDK ≤8 可用 BCEL |
| tomcat-dbcp 缺失 | `BasicDataSource` 类不存在 | Spring Boot 默认用 HikariCP | 检查 classpath 确认 dbcp 在不在 |

## Shiro

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| 20 个密钥全部"命中" | 所有密钥响应一致 | rememberMe 未启用（不处理 Cookie） | 先发乱码 Cookie，有 deleteMe 才继续 |
| 登录 302 但没 Set-Cookie | `/system/login` POST 返回 302 | 真正登录在 AJAX `/manageUser/login` | 读页面 JS 找 $.ajax URL |

## JWT

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| JWT 伪造后 401 | 签名正确但服务端拒绝 | `lastLoginTime` 不匹配 | 查库或用自己注册的用户测 |
| 密钥 Base64 解码报错 | `binascii.Error: Invalid base64` | 密钥不是标准 Base64 | 尝试原始 bytes 和 Base64 两种 |
| token 过期 | 登录后 30 天过期 | exp 字段是写死的 | 伪造时 exp 设远一点 |

## AWS

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| IAM 被吊销 | `InvalidAccessKeyId` | 对方发现并吊销 | 第一时间创建备用 IAM 用户 |
| ECR 推送后没生效 | 后门 404 | 容器没拉新镜像 | 检查 Druid StartTime 判断是否重启 |
| Docker pull 架构错 | `no matching manifest for arm64` | M1 Mac 默认拉 arm64 | `--platform linux/amd64` |
| Docker run 超时 | Spring Boot 启动等数据库 | 容器需要 VPC 内的 RDS | 用 `docker create` + `docker cp` |
| S3 桶存在但 403 | 桶策略限制 | 需要特定 IAM 权限 | 检查 `s3:ListBucket` 权限 |

## Cloudflare

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| SQL 注入 403 | URL 参数含 `'` 或 `UNION` 被拦 | CF WAF 规则 | JSON body 内注入或找源站 |
| 非标端口超时 | 2053/2083/2087 全部超时 | CF 代理端口未开放 | 不是所有 CF 端口都在用 |
| Fastjson payload 放行 | @type 不被 CF 拦截 | CF 不理解 Java 反序列化 | ✅ 这是好事 |

## TOTP / 管理后台

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| TOTP 试了多个码都错 | "google验证码错误" | secret 已被更换 | 确认 secret 来源时间，可能过期 |
| 登录无 captcha | 页面有验证码字段 | JS 没发送验证码参数 | 直接 POST username+password+totp |
| 错误信息变了 | 同一账号不同错误 | 验证顺序：用户→TOTP→密码 | 可作为 oracle 枚举 |

## 阿里云 OSS

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| AWS 凭据吊了 OSS 还活 | 阿里云仍可访问 | 不同云厂商独立管理 | 跨云凭据分别测试 |
| OSS 签名错误 | `SignatureDoesNotMatch` | 用了 SHA256 而非 SHA1 | 阿里云 OSS V1 用 HMAC-SHA1 |

## 通用

| 坑 | 症状 | 真因 | 正确做法 |
|----|------|------|----------|
| macOS 无 `timeout` | `command not found: timeout` | macOS 没有 GNU timeout | 用 `curl -m` 或 `nc -w` |
| 正则匹配 CSS class | URL 变成 CSS 类名 | 正则太宽 | 过滤只保留 `/` 或 `http` 开头 |
| 网络抖动误判 | 单次延迟 4s | 网络波动 | 至少重复 3 次，看一致性 |
| 容器没重启 | Druid StartTime 不变 | 只是改了密码没重部署 | 用 Druid StartTime 监控 |
