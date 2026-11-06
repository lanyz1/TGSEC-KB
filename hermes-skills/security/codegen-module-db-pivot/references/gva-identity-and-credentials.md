# GVA 系:Credential 获取 与 JWT 伪造要点

配合 SKILL.md 的「线 A — 先把后台身份升到最高权」。
本卡覆盖**拿到身份之后**的两件事:去哪捡真口令、JWT 能干什么/不能干什么。

---

## 一、审计日志 = 明文口令金矿(优先查,比爆破快几个数量级)

`sys_operation_records` 把管理动作的**请求参数原样入库**,于是重置密码/建号类请求的
**明文口令直接躺在表里**:

```json
{"status":"active","loginUsername":"demo9999","loginPassword":"<明文>","agentName":"demo9999"}
```

来源通常是 `POST /user/resetPassword`、`/user/setUserInfo` 这类 body。

**用法:全量拉 `body` 列 → 正则捡 `loginPassword`/`password` → 得到真实可用凭据。**

**实测注意:**
- 表达式过长会被拒(`record not found`)→ 用最短形式 `IFNULL(body,'')`
- 拿到口令后**本地 bcrypt 验证一遍**再采信(对照该账号的哈希)
- 同一批口令常在多个账号间复用 → 拿去撞其它账号/其它套控制台
- ⚠️ 这张表同时也**记录你自己的操作**(含来源 IP) —— 是 OPSEC 风险点,别忽略

---

## 二、JWT 伪造:三重要点

### 1. 密钥位置与离线验证(零请求)

密钥在系统配置的 `jwt.signing-key`(GVA 默认是个 UUID 形态的串)。

**不要靠"拿候选密钥去请求看通不通"** —— 太慢且会被风控。
**正确做法:拿一个真实 token 离线比对。**

```python
import hmac, hashlib, base64
h, p, sig = open("real_token.txt").read().strip().split(".")
real = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
msg  = (h + "." + p).encode()
for key in candidates:
    for alg, fn in (("HS256", hashlib.sha256), ("HS512", hashlib.sha512)):
        if hmac.new(key.encode(), msg, fn).digest() == real:
            print("命中", alg, key)     # 签名长度可先判 alg: 32B=SHA256, 64B=SHA512
```

**优点:命中即铁证,零请求、零风控。** 先按签名长度锁定 alg 再刷候选。

### 2. payload 结构必须与真实 token 逐字对齐

**签名算对了、服务端照样可能拒收** —— 因为载荷字段不一致。
**先解码一个真实 token,照抄它的字段名与顺序,再改值。**

实测该平台真实 token 里有两个**容易漏掉**的字段:
```json
"MFAAuthenticated": true, "TokenType": "session"
```
漏了它们 = 校验过不去(症状是登录态/鉴权直接失败,而非报错)。

### 3. ⚠️ 身份以 Redis 为准 —— 改 claims **提不了权**

中间件流程:`解析 token → 取 claims.UUID → 去 Redis 查该 UUID 的会话/用户信息`,
**以 Redis 记录为权威**。

所以:
- ✅ 能做的:**复用已存在的 UUID**,伪造一个签名有效的票(免密码/免验证码维持访问)
- ❌ 不能做的:把 `AuthorityId` 改成 888 来提权 —— **claims 会被 Redis 覆盖**
- 想真提权,只能从**数据库/Redis/接口**层面改真实归属

**反过来也说明:** 想知道"某个伪造到底成不成",看它对**已存在 UUID**的表现即可。

---

## 三、权限固化:改完必须换票

GVA 的 authority **固化在签发的票里**。改完账号权限后:
**必须重新登录换新票**,旧票仍按旧权限判。
不换票就断言"提权失败"是误判。

---

## 四、排查速查

```
拿到的口令登不上          → 先本地 bcrypt 验证该库哈希,确认口令真的对
                              (对而登不上 ⟹ 这个控制台不读这个库,见
                               console-db-identity-verification.md)
伪造 token 签名对但被拒    → payload 缺字段(查 MFAAuthenticated / TokenType)
伪造 token 能过但权限没变   → 正常:身份以 Redis 为准,claims 提不了权
改完权限仍判低权           → 没重新登录换票
error-based 读审计表被拒    → 表达式太长,用 IFNULL(body,'')
```

---

## 五、同类平台的通用性

这套"审计表存明文口令 / JWT 密钥在系统配置 / 身份以缓存为准"的组合,
在**国产低代码后台(GVA / 若依 / Vol.Core 一族)**里反复出现。
换目标时**优先检查这三处**,再考虑爆破。
