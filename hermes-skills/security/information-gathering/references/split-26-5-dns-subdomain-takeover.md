## 5. DNS 接管检测(Subdomain Takeover)
**原理**: 子域 CNAME 指向已注销/未认领第三方服务(GitHub Pages/Heroku/S3/Shopify/Fastly)。
```bash
subjack -w subdomains.txt -t 100 -timeout 30 -o takeover.txt -ssl
subzy run --targets subdomains.txt --verify-ssl
nuclei -l subdomains.txt -t ~/nuclei-templates/takeovers/ -o takeover_nuclei.txt
```
**手工确认**:
```bash
dig CNAME sub.target.com   # 看是否指向第三方
```
- GitHub Pages: "There isn't a GitHub Pages site here."
- Heroku: "No such app";Fastly: "Fastly error: unknown domain";S3: "NoSuchBucket"
- 认领验证(GitHub Pages → fork 仓库 → Settings → Pages → 绑定该域名)

