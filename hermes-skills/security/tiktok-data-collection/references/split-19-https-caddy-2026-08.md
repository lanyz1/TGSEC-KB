## 域名 + HTTPS 上线(Caddy,2026-08 实测)
- **分工**:用户去注册商加 DNS(我不能碰注册商),我配服务器 Caddy。用户只做一步:A 记录 `@` → `118.107.3.134`(www 可选),各注册商位置:阿里云/腾讯云/Namecheap Advanced DNS/Cloudflare
- **Caddyfile 双块结构**(IP 回退 + 域名 HTTPS 块共存):
  ```
  http://118.107.3.134 { encode gzip; reverse_proxy 127.0.0.1:3000 }
  tiktide.com, www.tiktide.com { encode gzip; reverse_proxy 127.0.0.1:3000 }
  ```
  → `caddy validate --config /etc/caddy/Caddyfile` → `systemctl reload caddy` → **443 自动开始监听**(证书由 Caddy 自动向 Let's Encrypt 申请,无需手动配置)
- 证书签发依赖 DNS 生效;域名块配好后 443 监听即就绪,等 DNS 解析过去即可访问 https://域名
- HTTPS 就绪后:**删除 .env 的 `COOKIE_SECURE="false"`** → `pm2 restart tikflow --update-env`(登录 Cookie 全面启用 Secure 属性)
- **域名挑选**:Tik 生态词(tikflow/tikpulse/tiksurge...)基本全被注册,连 .io/.ai/.net 都难;可行方向=换序(flowtik)、造词(tiklly/tikyflow)、小众后缀(.tech/.xyz/.cc/.me)、语义组合(boosttik/tiktide)
- **域名可用性探测**:`nslookup domain | grep Address` 会误判(**解析服务器地址也匹配 Address**,所有域名都显示"已注册")——用 Python `socket.gethostbyname(d)`,`socket.gaierror` = 无 A 记录 = 可注册候选;⚠️无 A 记录≠一定可注册(注册未解析的很多),最终以注册商搜索结果为准,看好立刻注册

