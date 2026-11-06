# cloudflare-bypass — 全文续篇

> 主卡保留前 14 节；本文件从第 15 节起。原文件：`/root/.hermes/skills/security/cloudflare-bypass/SKILL.md`

## 1. 分层识别(30 秒,决定打哪条路径)

```bash
nslookup target.com
curl -sI https://target.com/ | grep -iE "server|cf-ray|cf-cache-status|set-cookie|retry-after"
curl -s -o /dev/null -w "%{http_code}\n" https://target.com/api/任意路径   # 区分路径级 WAF
```

| # | CF 防护层 | 现场特征 | 首选绕过路径 |
|---|---|---|---|
| L1 | 边缘/网络层 | Anycast IP + `Server: cloudflare` + CF-RAY | **A 源站发现→直连**(没有"绕过 CF 边缘"这回事) |
| L2 | WAF 规则(路径/载荷级) | `/api/*` 全 403 而静态资源 200;payload 触发 403 | **A** 直连源站;无源站时 payload 变形 + 静态资源通道 |
| L3 | Bot 管理 / JS 质询 | `Just a moment...`、`cf_clearance` cookie、1010 | **D 会话/指纹绕过** |
| L4 | 限流 Rate Limit | 429 / `{"detail":"Rate limit exceeded"}` / `Retry-After` | **C 边缘绕过**(duplicate Content-Type)或 A 直连 |
| L5 | TLS/JA3 指纹 | curl/Node 被拦,浏览器能过(EO 567 同型) | **D**(真实浏览器)或 curl-impersonate/curl_cffi |
| L6 | 无源站形态 | cloudflared Tunnel / Workers / Pages | **A 无解** → 打隧道服务本身或应用层(§2 E) |

**输出**: `{CF 确认?, 哪几层生效, 源站线索(nginx 版本从 405/错误页取), 选定路径}`

## 2. 决策树 — 五条路径

```
挂 CF
├─ A. 找源站 IP → 直连(绕过全部六层,成功率最高,先做)
│    失败? → 判死清单见 references/origin-ip-discovery-matrix.md
│         └─ 是 cloudflared Tunnel/Workers/Pages → 没有源站,转 E
├─ B. 找到源站但直连 403 → 伪造 CF 头(源站只查头存在不验真)
├─ C. 拿不到源站,只被限流/规则挡 → 边缘绕过(重复 Content-Type / payload 变形 / 静态资源通道)
├─ D. 质询挡会话 → 复用已信任浏览器会话(CDP),或 curl_cffi JA3 模拟
└─ E. 全打不通 → 收手:把边界当既成事实,转应用层逻辑漏洞/数据面
```

### A. 源站 IP 发现 → 直连 ⭐(主力)

```bash
# 1) 单发 Censys 内容搜索(免登录 5 次/天, 用 CDP 渲染读 innerText)
#    https://search.censys.io/search?resource=hosts&q=<基础设施域名/品牌唯一串>
# 2) 历史 DNS(CDN 接入前的 A 记录) / 证书 SAN / 邮件头 / 未挂 CF 子域 / APK 硬编码
# 3) 验证(必须 --resolve 保 SNI, 否则 SSL EOF)
curl -sk -D - --resolve "target.com:443:候选IP" https://target.com/ | head
```
**判据**: 页面 title 匹配 + **无 cf-ray** + 服务器指纹(nginx 版本)与 CF 后面一致 = 源站。
全量方法矩阵 + 反误判 + 判死条件: `references/origin-ip-discovery-matrix.md`
泛 CDN 深度层(50 法/JA3-JA4/贝叶斯评分/6 个脚本): 兄弟技 `cdn-origin-tracing-v51`

### B. 源站头校验绕过(伪造 CF 头)

源站 nginx/后端**只检查头存在与否,不验证真实性** → 403 变 200:
```python
headers = {"Host": "<域名>", "CF-Connecting-IP": "104.21.85.110",
           "X-Forwarded-For": "104.21.85.110", "X-Real-IP": "104.21.85.110",
           "Origin": "https://<域名>", "Referer": "https://<域名>/",
           "Content-Type": "application/json"}
```
单加 `CF-Connecting-IP` 不够,三个 IP 头要一起带。详见 `references/forged-cf-headers.md`(附多租户 vhost 品牌泄露)

### C. 无源站时的边缘绕过

**CF WAF 限流用 `Content-Type` 精确匹配规则时** → 发两个 Content-Type 头:
```bash
curl -s -X POST "https://target/api/auth/register" \
  -H "Content-Type: application/json" -H "Content-Type: text/plain" \
  -d '{"name":"T","email":"<EMAIL-REDACTED>","password":"Pass1234!"}'
# 429 → 200/422(到达后端) 即成功; 限速窗口仍在, 只适合单发关键请求
```
变体矩阵 + FastAPI `/openapi.json` 快打: `references/cf-edge-bypass-rate-limit.md`
CF **路径级** WAF(过质询也没用,前端自己 403)的无效清单/有效线索(静态资源是唯一稳定通道): `references/cf-waf-path-block-playbook.md`

### D. 质询 / 指纹绕过

