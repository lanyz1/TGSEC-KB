# 批量抓取海外赌场/博彩目录（USDT 筛选） — 2026-08 实测

用户需求形态："批量扫海外博彩平台 500 个网站，要求支持 USDT 提现" → 竞对清单交付。
核心难点不在搜索，而在**目录站 JS 渲染 + Cloudflare 反爬 + 单站只展示 Top 列表**。

## 可行数据源（经代理 curl + Chrome UA 可达，2026-08 验证）

| 源 | URL 模式 | 提取点 |
|---|---|---|
| cryptoslate | `cryptoslate.com/crypto-casinos/tether/`（还有 /bitcoin/ /crypto-casinos/） | HTML 内 `href="/go/{casino-slug}"` 跳转链接，**每页 ~114 个**，服务端渲染可用 |
| cryptomaniaks | `cryptomaniaks.com/gambling/crypto-casinos/tether` | 同上 /go/ 模式 |
| casinobonuswise | `casinobonuswise.com/usdt-casinos/` | /go/ 模式 ~34 个 |
| casinosblockchain | `casinosblockchain.io/tether-casinos/` | /go/ 模式 |
| vip-grinders | `vip-grinders.com/crypto-casinos/tether/` | /go/ 模式 |
| askgamblers | `askgamblers.com/online-casinos/crypto/tether` | `href="/online-casinos/reviews/{slug}"`，每页 ~10 个 |
| coincentral / webopedia / blockonomi / tokenist / cointrust / coinpaper / playonstake | 文章型列表 | 正文链接 |
| casino.guru | `casino.guru/top-online-casinos/tether` | **仅 7-20 个**（地域限制 userCountryId），且赌场卡片 JS 渲染 |
| casinorank / cryptogambling.tv / cryptocasinos.com | 首页 | 全 JS 渲染，curl 拿不到列表 |

## 关键结论

1. **目录站普遍只展示 Top 10-50 个**，没有任何单站能列出 500 个 USDT 赌场 → 必须多站合并去重。
2. **casino.guru 的 `?page=N` 服务端忽略**（JS 分页，p1/p2 内容相同）；浏览器访问被 Cloudflare 挑战拦截，但 **curl+代理+Chrome UA 能拿到 200 服务端渲染 HTML**（只含首屏 7-20 个）。
3. casino.guru 页面含 `window.__FILTER_PRELOADED_STATE__ = {"filters":{"sp_cry":"true"}}` —— sp_cry 是 crypto 筛选参数，但服务端 URL 传参无效，需 JS 交互。
4. **HTTP 状态判活**：`503` = Cloudflare 反爬拦截但**站点存活**（bc.game/cloudbet 等知名站全 503）；`000` = 真死或超时；`301/302` = 存活跳转。验证脚本里把 503 当存活。
5. 抓取的 HTML 里混大量噪音域名（CDN/合规链接：gambleaware、gamstop、trustpilot、jsdelivr、cloudflare 等）→ 必须黑名单过滤（NOISE 列表，见 scan 脚本）。

## 提取模式（python re）

```python
# 跳转 slug（目录站最干净的数据）
re.findall(r'/go/([a-z0-9-]{3,40})', html)
# 赌场名（a 标签文本）
re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{2,50})</a>', html)
# 域名（过滤后）
re.findall(r'href="(https?://([a-z0-9][a-z0-9.-]*\.[a-z]{2,}))[^"]*"', html)
```

## 工作流

1. `curl -s -L -m 30 -x http://127.0.0.1:10808 -A "$UA" <url>` 批量抓目录页（UA 必须完整 Chrome UA）
2. 提取 slug/域名 → 多源合并去重（dict: slug → sources）
3. 黑名单过滤噪音域名 → 候选池（~230 个）
4. `ThreadPoolExecutor(8)` 并发验证 HTTP（503 记存活）→ alive 清单
5. 交付 CSV/清单（域名/名称/来源）
6. **500 个目标需 3+ 轮扩展源**：DDG-html 搜 "usdt casino list tether withdrawal" 找新目录站 → 抓 → 合并，循环补量

## 脚本与中间产物（Desktop\casino_scan\）

- scan_usdt.py / scan2_expand.py / scan3.py — 多源抓取
- extract_slugs.py / merge_all.py / final_clean.py — 合并去重清洗
- verify_domains.py — 并发存活验证
- final_domains.txt（233 候选）/ alive_casinos.txt（存活）/ clean_result.json

## 已知坑

