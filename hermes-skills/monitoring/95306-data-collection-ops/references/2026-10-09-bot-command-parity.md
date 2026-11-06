# bot 换版丢命令：/proj、/ent 静默无响应（根因 + 对齐审计工装）

## 症状 vs 真因
用户说「bot 的 /proj 这个功能还是不能用」。真因**不是**配置/权限/数据源，而是：

```
老 bot  /opt/v6/pix_bot_server.py:2429  elif low.startswith("/proj ") or ... "/file " ... "/search "
线上 bot /opt/v6/v6m.py bot  ← 2026-10-08 09:58 换版重写，**这些命令没被搬过来**
         且 $T/bot/commands_parts.py 的注册表**没有未知命令兜底（catch-all）**
⇒ 用户发 /proj xxx → 没有任何 matcher 命中 → 静默无响应（看起来像"坏了"）
```

**TG 侧命令菜单是坑的来源**：`getMyCommands` 读到的菜单是老 bot 用 `setMyCommands` 注册的，
换版后菜单**不会自动更新** ⇒ 菜单里挂着 `proj`🔍「项目搜索」、`ent`🏢「企业查询」等
新版根本没实现的命令，用户点菜单就必然踩空。
**换 bot 版本后第一件事：`getMyCommands` × 实际 handler 覆盖率对齐审计。**

## 对齐审计工装（已沉淀到主控 `$T/tools/`）

| 文件 | 用途 |
|---|---|
| `$T/tools/audit_bot_menu.py` | 喂任意命令清单，报每条命中第几个 handler / ❌无 handler；带豁免位 |
| `$T/tools/legacy_cmds.json` | 老 bot 命令面 31 条清单（含人工核实豁免理由） |
| `$T/tools/probe_proj_alias.py` | /proj 路由离线自证 13 例 |

用法（判据：`死命令 0 条`）：
```bash
T=$(readlink -f /opt/v6/current); cd $T
python3 tools/audit_bot_menu.py "$T"                      # TG 菜单 10 条 → 应 10/10
python3 tools/audit_bot_menu.py "$T" tools/legacy_cmds.json   # 老→新 31 条 → 应死命令 0 / 豁免 4
python3 tools/probe_proj_alias.py "$T"                     # 应 13/13 通过
```

## 修法（保持「注册序=匹配序」，不可乱插）
1. **不要**直接在 `_register` 里堆注册行 —— 会撞 `tools/struct_check.py` 的**函数 ≤50 行**棘轮。
   正解：抽成 `register_alias_cmds(self, r)`（正文 ~14 行），`_register` 里只留 1 行调用，
   **调用点必须原地不动**（注册顺序=匹配顺序，挪位会抢前缀匹配）。
2. `bot/commands.py` 的类是**逐条显式绑定**的（`_register = _P._register`）⇒ 新函数必须补一行
   `register_alias_cmds = _P.register_alias_cmds`，否则运行期 `AttributeError`。
3. `/proj`、`/file`、`/search` → `self._args(lambda c, a: self.do_search(c, a))`；
   裸命令给用法别静默：`self._simple(lambda c: self.tg.send("💡 用法：..."))`。
4. `/ent 企业名` → `self.do_ent_search(c, a)`（等价 `e 企业名`）。
5. 老命令面里**别硬映射**的：`/fav <企业名>` 老版只写 stars.json、全库无消费方=死功能，
   新版收藏是**项目级**（`star:` 回调 + `/favs`）；`/cancel`、`取消`、`算了` 由
   `bot/menus_parts2.py:65` 的**前置 pending 状态机**处理（不在 text_handlers 表里，
   审计看不到 ≠ 缺失）。

## 变更纪律（本轮踩过的坑）
- **改 bot 必须:先跑 `python3 tools/offline_bot.py` 取全绿基线（123/123），改完复跑**；
  判据 = 末行 `N/N 通过` + 「结束请求数=0」。
- **结构棘轮**：`python3 tools/struct_check.py`，要求文件 ≤400 行 / 函数 ≤50 行 / 嵌套 ≤4，
  「本次新增/变大」必须 0。
- **★ 测试桩陷阱（假阴性）**：自写审计桩若用 `__getattr__` 兜底返回 Null 对象，会把
  **缺失的方法静默吞成 no-op** —— 本轮就因此把 `register_alias_cmds` 误判为「已生效」。
  桩里凡是 `_register` 会调用的方法都要**显式绑定**（缺失即 AttributeError 报错）。
- **改完必须重启 bot 才生效**，且**每次 kill 前要获得用户明确同意**：
  启动方式 = `flock -n /tmp/v6_bot.lock` + `setsid/nohup`（**不在 systemd 下，无启动脚本**）。
  就绪判据：日志出现 `按钮层已接线：N 组回调` + `线程启动：sub/health/gaps/data/watch/packnew`，
  且 `bot_offset.json` mtime 持续前进（轮询真活着）。
- 可回滚备份：`$T/bot/commands_parts.py.bak_20261009_projalias`（原始基线）、`.bak_20261009_entalias`。

## 本轮最终状态（2026-10-09）
- 盘上最终版：`commands_parts.py` md5 `dea59ee84672`、`commands.py` md5 `ffdb769d3500`。
- 闸门：菜单 10/10、老→新 31 条死命令 0、/proj 自证 13/13、结构棘轮 0 违规、离线回归 123/123。
- 线上进程 17:01:55 那版**只含 /proj**；`/ent`+裸词 `ai` 需再重启一次才生效。
