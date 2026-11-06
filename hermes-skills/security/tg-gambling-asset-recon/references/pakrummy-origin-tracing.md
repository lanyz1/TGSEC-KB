# YonoGames/bdrummy 源站溯源（FOFA 完整结果）

## FOFA API（[FOFA-MIRROR-REDACTED]）
- URL：`https://[FOFA-MIRROR-REDACTED]/api/v1/search/all?key=KEY&qbase64=BASE64(query)&size=N&fields=ip,port,host,title,server,org,country`
- 搜索语法：`domain="x"` / `host="x"` / `cert="x"` / `body="x"` / `title="x"` / `server="x"` / `org="x"` / `country="x"` / `ip="x"`
- 注意限流（“请求过于频繁，请3秒后再试”），每查询 sleep 4s
- cert="bdrummy.com" 搜到 69 结果、body="BD RUMMY"&&org!="Amazon" 搜到 418 结果

## 完整域名矩阵（FOFA 交叉验证）
### 游戏域名（全 CloudFront，org=Amazon，边缘 13.35.36.x/13.33.183.x/3.175.214.x/65.8.131.x/65.9.126.x/99.84.x）
- bdrummy1~19.com、bdrummy1~9.bet、bdrummya~z.com（单字母变体）
- bdrummy.bet / bdrummyapk.com / bdrummyagent.com / bdrummy.com / bdrummyofficial.com
- 随机域名：cweubis96s.com(ga→3.163.125.23)、fcwjosk830sj.com(img→18.245.86.80)、fwui238929sh.com(ifs→3.169.252.127)

### 推广/SEO 站（Cloudflare 保护，独立源站）
- bdrummyslot.com（源站 38.54.85.64，Windows VPS，LIGHT NODE/Kaopu Cloud HK）
- bdrummyapps.com、bd-rummy.online、crekex.online、wine-bdb.com、ok777-slot.online、joya-9.online、baazi-life.online
- toproutehub.com、maxfieldzone.com（BD RUMMY 页面，CloudFront）

### 新盘矩阵
- **jaiho777 系列**（印度盘）：jaiho777vip.website/.live/.biz/.cc/.site/.top 等，jaiho777app.live、jaiho777go.com（CloudFront 13.33.88.x/54.192.35.x）
- yonogames-in.com（Yono Games India，Cloudflare）

## 源站结论（重要）
- **游戏后端源站 IP 不通过任何公开渠道暴露**：安全组只放行 CloudFront IP 段，端口扫描（FOFA/Shodan/Censys）看不到源站
- 源站是 Go 后端 + OpenResty，WebSocket 登录入口 wss://lo.fcwjosk830sj.com/ws 走 CloudFront
- 邮件 MX 泄露阿里云新加坡（mail.sg.aliyun.com 47.246.110.147），但源站 IP 未暴露
- 推广站源站已定位：38.54.85.64（bdrummyslot.com，Windows，开 22/21/80/443/888/3389/445/135/5985）

## 下一步建议
1. 38.54.85.64 是推广站 Windows VPS（开 3389/445/5985），可尝试 RDP/SMB 弱口令（推广站与主盘可能同伙，可能有关联凭据）
2. 游戏源站需通过 CloudFront 行为泄露（502 错误、Host 头、SSRF）或拿 Censys/Shodan 高级 API 搜源站指纹
3. jaiho777 新盘可套用 bdrummy 的全套协议（同一套 Go 后端）