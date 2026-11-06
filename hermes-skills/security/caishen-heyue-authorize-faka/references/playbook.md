# Playbook — 财神 / heyue faka authorize-drain

## payment-config fields

```
domain, payment_address, permission_address (spender),
authorized_amount, authorize_note, model (1|2),
0x_payment_address, 0x_permission_address,
frontend_api_token (optional), main_domain, default_id, qr_domain
```

## HTTP surface

| Path | Notes |
|------|--------|
| GET /payment-config | No auth crown |
| POST /custom-payment | May need X-Api-Token from config; jhlicai worked without |
| POST /create-order | `_token,gid,by_amount,email,payway` — Geetest UI may be fake |
| /bill/SN | initPaymentUI + pay.js |
| /search-order-by-sn · -by-email | Own order oracle |
| /admin/auth/login | Dcat username/password/_token, often no captcha |
| POST /payment/trc20/verify | Needs real chain tx |
| /pay/vpay\|yipay\|epusdt/notify_url | fail without key |

## pay.js hooks

`TRCapproval`, `TRCincreaseApproval`, `EVMapproval`, `permission_address`, `authorized_amount`, `authorize_note`, `fish_address`, `https://tronweb.net/api/approve`, `/payment/trc20/verify`

## heyue

- Methods: `b82a91eb` controlAndTransferToken(token,from,to,amount); `f2fde38b` transferOwnership
- Non-owner call → REVERT
- List Approvals: TronGrid `/v1/accounts/{spender}/transactions/trc20`

## Sibling domains (same IP batch example)

shangchengcnc00N.icu, fadacai00N.top, faxiaocai00N.top, facaifacaiaaa|bbb|ccc.top, shashasha.icu, shouqqqqq.icu, beiyongim*.top, dawenxiniubi.shop

## FOFA

```
title="财神系统 - 后台控制中心"
body="permission_address" && body="/payment-config"
body="财神杂货铺-账号批发"
```
