---
name: intel-ingest
description: "情报摄入——定时抓全网新CVE/新writeup/目标品类动态,消化成打法增量合并进技能库。触发: intel-ingest, 情报摄入, 技能自动长大, 拉情报, 今日情报, 吸收新打法。"
---

# Intel Ingest — 情报摄入(进化闭环 B:从全网学习)

**定位**:技能库的"外部喂食端"。每日定时抓候选 → AI 消化 → 类级合并进家族技能 → 推增量摘要给用户。没有它,技能库只能从实战长;有了它,技能库每周自动长大(对应 NCSC 结论:AI 让低技能者获得最大能力增益——机制化就是本技能)。

**配套组件**:cyber-ops(实战端,任务结束调 ops-review 回写)→ intel-ingest 补外部情报。

## 数据流

```
[cron 每日 09:00] intel_ingest.py(抓候选: NVD CVE + 国外 RSS + 国内安全媒体)
        ↓ stdout 注入 agent prompt
[agent] 筛选高相关 → web_search/web_extract 深挖确认
        ↓ 类级拓展
[agent] patch 家族技能(Pitfalls/新路径段)+ 输出增量摘要
```

## 抓取脚本

`profiles/123/scripts/intel_ingest.py`(cron 挂载用,技能内同款脚本在 scripts/ 下可手动跑):

```bash
# 手动拉取候选(最近 7 天)
python "tools/ops/intel_ingest.py"
python "tools/ops/intel_ingest.py" --days 3
python "tools/ops/intel_ingest.py" --source nvd   # 只拉单源
```

网络拓扑(已实测 2026-09):
- NVD API(services.nvd.nist.gov)→ **直连**可用
- BleepingComputer / TheHackerNews / FreeBuf / Exploit-DB → **必须走** `socks5h://127.0.0.1:10808`(v2rayN;直连被 CF 1005 拦)

## 国内直连源: 77169(华盟/安界网) — 2026-10-19 实测

- RSS: `https://www.77169.net/feed` → HTTP 200，**直连可用，无需代理**
- 标签源: `https://www.77169.net/html/tag/0day/feed` 同理 200
- 批量: WP REST API `https://www.77169.net/wp-json/wp/v2/posts?per_page=100&page=1..3&_fields=id,date,link,title,content` — 未鉴权直通，一次 100 篇
- 定位: **编译报道型**（CVE 中文速报 + 一手 PoC 仓库索引），不是原创深挖；编译对象含 abraxas/Dinosn/beaksec/腾讯朱雀/Zer0SumGam3
- 筛法: 标题剔除新闻/融资/政策 → 正文抽 `github.com` 链接 + 代码块数 → 代码块 <3 且无 PoC 链接的直接丢
- 体量: 本次 300 篇（2026-08~10）中约 100 篇 grade≥6，8 个抽检 CVE 全部 NVD 可查
- 已提炼: `1day-nuclei-kit/references/77169-intel-2026q3.md`（A级未认证 RCE/B级 LPE/C级边界/D级移动端/E级手法/F级工具）
- 原文归档: `/root/intel/77169_2026q3/`（bodies.json + INDEX.md）

## PoC 聚合索引 (2026-10-19 实测直连 200)

- `https://github.com/nomi-sec/PoC-in-GitHub` — 按 CVE 列的仓库聚合。README ~6.9MB，`## 2026` 段约 1.07 万条，**按 CVE 编号升序而非日期**；取增量：`git clone --filter=blob:none --depth=50` 后 `git log --since=<date> --oneline` 看每日自动 commit，或解析条目里的 `<code>date</code>` 字段排序。实测 2026-10-17 为当时最新。
- `https://github.com/trickest/cve` — 每日更新 CVE→PoC 映射，仓库 ~910MB（不要整仓 clone）。按年目录：`2026/CVE-2026-xxxxx.md`，单文件即链接合集；按编号直取 `https://raw.githubusercontent.com/trickest/cve/main/2026/<CVE>.md`。
- 两者都只是**链接聚合、不含利用代码**：用来发现新 PoC 链接，细节回原仓库核 `created_at`。
- `https://www.yazoul.net/advisory/poc/` — 顾问式 PoC 列表
- `https://sploitus.com/` — 按 CVE 搜 exploit/PoC（部分条目需登录）
- GitHub 搜索 API: `https://api.github.com/search/repositories?q=<CVE>`（无 token 60次/小时）
- 核验纪律: NVD published + GitHub `created_at`/`pushed_at` 双核，X 帖时间不作日期证据；错链先 API 复核再入库

