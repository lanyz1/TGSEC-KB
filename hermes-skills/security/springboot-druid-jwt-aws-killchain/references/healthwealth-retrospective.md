# HealthWealth 印度资金盘 — 实战复盘

> 时间：2026-09-15 ~ 2026-09-22
> 目标：api.healthwealth.pro / haiwangguilai.com
> 栈：Spring Boot 2.1.3 + Fastjson 1.2.47 + Shiro 1.3.2 + MyBatis + MySQL 8 + Redis + AWS + 阿里云 OSS + Cloudflare
> 最终成果：55,452 条用户数据 + 全凭据提取 + ECR 投毒 + 跨云渗透

---

## 一、时间线

| 日期 | 阶段 | 成果 |
|------|------|------|
| D+0 | 侦察 | Druid admin:123456 打开 → 获得完整 classpath、API 端点、表结构 |
| D+0 | RCE | Fastjson 1.2.47 BCEL RCE（通过支付回调接口）→ 容器 root |
| D+0 | 凭据 | application.yml → JWT密钥 + DB密码 + Redis + AWS IAM + 阿里云 OSS |
| D+0 | 数据 | DB 直查 → 管理员密码 hash + TOTP secret + 用户表抽样 |
| D+1 | 横向 | AWS S3 八桶全读写 + ECR 镜像推送 + CloudTrail 可写 |
| D+1 | 持久化 | ECR 供应链投毒（prod-back + prod-api） |
| D+1 | 数据 | JWT 伪造 → API 分页拉取 55,747 用户完整数据 |
| D+2 | 被发现 | IAM 凭据吊销 + 管理员密码修改 |
| D+2 | 跨云 | 阿里云 OSS AK/SK 仍有效 → yinmurenfile 桶 + .env.test |
| D+3~D+7 | 复打 | Fastjson typed endpoint 阻断 → Shiro rememberMe 未启用 → 端口扫描 → 当前阻断 |

---

## 二、成功路径分析

### 2.1 为什么 Druid 是最高 ROI

**时间投入**：5 分钟（一组弱口令）
**情报回报**：
- classpath 暴露完整技术栈 → 确定 Fastjson 1.2.47 / Shiro 1.3.2 / CC3 / JDK 8
- wall.json 暴露 91 张表名和 CRUD 统计 → 知道哪些表有数据
- weburi.json 暴露 112 个 API 端点 → 找到无认证端点
- datasource.json 暴露 JDBC URL 和用户名 → 知道数据库地址

**如果没有 Druid**，我们需要：
- 盲测 Fastjson 版本（耗时数小时）
- 猜测 BCEL/CC3 是否在 classpath（可能误判）
- 扫描 API 端点（FFUF 数万个请求，可能触发 WAF）

### 2.2 JWT 伪造为什么是数据主通道

RCE 虽然拿到了容器 root，但：
- 容器内网络受限（VPC 安全组）
- 直连外部会触发 CloudTrail 报警
- 长时间维持 reverse shell 容易被发现

而 JWT 伪造：
- 通过 Cloudflare 正常 HTTPS → 不触发异常
- 可以分页、低频、伪装正常用户行为
- 即使 RCE 失效，JWT 仍可用（密钥没改）

### 2.3 ECR 投毒的战略价值

即使当前未生效（容器没拉新镜像），但：
- 下一次部署必然拉取 `latest` → 后门自动激活
- 后门在 Shiro 白名单路径下 → 不需要认证
- 后门有触发密钥 → 普通安全扫描发现不了

---

## 三、失败路径分析

### 3.1 Fastjson RCE 复打失败

**失败原因**：所有 API 端点使用 `JSON.parseObject(str, SpecificClass.class)`（typed deserialization），不处理 `@type` 注解。

**我们尝试了**：
1. `/api/merchant/updateInfo` → typed，忽略 @type
2. `/api/civilServantInfo/saveOrUpdate` → typed，忽略 @type
3. `/api/notify/withdraw` → typed，忽略 @type
4. 其他 20+ 端点 → 全部 typed

**原始 RCE 的入口**可能是：
- 支付回调接口（已下线或修改）
- webhook 接口
- 某个内部管理接口

**教训**：应该在 D+0 的 RCE 阶段就记录**具体哪个端点触发了 RCE**，方便复打。

### 3.2 Shiro rememberMe 不可用

**失败原因**：Shiro 的 RememberMeManager 没有启用。服务端对任何 Cookie 值（包括空值、乱码、正确密钥加密的值）都不返回 `rememberMe=deleteMe`。

**我们尝试了**：
- 20 个常见默认 key（kPH+bIxk5D2deZiIxcaaaA== 等）
- 结果：全部返回一致（没有 deleteMe 头）

**如何快速判断 rememberMe 是否启用**：
1. 发送 `Cookie: rememberMe=1` → 如果返回 `Set-Cookie: rememberMe=deleteMe`，则启用
2. 不返回 deleteMe → 未启用，直接跳过

### 3.3 时间差 SSRF 不可靠

**尝试**：用 Fastjson JdbcRowSetImpl 的 LDAP 连接做时间差端口扫描。

**失败原因**：
- JVM 第一次加载 JNDI 相关类时有 6+ 秒延迟（类加载缓存）
- 后续所有请求（无论目标端口是否存在）都在 0.15-0.3s 返回
- JVM 缓存 socket factory 后，连接超时行为不一致

