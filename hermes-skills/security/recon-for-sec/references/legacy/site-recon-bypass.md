<!-- archived from /root/.hermes/skills/security/site-recon-bypass/SKILL.md on 2026-10-21 -->

---
name: site-recon-bypass
description: "测绘边界绕过总纲:源站主IP/CF/WAF/白名单/JWT。触发:测绘,找源站,真实IP,CF绕过,jwt"
---

> 归档卡：原目录 `/root/.hermes/skills/security/site-recon-bypass`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/site-recon-bypass/…')`，不要相对 `references/legacy/` 解析。

# Site Recon & Edge Bypass — 网站测绘与边界绕过总纲

**家族地图技能**:任何目标先跑完本总纲(0-5 阶段),再进漏洞链。把散落技能(CF 源站/Censys 引擎/IP风控/JWT/前端认证)串成一条完整流水线。

## 0. 边界识别(30 秒,决定后续打法)

```bash
nslookup target.com   # 看 IP 段
curl -sI https://target.com/ | grep -iE "server|cf-ray|x-cache|via|set-cookie"
```
| 特征 | 判定 |
|---|---|
| IP 104.16-19/172.64-67/188.114.x + `server: cloudflare` + `cf-ray` | Cloudflare |
| `x-cache: hit` / `via: 1.1 amazon` | CloudFront/其他 CDN |
| 403 页含「已记录取证/请求非法」 | 云 WAF/风控(阿里/腾讯) |
| 质询 `Just a moment...` / Turnstile | CF challenge(交互式难自动) |

输出:`{边界类型, 全站CDN?, 源站指纹线索(nginx 版本等从 405/错误页拿)}`

## 1. 资产测绘(域名/IP 线索全量收集)

1. **证书透明**:`curl -s "https://crt.sh/?q=%25.target.com&output=json"`(被 CF 挡就走代理);Censys cert 搜索;certspotter
2. **被动 DNS**:hackertarget `api.hackertarget.com/hostsearch/?q=x`、rapiddns.io、SecurityTrails(注册)、微步 x.threatbook.com
3. **证书 SAN 挖隐藏 vhost**(快速):
```bash
echo | openssl s_client -connect target.com:443 -servername target.com 2>/dev/null | openssl x509 -noout -text | grep -A3 "Subject Alternative Name"
```
4. **子域主动枚举**(纯 DNS,不触 web):字典 + `nslookup`/socket 批量解析;优先 dev/test/staging/api/ws/admin/内部名
5. **JS 挖域名**:抓 SPA 的 JS/源码提取 `api.*`/`ws.*`/隐藏域(CDP 抓页或下载 chunk)
6. **同主体/兄弟资产**:ICP 备案反查、同 IP 反查、whois 邮箱关联
7. **历史 DNS(源站关键!)** ⭐:SecurityTrails/ViewDNS.info 查 **CDN 接入前的 A 记录**——经常直接是源站 IP
输出:`{域名表, 解析/历史IP/证书SAN, 兄弟资产}` → 存 `D:\渗透\<目标>_recon\assets.md`

## 2. 源站 / 真实 IP 发现(核心,收益最大,按序试)

| # | 方法 | 命令/工具 | 备注 |
|---|---|---|---|
| 1 | **历史 DNS** | SecurityTrails / ViewDNS | CDN 前旧 IP,最快常中 |
| 2 | **测绘引擎内容搜索** | Censys/Shodan/Fofa 搜基础设施域名/品牌唯一串 | ⭐主武器,语法额度见 `space-mapping-engine-recon` |
| 3 | 未挂 CDN 的子域 | §1 结果里非 CF IP 的 | 直连即源 |
| 4 | 证书指纹反查 | 目标证书 SHA256 → Censys cert search | 源站从未直连时无效 |
| 5 | 邮件头 | SPF 记录 / 注册邮件原文 IP | 发信服务器常与源站同段 |
| 6 | 边缘泄露 | SSRF / 报错页 IP / debug | 需要入口 |
| 7 | APK/客户端 | 抓 APP 内 API 域名 | 常直连源站不走 CDN |
| 8 | 测试/分站 | dev.staging.test 子域裸奔 | 同源同服 |

**验证(防误判,血泪)**:
```bash
curl -sk --resolve "target.com:443:候选IP" https://target.com/ | head   # 必须 --resolve 保 SNI
# ✅ 判据: 页面 title 匹配 + 响应头无 cf-ray + server: nginx/版本匹配 = 源站确认
```
详见 `cloudflare-bypass`(六层防护分层识别 + Censys 内容搜索实战 + TUN 假象坑)

## 3. 服务器指纹 / 端口测绘

