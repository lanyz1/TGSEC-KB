## Pitfalls
- **泛解析过滤**: 目标域名泛解析 *.domain 全回同 IP → DNS 爆破结果全是假的,必须过滤
- 证书 SAN 常暴露隐藏 vhost: `openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -text | grep -A3 "Subject Alternative Name"`
- 本机 v2rayN TUN 时 socket 直连全端口假 OPEN → 存活判定以 httpx 业务响应/Censys 为准
- FOFA/Shodan 额度省着用: 先被动(零成本)再主动爆破
- 旁站≠同库同业务,验证 HTTP 行为是否独立应用
