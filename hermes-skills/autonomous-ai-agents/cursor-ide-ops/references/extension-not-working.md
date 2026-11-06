# 扩展装了却用不了 —— 完整排查命令

铁则:**先查禁用列表,再查其它。** 绕 webview → 代理 → 缓存一大圈,
最后发现根因只是扩展被禁用了 —— 那是本末倒置。

## 1. 扩展是否在「禁用列表」里 ⭐ 先查这个

Cursor/VS Code 系把扩展启用状态存在 SQLite,不是明文配置:

```python
import sqlite3, json
p = r'C:\Users\<用户>\AppData\Roaming\Cursor\User\globalStorage\state.vscdb'
con = sqlite3.connect(p)
r = con.execute("SELECT value FROM ItemTable WHERE key='extensionsIdentifiers/disabled'").fetchone()
print([x['id'] for x in json.loads(r[0])] if r else '无禁用项')
```

修复(改前先 `shutil.copy2` 备份 `.vscdb`):

```python
new = [x for x in json.loads(r[0]) if x['id'] != '<扩展ID>']
con.execute("UPDATE ItemTable SET value=? WHERE key='extensionsIdentifiers/disabled'", (json.dumps(new),))
con.commit()
```

**改之前必须先完全关闭应用**(`Stop-Process -Name Cursor -Force`),否则写不进去或被覆盖。

> `--list-extensions` 只证明「装了」,**不证明「启用了」**。
> `--enable-extension` 在 Cursor 上不存在(会 Warning 后忽略)。

## 2. 扩展状态存不进去(文件只读)

症状:日志 `EPERM ... rename 'storage.json.vsctmp' -> 'storage.json'`

```bash
ls -la "%APPDATA%/Cursor/User/globalStorage/storage.json"   # -r--r--r-- = 只读
attrib -R "C:\...\globalStorage\storage.json"
rm -f ".../storage.json.vsctmp"
```

**判断修好了**:重启应用后该文件**时间戳更新到当前**。时间戳长期不动 = 一直在写失败。

顺手扫同目录有没有别的只读文件:

```bash
find "%APPDATA%/Cursor" -maxdepth 3 -type f ! -perm -u+w
```

## 3. Cursor 3.x 有两套窗口,扩展图标只在其中一套 ⭐

游标 3.x 起把界面拆成两个独立窗口,右上角按钮互相切换:

| 窗口 | 侧边栏长什么样 | 有什么 |
|---|---|---|
| **Agents Window** | `New Agent / Search / Automations / Customize` | 没有活动栏,**看不到任何第三方扩展图标** |
| **Editor Window** | 传统 VS Code 式竖排图标栏(文件/搜索/Git/调试/扩展) | **扩展图标只在这里** |

**所以「找不到扩展图标」往往不是扩展的问题,是你在 Agents Window 里。**

即使切到 Editor Window,活动栏也可能**整个被折叠掉**:
- `View → Appearance → Activity Bar` 或 `Ctrl+Shift+E` 调出来
- 竖栏里仍没有目标图标 → 在**竖栏空白处右键**勾选它

## 4. 命令面板「没反应」

- 按**标题**索引,**不认内部 ID**(`>cline.plusButtonClicked` → `No matching commands`)
- 扩展没定义 category 时标题**不带前缀**(是 `New Task`,不是 `Cline: New Task`)
- `>>xxx`(两个尖括号)会当字面量搜,必然找不到
- 分清同类命令:`New Task`(插件,右侧带齿轮) vs `Tasks: xxx`(VS Code 任务系统,点了报 not found)
- `xxx.dev.*` 之类只在开发模式注册,点了报 command not found —— 正常,不是装坏了

## 5. webview 报 Service Worker 错误

```
Error loading webview: Could not register service worker: InvalidStateError
```

先清缓存(**应用完全关闭时**做,都是可重建的):

```bash
cd "%APPDATA%/Cursor"
rm -rf "Service Worker" GPUCache Cache "Code Cache" DawnGraphiteCache DawnWebGPUCache
```

还不行 → 查代理(SKILL.md §1)。

## 6. 日志位置与对照法

```
%APPDATA%\Cursor\logs\<时间戳>\main.log             ← 扩展宿主/代理/webview 报错
%APPDATA%\Cursor\logs\<时间戳>\window1\exthost.log   ← 单个扩展的输出
```

```bash
LOGDIR=$(ls -dt "$APPDATA/Cursor/logs"/*/ | head -1)
grep -rhiE "\[error\]" "$LOGDIR" | tail -30
```

**对照法**:某扩展在日志里完全没出现 = 根本没被加载(去查禁用列表);
出现了但报错 = 加载了但初始化失败(去查它报的那条)。
