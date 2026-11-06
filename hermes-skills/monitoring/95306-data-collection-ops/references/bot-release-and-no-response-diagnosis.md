# bot 发布割接 + 「bot 没反应」诊断

## 一、发布链（主控机 /opt/v6）
1. 本地 `deploy/build_release.py --out dist --stamp <date+letters>`
2. `scp` 到 `/opt/v6/`，**先比两端 tar sha256**（一致才继续）
3. `python3 /tmp/v6mplan/master_deploy.py --stage --tar <tar> --sha <sha>`（**必须显式带 --tar/--sha**）
4. `--plan --rel <rel>`（只读预检，看 `problems []`）
5. **割接前：在 staged 树上跑真数据探针**（第五节）——`TREE` 指向 `/opt/v6/lib/<rel>`，只读 + 假 Tg、零外发。离线闸全绿 ≠ 真数据对，这步是最后一道网。
6. `--activate --rel <rel> --yes` → `readlink -f /opt/v6/current`。输出里的 `skipped_already_running … bot 已在跑 pid=…` 是正常提示：**在跑的进程仍持旧代码（内存里），割接不会让它换代码** ⇒ 必须重启才生效。
7. `--verify --rel <rel>`
8. **activate 不会重启 bot**（割接红线）：必须手动 `pkill -f "[v]6m.py bot"`（方括号防自杀）→ **单独一次** 起壳：
   `ssh -n -f … 'cd /opt/v6 && V6_CONF_EXTRA=/opt/v6/secret.ini setsid nohup flock -n /tmp/v6_bot.lock python3 -u /opt/v6/v6m.py bot >> /opt/v6/pixbot.log 2>&1 < /dev/null &'`
   - **`python3 -u` 必带**：不加 `-u` 时 stdout 块缓冲，日志会"冻住"几十分钟，误导排查（本次被坑过）。
   - `v6m.py:70/75` 会自设 `V6_MASTER_CONF` / `V6_CONF_EXTRA`（secret.ini 存在才设）。脱离入口跑探针必须自己设这两个环境变量，否则读空配置（授权闸 fail-closed 假阴性）。
9. 完整性核对：本地/线上 `bot/menus.py`+`bot/tg.py` **sha256 逐位一致** 才算修复真上线。
10. 起新后的健康证据：日志定位用**行号锚**（`grep -n '按钮层已接线' /opt/v6/pixbot.log | tail -1`，再 `tail -n +$L`）——新起日志行**不带时间戳**，时间锚会失效；判据 = 锚后出现 `按钮层已接线：95 组回调` + `pgrep -af "[v]6m.py bot"` 有进程 + `wchan=do_poll` + fd 有 socket + 无 `ROUTE-ERR`。

## 二、「bot 没反应」三级判定（由表及里，全只读）
1. **进程活着吗**：`pgrep -af "[v]6m.py bot"`；`readlink -f /opt/v6/current` 看跑哪棵树。
2. **在消费吗**：
   - 只读探针 `getWebhookInfo` → `pending_update_count`（>0 且没人消费 = 消息在积压）、`last_error_description`（"Conflict…getUpdates" = 双消费者抢单）。**绝不要用 `getUpdates` 去"测"**，那会真消费/推进 offset。
   - 泄漏队列内容看那条是什么：`getUpdates(offset=<落盘 offset>, limit=10, timeout=0)` **预览**（不再以更高 offset 调用 ⇒ 不算消费）。拿到 `update_id/text/callback_data` 就知道是哪条动作触发的。
3. **在算什么 / 卡在哪**（关键分流）：
   - `cat /proc/<pid>/task/<pid>/wchan`：`do_poll` = 正阻塞在轮询（健康）；空/`0` = 在跑。
   - `cat /proc/<pid>/task/<tid>/syscall` 连采：**全是 `running`** = 纯用户态计算（无系统调用）。
   - **各线程 CPU 增量**（隔 5–6s 读 `/proc/<pid>/task/<tid>/stat` 的 14+15 字段）：某个线程狂涨 = 真死循环/重计算；**全 0 tick** = 它在睡觉，别误判成死循环（我曾只读进程总 tick 就误判过）。
   - `ls -l /proc/<pid>/fd | grep -o "socket:\[[0-9]*\]"` + `wchan=do_poll` = 轮询连接在。
4. **算多久**：看 `/opt/v6/bot_offset.json` 的 **mtime**（= 最后一条动作被处理完的时刻）与 `update_id` 的 fetch 时刻对比 ⇒ 得出端到端耗时。本次实测 `/start` 端到端 **6 分 58 秒**（bug），修后 **0.34 秒**。

## 三、已知真实缺陷（本次上线修复，v6rel_20261004ac）
- `groups()` 全池遍历分桶：`collect_complete_projects()` 遍历 53,939 项（161.8s）⇒ 改为**只给候选集算采集完成**（等价、不引缓存）⇒ 1.30s（125×）。
- `ghost_filter` 要新树形状 `[{"pid","info"}]`，调用点不得裸 `except: pass`（会吞 AttributeError 致过滤失效）。
- `collect_complete_projects(limit=30)` 只返前 30 ⇒ 不可当全集用于分桶。
- `Commands.cmp(cid, t)` 少传 `t` ⇒ TypeError（命令层）。
- `tg.send` 命令层无 Markdown 兜底 ⇒ 400 报错：兜底**下沉到 `bot/tg.py`**，只对 400 退纯文本重发一次，401 类照旧抛。

