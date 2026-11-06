# PayPal 经典 NVP API 接口速查

## 认证
- endpoint: `https://api-3t.paypal.com/nvp`（生产）/ `https://api-3t.sandbox.paypal.com/nvp`（沙箱）
- 认证：API 签名三件套作为 POST 表单参数发送，每个请求带 `METHOD` 和 `VERSION`（如 204.0）
  - `USER` = API Username（格式 `xxx_api1.xxx.com`，注意 `_api1` 是经典 API 标识）
  - `PWD` = API Password（签名密钥，不是登录密码）
  - `SIGNATURE` = API Signature

## 常用接口
### GetBalance（查余额，验证凭据首选）
```
METHOD=GetBalance&VERSION=204.0&USER=...&PWD=...&SIGNATURE=...&RETURNALLCURRENCIES=1
```
返回 `ACK=Success` + `L_AMT0=<金额>&L_CURRENCYCODE0=<币种>&L_AMT1=...`（多币种余额）。ACK=Success 即凭据有效。

### TransactionSearch（查流水）
```
METHOD=TransactionSearch&STARTDATE=2026-01-01T00:00:00Z&ENDDATE=...&TRANSACTIONCLASS=Received
```
`TRANSACTIONCLASS=Received` 只看收款。响应无 `L_` 字段 = 该时间段零交易（账户可能已停用）。

### MassPay（批量付款/转账）
```
METHOD=MassPay&RECEIVERTYPE=EmailAddress&L_EMAIL0=xxx&L_AMT0=0.01&CURRENCYCODE=USD
```

## 错误码
- `ACK=Success` = 成功
- `L_ERRORCODE0=10329` + `L_SHORTMESSAGE0=User is blocked` = **账户无批量付款/转账资格**，需 PayPal 人工开通，无法 API 自助开启。MassPay 官方已废弃（改用 Payouts REST API，需 client_id/secret + OAuth2）。

## 关键陷阱
- MassPay 权限是账户级风控，10329 只能联系客服/账户经理，不存在自助开启接口。
- Payouts REST API 与经典 NVP API 是两套体系：Payouts 要 OAuth2 应用（client_id/secret），经典三件套调不了 Payouts。查库里的 client/oauth/secret 字段判断有无 REST 凭据。
