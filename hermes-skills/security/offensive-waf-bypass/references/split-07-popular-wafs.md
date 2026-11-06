## Popular WAFs

- **Cloudflare** - Identified by `__cf_bm`, `cf_clearance`, `cf_chl_*` cookies and "/cdn-cgi/" routes (cookies rotate roughly every 30 min)
- **Akamai**
- **Imperva/Incapsula** - Look for "X-CDN: Incapsula" headers
- **AWS WAF** - Commonly sets `AWSALB` or `AWSALBCORS` cookies
- **Sucuri** - Check for "X-Sucuri-ID" headers
- **DataDome**
- **F5 Networks**
- **Barracuda**
- **Fortinet**
- **ModSecurity** - Open-source WAF, commonly used with Apache
- **NAXSI** - Open-source WAF for NGINX
- **Azure Front Door**
- **Fastly Next-Gen WAF**
- **Cloudflare AI WAF**
- **Radware**
- **Coraza** - Modern open‑source WAF written in Go