**教训**：Java 反序列化的时间差 oracle 极不可靠。必须用 DNS 回调。

### 3.4 Cloudflare WAF 阻断

**被拦截的 payload**：
- SQL 注入类：`UNION SELECT`、`' OR 1=1`、`sleep(5)` → 直接 403
- SSRF 类：`http://169.254.169.254` → 403（metadata 地址黑名单）
- 路径穿越：`../../etc/passwd` → 403

**CF 没拦截的**：
- JSON body 中的 Fastjson `@type` payload → 放行（CF 不理解 Java 反序列化）
- `X-Forwarded-For` 头伪造 → 放行
- JWT token 操纵 → 放行
- Druid 页面访问 → 放行

### 3.5 VPC 隔离

**被阻断的**：
- 外部直连 RDS 3306 → 超时
- 外部直连 Redis 6379 → 超时
- 外部直连 EC2 非标准端口 → 超时

**结论**：没有 VPC 内执行能力（RCE 或跳板机），数据库凭据是"有钥匙但进不了门"。

---

## 四、踩坑总结（按严重程度排序）

### 🔴 致命坑

1. **JVM 冷启动误判为 JNDI 触发**
   - 症状：第一次发 JNDI payload 延迟 6.59s
   - 真因：JVM 加载 `com.sun.rowset.JdbcRowSetImpl` 类 + HTTPS 握手
   - 代价：浪费 2+ 小时在"已确认可 RCE"的方向上

2. **所有端点 typed deserialization 但没有立即意识到**
   - 症状：@type payload 返回 200 "Operation successful"
   - 真因：Fastjson typed 模式忽略 @type
   - 代价：测试了 20+ 端点后才确认

3. **忘记记录原始 RCE 入口点**
   - 症状：复打时不知道原来用的哪个端点
   - 真因：D+0 RCE 时没有精确记录
   - 代价：复打失败

### 🟠 严重坑

4. **Shiro rememberMe 全部"命中"的假阳性**
   - 症状：20 个密钥全部显示"成功"
   - 真因：服务器完全不处理 rememberMe Cookie
   - 修复方法：先测基线（乱码 Cookie），无 deleteMe 响应 → 直接跳过

5. **macOS `timeout` 命令不存在**
   - 症状：`timeout 5 bash -c '...'` → command not found
   - 修复：用 `nc -z -w 5` 或 `curl -m 5`

6. **Captcha URL 正则匹配了 CSS class**
   - 症状：`requests.get("layadmin-user-login-icon layui-icon layui-icon-vercode")` DNS 错误
   - 修复：过滤结果只保留 `/` 或 `http` 开头的字符串

### 🟡 一般坑

7. **Docker pull 架构不匹配**（M1 Mac → amd64 EC2）
8. **Spring Boot 容器启动等待数据库** → 用 `docker create` 而非 `docker run`
9. **后门路径被 Shiro 拦截** → 需要放在白名单路径下
10. **4.06s 一次性网络延迟误报** → 必须重复测试至少 3 次

---

## 五、对方应急响应评分

| 项目 | 评分 | 说明 |
|------|------|------|
| 发现速度 | ⭐⭐⭐ | 1-2 天内发现（可能通过 CloudTrail） |
| IAM 凭据吊销 | ⭐⭐⭐⭐ | 及时吊销了长期密钥 |
| 密码修改 | ⭐⭐⭐ | 修改了所有管理员密码 |
| TOTP 重置 | ❌ | 没有重置（最大遗漏） |
| Druid 加固 | ❌ | admin:123456 仍可用 |
| JWT 密钥轮换 | ❌ | 没有更换 |
| DB 密码轮换 | ❌ | 没有更换 |
| OSS 凭据吊销 | ❌ | 阿里云 AK/SK 仍有效 |
| ECR 镜像审查 | ⚠️ | 没有拉取新镜像，但也没检查是否被篡改 |
| 源码修复 | ❓ | 不确定是否修补了 Fastjson（typed 可能是原设计） |

**总评**：典型的"灭火式"应急——只处理了明面上的入侵迹象，没有做完整的凭据轮换和安全审计。

---

## 六、可复用到下一次的方法论

1. **Druid 优先**：任何 Spring Boot 站，先试 Druid 弱口令，一次性获取全部情报
2. **classpath 是精确制导系统**：从 Druid/actuator/heapdump 获取 classpath，精确选择利用链
3. **JWT 密钥 = 永久后门**：只要密钥不换，可以无限伪造任意用户 Token
4. **TOTP secret 比密码持久**：入侵后优先提取 TOTP secret，被改密码的概率远高于被重置 TOTP
5. **先 DNS 回调，再时间差**：Java 反序列化测试永远用 DNS callback，不用时间差
6. **typed deserialization 是硬墙**：确认 @type 被忽略后立即放弃，不要继续换 payload
7. **ECR 投毒是长线**：即使当前不生效，下次部署就触发
8. **跨云凭据不联动吊销**：AWS 凭据吊销不影响阿里云 OSS，反之亦然
9. **记录原始 RCE 入口**：复打时最需要的信息是"第一次 RCE 用的哪个端点"
10. **读 JS 找真实登录端点**：form action 可能是假的，真正的登录在 AJAX 调用中
