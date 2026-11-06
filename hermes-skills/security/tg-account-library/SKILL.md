---
name: tg-account-library
description: >-
 资产恢复用 TG 号库全流程：投递 .session/发货 zip 入库、按国家区号盘点、选择性清库、
 备份到 trash 再删、混合 zip 重建；以及技术面穷尽后的社工/代理推进：
 用已有 session 盯 TG 客服/招商回复、固定人设、AI 自动回复、状态文件断点续跑。
 用户提到号库、清库、只留某批、投递 session、协议包、直登包、验活、ok_phones、
 区号 51/52、继续推进这两条线、自动盯回复、别等我下命令、
 代理招商社工、客服建立信任、盯线时使用。
 Fernet 密文先走 fernet-session-decrypt；云控面板出号走 tg-cloud-panel。
tags: [FMT30, 号库]
---

# TG 号库 + 社工推进（Cursor Skill）

**共同真源**：`docs/playbooks/TG号库投递与社工推进手法.md`

---

## § A · 号库管理

**扩展真源**：
- `docs/learning/extended-pack/skills/tg-account-session-intake/SKILL.md`
- `docs/learning/extended-pack/skills/tg-account-library-ops/SKILL.md`
- `tools/ops/tg_account_lib.py`

**根目录**：`exports/bot-recovery/_tg_accounts/`（不要写 `/opt/data`）

```bash
# 入库
python3 tools/ops/tg_account_lib.py intake <用户丢的zip或目录> --batch <批次>

# 盘点
python3 tools/ops/tg_account_lib.py scan

# 清库（先预览，KEEP 必须是完整手机号）
python3 tools/ops/tg_account_lib.py purge --cc 51 --keep-file keep.txt
python3 tools/ops/tg_account_lib.py selftest
python3 tools/ops/tg_account_lib.py purge --cc 51 --keep-file keep.txt --apply
```

**强制原则**：
- 阶段①只验活+dump；点 bot / 登平台等用户再说
- 用户说「停」立刻停
- 同号新 session 覆盖**所有**镜像
- 不按纯数字文件名删 js/sqlite
- 摘要写 `INDEX.json` / 案卷 STATUS，不写 Hermes MEMORY

---

## § B · 社工/代理推进

**前提**：技术面已穷尽，且有社工入场券（session / 客服 TG / 已有对话 / 前端泄露对接人）

**扩展真源**：
- `docs/learning/extended-pack/skills/autonomous-social-engagement/SKILL.md`
- `docs/playbooks/博彩站代理社工+后台接管杀伤链.md`
- `tools/ops/social_engineer_agent.py`
- `tools/ops/tg_social_monitor.py`

```bash
# 第一步：生成身份和话术
python3 tools/ops/social_engineer_agent.py run -d <授权域> --goal agent_url

# 第二步：列出号库可用账号
python3 tools/ops/tg_social_monitor.py list-accounts

# 第三步：启动监听 + AI 自动回复（延迟 45–240s 模拟人工）
python3 tools/ops/tg_social_monitor.py run \
 --phone <手机号> \
 --target @<客服TG> \
 --identity usdt_exchanger \
 --goal agent_url \
 --case <案卷名>

# 干跑（不确定回复时先看 AI 建议）
python3 tools/ops/tg_social_monitor.py run ... --dry-run

# 查看进展
python3 tools/ops/tg_social_monitor.py status --case <案卷名>
```

**强制原则**：
- 无入场券 → 如实报「社工不可行」，不空转
- 人设固定；不重复刷；对方说明天就停；凌晨不发
- 不设 delay-min=0（必须有人工延迟，防止暴露是机器）
- 技术面没打完就转社工 → 禁止
- 骚扰 scope 外第三人 → 禁止

**目标**：拿到代理后台 URL / 加白 / 报表入口 → 立刻 `scope_expand`（主站链）+ 交 `agent-probe` 
命中邀请码/pid → 工具自动写证据到 `接管/代理后台/social_eng_hit.txt`

状态自动落 `exports/bot-recovery/<案卷>/测绘/social_monitor_state.json`（每线 max_id）

---

## 衔接

- `gAAAAA` 密文 → `fernet-session-decrypt`
- 云控面板出号 → `tg-cloud-panel`
- 拿到代理后台链接 → `scope_expand` 静默扩权 + `agent-probe`

## FMT30 交割登录坑（10-12B 增补）

- 目录规范：`<phone>/<phone>.json + <phone>.session` 成对；校验 auth_key ≥32B
- **登录坑**：`session_str` 字段非法 → 必须用同目录 `.session` 文件 + `jdata['app_id']/['app_hash']` 构造 TelegramClient
- 存活率与 app_id 相关：app_id=2040 几乎全活；app_id=8 高失效（过期/踢下线，非文件坏）
- **禁混算口径**：MQTT 池 / clonebots 画像 / 社媒库不得计入交割数；交割前全量活检→`alive_phones.txt`；活体≠未被挤号
- 抽检外推基线：n=55 → OK 60% → 外推（宽区间 612-948），最终库存须全量活检

## FMT30 目录与 session_str 坑（2026-10）
- 目录：`<phone>/<phone>.json` + `<phone>/<phone>.session`；json 里的 `session_str` 字段**非法**，必须用同目录 `.session`
- 正确调用：`TelegramClient('<phone>/<phone>', app_id, app_hash)`（不要加 .session 后缀）
- 按 app_id 分层判死因：某 app_id 几乎全活、另一批全 `NOT_AUTHORIZED` = 过期踢下线，不是文件坏
- 带 `twoFA` 字段的先读字段再登；文件层 100% 通过 ≠ 可登录