- **最快**: 复用一个**已访问过同族站**的真实浏览器 CDP 会话(指纹已被 CF 信任),页面内 `fetch` 全通;外部 curl 依旧 1010/567
- 有头 Chrome + `--remote-debugging-port` + `--remote-allow-origins=*`;headless 必被检测(跳 about:blank)
- `cf_clearance` 与 IP/UA 绑定,换出口即作废 → 会话复用要同出口
- 细节: `references/challenge-session-reuse.md` + 兄弟技 `browser-cdp-pentest`

### E. 判死与换面

教科书级 CF 保护(全域名含基础设施域全挂 CF / 无 MX-SPF 邮件泄露 / 域名新注册无历史 DNS / 证书仅通配符 / 无未保护子域 / 无 SSRF 点)= **纯外部侦察下绕不过**,一个缝隙都没有就是没有。
收手条件与替代打法: `references/origin-ip-discovery-matrix.md` §判死 + `references/cf-waf-path-block-playbook.md` §收尾

## 3. 验证(怎么算赢)

- ✅ `curl --resolve` 返回目标完整页面/业务 JSON,且**无 cf-ray** = 源站确认(记录命令作 PoV)
- ✅ 直连返回体比经 CF 更全(实测 92B → 2207B)= CF 有裁剪/脱敏,后续枚举一律改走源站
- ✅ 从 429 → 200/422 = 边缘限流绕过生效
- ✅ 直连从 403 → 200 = 源站头校验绕过生效
- ⚠️ 经 CF 看起来"没料" ≠ 接口没料(`references/origin-direct-access-discipline.md`)
- ⚠️ 代码审计/静态分析确认的洞,若实际利用仍被 WAF 拦,报告里必须标注"未实际利用"

## 4. Pitfalls(血泪)

1. **本机 TUN/系统代理假象**: sing-box/v2rayN TUN 开启时任意端口 connect 都 OPEN(随机端口 12345 也 OPEN),Python `connect_ex` 全假。**curl 的真实 HTTP 响应才可信**;测端口前先 `Disable-NetAdapter singbox_tun` + `ProxyEnable=0`,或用 Censys 单 IP 页做权威核对。
2. **`curl https://IP/` 不写 `--resolve`** → SNI 不匹配,SSL EOF/空响应,误判"源站不通"。
3. **AWS IP ≠ 非 CF**: CF 边缘/回源也跑在 AWS(54.x/15.x),判据是**无 cf-ray + 指纹匹配**,不是 IP 归属。
4. **证书签发方骗局**: 源域用 Google Trust Services / Let's Encrypt 证书**不代表没挂 CF** —— 判 CF 只看解析 IP 段。
5. **Host 不匹配静默落 default vhost**: 源站一 IP 挂几十个 vhost,Host 写错不报错,而是返回别的站页面 → 极易误判"源站不在这台机/路由不存在"。先用已知存在的 Host 取基线再对比。
6. 内容搜索词要**唯一**(基础设施域名/品牌串);通用词烧掉 Censys 5 次/天额度。
7. **CDN 段 IP 过滤后**才能报"疑似源站";报源站必须带正确 `Host:`,HTTPS 优先。
8. 找到源站后保持**原有频率纪律**(直连只是换了入口,不是新目标);要论证 WAF 有效性就两边各取一次响应做对照。

## 5. 家族地图

| 技能 | 定位 |
|---|---|
| `cdn-origin-tracing-v51` | 泛 CDN/WAF 溯源深度层:50 法矩阵 + JA3/JA4 指纹 + 贝叶斯评分 + 6 脚本 |
| `site-recon-bypass` | 测绘边界绕过总纲(0-5 阶段流水线) |
| `space-mapping-engine-recon` | Shodan/FOFA/Censys/Quake 语法 + 额度 + 登录态恢复 |
| `browser-cdp-pentest` | CDP 驱动真实浏览器(过质询/反自动化/会话收割) |
| `edgeone-origin-bypass` | 腾讯 EdgeOne 同型(含 42666 TLS 口径实战) |
| `ip-ban-bypass` | IP 风控诊断 + 跳板换出口 |
| `white-label-pentest` / `gambling-platform-risk-control` | 白标博彩目标上的 CF 实战结论(含"绕不过"矩阵) |

## References

- `references/origin-ip-discovery-matrix.md` — 13 法全表 + 硬核目标实战结果 + CF 段速查 + 判死条件
- `references/forged-cf-headers.md` — 伪造 CF 头绕源头校验 + 多租户 vhost 泄露
- `references/cf-edge-bypass-rate-limit.md` — 重复 Content-Type 破 CF 429 + 变体矩阵 + FastAPI/OpenAPI 快打
- `references/cf-waf-path-block-playbook.md` — CF 路径级 WAF:无效方法清单 + 有效线索 + 静态资源通道
- `references/challenge-session-reuse.md` — cf_clearance / EO 567 质询的会话复用姿势
- `references/origin-direct-access-discipline.md` — 直连时机/裁剪判据/default vhost 陷阱/证据对照
- `references/m9600-cf-bypass-case.md` — m9600(MM99)完整实战:常规侦察全败 → Censys 破局 → 51 源站 IP

