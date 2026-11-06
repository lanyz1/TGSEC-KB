# bot 用户面「隐藏 vs 没做进去」对账

用途：用户问「某功能在 bot 里`还是没有显示`——是隐藏没显示还是没做进去」时的取证流程与判定口径。

## 0. 判定词表（先定义，再下结论）
- **显示且真跑**：按钮上屏 + handler 真执行动作。
- **显示但空转**：按钮上屏，点击只回一段说明/回执（开关关着或 handler 本身只回执）。
- **条件渲染**：只在特定状态（文件已生成/生成中/有清单/有报名数）才注册到键盘上，平时看不到。
- **隐藏**：handler 已注册、但没有任何面板渲染出该 callback ⇒ 有代码没入口。
- **死键**：有按钮、无 handler 前缀命中。
- **没做进去**：两边都没有 ⇒ 这个词/能力从来没被实现过。

## 1. 两套集合都要枚举（注册 ⊕ 上屏）
离线桩在 `tools/offline_ui.py` + `tools/offline_ui_parts.py`（`FakeConf/FakeTg/FakeRouter/FakePool/FakeRender/FakeCmds/FakeCompat`）。桩自带的是「按钮→分发表」**单向**校验；要的**反向**差集得自己写探针。

探针三步：
1. 逐块渲染面板（管理员 cid 与普通用户 cid **各跑一遍**），从 `FakeTg` 抓每次 `send` 的键盘，收集真上屏 `callback_data`；
2. 取 `router.cb_handlers`（已注册 callback 前缀）与 `mn._cb_table()`（分发表）；
3. 求两个差集：注册未渲染（隐藏候选）/ 按钮无前缀（死键）。

纪律：探针用 `python3 -X utf8` 跑；import 段别写多余表达式（`False if False else X` 这类笔误直接炸）；输出用集合的长度+排序列表，不要只 print 一行，否则回包被压缩后白跑一轮。路由构造是 `FakeRouter(tg)`，别写成无参。

## 2. 权限差分
同一批面板用「管理员 cid」与「普通用户 cid」各渲染一遍取差集。健康结果：差集只落在授权/运维/跳板机类按钮上。**若差集里出现用户要的那个功能，才是真「对他隐藏」**。

## 3. 本地树 vs 线上树对齐（按钮是否真上线）
- 线上树 = 主控 `readlink -f /opt/v6/current`；同一条 `grep -n "<按钮文字>" <tree>/bot/<file>` 在两边取，**行号一致**才算按钮真在线。
- **整目录 sha 不相等 ≠ 树漂移**：部署侧文件可能是 CRLF（远端 grep 输出里会出现 `\r`），本地是 LF，整体哈希天然不同。判漂移要按行级锚点对比或先做换行归一化，别据此下「没上线」结论。

## 4. 别名表是最大的伪装
`bot/menus.py` 有旧键→新键别名表（例：`"repack:": "genpacks:"`）。老消息里的按钮仍能点，但**语义可能已被换掉、参数被丢弃**。查到别名必须顺着走到新 handler，逐行确认参数有没有真的被使用。

## 5. 写动作的开关与「只读消费者」红线
- `conf/master.ini` 的 `[bot] apply_enable`（0 ⇒ bot 只读，按钮只回执）。
- `bot/commands.py` 里写类命令的 docstring 本身就声明定位：`repackall` = 「重打包属主控侧运维动作（bot 是只读消费者，不代跑）」。
⇒ 报告必须区分「显示且真跑 / 显示但空转 / 完全不显示」三种状态；把空转说成隐藏会让用户以为只要打开开关就行。

## 6. 老正本对照（重写割接常丢的是动作，不是按钮）
- 老单体 bot 仍在主控：`/opt/v6/pix_bot_server.py`（老键、老 handler、真动作原文可整段引用）。
- 采集机上老脚本可能**还活着**（例 `/opt/v6/collect_one.py --pid <pid>` 单项目补采），能力在主控侧也在，只是没接进新 bot。
- 新架构的等价落点（把单项目粒度接回来）：ctx 名册（`paths.ctx_file`，采集机跑 `tools/gap_once.py <ctx> <shard>`）+ `master/backfill.py` 的 `build_ctx`（`{miss_names, miss_accts, stale_map}` 结构）+ `master/orch.py` 的 `push_ctx / dispatch_cmd`。**「只采一个项目」= 构造只含该 pid 的 ctx 下发**，不破 bot 只读红线。
- 结论落法：「老正本有 X、新树没做进去（按钮显示但丢参数/退化成回执）」。

## 7. 现状基线（本次割接版本，可直接引用）
- 项目卡（`bot/menus_parts8.py`）8 键：公告原文 / 复制名称 / **补采包件 `genpacks:`** / 分享 / 同名场次 / 订阅 / 收藏 / 返回。
- 4 个条件显示键：`file:`（18 列文件已生成）、`gen18:`（生成中）、`packfile:`（有包件清单）、`projents:`（有报名数）。
- bot 用户面合计 **88 个真上屏 callback / 95 个已注册前缀**，**无任何「导入」类入口**；权限差分无导入类被藏。
- 单项目补采：老正本 `repack:<pid>` 真跑（SSH 采集机 `collect_one.py --pid`）；新树 `act_genpacks`（`bot/menus_parts4.py`）丢 pid 转 `repackall`（只回执）。
- 交付件：按钮全清单 md（43 面板 × 管理员/普通用户两栏 × 88 callback）落 `out/` + 桌面，供用户按名字对照。