- 搜索旋转：Bing/Baidu/Sogou 全验证码；Brave 可用 ~8 次/需 sleep 8s；DDG-html 限 3-5 次
- 赌场域名常带 `-casino` / `-io` 变体重复（stake vs stake-casino）→ 去 `-casino` 后缀后再去重
- USDT 确认：目录站声称 tether 支持 ≠ 平台真支持，交付前抽查页面含 "USDT/Tether/TRC20" 关键词（浏览器验证 503 站时顺带做）

---

# ⚠️ 用户验收修正（2026-08 同会话后半段）—— 交付质量红线

用户对"目录站抓取直接交付"明确不满：**"质量不行啊这一批"、"这里面很多都不是博彩网站，很多甚至都无法访问"**。教训：抓取 ≠ 交付，交付前必须验证 + 分层。

## 红线 1：绝不猜域名

- 把品牌名拼 `.com` 是错的最快方式。真实例子：`mybookie` 正确是 **mybookie.ag**（非 .com）、`ignition` 是 **ignitioncasino.eu**（非 ignition.com）、`bovada` 是 **bovada.lv**、`slots` 是 **slots.lv**、`stake` 用 **stake.com** 但 `stake.bet` 可能是别人。
- **只用页面里实际出现的链接**，任何"推测"的域名都标为 unverified 或直接丢弃。品牌精选清单里塞猜测域名 = 交付即被打脸。

## 红线 2：四重验证（DNS → HTTP → 特征词 → USDT）

```python
# 1. DNS 存在性: nslookup <domain> 8.8.8.8 (指定公共 DNS 避开 GFW 污染), 有真实 A 记录才继续
# 2. HTTP 访问: curl 代理抓首页; 200/301/302/403 算存活; 000=网络不通(可能被墙, 见分层)
# 3. 页面特征词: casino/slot/bet/blackjack/roulette/deposit/withdraw/bonus 命中≥2 才算博彩站
#    (单命中不算——很多非博彩页也含 "casino" 字样)
# 4. USDT 关键词: USDT|Tether|TRC-?20|ERC-?20 命中才符合"支持USDT提现"
```
验证脚本示例：`verify_strict.py`（DNS+HTTP+特征词+USDT 四合一，ThreadPoolExecutor 并发）。

## 红线 3：分层交付（诚实 > 凑数）

大陆网络下**一半以上知名站测不了**（TCP RST/000）：stake/rollbit/roobet/1xbet/betway/pinnacle 全被墙。交付必须分两层并明说：

- **Tier1 已验证**：本地实测可访问 + 确认博彩站 + USDT（本次 22 个：bitstarz.com、shuffle.com、wild.io、duckyluck.com、las-atlantis.com、slots-ninja.com、trustdice.win、queen-casino.com 等）
- **Tier2 行业公认**：DNS 能解析但被墙 → 标注"真实存在，需海外网络访问"（54 个：stake/rollbit/roobet/1xbet/betway 等）
- **明确告知限制**："500 个能打开验证的站"在纯大陆网络无法完成。不要硬凑 500 交付——用户宁要 20 个真的，不要 500 个混的

## 红线 4：参考站反推用户标准

用户给参考站（如 queen-casino.com）时，先分析它是什么：
- queen-casino.com = **QUEEN.GAME，BC.GAME 白标站**（页面正文含 BC.GAME 服务条款文案 + 同一平台引擎：Casino/Pachinko/Slots/Live/Sports 全产品线 + provably fair）
- "找这种类似的" = **成熟品牌加密赌场平台**（Stake/Rollbit/Roobet/BC.GAME 级别），**不是目录站里的杂域名**
- 从参考站反推筛选标准（全产品线/自研游戏/加密原生/provably fair），再回到候选池筛 Tier

## 红线 5：验证期陷阱

- **域名劫持**：metaspins.com / moonbet.io 显示印尼盗版站（title "BISAJP | Situs Slot777..."）——与预期品牌不符即剔除，验证时看 title 一致性
- **403 vs 503 语义**：403 常是 Cloudflare 反爬（站活着），503 对 curl 是反爬但对浏览器可能是真 503；同码不同因，别一刀切
- 浏览器被 Cloudflare 拦但 **curl+代理+Chrome UA 能过** 的情况真实存在（casino.guru 实测），两者都试再下结论
- DNS 能解析出 IP ≠ 能访问（被墙的站 DNS 正常、TCP 被 RST）——DNS 只证明存在，HTTP 才证明可达
