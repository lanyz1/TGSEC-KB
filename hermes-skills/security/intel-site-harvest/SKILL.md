---
name: intel-site-harvest
description: Use when 情报站全量采集落卡：sitemap 枚丙+外链挖 PoC。
---

# 情报站采集 → 落卡（intel site harvest）

适用：老板丢一个链接（`https://x/cve`、writeup 站、PoC 索引站），问「有能吸收的吗」。
目标不是列标题，是 **判值 → 抽硬信息 → 落成卡 → 证明调得到**。

## 0. 判定顺序（别从首页开始）

1. 先判站点形态：静态 / Next.js（`self.__next_f` 或 `__NEXT_DATA__`）/ Hugo / Docusaurus / WP。
2. **枚举 sitemap，不信首页列表**。首页/分页往往是「精选」，最新日期会落后于文章层。
3. 用 `<lastmod>` 筛时间窗内的文章，逐篇抓 **HTML**（不只是正文）。
4. 正文抽版本/前置条件；**外链抽 PoC 仓/修复 commit/厂商公告**——这才是硬通货。
5. 写前去重 → 落卡 → 重建索引 → 抽检可调性。

## 1. sitemap 全量枚举

```bash
python3 scripts/sitemap_enum.py https://www.threatwire.tech --since 2026-10-20
```

输出子 sitemap 的条数 + 时间窗内 URL 数（`--json` 拿列表）。手动版：`curl -s https://<site>/sitemap.xml` → 子 `sitemap-*.xml`。

实测样本：119 个 CVE 页 + 114 篇文章，而首页 CVE 列表最新只到 10-16、文章层 10-20 后还有 45 篇 —— 只看首页会得出「没新东西」的错结论。

## 2. Next.js 列表解析（两个必踩的坑）

App Router 的数据在 `self.__next_f.push([1,"…"])` 里，不是 `__NEXT_DATA__`（那是 Pages Router）。

```python
for m in re.finditer(r'"href":"/cve/(cve-[0-9-]+)"', payload):
    seg = payload[m.start(): m.start() + 3000]        # 往后取，不要往前
    vals = [x.group(1) for x in re.finditer(r'"children":"((?:[^"\\]|\\.)*)"', seg)]
    # 依次：severity / CVE-id / 标题 / 类型 / "Published" / "6 Oct 2026"
```

- **取 href 之前的窗口 = 记录错位**：标题张冠李戴、日期全空（实测就这么上当的）。数据在同级 anchor 的 children 里，只能往后。
- **`findall` 带嵌套分组返回 tuple** → `TypeError: too many values to unpack`；改 `finditer` + `group(1)`。
- 日期常见 `6 Oct 2026`（单位数日）：`%d %b %Y`；`%d %B %Y` 只对全称月份有效。

## 3. 外链挖 PoC（本类任务最高价值一步）

```python
links = {u for u in re.findall(r'href="(https?://[^"]+)"', html)
         if not re.search(r'<site>|twitter|x\.com/|linkedin|bsky|mastodon|reddit', u)}
```

判值不用 clone，三个 API 就够：

```bash
curl -s https://api.github.com/repos/<owner>/<repo>                                  # desc/lang/pushed_at
curl -s "https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1"  # 文件列表
curl -sL https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md           # 用法
```

文件列表出现 `run.sh` / `Dockerfile` / `*Gen.java` / `send_payload.py` = 有一键复现环境，优先收；只有 `.md` 的是「声称」，降级。

## 4. 写前去重（不 grep 就会重写已有卡）

```bash
for c in CVE-2026-110264 CVE-2026-34486; do
  echo "$c -> $(grep -rl "$c" /root/.hermes/skills --include=SKILL.md | wc -l)"
done
```

实测 17 条里 16 条库内没有（真增量）；剩下 1 条已有产品矩阵卡——这种只加指针，不另起卡。

## 5. CVE 简报卡形状

一条 CVE 固定四行，前置条件不能省：

```
### CVE-xxxx-yyyyy — <产品> <一句话>
- 影响：<版本区间> → 修复 <版本号>
- 前置：<必须开什么功能/什么角色/什么配置，否则不中>
- 动作：<打哪里、什么机制>
- 状态：KEV 日期 / 公开 PoC 与否
- 现成 PoC：<repo> — <怎么跑>
```

卡尾挂一张「现成 PoC 仓库表」。同批洞按面分组（设备/中间件/Web-CMS/身份/客户端），别按字母排。

## 6. 落卡之后必须证明调得到

`arsenal_build.py` → `skill_find` 抽检 → 按 `skill-library-invocation-audit` 的**四通道实测**（钩子 / skill_view / CLI / arsenal_load）。不重建 = 搜不到 = 白吸；只报分数不报通道 = 没证明。

## Pitfalls

- **首页 ≠ 全库**（精选列表会停在半个月前）。
- **别把站点自己写的 tag 当日期**：`<lastmod>` 才是更新节奏，发布时间在 payload 的 `Published` 字段。
- **正文提取要保 HTML**：只存纯文本就拿不到外链，PoC 仓全丢。
- **API 限速**：GitHub 未鉴权 60 次/小时；批量查仓前先 `gh auth status`，或只查已筛过的。
- **站上没利用代码**：这类站是索引+解读，payload 全在外链仓里；卡里必须写清「去哪拿 PoC」。

实战记录：`references/threatwire-20261101.md`。脚本：`scripts/sitemap_enum.py`。
