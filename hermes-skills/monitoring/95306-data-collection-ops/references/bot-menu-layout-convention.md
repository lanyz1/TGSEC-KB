# bot 菜单分层约定（95306 主控 bot，用户确认）

## 现状
- **主菜单 `ui_home` 只放老 `menu_b` 那 8 行**：4 个可拦截分类计数 + 🏁 已结束项目 + 🔍 搜索项目 + 🤖 AI 查询(直接问) + ⚙️ 设置中心(更多功能)。
- **工具/管理键一律收在 `ui_settings`（⚙️ 设置中心）里点选**：数据池 / 竞价监控 / 项目搜索 / 企业查询 / 下载中心 / 我的订阅 / 加速器 / 设置 / 帮助 / 我的收藏 / 企业监控 / 最近浏览 / 工坊 / 数据池更新 / 更新记录 / 采集机健康 / 日志 / 周报 / 授权管理 / 跳板机。
- 命令面不变（`/pool /live /download /mine /hist …` 仍可用）。

## 落码纪律
1. 主菜单键位改动**只动 `bot/menus.py::ui_home` 的 `rows`**；**不要新增回调键**（曾一度加 `ctrl` 后又撤) —— `_cb_table()` 回调数应恒为 95，变了就是死键/漏接线。
2. 改完必跑：`py_compile` + `tools/offline_ui.py`（按钮数随键位变：192→180 属预期）+ `tools/coverage_vs_old.py`（须仍 100%）+ `offline_bot/groups/tg/integration`。
3. 上产链：`build_release --stamp → scp 包+manifest → --stage（显式带 --sha）→ --plan → 未割接新树跑只读探针（先验后切）→ --activate → --verify → 串行 pkill/起壳`。**activate 不重启 bot** ⇒ 必须手动停/起；起壳形态照抄现役：
   `cd /opt/v6 && V6_CONF_EXTRA=/opt/v6/secret.ini setsid nohup flock -n /tmp/v6_bot.lock python3 -u /opt/v6/v6m.py bot >> /opt/v6/pixbot.log 2>&1 < /dev/null`
4. 纯菜单/文案类改动**不必**再发 TG 自检；`bot/tg.py` 未变则送信链沿用上一版已验结论（差分证明 only menus.py changed 即可）。
5. 停旧/起新**严禁并发**（同 token 双 `getUpdates` 会 409）：停 → 确认 `STOPPED_CLEAN` → 起，两次 ssh 分开调。
