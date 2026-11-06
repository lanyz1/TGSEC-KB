## 4. 域名 + HTTPS(Let's Encrypt)

- 先确认 DNS(A + www → IP); **Let's Encrypt 的 DNS 视角与本地不同步**: www 刚解析时 LE 挑战报 `SERVFAIL looking up A`。先签主域, www 传播后再补, 最后合并:
  `certbot --apache -d xeelee.top -d www.xeelee.top --cert-name xeelee.top --non-interactive --agree-tos --redirect --expand`
- **坑: 分开签的两个证书会让其中一个域名拿到 CN 不匹配的证书**(openssl 验证 SAN 只有 www)。必须 expand 合并成单证书 SAN 双域名。
- HTTP→HTTPS 301: certbot `--redirect` 自动配; 续期 `certbot renew` 自带 cron。

