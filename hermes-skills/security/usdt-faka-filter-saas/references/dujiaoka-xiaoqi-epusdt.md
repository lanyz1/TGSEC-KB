# 独角数卡 / 小柒 + epusdt / 易支付

## 指纹

- cookie `dujiaoka_locale`；`/assets/unicorn/`
- robots `Disallow: /manage-<hex>` → 后台真路径
- 标题小柒.APP V14；`/manage-<16hex>/auth/login` 可无验证码
- `hello epusdt`：`pay.` 子域或源站 `:8000`
- `/buy/{id}` → `POST /create-order` → `/bill/{SN}`

## 顺序

1. 确认非 approve
2. 下单抽 token/字段；bill 选 payway
3. 跳 epusdt 收银台：`data-clipboard-text` = 金额+TRC20
4. 查单：SN-only（如 pttget）= 高危隐私；有 pwd+429 则换面
5. 后台 manage-hash + 弱口；限流换字典/换面
6. 回调：V14 勿套老独角 merchant_id=key；先抓支付跳转 pid/key
7. epusdt API：`signature=md5(sorted k=v + api_token)`；弱 token 常 401

## 锚点 2026-09

| 站 | 要点 |
|----|------|
| laotie.app | 小柒 V14；manage-73615…；LAO SN；yipay 在；老伪造未中 |
| pttget.com | 独角+66.42.44.209；payway=23；SN-only 查单；收款 TQCMsTm8…→TA3tfg… |
| inspifa.com | ThinkPHP jingdian，非独角 |

## 坑

- `/admin` 404 ≠ 无后台
- create-order 回 HTML 账单，从 `/bill/SN` 抽单号
- epusdt hello ≠ 未授权下单
