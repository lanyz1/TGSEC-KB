# cvebird / t.me 频道批处理管道（增量 → triage → 吸收）

2026-10-08 实战验证：窗口 #16999→#17100（102 帖）、抓取 160 帖零缺口、全量过目、决策表交付用户拍板。
适用：用户丢 t.me 频道链接（多为 https://t.me/cvebird）说「提取这几天新发的仓库链接进行吸收提炼」。

## 0. 总流水线
抓取（t.me/s 预览页）→ 定义增量窗口（上批边界 id+1）→ 全量过目 → 轻探候选（不 clone）→ 四桶分类 → 决策表（草稿，发用户）→【先告诉我决策门】→ 用户点头 → 吸收 → scan_push 闸 → 再点头 → 推。

## 1. 抓取（免登录，直连可用）
- `curl -sS "https://t.me/s/<channel>"` 直连 200（≈112KB，本机无需代理）。翻页 `?before=<本页最小id>`，每页 ≈20 帖，间隔 ≥1s。
- 解析：`data-post="<channel>/<id>"` 切块 → `<time datetime>` 取 UTC 时间 → `tgme_widget_message_text` 取正文（嵌套 div 用计数法，非贪婪正则会截断）→ 链接 href 与正文纯文本**双通道** regex（github/gitlab/gitee）。
- 完整性自检：id 应连号，`max-min+1 == count`；有缺口 = 删帖或解析漏。
- 现成脚本：`scripts/fetch_tme_channel.py`（本卡配套；dumps JSON + 按日统计 + 链接清单）。

## 2. 增量窗口
- 锚点 = 仓库内上批存档 `domains/0day-exploits/INGEST-*-CVEBIRD.md` 记的覆盖 id 区间；窗口 = 边界+1 → 最新 id。
- 别用「链接集合差集」去重（镜像/转发会漂移）；id 边界最干净。「这几天新发的」= 上批复核之后至今。
- 边界兜底：上一批已 triage 但尚未吸收入库时（仓库内还没有对应 INGEST 文件），先查本地 `/root/cvebird-*-triage.md` 已过目 id 段，抓取后跳过，勿重复 triage。
- 抓完先对账：Σ 桶分类 = 窗口总数，少一条即回头查。

## 3. 轻探（先读后 clone 原则，本批 3 个大货全靠轻探定性）
- GitHub API `/repos/{owner}/{repo}`（stars/size/fork/pushed_at/description）→ 存 JSON 备查；先查 `/rate_limit`，`remaining < 需求+3` 即停（匿名 60/h）。
- README / 单文件走 `raw.githubusercontent.com/{o}/{r}/{branch}/{path}` —— **不吃 API 配额**，批量看内容是首选（中文路径 urllib quote）。
- 目录结构走 `git/trees/{branch}?recursive=1`（存 JSON），过滤 .md / 顶层文件判断「产品 vs 知识 vs 空壳」。
- 空壳判据：size≈0 + 宏大描述 = SEO/垃圾（本批 5 个）。
- **镜像洪水**：同一项目 N 个镜像（本批 ARTEX×16）只探 1–3 个代表（挑 stars 最高 / 含上游注明的），报告注明「镜像组仅提炼代表页」，绝不逐镜像 triage。

## 4. 四桶分类 + 决策表
- 桶：**真缺口（P0/P1/P2/P3）/ 已融 / 可疑投毒 / 淘汰（写原因）**。
- P 级参考：P0 = 产线核心直接对标（卡密逆向 / iOS 收割链 / C2 框架）；P1 = 高星对口工具 / 范式；P2 = 轻量提炼 1 页；P3 = 另行再定。
- 可疑投毒判据：乱码随机用户名 + 预编译 exe、空壳 + 诱饵名（如「免费充值漏洞」）→ 标「勿运行」，不做二次探测。
- 生成方式：把分类写成 `{id: (桶, 注记)}` dict → 程序化生成 md（含「建议动作」摘要块）；命名 `/root/cvebird-YYYYMMDD-triage.md`，标题标「草稿，未入库」。
- 交付：聊天里发摘要 + `MEDIA:` 附件；**此时不 clone、不动仓库、不推**（「先告诉我」决策门 = 用户既定惯例）。
- 用户会拍板「按最优吸收」或点名 → 才进入吸收。

## 5. 坑（现场踩过）
- **压缩存根幻觉**：被上下文压扁的工具输出（如仅回显 "(1 lines output)"）不得凭印象引用其内容 —— 本批曾「记得」某帖存在，全量 grep 原始 JSON 实为 0。凡关键事实先 grep 落盘工件（JSON/HTML/日志/raw 目录）验证，再写进决策表。
- 上批工件可能在 /tmp 被清；增量锚以仓库内 INGEST 文件为准，不以本地 /tmp 缓存为准。
- 分类 dict 有未映射帖时生成器会暴露对账差异 → 补映射后**重跑生成器**，别手改 md（否则重跑会覆盖）。
- t.me 预览页同帖可能重复出现 → 用 id 集合去重（data-post id 唯一）。

## 6. 收尾（用户拍板后）
吸收只落提炼层（脱敏）→ 过 `/root/tgsec-guard/scan_push.py` 闸（0 命中才准推）→ 用户点头 → 推。原文全文永不入仓（RULES #6 硬门）。
