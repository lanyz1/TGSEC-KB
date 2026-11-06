## 2. ★ 主招:Host 行归一化(一次绕过整层规则)

云 WAF 的规则集按**保护域名的精确 Host 字符串**绑定。Host 不等于任何已配置域名时规则集整体不生效,
而后端 Host 匹配更宽松(Java/Tomcat 尤其),仍会正常路由。这条一次性解开路径黑名单、SQLi、actuator、druid,
所以**优先于逐个路径试混淆**。

```
Host: target.com      + /druid/index.html → 403 拦截页   (基线)
Host: target.com.     + /druid/index.html → 200 ✓ 尾点
Host: target.com:443  + /druid/index.html → 200 ✓ 带端口(真端口、假端口都行)
Host: TARGET.COM      + /druid/index.html → 403 ✗ 大小写会被归一化
Host: target.com\t    + /druid/index.html → 502 路由丢失
```

顺序:**尾点 → 显式 `:443` → 尾点 + 端口**。

- ⚠ **必须用裸 socket 发**:普通 HTTP 客户端会从 URL 重写 Host 行,根本表达不出这个变形。
- SNI 保持真实域名,否则 TLS 握不上;只变 `Host:` 行。骨架见 `references/cloud-waf-rule-bypass.md` §5。
- 实测无效、不必再试:双 Host 头、`X-Forwarded-Host`、`X-Original-URL`、`X-Rewrite-URL`、
  方法切换(POST/OPTIONS)、HTTP/1.0、尾空格。
- Host 变形也被拦 ⇒ 该 WAF 配了 catch-all 域名组,退到 §3,再不行就换攻击面。

