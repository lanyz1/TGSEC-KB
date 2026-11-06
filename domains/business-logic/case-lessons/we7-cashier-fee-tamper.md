# 案例课：微擎收银台 —— 金额与 fee 都在客户端

> 来源：报告包 aixiaoka（2026-10）· 域：business-logic

## 一句话

模板里 `￥{php echo $item['pt_price'] * $item['miane']}` 在客户端算，下单 JS 直接读 DOM 文本 `$('#sj_price').text()` 当 `sj_price`；服务端无签名/无 nonce/无 token/无 CSRF。收银台 `params` 只是 base64，改 `fee` 重编码即可显示任意金额。

## 链

```text
GET {payUrl}&sj_price=0.01&price=100&...
```

- `sj_price` 来自 DOM，不是服务端订单
- `params` base64 解码 → 改 `fee` → 重编码 → 重开收银台
- 实测 `fee=0.01/0.00/-1/999999` 全被原样接收 = 收银台层不校验

## 措辞纪律

- 只写「金额可被请求方指定」
- **不写**「可任意金额下单 / 可造成资损」，除非真走到建单 + 回调核额
- 报告里把「收银台展示」与「订单实付」分开定性

## 边界

- 微擎模块 `do=pay`/`do=paymethod` 在无 openid 会话下返回「模块不存在」
- 微信 UA 下 302 OAuth = 前置会话缺失，不是漏洞
- 服务端可能在下单/回调时二次核额，必须走到最后一步

## 检查清单

- [ ] 金额字段是否来自 DOM
- [ ] 请求是否带签名/nonce/token
- [ ] `params` 是否可解码改字段
- [ ] 建单接口是否复核金额
- [ ] 回调是否按订单金额入账

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
