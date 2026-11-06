## 第 5 步: 商户 API 网关测试(HMAC-SHA256)
1. docs 站被 CF 挡 → 用已过 CF 的浏览器 tab 执行 JS 抓全文(别 curl)
2. 下载 SDK zip(php/python/node/java/go),用文档测试向量验证签名实现 100% 一致
3. 签名规则:去 sign/null/空串(保留 0 与 false)、嵌套点号展开、键 ASCII 升序、`k=v&` 拼接不 URL 编码;`sign=UPPER(HMAC_SHA256(base, token))`
4. 接口套路:balance → payLink → checkDeposit/checkTransferByTxid → censorUserByTG → transfer
5. 成功响应也带 sign → 用 verify(恒定时间)确认双向往来

