<!-- archived from /root/.hermes/skills/security/ai-content-automation/SKILL.md on 2026-10-21 -->

---
name: ai-content-automation
description: >-
  测绘引擎·Use when 构建/维护 LLM 自动生成内容的管线或 AI 返回 JSON 解析失败。含容错解析代码与推送渠道坑。
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/ai-content-automation`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ai-content-automation/…')`，不要相对 `references/legacy/` 解析。

# ai-content-automation（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ai-content-automation/`

溯源（仅标记）：`hermes/mlops`

---

# AI 内容自动化管线（LLM → 结构化内容 → 推送）

适用：定时调用 LLM 生成日报/资讯筛选/摘要/榜单，再推送企微/公众号/本地的自动化系统（如 `D:\ai资讯每日更新\ai-news-system`）。

## 核心铁律：LLM 输出 JSON 必须容错解析

LLM 返回 JSON 是**概率性**的——同一 prompt 这次合法、下次就带尾随逗号/行注释/围栏/多余文本。**不能裸 `json.loads()`**，解析失败也不许崩掉整条流水线。

已验证的健壮解析（两个文件里各放一份，模块独立）：

```python
import json, re

def _extract_json_body(text: str) -> str:
    """截取第一个 { 或 [ 到其配对结束符之间的内容（跳过字符串内的括号）。"""
    start = -1
    for i, ch in enumerate(text):
        if ch in "[{":
            start = i
            break
    if start == -1:
        return text
    open_ch, close_ch = text[start], ("]" if text[start] == "[" else "}")
    depth = 0
    in_str = esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == open_ch: depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return text[start:]

def _safe_json_loads(text: str):
    if not text or not text.strip():
        raise ValueError("empty LLM output")
    text = text.strip()
    if text.startswith("```"):                      # 剥 markdown 围栏
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    text = _extract_json_body(text)                 # 截取主体（去掉前后解释文字）
    text = re.sub(r"(?m)^\s*//.*$", "", text)       # 去行注释（只匹配行首，不误伤 URL）
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r",\s*([}\]])", r"\1", text)      # 去尾随逗号
    return json.loads(text)
```

**调用侧必须降级**（try/except 包住，失败打 `[WARN]` + 原文前 200 字，返回空/占位内容继续跑）：
- 筛选失败 → 返回 `[]`，让下游生成"今日无重要新闻"占位日报，推送照走
- 日报生成失败 → 返回带错误提示的三版占位文本，不要 `raise`

## 推送渠道配置坑

| 渠道 | 坑 | 处理 |
|---|---|---|
| 企业微信 Webhook | Markdown 上限 **4000 字符**，超了截断 | free 版控制 800 字内 |
| 微信公众号草稿 | API 要求出口 IP 在白名单，报 `invalid ip xxx not in whitelist` | mp.weixin.qq.com → 设置与开发 → 基本配置 → IP 白名单；**家庭宽带动态 IP 会变**，再报错就是 IP 变了，重加 |
| 公众号草稿 | 推送的是草稿，需后台手动点发布 | 流程上告诉用户 |

排错技巧：`curl -s https://api.ip.sb/ip`（直连出口）vs `curl -s -x socks5h://127.0.0.1:10808 https://api.ip.sb/ip`（代理出口）——分清微信 API 请求实际走哪条链路，白名单就加哪个 IP。

## Windows 部署坑

- **依赖装到系统 Python 即可跑**（无 .venv 时 `pip install -r requirements.txt`），但建议日后建 .venv 隔离
- **Python 源文件带 UTF-8 BOM** → `ast`/lint 报 `invalid non-printable character U+FEFF`。检测+剥离：
  ```python
  data = open(f, 'rb').read()
  if data[:3] == b'\xef\xbb\xbf':
      open(f, 'wb').write(data[3:])
  ```
- 定时：项目自带 `scheduler.py`（schedule 库）或 Windows 任务计划程序每天调 `main.py`

## 验证流程（"系统还活着吗"）

1. 检查 .env 键齐全（`grep -oE "^[A-Z_]+=" .env`，**不打印密钥值**）
2. `pip install -r requirements.txt`（缺啥装啥）
3. `python main.py` 跑全链路，盯四个里程碑：采集 N 条 → 筛选 N 条 → 三版落盘 → 推送结果
4. 推送失败先看 errcode：企微 `0`=成功；公众号 `40164`=IP 白名单

## 参考

- `references/ai-news-system.md` — 本项目（三版日报分层运营逻辑、配置项、已修 bug 记录）
