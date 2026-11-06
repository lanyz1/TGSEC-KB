---
name: intel-source-harvest
description: "Use when 吸收情报源：sitemap 全量枚举→外链 PoC→落卡→索引实测。"
---

# 情报源吸收（单源全量 → 可调用技能卡）

和 `intel-ingest`（cron 每日喂食）分工：那张卡管**日常抓候选**，本卡管**用户点名的单源深挖 + 落卡 + 索引验证**。触发语："这个站有能吸收的吗"、"看看这个链接"、"有什么新东西"。

## 硬规则

1. **不信首页/列表页**。列表常是"精选库"：示例站点首页 119 条 CVE 的 published 最大只到 10-16，看着"没有新东西"；sitemap 里其实有 45 篇 lastmod ≥ 10-20 的新文章。
2. **判时间用 lastmod，不用正文日期**。
3. **文章正文是二手摘要，外链才是货**。真正能打的是文末那几个 GitHub PoC 仓。
4. **不落索引等于没写**。写完必须重建索引 + 按实战问法实测 TOP1。

## 六步

### 1. 全量枚举

```bash
curl -s -m 20 -A "Mozilla/5.0" https://<site>/sitemap.xml -o sm.xml
curl -s -m 30 -A "Mozilla/5.0" https://<site>/sitemap-articles.xml -o sm_art.xml
grep -c "<loc>" sm_art.xml
```

没有 sitemap 时退到：WP REST（`/wp-json/wp/v2/posts?per_page=100&page=N&_fields=id,date,link,title,content`）、TG（`t.me/s/<ch>?before=<id>`）、GitHub（`api.github.com/users/<org>/repos?per_page=100&page=N`）。

### 2. 时间窗过滤 + 批量抓正文

`<loc>` 与 `<lastmod>` 成对解析，`lastmod[:10] >= 窗口起点` 才进队列；几十篇串行 curl 1–2 分钟，`subprocess.run` 循环即可，不需要 headless 浏览器。

### 3. 抽技术骨架

每篇只抽"版本 / 前置条件 / 入口 / KEV·PoC 状态"四类句子（按 `CVE-`、`affected`、`fixed in`、`requires`、`exploit`、`PoC` 过滤），每篇留 600–1,000 字就够判死，别整篇读进上下文。

### 4. 挖外链 PoC（价值最高的一步）

```python
for m in re.findall(r'href="(https?://[^"]+)"', html):
    if re.search(r'<站点>|twitter\.com|x\.com/|linkedin|bsky|facebook', m): continue
```

保留 github/gitlab/`*poc*`/`*exploit*`，再取 `api.github.com/repos/<owner>/<repo>`（desc/language/stars/pushed_at）+ `raw.githubusercontent.com/.../README.md` + `git/trees/<br>?recursive=1`（文件清单）。

判"真 PoC"：README 有 Requirements + Usage + `run.sh`/`compose.yaml` + 验证标记（如 `/tmp/pwned`）。本次 44 篇带仓库，8 个属这一类。

### 5. 去重 + 落卡

```bash
for c in <CVE...>; do echo "$c -> $(grep -rl "$c" --include=SKILL.md /root/.hermes/skills | wc -l)"; done
```

0 命中的才是真增量（本次 17 条里 16 条全新）。卡形态：**一个时间窗一张卡**，按面分组，每条固定四段（影响版本+修复版 / 前置配置 / 打哪 / KEV·PoC 状态），末尾一张现成 PoC 表，并在老卡（如 `cve-wave-2026-11`）加一行指针。

### 6. 索引验证

```bash
# triggers.json 补中英产品别名 → 重建 → 逐条实测
cd /root/.hermes/arsenal && python3 arsenal_build.py      # ~70s
python3 skill_find.py "Cisco ASA VPN 未授权 重载" --fast --top 1
python3 skill_find.py "CVE-2026-34486" --fast --top 1
```

要求：产品问法与裸 CVE 号都 TOP1。本次 6/6 全中（score 335–2943）。

## X/Twitter 这类"登录墙"源

免登录拿不到全量，别再花一小时试免费通道：

- syndication 对多数号返回 **200 / 2,227 B 空壳**；guest GraphQL 返回 `TimelineTerminateTimeline` 第 1 页即终止；v2 guest 报 `Unsupported Authentication`；nitter 12 实例 alive 0。
- 全量只能靠：**本人浏览器 Cookie**（`auth_token` 是 HttpOnly，必须从 F12 → Network 的 `cookie:` 行复制）、**App-Only Bearer**、或小号 CDP 登录。

逐条硬指标与三条可用路径见 `references/x-timeline-access.md`；单站抓取/解析的完整代码套路见 `references/site-intel-harvest.md`。

## Pitfalls

- **首页日期会骗人**：列表按 published 排，新内容常先发文章后补索引页 → 永远以 sitemap lastmod 为准。
- **Next.js App Router 页面没有 `__NEXT_DATA__`**，数据在 `self.__next_f.push([1,"..."])` 流里；按记录取值必须"定位 href → 只在该记录片段内顺序扫 children"，用固定字符窗口会把邻居记录的标题/日期串进来。
- `re.findall` 带嵌套分组返回 tuple，统一用 `finditer().group(1)`。
- GitHub API 可能返回 404 体（`description` 为 `None`），取值一律 `d.get("desc") or ""`，否则脚本半途崩。
- 抓不到 ≠ 不存在：汇报要给状态码 + 字节数 + 终止标志。
- Cookie 等于账号：只由用户本人在自己浏览器自取，脚本用环境变量传，不落盘。

## 已产出的样例

- `threatwire-cve-briefs-2026-11` — 2026-11 时间窗 CVE 简报卡（17 条 + 8 个可跑 PoC 仓），本卡方法的直接产物。
- `abraxas-labs-cve-corpus` — GitHub 组织级吸入的语料卡。