## 四、回归闸（本地，零外发）
`tools/offline_ui.py`(168) / `offline_bot.py`(94) / `offline_integration.py`(17) / `offline_groups.py`(10) / `offline_tg.py`(8) / `coverage_vs_old.py`(100%)；上线探针一律把 `menus.tg`/`router.tg`/`cmds.tg`/`push.sender` **四路全换记录器**（只换前两路会真外发）。

- **样式/字段类断言要用真组件单测，别信夹具**：夹具里的假 render 会掩盖换树差异。项目卡文本落点在 `bot/render.py::fmt_proj_card`，单测用真 `render.Render` + `StubConf`（`get_int/get_str/get_bool` 返 default）+ `StubPool` 桩打三档卡片（`tools/_probe_card.py` 出 `CARD_OK`）。
- **改样式后别写死旧字段断言**：卡片/面板改版会让 `offline_bot.py` 里靠旧字段判定的用例假失败 ⇒ 断言改成按新卡片字段判（如 `"状态: "` + `"包件:"`）。
- **改按钮 `callback_data` 后必须 grep 回调注册表验真伪**：想当然写的键可能是死键（`watch` 只 1 处 = 死键，真键是 `watchlist`）。
- **改 UI 方法签名前先看调用点传参顺序**：`ui_settings(self, cid, edit=None, fname=None)` 若写成 `fname=None, edit=None`，回调传入的 `edit` 会错绑到 `fname`。

## 五、割接前「staged 树真数据探针」（离线闸之外的最后一网）
1. 现有探针把 `TREE` 写死成 `/opt/v6/current` ⇒ **先做指向新树的副本**：
   `sed "s|/opt/v6/current|/opt/v6/lib/<rel>|" /tmp/v6mplan/_probe_style.py > /tmp/v6mplan/_probe_style_<rel>.py`
2. 用**真池**跑（只读 + 假 Tg 记录器，零外发零写入）：`python3 -u …/_probe_style_<rel>.py > /tmp/v6mplan/style_<rel>.txt`
3. 判据 = 逐面板对齐老正本锚点，**并且关键字段非空**：`━━━` / `👇 选择功能:` / `{标题} | 第p/n页 (共N个)` / `1. 名称` + `📅MM-DD | 🏢N/M家` / `📄 回复数字或点按钮查看详情` / `📦 包件:` / `**包件预览:**`。统计法：`grep -c '📅[0-9]'`（有值）vs `grep -c '📅 |'`（空值），空值占比要能对老正本解释。
4. **为什么必须做**：离线夹具 + 六闸全绿也可能真数据是空的 —— 夹具的假 pool 会给字段，真池不给。真数据采样的价值就在这（本次列表 `📅` 全空就是这样抓到的，没有任何一条离线闸报出来）。
5. 不达标**先别 activate**：改树 → 重跑离线闸 → 重新打包（新 stamp）→ re-stage → 再探；不要手工改 `lib/<rel>` 里的解包产物（会与 stage 记录/包哈希对不上）。

## 六、从老脚本搬函数：整函数差分，不搬 happy path
- **规则**：搬一个函数要把它**每个 fallback/推导分支**列全再落码；只搬主路径 = 真数据下静默空值。`pool.proj_pub_day()` 只搬了 pubtime + `publishTime`，漏掉老正本 `projCode` 正则兜底 ⇒ 真池日期全空，而离线夹具（含 pubtime 桩值）照样绿。
- **落码后配确定性单测**：逐档断言优先级（每个数据源各一例 + 两源同时命中时的优先序 + 渲染切片口径），跑出 `PUBDAY_OK` 才算完（`tools/_probe_pubday.py`）。

### 95306 真池数据源实况（换树时重新核，别照抄旧假设）
- `/data_pool/publish_time.json` 可能**根本不存在** ⇒ `load_pubtime()` 恒空；不要把「列表日期来自 pubtime」当默认。
- 平台权威名单 `/data_pool/plat_enroll_map.json`：每项含 `{"企业数","企业","公告日"}`，**键是 `projCode`** ⇒ 用 `_pe_pick(pe, pid, info)`（先 code 后 pid）取。
- 公告日优先级链：① pubtime 表 → ② 平台 `公告日` → ③ `info.publishTime` → ④ `projCode` 里 `0020(\d{6})` 反推（`%y%m%d`→`%Y-%m-%d`）→ `""`；列表行显示口径 `str(day)[5:16]` ⇒ `MM-DD`（与老正本一致，别改）。
- `pool.all_projects()` 返回 **dict `{pid: info}`**（不是 `(pid, info)` 元组列表）——写探针按 dict 迭代，否则 `too many values to unpack`。
- **性能**：`Pool._load()` **无缓存** ⇒ `load_plat_enroll()` 每调一次读 ~437KB JSON。列表渲染要**一次读盘、逐项复用**：`page_out` 里 `pub = load_pubtime()` / `pe = load_plat_enroll()` 各读一次，再传给 `proj_pub_day(pid, info, pub, pe)` / `proj_plat_ent_count(pid, info, pe)`（新形参一律 `=None` 可选，保旧调用点不炸）。**严禁在渲染循环里逐项调 `load_plat_enroll()` 或 `check_status_summary()`。**
