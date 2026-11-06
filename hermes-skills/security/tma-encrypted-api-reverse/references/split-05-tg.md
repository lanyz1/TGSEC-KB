## TG 侧硬限制(省时间)
- **inline callback data 有完整性校验**:对某条消息发 `GetBotCallbackAnswerRequest(data=…)`,凡不在该消息键盘上的 data 一律 `DataInvalidError` → **回调参数不可伪造、ID 不可枚举**。
- bot 状态机多为**文本驱动 reply keyboard**,状态消息**原地编辑**且**每个菜单固定住在一个老 id**(如 587~600),而你自己的消息会涨到 700+ → **扫描窗口必须够大(limit≥400)且按 `edit_date` 取最新**,否则 window 只包含自己的消息,永远读成「bot 没反应」。
- ★ **不要用洪水式脚本探 bot UI**:~十几条消息就会 `FloodWait`,继续发会让 bot 对该用户**只答 `/start` 命令、彻底忽略菜单文本**(实测:`/start` 每次新建消息,菜单文本零响应,各菜单 `edit_date` 停留在触发前)→ **该号在 bot 侧的 UI 路线基本烧掉**。节奏从第一发就 ≥8-11s,且先想清楚要跑几步。
- **bot 冷却不影响 mini-app 路线**:initData 由 Telegram 铸(`RequestAppWebView`),不经过 bot 的消息处理 → 只要 token/余额另有来源,接口层攻击不被影响。
- ★ **bot 侧脚本一律用 bot 的 int id,绝不用 `@username` 字符串**:字符串走 `ResolveUsername`,而它是最先被 FloodWait 冻结的接口(实测 20.8h、解不开、重试不缩短)→ `send_message("@BOT")` 当场抛异常;**改 `get_entity(<int id>)` 走 session 内实体缓存**(实测自打印 `ent=cache`、零网络解析)⇒ 解析被罚后 bot UI 路线照样能跑(同账号同刻实测:int id 成功、字符串名失败)。
- session 崩溃后 `.session-journal` 残留会 `database is locked`:**连 journal 一起拷贝**到工作目录让 SQLite 自行回滚,勿动共享号库原件;只拷 .session 会 `MsgidDecreaseRetryError`。

