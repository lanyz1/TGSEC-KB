# 搜索「只能看不能点」修复 + 离线夹具的两个静默洞(2026-10-07)

## 一、报障定性:多命中走纯文本 ⇒ 按钮「没做进去」

用户报「搜索出来的项目只能看、无法点击、无法挑选」。根因 = `bot/commands_parts.py::do_search` 三分支里,**命中 ≥2 条那一支只发 `rd.render_mb(...)` 纯文本(无 keyboard)**,单命中直接开项目卡、菜单「筛选」走 `show_list`(有按钮)⇒ 只有多命中这一支没接线。

- **修法(最小改动 + 复用已审计路径)**:多命中行改
  `self.tg.send(self.rd.render_mb("搜索 · %s" % kw, rows), cid, keyboard={"inline_keyboard": _search_kb(rows)})`;
  新增 `_search_kb(rows)`:每条命中一行按钮 → `callback_data = proj:<pid>`,文案经 `bot/menus_util._d`。
- ★**`tg.send` 的 `keyboard=` 必须自带 `inline_keyboard` 外层**(`_send_once` 直接 `json.dumps` 整个 markup,少一层就是无声失败)。
- ★**一处修覆盖两入口**:`s 关键词` 与菜单搜索共用 `do_search` ⇒ 别去改两处。
- 通用判据:**「出来能看不能点」= 该分支调的是渲染器而不是带 keyboard 的发送器**;grep 按 `render_mb(` 找纯文本出口 (`show_list`/`page_out`) 才是对的方向。

## 二、真池真码验证(必做,不能只靠夹具)

夹具断言只覆盖 callback 存在性,**抓不到「文案退化成 UUID」**这类静默洞。固化探针(只读:不连 TG、不写池):

```python
from conf import Conf; from pool import Pool      # 类名照抄树内模块,别猜
p = Pool(Conf("/opt/v6/lib/<rel>/conf/master.ini"))
rows = p.search_projects(kw, limit=10)             # 真 API 名,读活代码确认
kb = _search_kb(rows)                              # 活树里的 helper
print([b[0]["text"] for b in kb], [b[0]["callback_data"] for b in kb])
```

- ★**API 名别猜**:本轮先写 `pool.search` ⇒ `Pool has no search`;读活代码 (`bot/commands_parts.py:253` 起) 才确认真 API = **`search_projects(kw, limit)`**。规矩仍旧:**池探针先列方法表 / 照抄既有探针再动手**。
- ★**按钮文案的键必须与真池返回对账**:`_search_kb` 读 `info.get("projName")` ⇒ 核对 `pool.py` 装载 info 时用的键名(实测 = `projName` ✓)。若真池给 `name`,按钮会静默显示 UUID 而夹具全绿。**⇒ 夹具断言必须同时断「文案来源键」,不只断 callback。**
- 本轮真池结论:5 个真实关键词全部 ≥10 条命中(上限 10 ⇒ 多条是常态,正是用户遇到的场景),按钮 = 真实项目名(截 30 字) + `proj:<真UUID>`,行数 = 命中数 + 1(主菜单出口)。

## 三、结构闸对 `tools/` 同样生效(加断言会顶穿上限)

给夹具加断言后:`struct_check` 报 `tools/offline_bot.py::main_p2` >50 行、**该文件 403 行 >400**。

- **修法 = 抽 helper 到已存在的兄弟模块**(`tools/offline_bot_parts.py`,用 `_bind(orig)` 注入模式),两 helper 走**显式传 `chk` 参数**、**不反向 import**;宿主加
  `try: from offline_bot_parts import … except ImportError: from tools.offline_bot_parts import …` 兼容两种跑法。结果 403→388 行,棘轮「新增/变大 = 0」。
- 改完仍要过全套:`offline_{run,cli,master,bot,ui,repack}` + `struct_check` + `bind_audit` + `compileall`。

## 四、bot「真活着」的验收(比看 pid 强)

重启后同时满足才算活:① `ps -o stat,nlwp` = `Sl` + 6 线程;② **`ss -tnp` 持留 `ESTAB → 149.154.166.110:443`(TG DC 长轮询 fd)**;③ 日志静默 75s 不增长(长轮询零 CPU 属正常);④ 尾段 `conflict|409|terminated by other` = 0。

- ★**启动横幅重复 ≠ 崩溃循环**:本轮尾部出现 4 组 `[bot] 按钮层已接线` / `[bot] 线程启动`,紧邻其上是一串 `[TG-ERR] HTTP Error 502 / read timed out` ⇒ 属**启动期网络失败后的应用内重试**(判据:同 pid + ESTAB 持留 + 日志不再增长)。真崩溃循环会换 pid 且日志持续增长。
- 日志里的历史 `Traceback` 要**读路径判归属**:本轮那条 `AttributeError: 'Router' object has no attribute 'poll'` 出自 **旧树 `/opt/v6/lib/v6rel_20261004k/bot/main.py`** ⇒ 历史残留,与当次改动无关。

## 五、本轮发布批次(可对照)

`v6rel_202610070943`(tar sha256 `4016e40eab…`,tree_hash `e02e5e8f5e17a99d`);相对上一版 `0924` **仅 3 个文件**(生产码只有 `bot/commands_parts.py`)。12 台 stage 12/12 + activate 12/12、主控 `--stage` → `--activate --yes`、bot 手动停+起(取原进程环境)。
