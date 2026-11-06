---
name: unauth-fixed-token-mint
description: >-
  Use when 前端调 /api/getToken、/api/anonymous、/api/guest 这类「未认证取 token」接口：返回固定单例
  token 且绑定真实账号（常是官方/根推广号），带上它全站 App API 变已登录，还能 refreshToken 续期。
---

# 未认证固定令牌签发 → 全站 API「已登录」

实战来源：fuzhuFM 福助（2026-09，`prod-api`），`GET /api/getToken` 每次返回同一个 token，绑定官方根推广账号（inviteNum 3875），可直接拉会员数据、佣金、订单，`refreshToken` 续 7 天。

## When to Use

- App/小程序后端是 `prod-api` / `app-api` / `/api/v1` 风格，前端启动时先取 token
- 接口名带 `getToken`、`token`、`anonymous`、`guest`、`visitor`、`init`
- 页面未登录也能浏览商品/列表（说明有游客态）

## 判定（两步）

```bash
# 1. 连调两次，看是不是同一个值
for i in 1 2; do curl -s 'https://目标/prod-api/api/getToken'; echo; done

# 2. 带上它打一个需要登录的接口
TOK=$(curl -s 'https://目标/prod-api/api/getToken' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["token"])')
curl -s -H "Authorization: Bearer $TOK" 'https://目标/prod-api/api/member/getInviteData' | head -c 400
```

- 两次相同 = **单例令牌**（不是随机游客 token）
- 第二步返回 `code:200` + 真实会员字段（memberId / userName / inviteCode / 佣金）= 命中
- 再看 `expiresIn` 与是否有 `/api/refreshToken`

## 为什么危险

- 令牌绑定的是一个**真实账号**（常是官方号/根推广号/演示号），权限比游客高
- 单例 → 全网共用，泄露面极大（前端硬编码、日志、GitHub）
- 可 refresh → 持续访问，不是 24 小时过期就完

## 放大路径

| 方向 | 动作 |
|---|---|
| 数据面 | 用 token 翻 `member/*`、`order/*`、`invite/*`，看是否只返回自己还是可带 `memberId` 参数 |
| 越权 | 带 `memberId=`/`userId=` 换目标（多数后端不校验 token 与参数一致性） |
| 资金面 | 佣金/钱包/提现接口是否只凭 token |
| 续期 | `/api/refreshToken` 拿新的，验证过期后仍可用 |
| 管理面 | 试 `/prod-api/admin/**`，有的部署同一 token 通吃 |

## 判据门槛

- **L1**：接口无鉴权返回 token
- **L2**：两次调用同一 token
- **L3**：token 打业务接口返回真实用户数据（非空、非 demo）

## 坑

1. 有的站 getToken 返回**游客 token**（每次不同）——不算洞，别写成单例
2. token 可能绑 IP/UA → 复用时要带同样的头
3. 单例 token 常被风控重点盯，批量拉数据要控速
4. `Authorization: ***`（掩码）这种写法在报告里是脱敏，实际要发完整值

## 相关卡

- `jwt-bypass-pentest` — 令牌是 JWT 时的伪造/绕过
- `api-noauth-hunt` — 未授权 API 面系统排查
- `api-authz-idor-testing` — 拿到令牌后的越权
