---
name: cognito-health-leak
description: >-
  /health 或 /ciam/health 端点未授权泄露 AWS Cognito client_id/client_secret/user_pool_id/管理员邮箱。
  用户提到 Cognito 凭据泄露、health端点泄密、AWS用户池、client_secret明文、
  /ciam/health、PreventUserExistenceErrors差分 时使用。
  与 cognito-unauth-s3-chain(IdentityPool→S3)互补。
---

# AWS Cognito Health 端点凭据泄露

**前提**：目标在 scope。

## 指纹

- `GET /health` 或 `GET /ciam/health` 返回包含 `user_pool_id`/`client_id`/`client_secret` 的 JSON
- 常见于自研 AI/SaaS 平台（FastAPI/Flask 包装 CIAM 层）
- `deploy_env: dev` 不代表安全，生产凭据经常就在 dev 端点里

## 攻击链

### 1. 未授权读凭据
```bash
curl -sk https://TARGET/ciam/health
# 看 bootstrap.config 里的 user_pool_id / client_id / client_secret / admin_email
```

### 2. 差分实验确证凭据有效性（四组）
Cognito 开启 `PreventUserExistenceErrors` 后，单点调用无法确证。**必须差分**：

| 组 | 构造 | 预期返回 | 判读 |
|---|---|---|---|
| D1 | 不带 SECRET_HASH | `Client ... is configured with secret but SECRET_HASH was not received` | 确认 client 配了 secret |
| D2 | 伪造 ClientId | `User pool client 000...0 does not exist` | 基线：client不存在时的错误 |
| D3 | **用泄露的secret** | `SignUp is not permitted for this user pool` | **secret校验通过**→推进到业务规则层 |
| D4 | 用**损坏的secret** | `Unable to verify secret hash for client ...` | **secret校验失败** |

**D3 vs D4 = 完美差分** → 凭据确证有效。

### 3. 利用路径
- 持有 client 凭据 → `InitiateAuth`(USER_PASSWORD_AUTH) / `ForgotPassword` / `SignUp`
- 配合泄露的 `admin_email` → 管理员账号接管候选
- **边界**：client_secret ≠ 平台 Bearer（如 `/ciam/auth/api-token` 需 `access_key/secret_key` 三元组）

## 已知坑位

1. **422 暴露字段名**：`/ciam/auth/api-token` 的 422 会吐 `pool_name`/`access_key`/`secret_key` 必需参数名
2. **不要爆破**：会触发 Cognito 账户锁定，影响目标方 dev 登录
3. **不要 ForgotPassword**：会向真实管理员邮箱发信留痕
4. **Cognito 凭据换不到平台 Bearer**：`access_key/secret_key` 是用户级用户名/口令对，与 Cognito client 凭据不是同一物
