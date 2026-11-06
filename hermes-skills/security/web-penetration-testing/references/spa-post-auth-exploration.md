# SPA 登录后渗透方法论

## 场景
目标 SPA 需要登录，已通过凭证/注册/社工获取到有效账号。

## 步骤

### 1. Token 注入法（绕过登录页面）

```javascript
// 在浏览器控制台执行：设置 localStorage 后刷新
localStorage.setItem('token', '获取到的token');
localStorage.setItem('account', JSON.stringify({...userInfo}));
location.reload();
```

注意：有些 SPA 的 key 名不是 `token`，需从 JS 源码中搜索 `localStorage.getItem(` 提取正确 key 名。

### 2. Cookie/Session 注入

```javascript
// 通过 API 登录后检查 Set-Cookie 头
document.cookie = "token=值; path=/";
```

### 3. 直接填写表单登录（推荐）

最稳定：直接操作 DOM 填写账号密码，点击登录按钮。
```
browser_type → 输入账号
browser_type → 输入密码
browser_click → 点击登录按钮
browser_snapshot → 确认登录成功
```

### 4. 登录后信息收集

| 操作 | 方法 |
|------|------|
| 导出 localStorage | `for(let i=0;i<localStorage.length;i++){console.log(localStorage.key(i), localStorage.getItem(localStorage.key(i)))}` |
| 检查 API token | localStorage 中搜寻 `token` / `auth` / `session` 等 key |
| 获取用户信息 | localStorage 中通常存有 `account` / `user` / `profile` 等对象 |
| 检查权限 | 注意 `role` / `plan` / `isActivated` / `quota` 等字段 |

### 5. 已认证 API 探测

登录后获取 token，通过 curl 批量测试 action：

```bash
# 批量测试 action
for action in "list" "detail" "create" "delete" "update"; do
  curl -s "https://target.com/api/?action=$action" -H "Authorization: Bearer $TOKEN"
done
```

### 6. 通过浏览器交互探索隐藏功能

登录后的 SPA 可能有引导流程（新手引导），必须先跳过/完成才能看到完整功能：

```
browser_click → "跳过引导" / "下一步" 按钮
browser_snapshot → 查看仪表盘
```

注意导航栏元素——通常包含未在 JS 中直接暴露的路由/功能入口。

### 7. 账号信息提取

登录 API 返回的 payload 通常包含：

```json
{
  "account": {
    "accountId": "acc_customer_xxx",
    "role": "customer",        // 是否有 admin 角色？
    "plan": "monthly",          // 套餐等级
    "watchQuota": 20,           // 功能配额
    "expiresAt": 1785641063012  // 到期时间
  }
}
```

### 8. 小号注册法（当无法获取现有账号时）

如果目标有注册功能，注册免费账号进入：

| 步骤 | 操作 |
|------|------|
| 探测注册接口 | `POST /api/user/register {phone, password}` |
| 枚举用户 | 不同手机号返回差异 → "该手机号已注册" vs "注册成功" |
| 注册小号 | 使用未注册手机号创建免费账号（注意 `isActivated` 字段） |
| 登录小号 | 通过 API/browser 登录，探索可用功能 |
| 配额限制 | 记录免费账号的 quota/plan 限制 |

### 9. 密码重置分析

如果登录失败或忘记密码，测试重置流程：

```http
POST /api/user/reset-password
Content-Type: application/json

{"phone": "目标手机号", "wechat": "绑定的微信号"}
{"phone": "目标手机号", "email": "绑定的邮箱"}
```

注意重置接口返回的错误信息——可能泄露用户绑定方式（微信/邮箱）。
