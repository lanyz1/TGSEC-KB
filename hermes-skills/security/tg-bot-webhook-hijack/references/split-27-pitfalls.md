## Pitfalls
- 别用 urllib + socks 打 HTTPS(SSL EOF),用 requests + socks5h 代理
- SSRF/恶意 callback 探测是「记录取证」风控直接诱因——先评估再发,一次触发=IP 拉黑
- censorUserByTG 类接口=用户枚举器(exist+username),限速用(120/min)
- 同族 bot 可能 typosquat:核对 users 数与 og:title

