---
name: edgeone-origin-bypass
description: "源站绕过: EdgeOne/CDN 后源站IP发现与403白名单突破。"
---

# EdgeOne/CDN 源站绕过方法论

## 场景
目标站受腾讯 EdgeOne CDN 保护,想绕过 CDN 直连源站(绕过 WAF/限流/JS挑战)。

## 1. 源站 IP 发现(按优先级)
1. **JS 资产内嵌域名**: app.js / vendor.js 里找 `imgUrl`/`startGameUrl`/`launchGameCDNs` 等源站域名(如 `www2.854819.com:42666`、`images.b298100.com:42666`)
2. **Censys 内容搜索**: 搜目标首页特征/JS 指纹 → 源站 IP(Censys 账号见记忆)
3. **hackertarget 反向 IP**: `api.hackertarget.com/reverseiplookup/?q=<源站IP>` → 同 IP 的兄弟域名(同一平台所有白标站的源站!)
4. **历史 DNS**: hackertarget hostsearch / crt.sh

## 2. 源站验证(重要: 区分真实端口 vs TUN 假象)
- ⚠️ 本机开 singbox_tun 时,**对任意 IP 的所有端口 connect 都显示 OPEN**(假象)
- ✅ 必须用**代理出口**(住宅 SOCKS5)做真实验证
- 真实端口通常只有: 80 / 443 / 业务端口(如 42666)

## 3. 403 白名单绕过(学到但此处无效)
- 方法变体: GET/POST/PATCH/OPTIONS/TRACE/HEAD/PUT/DELETE
- 路径混淆: `///` 三斜杠、`/./`、`%2f`、`//;//`、`/*/`、大小写、尾斜杠
- 头部伪造: X-Forwarded-For / X-Real-IP / Client-IP / X-Originating-IP / X-Remote-IP / X-Remote-Addr / X-ProxyUser-Ip / Host: localhost / X-Original-URL / X-Rewrite-URL
- 参考: github.com/LucasPDiniz/403-Bypass

## 4. 实战结论(2026-08 AQ777 案例)
- 源站 nginx 常配**精确路径白名单**(只放行 domainRoute 健康检查),403 绕过(方法/路径/头)全部无效
- ⚠️ **2026-09 重大修正**: "403 白名单不可破"只试了 80/443!**平台源站群常有隐藏高端口
  (如 42666)对公网开放且按 Host 路由** —— 34.92.19.239/35.220.223.241:42666(TLS)直接
  返回完整 `/wps/*` JSON。必须先做**全端口扫描(1-65535)+ 对每个非 80/443 开放端口做
  TLS Host 头枚举**,再下"锁死"结论。
- 判定边缘节点 vs 真源站: 边缘(EO)8080 返回 `Server: TencentEdgeOne`+418、证书 SAN 空、
  /cdn-cgi/trace=567、全 C 段无业务端口;真源站(IMG-PROXY/EdgeBot-IMG)42666 有 vhost 服务。
- 42666 是 **TLS 口**: 明文 HTTP 送 → `400 The plain HTTP request was sent to HTTPS port`,
  必须 ssl 包一层再打。
- 兄弟域名横向: 同一源站 IP 挂 16+ 白标站域名,有的返回 301(www 跳转),有的是**裸 nginx 默认页(200 Welcome to nginx)** = 未配置的悬空域名
- 裸 nginx 服务器无业务路径(全 404),只有默认页+robots.txt
- **EO 567 备用域突破**: 备用域解析到 EdgeOne 边缘(非源站),但 567 质询可用
  **已访问过同族 EO 站的浏览器 CDP 会话**(指纹已被信任)直接过;页面内 fetch 全通,外部 curl 全 567。

## 5. 结论
- 严格路径白名单的源站 = 边缘节点(IMG-PROXY 类),业务数据全在 CDN 后的 wps-core
- 突破方向: 换 Host 头找未锁 vhost → 兄弟域名逐个测 → 若全 403/404 则源站不可达业务
- 此时应转向: CDN 前端的业务接口(注册/登录/枚举)、多商户横向、社工代理资格


---

## 外部库增量（2026-10-11 分享包）

## 0. ★★ 源站直连 = WAF 配额整体旁路(不只是"找 IP")

找到源站 IP 后**不要只把它当"绕过 CDN 的备选"**——直连源站 = **ATD/智能限速/区域封禁整层消失**,可放量、可发被 WAF 拦的载荷。这是免费拿到的"无限速通道"。

```bash
# 直连源站 + 伪 SNI/Host(htt...[truncated]方法论
