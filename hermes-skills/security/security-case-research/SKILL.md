---
name: security-case-research
description: "挖掘全网渗透案例时使用: writeup数据库 + Google News RSS + 反爬绕过方法论。"
---

# 公开安全案例研究(Writeup 挖掘 + 事件验证)

当用户要求「查找全球 XX 行业渗透/爆破/逆向实操案例并整理思路」时,主流搜索引擎常被反爬挡住,需要专用渠道。本 skill 提供可复现的案例挖掘工作流与已验证的可靠数据源(2026-08 实战验证,博彩行业案例研究场景)。

## When to Use

- 用户要「全网找 XX 行业(博彩/金融/电商等)渗透/破解实操案例,整理成思路」
- 需要验证公开安全事件(撞库事件、被盗金额、攻击者判刑、归因)
- 需要从 writeup 数据库挖掘某目标类型的漏洞模式
- 目标行业站点反爬严重,搜索引擎查询全部被限流/拦截

## 可靠数据源(按优先级)

1. **Google News RSS** ⭐(最可靠,零反爬):
   ```
   https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en
   ```
   Python `urllib` + `xml.etree.ElementTree` 解析 title/link/pubDate。验证公开事件用它准没错,还能拿到**真实文章 URL**(不用猜新闻站 URL)。

2. **Pentester Land writeups 全量数据库**:
   ```
   https://pentester.land/writeups.json
   ```
   6421 条 writeup 完整 JSON(标题/链接/Programs/Bugs/Bounty/日期),一次下载离线过滤。注意结构是 `{"data": [...]}` 数组;标题可能在 `Links[0].Title` 里,过滤时把整条 json `dumps().lower()` 后匹配关键词。

3. **Medium writeup**: 浏览器 navigate 会被 Cloudflare 挡("Attention Required"),但 **curl + 浏览器 UA 直接可抓全文**:
   ```bash
   curl -sL "<medium-url>" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36" \
     | python -c "提取 <article> 正文并去标签"
   ```

4. **WIRED 等深度报道站**: Python urllib + 浏览器 UA 可抓全文,`<article>` 或全文去标签提取即可。

5. **Wikipedia**: 大事件的背景/关键事实可快速确认(但安全事件的细节以新闻+官方报告为准)。

## 会被反爬的渠道(别浪费时间)

- **DDG html/lite**: 连续 3-4 个查询后返回空结果(限流);若必须用,查询间 sleep 5-10s 且用 curl 而非函数内 python
- **Bing**: 返回 JS 渲染页,`<h2><a>` 正则解析不到(即使 UA 正常)
- **Startpage / Ecosia / Yandex**: 空结果或验证页
- **Medium 浏览器访问**: Cloudflare "Attention Required";浏览器被挡后换 curl 直抓
- 有头浏览器 navigate 到强反爬站: 换 curl/Python urllib 直抓

## 中文内容检索(2026-08 实测,国内环境)

- **360 搜索(so.com)⭐ 中文内容首选**: `curl -A "Mozilla/5.0..." "https://www.so.com/s?q=<urlencoded>"` → python 正则 `<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>` 提取标题+链接;中文关键词命中质量远高于其他引擎(Tether 冻结案例、公安 USDT 冻结等都能搜到)
- **so.com 的 /link?m= 跳转链接直接 404 打不开**——标题/摘要本身够用,不必追原文;追原文换 Google News RSS 或 r.jina.ai
- **Bing 中文查询(cn.bing.com / mkt=zh-CN)被污染**: 返回无关英文新闻(如梅西新闻),别浪费时间
- **Google 直连/走代理**: 返回 JS 重定向页(enablejs),`<h3>` 解析不到;需真实浏览器渲染才可用
- **搜狗/百度**: antispider 验证码拦截
- **知乎 zhuanlan**: 403 反爬,r.jina.ai 也 403;靠搜索引擎标题摘要即可
- **PANews 等 JS 渲染站**: 文章 ID 难猜(猜 URL 全 404),正文拿不到;靠搜索结果标题+摘要取证
- r.jina.ai 对 404/403 站返回错误页(先看输出头部的 Warning 行再判断)

## 空间测绘引擎查询(Shodan/Fofa/Censys 语法 + 登录态)

