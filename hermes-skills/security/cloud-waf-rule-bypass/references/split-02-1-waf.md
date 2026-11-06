## 1. ★ 先判 WAF 在哪一层——它决定你打源站还是打规则集

拿不到业务面时,**第一件事不是找源站 IP,而是判 WAF 在哪一层**。

```bash
curl -sk -o /dev/null -w '%{http_code}\n' --resolve target.com:443:IP https://target.com/actuator/env
curl -sk -o /dev/null -w '%{http_code}\n' --resolve target.com:443:IP https://target.com/druid/index.html
```

- 直连 IP 干净、不再出现拦截页 ⇒ WAF 是 **DNS 前置(SaaS 版)** ⇒ 直连 IP 就是总旁路,走源站打法。
- 直连 IP **仍旧返回厂商拦截页** ⇒ WAF 是 **inline**(如阿里云独享版,自建 ECS 就在链路里)
  ⇒ **那个 IP 本身就是 WAF,找源站是白费功夫**,改打规则集。
- 控制组:同 IP 换个未配置的 Host 回回 502(厂商自己的默认上游)→ 进一步证明 WAF 就在这个 IP 上。
- 每个 IP 都先发一发控制请求再下结论,不要凭 CNAME / 证书推断。