- Banner: `server`/`x-powered-by`/`x-aspnet`/错误页(nginx 版本/thinkphp/tomcat/spring)
- TLS: 证书签发者(Let's Encrypt / **CF Origin CA**=源站用 CF 证书)、ja3/jarm
- 端口权威数据: **Censys hosts/IP 页核对**(本机扫受 TUN/代理劫持全假 OPEN)
- 非标端口: 8080/8888/8443/9000/8081 试管理面
- 技术栈: favicon hash、meta generator、robots.txt、触发报错、响应时序
输出:`{服务器/框架/端口/中间件 → 对应打法家族}`

## 4. 边界绕过矩阵

### 4.1 CF/EdgeOne → 源站直连
- 主路径 = §2 找到源站后 `--resolve`/改 hosts 直连(保 SNI,WS 同理)
- 质询: 普通 CF 质询 headless 等 8-12s 可过; **Turnstile 交互式难自动** → 换面或真实浏览器
- 细分: `cloudflare-bypass`(CF 全层: 源站/WAF/质询/限流) / `edgeone-origin-bypass`(腾讯 EO)

### 4.2 WAF 绕过
1. **首选直连源站**(绕一切 WAF)——§2 是前提
2. 编码混淆: tamper 家族(SQLi 69 式见 `sqlmap-chinese-guide`)、HPP 参数污染、Content-Type 切换(form/JSON/XML)、unicode 规范化、大小写/注释变体、垃圾字符截断、分块传输
3. 云 WAF 差异: 同 payload 阿里 403 / 腾讯放行 → 对比绕过(多 WAF 交叉测试)

### 4.3 白名单 / IP 风控 → `ip-ban-bypass`
- 诊断: 正确/错误/无凭据**全同错** = IP 级风控 → 换出口(跳板 paramiko SOCKS5,四电信实战)
- 伪头: XFF/X-Real-IP/Client-IP 仅当目标信任代理头(直连源站后可试;CDN 后有 cf-connecting-ip 覆盖难伪)
- 区分: 商户级 IP 白名单(文档写明) vs IP 拉黑(换干净出口立即恢复)

### 4.4 JWT 绕过(补齐空壳)
结构 `header.payload.signature`;攻击面按序:
1. **alg=none**(header 改 `{"alg":"none"}` + 空签名)——库校验 alg 白名单前的老洞,先试
2. **RS256→HS256 算法混淆**: 拿 RSA **公钥**当 HMAC 密钥签(公钥常从 jwks 端点/前端拿到)
3. **弱密钥爆破**: 字典跑 HMAC 密钥(hashcat 16500 / jwt_tool)
4. **kid 注入**: kid 参数进 SQLi/路径遍历/`../../dev/null`(控制签名密钥来源)
5. **jku/x5u 注入**: 指向自控 JWKS 端点,让服务器用攻击者公钥验签
6. **claims 篡改不验**: 改 role/admin/user_id/exp——直接试,很多实现不校验
7. **签名剥离/错误差异**: 部分库异常处理差异泄露信息
工具: `jwt-attacks` 脚本(jwt_toolkit.py)/ jwt_tool / python-jose 自签

### 4.5 前端认证/加密参数 → `frontend-auth-bypass`(Altcha/验证码/RSA 登录逆向)、`webapp-api-crypto-reverse`(SM4/AES/webpack chunk 逆向)

### 4.6 全站 CSRF 护栏 → `spring-security-csrf-bypass`(Spring Security 家族)

### 4.7 低代码/后台族(登录锁 JWT/防注入) → `volcore-pentest` 等

## 5. 决策收口

跑完产出:`{资产地图, 已确认源站(IP+验证命令), 可用绕过通道, 推荐下一攻击面}` →
- 编排: `cyber-ops` / 漏洞链: `full-pentest`
- 数据目标: `userdata-grab`(拖库决策树)
- 时间盒: §2 源站发现给最多时间(收益最大); 每阶段 30 分钟上限,卡死换面
- 判胜: **直连源站拿到业务响应 = 边界突破 PoV**(记录 curl --resolve 命令作证据)

## Pitfalls(血泪)
1. 本机 v2rayN TUN/代理 → 端口扫描全假 OPEN、curl 被劫持(关 TUN+代理或 Censys 权威核对)
2. `curl https://IP/` 不写 --resolve → SNI 不匹配拿不到内容(SSL EOF)
3. 源站判据 = 无 cf-ray + 服务器版本指纹匹配,不是"能连上"
4. 内容搜索词要唯一(基础设施域名/品牌串),通用词烧 Censys 5 次/天额度
5. CF Turnstile 交互质询 headless 过不了 → 换面不硬刚
6. 换新出口后保持低频,防二次风控(SSRF/恶意回调=「已记录取证」直接拉黑)

## 关联地图(本家族细分)
| 技能 | 定位 |
|---|---|
| `cloudflare-bypass` | **CF 唯一入口总纲**: 分层识别→5 条绕过路径(源站直连/伪造CF头/边缘破429/质询会话复用/判死换面) |
| `edgeone-origin-bypass` | EdgeOne/CDN 源站绕过 |
| `space-mapping-engine-recon` | Shodan/Fofa/Censys 语法+额度+登录态恢复 |
| `ip-ban-bypass` | IP 风控诊断+跳板换出口 |
| `bot-panel-spacemapping` | TG bot 管理面板测绘 |
| `jwt-attacks` | JWT 攻击工具脚本 |
| `frontend-auth-bypass` / `webapp-api-crypto-reverse` | 前端认证/加密参数 |
| `spring-security-csrf-bypass` | CSRF 护栏 |
| `browser-cdp-pentest` | CDP 驱动真实浏览器(过质询/抓渲染页) |
