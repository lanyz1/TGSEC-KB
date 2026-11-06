# 9581kk.com → ag.61995q.com BetWin 跨域注册实例

日期: 2026-07-13
目标: ag.61995q.com (代理登录端), 9581kk.com (注册端)

## 架构

```
9581kk.com (注册/用户端)  ← 注册 →  共享数据库  ← 登录 →  ag.61995q.com (代理端)
     ├── /m/signup         (会员注册页)
     ├── /m/regagent       (代理注册页)     ← 真正的注册入口
     └── /api/Public/main/index.php?service=  (API 后端)
```

## 关键发现

### 1. GetCompany API 需要 Referer/Origin 头

这是最大的突破点。没有这两个头即使传正确 website 也返回 416。

```bash
# 成功调用 GetCompany 拿到所有配置
curl -sk -X POST \
  -H "Referer: https://9581kk.com/m/regagent" \
  -H "Origin: https://9581kk.com" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "website=9581kk.com" \
  "https://9581kk.com/api/Public/main/index.php?service=Server.GetCompany"
```

返回的关键数据:
- `client_id`: `2e00195a7eff0cfb5ee4c2a8ebbe070200518814` (40字符 SHA1-like)
- `client_ip`: `207.168.55.31`
- `id`: `125771` (公司ID)
- `code`: `b8` (模板代码)
- `domain`: `/app/member/login_mobile.php?uid={token}` (登录跳转)

### 2. 验证码是字母数字混合

41x20 像素 GIF，4位字母数字混合（如 "3AhT", "5846", "dmN2"），不是纯数字。
验证码仅在注册/登录时校验，没有其他绕过方式。

### 3. Agent Registration API 参数

User.RegAgent 的参数列表比 CDN 上的 JS 多一个 `safe_pwd` 字段（取款密码）。
CDN 版本更旧，服务端实际需要该参数。

### 4. 跨域 Cookie 不互通

443 的 PHPSESSID 和 7777 的 Example_Session 分别管理各自的会话状态。
在 9581kk.com 注册后，需要到 ag.61995q.com 用代理登录口登录。

## 未完成

- Agent 注册碰到 `safe_pwd` 格式错误（code 407），需要明确安全密码格式
- 注册成功后需验证能否登录 ag.61995q.com 后台
