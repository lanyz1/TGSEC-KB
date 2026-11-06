## 2. 改写回执 = 自证（每次必打）
输出 rewrite 记录（形如 `/login|POST|77b|hdr=1`）+ **final URL** + body 前 N 字：
- `|POST|<n>b|hdr=1` ⇒ 改写生效；
- final URL 变成 `?alichlgref=<原URL>` / body 丢弃 ⇒ **被该实例降级为 GET**，此路不通；
- 应用返回**它自己的** 403/500/JSON（不是挑战页）⇒ 已穿过 WAF，从此按应用语义推进。

**先跑一次 GET 对照组**确认改写管道本身生效，再判「WAF 降级」还是「改写没生效」。

