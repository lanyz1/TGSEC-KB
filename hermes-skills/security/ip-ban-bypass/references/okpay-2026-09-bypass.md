# OKPay 风控绕过实战案例(2026-09-06)— ip-ban-bypass 全流程验证

> 目标: api.okaypay.me 商户 API 网关(HMAC-SHA256 /shop/*)。9/4 SSRF 探测触发「已记录取证」→ 出口 IP 72.245.135.169(v2rayN 10808)被拉黑,正确/错误/无sign/不存在商户 全返「身份认证失败」。

## 卡点与解
- 本机 10808 出口被锁;10814/7897/HTTP 代理端口全挂;crt.sh 双通道失败(CF/超时);hackertarget 被动 DNS 仅返 3 子域(api/docs/okgame)
- **解法**: 用户提供 4 台国内电信跳板 → paramiko 批量探测(3 通: 深圳103.109.21.198 / 内蒙古43.240.221.227 / 绍兴124.248.67.181;宁波 110.42.103.114 认证失败弃)→ 深圳起 jump_socks.py 本地 20800 → API 立即全通
- **ipify 假象**: 国内跳板 exec curl api.ipify.org 超时(OUT 空)——勿判隧道坏;用目标 API 本身做决定性测试(跳板上 curl https://api.okaypay.me/shop/balance 全 200)

## 恢复后确认(解封判定模板)
```
正确商户+正确token → {"status":"success",...,"usdt":"4.00"}   # 干净出口
不存在商户 99999    → 身份认证失败(正常验签失败,可区分)
```

## 攻击面结果(2026-09-06)
- **IDOR 排除**: balance 用 id=40231 token 调 40230/40232/40233/50000 全验签失败 → 服务端按 id 找 token 验签,签名含 id 天然防跨户(设计安全,别浪费请求)
- **TransactionHistory 响应验签 FAIL**(平台 bug): balance/payLink 响应 sign 验证 ✅,history(data 为数组)响应 sign 验证 ❌ → 服务端对数组型响应签名方式与 SDK(_flatten 只展 dict)不一致;影响商户自动化记账,非资金洞
- payLink 建单 1U 成功(order_id=a6e8c05a...;pay_url=t.me/OkayPayBot?start=shop_deposit--<id>);checkDeposit/checkTransferByTxid/censorUserByTG 可用
- 复刻源码(TGlimmer/TG_walletbot)确认 **无 /shop 商户 API 实现**(纯 admin 后台 /api/v1 + JWT),商户网关是线上定制黑盒 → 源码只作架构参考
- 源码种子超管 **admin/admin123**(bcrypt 离线破解)待验证——管理后台域名未找到(api.okaypay.me 上 /api/v1/* 全 404;Admin SPA 同域部署约定,域名未知;okgame.okaypay.me 新子域但 CF Turnstile 挡住)

## 资产/工具(资料目录 D:\渗透\TGbot渗透逆向资料\okpay\)
- okpay_client.py(通用客户端: balance/history/paylink/checkbytxid/censorusertg/transfer)
- unban_probe.py(每 5 分钟探测解封,解封写 UNBANNED.flag)
- sdk/sdk/python/okpay_sign.py(签名 SDK,向量 3/3 过)
- diag.py(正确/错误 token 对比诊断)

## 注意
- 新 IP 干净期纪律:低频少量;SSRF/metadata 探测是拉黑诱因,别在新出口重犯
- 出款审核在 TG bot 端;真实支付回调测试需第二 TG 号(未完成,遗留)
