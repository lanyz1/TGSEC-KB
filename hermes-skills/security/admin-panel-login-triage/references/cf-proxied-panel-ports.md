# CF 代理端口与源站判读

## 现象

`api.target.com` 的 `2082/2083/2086/2087/2095/2096/8443/2052/2053/8080/8880` 全有响应,标题也像 cPanel/WHM,很容易判成「源站 cPanel 全端口暴露」。

## 判读

- 这组端口是 **Cloudflare 默认代理端口**;CF 先接受连接,再回源。
- `521` = CF 连不上源站;`526` = 源站 TLS 证书无效。两者都是**边缘错误**,不是源站应用响应。
- 所以 `2087 → 521` 只证明「CF 愿意代理 2087」,**不证明源站跑 WHM**。

## 验证

```bash
# 1. 找非 CF 的 A 记录
dig +short api.target.com
curl -sI https://api.target.com | grep -iE 'cf-ray|server'

# 2. 直连候选源站,带 Host/SNI
curl -sk --resolve api.target.com:2087:CANDIDATE_IP https://api.target.com:2087/ -D- -o /tmp/whm.html
curl -sk --resolve api.target.com:443:CANDIDATE_IP https://api.target.com/ -D- -o /tmp/o.html

# 3. 只有直连拿到 WHM 登录页/证书,才算源站面板存在
```

## 结论

- FOFA/DNS/crt.sh 都拿不到非 CF 的 A 记录 → 源站 IP 未暴露,这条线记为 blocked。
- 不要把 521 写进报告当「cPanel 暴露」,也不要在没有源站 IP 时打 WHM 口令。