**铁律: 针对性搜索,禁止全网泛扫(用户纠正 2026-08-09)**
- 必须用目标专属特征词: bot 用户名、客服账号、品牌名、已发现域名、i_code 推广码、已知 IP 段
- 例: 周氏PG 特征 = zhoushipgbot / aipg / kefuzhou / kefupipi / wwgpr.com / zhou-shi.com → 反查 hostname:wwgpr.com / net:186.240.59.0/24
- 泛扫 `http.title:"bot" + telegram` 命中几千个无关 bot 项目,浪费大量时间且大多不是目标
- 泛扫结果若命中,先验证归属(标题含目标品牌/域名? 服务器同 C 段?)确认是目标资产再深入
- 用户明确说了「针对性扫专属后台」就不要自作主张全网扫,先猜目标特征词

**引擎选择**: Fofa(中文特征最强, title="Bot" && body="telegram")、Shodan(非标端口/服务指纹强, http.title:"bot" http.html:"telegram")、Censys(用户已有登录态)。用户没 key 时**教注册**(Fofa: fofa.info 免费注册 → 个人中心 → API 信息 → email+key; Shodan: account.shodan.io/register → Account → API Key),不要只问「你有没有 key」。

**Shodan 免费账号硬限制(2026-08 实测)**:
- API key 可能是 oss 计划 → query_credits=0,搜索 API 直接不可用(即使 key 有效,/api-info 返回 usage_limits.query_credits=0)
- 数据中心 IP 调 API 会被 Cloudflare 拦(403 "Just a moment...")
- 网页版: 免费账号只能看 2 页(约 15 条),更多结果被会员墙(Purchase a Shodan membership...),会员 $69/月起
- 别让用户买会员: 精准特征词命中数 < 15 条时免费 2 页足够;真要全量提取就靠已登录浏览器窗口接管(见 references/browser-session-takeover.md)

**Censys 新平台语法(2026-08 实测,legacy 已失效)**:
```
# legacy(已失效, 返回 Invalid Query + Query Converter 提示):
services.http.response.body:"bot_token"        ← 错
# 新平台正确语法:
host.services.endpoints.http.body:"bot_token"
host.services.endpoints.http.html_title:"bot" and host.services.endpoints.http.html_title:"panel"
web.endpoints.http.body:"bot_token"            # Web Properties 资产
(host.services.endpoints.http.html_title:"bot" and ...) or (web.endpoints.http.html_title:"bot" and ...)
```
注意: 免费版 5 次搜索/天未登录限制;中文/拼音关键词误命中极高(如搜 "zhoushi" 命中公司名/路名),中文特征优先 Fofa。

**Censys 登录态恢复(Chrome profile cookies)**:
```
用户已登录过的 Censys profile(如 chrome_censys)的 Cookies 库里存有
auth_v1 / search.censys.io.session.id / cf_clearance / csrf_v2, 长期有效(expires 到 2090)。
启动 CDP Chrome 复用:
  chrome.exe --remote-debugging-port=9227 --user-data-dir="C:\Users\Administrator\chrome_censys"
然后 Network.getAllCookies 或直接导航搜索页即可;浏览器在跑时 DB 被锁,
不要直接 sqlite 复制(WinError 32), 走 CDP 拿 cookies 最稳。
```

**搜索结果提取**: Censys 搜索页是 SPA,结果需 CDP 滚动(`window.scrollTo(0, document.body.scrollHeight)`)+ `document.body.innerText` 正则 `\b(?:\d{1,3}\.){3}\d{1,3}\b` 提 IP;按 IP 批量探测(80/443/8080 + title + login 特征)筛选真面板。

## 工作流

1. **关键词分层**: 行业词(博彩: gambling/casino/sportsbook/betting/slot/poker/lottery)→ 攻击类型词(IDOR/credential stuffing/logic flaw/payment callback/replay/RNG/account takeover)→ 平台词(RTG/Gambit/SignalR/wasm/Next.js)
2. **writeup 库离线挖掘**: 下载 pentester.land/writeups.json → 关键词过滤 → 命中条目逐个 curl 抓全文
3. **公开事件验证**: Google News RSS 搜「事件名 + 年份」→ 读标题/pubDate/来源 → 从标题提取权威来源(BleepingComputer/SecurityWeek/TRM Labs/FBI)→ 抓正文确认金额/账户数/判刑/归因细节
4. **技术细节提取**: 抓全文后找方法关键词(PRNG/seed/statusUrl/IPN/signature/bruteforce/relay)→ 提取攻击步骤与参数 → 每条案例保留来源 URL
5. **输出**: 按攻击面整理成思路文档(资金链 > 账号体系 > 用户数据 > 游戏引擎 > 基础设施),每条案例附来源链接;再叠加本机实战技能库(白标赌场/wasm 协议等)形成「公开案例 + 本地打法」双轨文档

## 输出格式偏好(用户明确要求)

