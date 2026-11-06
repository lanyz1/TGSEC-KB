# Cloudflare 源站发现矩阵(硬核白标博彩目标)

> ⚠️ 2026-09: 本文件内容已并入家族总技 **`cloudflare-bypass`** → `references/origin-ip-discovery-matrix.md`。此处保留为原始实战记录。


针对**全站 Cloudflare + 内网隔离**的硬核白标博彩/包网目标,找源站 IP 的完整技术清单。m9600.com(MM99)实战全部尝试的结果记录。**结论先行:教科书级完整 CF 保护在纯外部侦察下无法绕过。**

## 为什么这类目标难绕

```
1. 全部域名(含基础设施: CDN/WS/API/客服)都挂 CF — 41+ 域名无一个直连
2. 无邮件服务器(无 MX/SPF → 没有"SPF 记录指向源站 IP"的经典泄露路径)
3. 域名新注册(2025-2026),从未"裸奔",历史 DNS 无记录
4. 证书只有 *.domain 通配符(无 IP SAN 证书)
5. 无未保护子域(爆破全 CF)
6. 无 SSRF 点(客服文件上传/REST URL 抓取/游戏 iframe 全无)
```

CF 绕过成功的站点通常至少有一个"缝隙"(邮件/历史/未保护子域)。一个缝隙都没有 = 绕不过。

## 完整技术矩阵(按成功率排序)

| # | 技术 | 工具/命令 | m9600 结果 |
|---|------|----------|-----------|
| 1 | 全域名批量解析找非 CF IP | python socket.getaddrinfo,CF 段过滤 | ❌ 41 域名全 CF(104.x/172.67.x/188.114.x) |
| 2 | 子域爆破(大字典 200+ 词) | python 并发 getaddrinfo | ❌ 全 CF(ws*/down* 前缀) |
| 3 | 证书 SAN/certspotter/crt.sh | crt.sh JSON, certspotter API | ❌ 只有 *.spiritapis.com 通配符 |
| 4 | 历史 DNS(ViewDNS/RapidDNS/SecurityTrails) | 网页接口 | ❌ 无数据(被墙/无记录) |
| 5 | DNS 全记录(A/AAAA/MX/TXT/NS/SOA) | dnspython 逐类型 | ❌ 全 CF NS,无 MX/TXT |
| 6 | DNS 区域传输(AXFR) | nslookup -type=AXFR @CF-NS | ❌ CF 拒绝 |
| 7 | SPF/DMARC/DKIM | nslookup TXT | ❌ 无(无邮件服务器) |
| 8 | whois 注册信息反查 | whois 原始协议 | ⚠️ 隐私保护;仅得注册商(Dominet HK/Dynadot)+ 创建日期(新域名) |
| 9 | Wayback Machine 历史快照 | web.archive.org CDX API | ❌ 只有 SPA 快照,无源站 IP(且限流 429) |
| 10 | FOFA/Shodan 候选 IP | fofa.info result 页 | ❌ 候选 IP 全部无效(混淆/第三方服务) |
| 11 | nginx 指纹/错误页泄露 | curl 404/405/TRACE | ⚠️ 得到 nginx/1.20.1 与 1.26.3 版本,无 IP |
| 12 | CNAME 链/多 DNS 源差异 | dnspython 多 resolver | ❌ 无 CNAME 差异 |
| 13 | 第三方资产(推广/客服/分析域名) | 从 JS 提取全部域名批量查 IP | ⚠️ 找到非 CF 域名(linkedbro/macan-native 等),但都是第三方 SaaS 非源站 |

## 关键判别技巧

- **证书签发方骗局**:wsm9.spiritapis.com 证书是 Google Trust Services(不是 CF 自己签的) — 这是 CF 配置了外部证书,不代表该域名没挂 CF。判断是否 CF 看解析 IP 段,不看证书签发方。
- **SPA fallback vs 真接口**:所有路径返回 200 HTML 且 size 相近 = SPA fallback;Content-Type: application/json 或 body 以 {/[ 开头 = 真 API;nginx 405 + nginx/x.y.z = 路径有路由但方法受限。
- **CF 段速查**:104.16.0.0/12、172.64.0.0/13、172.65-71.*、188.114.96-97.*、173.245.*、103.21-22.*、141.101.*、108.162.*、190.93.*、198.41.*、162.158.*、131.0.72.*、131.0.100.*。
- **CF 可用外部证书**:Google Trust Services / Let's Encrypt / 用户上传证书都常见,不能作为"非 CF"证据。

## "无 shell"结论逻辑(何时收手)

硬核白标目标拿不到 shell 不是技术不足,是**公网可达面没有 RCE 点**:

```
WS 游戏协议(600+ SUB)= 纯业务查询,无文件/命令功能 → 无 RCE
REST API = 7 个静态接口,参数被忽略 → 无注入
客服客户 API = 只能查自己会话(cid 校验),服务端 /service 401 → 无横向
源站 = CF 完全隐藏 → 无法直接打服务器
管理端 = 服务商内网 → 无入口
```

结论: 纯外部渗透,当"排行榜/撞库/客服客户 API"都已验证且 CF 无缝隙时,诚实收尾,把精力转已确认的数据路径,不硬刚。

## 相关

- 排行榜/撞库/客服的具体攻破配方见本 skill 其他 references(m9600-* 系列)。
