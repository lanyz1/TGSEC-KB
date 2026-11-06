# ai-news-system 项目速查（D:\ai资讯每日更新\ai-news-system）

全自动 AI 资讯日报系统：RSS 抓取 → OpenAI 评分筛选 → 三版日报 → 企微/公众号推送。社群运营内容引擎。

## 三版日报 × 分层运营

| 版本 | 文件后缀 | 内容 | 推送 | 对应人群 |
|---|---|---|---|---|
| 免费版 | `free` | 3-5 条要点+链接，末尾"更多深度分析见 88U 会员版 / VIP 版" | 企业微信 Webhook | 公域引流钩子 |
| 88U 会员版 | `88u-member` | 每条：发生了什么/工具价值/使用场景/行动建议/机会提示 + 今日关键词 | 公众号草稿 | AI 社群 88u/月 |
| VIP 版 | `vip` | 今日判断/行业影响/商业机会/风险/适合人群 + 本周关注 | 本地保存 | 门徒/高端 |

引流逻辑：免费版吊胃口 → 88U 版给足价值留客 → VIP 深度内容，分层付费闭环。

## 架构

```
main.py → collect_news(RSS) → score_news(OpenAI评分≥MIN_SCORE=6.5) → generate_daily_report(三版)
        → 存 output/YYYY-MM-DD-{free,88u-member,vip}.md → push_markdown(企微) → push_to_wechat(公众号草稿)
```
每次运行 2 次 OpenAI 调用（筛选+撰写），gpt-4o-mini 成本极低。定时：scheduler.py 每天 08:00 Asia/Shanghai，或 Windows 任务计划。

## 关键配置（.env）

- `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL`（gpt-4o-mini）
- `RSS_FEEDS`（HN q=AI/OpenAI/machine learning、Product Hunt、TechCrunch AI、The Verge AI、MIT TR AI）、`MAX_NEWS_ITEMS=30`、`MIN_SCORE=6.5`
- `WECOM_WEBHOOK_URL`（免费版群推）
- `WECHAT_APP_ID/SECRET`、`WECHAT_PUSH_ENABLED=false` 时跳过公众号
- `SCHEDULE_TIME=08:00` / `TIMEZONE=Asia/Shanghai`

## 已验证的修复记录（2026-08-25）

1. **AI 返回 JSON 概率性格式错误崩流水线**：`_safe_json_loads` 原版只剥 ``` 围栏，遇尾随逗号等直接 `json.loads` 崩。已换配对扫描版（见 SKILL.md），筛选失败降级返回 []，日报失败返回占位文本。**AI 输出不稳定是常态，容错+降级是必须，不是可选项。**
2. **源文件带 UTF-8 BOM**（ai_filter.py / ai_writer.py）：ast/lint 报 U+FEFF，用 `data[:3]==b'\xef\xbb\xbf'` 检测剥离。
3. **依赖未装**：无 .venv，`pip install -r requirements.txt` 装到系统 Python 3.11 即跑通。
4. **公众号 40164 invalid ip**：直连出口 113.25.1.167（运营商 NAT，动态！）不在公众号 IP 白名单——需用户到 mp.weixin.qq.com 基本配置加白名单；企微推送正常（errcode 0）。

## 坑位

- 企微 Markdown 4000 字符上限（free 版控制 800 字内）
- 公众号推的是草稿，要后台手动发布
- "今日无新闻" = RSS 无更新或全低于 MIN_SCORE，调低阈值或加源
- 验证跑通里程碑：采集 N 条 → 筛选 N 条 → 三版落盘 → 推送 errcode