用户会明确说「整理一下刚刚在网上搜索的,不是我本地的」——**网络公开案例与本地实战经验必须分开成两份独立文档**,不要混在一份里:

- `公开案例集-网络搜集版.md` — 只收录网络公开渠道案例,每条带来源链接,零本地实战内容
- `实战案例集.md` / 技能库 — 只放本机授权实战沉淀
- 第三份「对照」文档可以两者都引用,但**明确标注每条来自网络还是本地**

这样用户在复习时能区分「公开可引用的方法论」和「本机实操验证过的结论」,不会把爆料传闻当成本地实证。

## 关键词分层(跨行业)

行业词 → 攻击类型词 → 平台/技术词。已验证行业示例:
- 博彩: gambling/casino/sportsbook/betting/slot/poker/lottery → IDOR/credential stuffing/logic flaw/payment callback/replay/RNG/account takeover → RTG/Gambit/SignalR/wasm/Next.js
- 抢shell: RCE/webshell/file upload/command injection/deserialization/unauthenticated rce → Log4j/Struts2/WebLogic/ThinkPHP/ShowDoc/SharePoint → PHP/JVM/Node/Spring
- 钱包/加密: mnemonic/PRNG/seed → java.util.Random/SecureRandom/bip39 → imToken/TrustWallet/token-core

## Pitfalls

- **新闻 URL 别猜**: TechCrunch/BleepingComputer 的 URL 猜不对全是 404;用 Google News RSS 拿真实链接
- **事件双源验证**: 安全事件至少两个独立来源(如 BleepingComputer + 官方/研究机构报告)再写进报告;官方司法/监管来源(DOJ/FBI 新闻稿)是最强证据
- **RSS 解码**: 用 `.decode("utf-8", errors="replace")` 防个别条目特殊字符崩解析
- **付费墙/强反爬站点别硬刚**: 拿 Google News RSS 的标题+来源即可,不必拿到全文
- **浏览器被 CF 挡 ≠ 内容拿不到**: 先试 curl/Python urllib + 浏览器 UA,再考虑镜像
- **DDG 限流无输出时检查函数写法**: bash 函数内嵌 python heredoc 引号转义易出问题;直接用 execute_code 的 urllib 或独立 python 文件更稳

## 验证漏洞/安全爆料的技术取证工作流

当用户给一条「XX 软件/钱包/平台存在致命设计缺陷」的爆料(群聊/新闻/截图)要求验证时,不要只信爆料描述,走五步:

1. **数学验证原理** — 写 POC 复现核心数学声明(如 java.util.Random 48 位 LCG 从 2 个输出反推种子 = O(2^16),见 `scripts/java_random_break.py`)
2. **源码取证** — GitHub org 搜索 → 找官方核心 repo(imToken=consenlabs/token-core-monorepo)→ 递归 trees API 找 mnemonic/bip39/hdwallet/rand 文件 → 追依赖链到 RNG 实现
3. **核对规范细节** — 爆料者常记错基础规范(BIP39 12 词 = 128 熵 + **4** 校验和,不是 16);细节错 = 专业性存疑
4. **公开证据检索** — Google News RSS 搜「目标+漏洞关键词」→ 零报道/CVE/公告 = 高度可疑
5. **结论分级** — 原理成立 ≠ 目标中招;「被搞走几百万u」类传闻更可能是钓鱼/假钱包,非算法破解

imToken 案例实证: 爆料称其用 java.util.Random 生成助记词,实际官方 Rust 核心 `tcx-primitive/src/rand.rs` → `tiny-bip39 1.0.0` → `rand::thread_rng()`(ChaCha12 CSPRNG,128 位真熵),指控被源码证伪。完整配方: `references/prng-claim-verification.md`。

## 参考文件

- `references/gambling-case-study-sources.md` — 博彩行业案例研究:已验证数据源清单、命中案例清单(IPN 重放 £25k / DraftKings 撞库 30 万账户 / 俄罗斯老虎机 PRNG 逆向 / Stake.com $41M 等)与每案例抓取方式、验证到的权威来源链接
- `references/prng-claim-verification.md` — PRNG/助记词漏洞爆料验证工作流(imToken 案例):五步法、源码取证链、BIP39 规范核对、LCG 反推技术要点
- `references/browser-session-takeover.md` — 已登录浏览器窗口接管:无 CDP 时用 UI Automation + 截图 OCR + SendKeys 翻页驱动用户已登录的 Chrome,并提取 localStorage token(Shodan 批量抓取/分享页 token 提取)
- `scripts/java_random_break.py` — java.util.Random 48 位 LCG 可预测性 POC(种子反推 O(2^16),可复现)