## X 源评级 (2026-10 实测)

- **@abraxas_null — 高价值，每日跟。** 原始 0day 研究，按批公开 PoC 仓库（2026-10-11~18 一周 152 个/26 产品族，pfSense 53、OpenMeetings 12、Spark 9）；推文本身就是清单，抓 2 页足够。吸收落点：`1day-nuclei-kit/references/abraxas-0day-index-2026-10.md` + 对应产品卡。
- **@theXSSRat — 低价值，不必单列。** 约 90% 是课程/CTF/coaching 推广；技术点零星（如 Clojure `application/transit+json` 绕 JSON 过滤器、curl `--request-target` CRLF）。扫到具体技巧再收，不整号采集。

## X/Twitter 抓取 (nitter 流水线, 2026-10-16 实测)

X 无 API key 时的公开抓取路径 = 公共 nitter 实例:
- nitter.net 已死;实例健康表: https://status.d420.de/
- 活实例(2026-10 实测): **nitter.meowing.monster**(单号可翻 ≥25 页≈500推,首选) / nitter.tiekoetter.com(~7-8页后限速)
- 两者均有 **Anubis PoW 墙**: sha256(randomData+nonce) 前 difficulty/2 字节为 0 即解 → 已封装进脚本自动过墙

```bash
NITTER_OUT=/root/intel/x python3 scripts/nitter_agent2.py <handle> <pages> [instance]
# 例: NITTER_OUT=/root/intel/x python3 scripts/nitter_agent2.py n0aziXss 25 nitter.meowing.monster
```
输出: `<handle>@<inst>_pN.html` + `<handle>_tweets.txt`(### date / 链接 / 正文)

**Pitfalls(血泪)**:
- 分页 cursor 是**相对路径**(`?cursor=...`),必须拼在 `/<handle>` 后;拼到站根会静默变成 about 页
- 判断"时间线真加载"用 `body.count('timeline-item') >= 2`——限速**空壳页**(10-12KB,框架在时间线空)恰好含 1 处 `timeline-item` 字符串会骗过朴素检查
- 限速表现三种: 空壳页 / "rate limited" / "No items found";脚本内建 45~125s 退避重试
- 大号推文数远超 nitter 可翻深度(8.8K 推账号 ≈ 拿到最近 ~500 推),情报审读够用

## 消化规则(agent 执行时)

1. **筛选标准**(与用户关注域相关才算高价值):
   - 卡密商城/发卡网/EMSOP/ECShop/异次元(ZCard 系)
   - 白标赌场/博彩平台/包网(RTG/Gambit/TCG)
   - TG bot/小程序/支付钱包
   - 停车/门禁/智慧平台(dnake 系)
   - Windows 软件破解/卡密验证/网络验证/易语言系
   - 通用:新 CVE + 已公开 exploit / 大规模自动化可利用 / 供应链事件
2. **深挖**:候选条目用 web_search/web_extract 补齐利用细节(影响版本/复现条件/公开 PoC 链接),确认"可操作"才吸收
3. **类级合并**:增量 patch 进**现有家族技能**(新路径段或 Pitfalls),绝不新建窄技能;归属模糊时用 cyber-ops 的 target_triage.py 找语义最近者
4. **输出增量摘要**(中文):每条 = 情报标题 + 打法要点 1-2 句 + 来源链接。无实质增量 → 一两句话说明今日无高价值情报(静默推送)

## Pitfalls

- 源可能临时失效/改版:单源失败不致命,脚本已 try/except;持续失败的源在脚本 SOURCES 里注释掉
- RSS 标题党多:以"是否给打法增量"为准,不给就略过,不凑数
- 吸收的是**知识**,不针对任何真实第三方目标行动(用户授权目标除外)
- 代理规则别搞混:NVD 直连、其余走 socks5h 10808;新增源先 curl 实测再固化


---

## 外部库增量（2026-10-11 分享包）

## 配套本地资料包(2026-09 建)

`D:\CVE研究\` — 离线优先的 CVE 研判台, 与本技能分工:
- 本技能 = **上游抓候选** → 消化进家族技能
- `D:\CVE研究\tools\cve_hunt.py` = **单洞研判**(KEV 命中/EPSS/CVSS/影响版本/PoC/本地 nuclei 模板), KEV 全量 1716 条 + EPSS 全量 37.6 万条已落盘, **断网可用**
- `fetch_cve.py` = 用 cveawg 批量拉官方详情 → `数据/cve_details/`
- 打击执行仍归 1day-kit(`od_kit.py nuclei`), 本包只做情报与研判
