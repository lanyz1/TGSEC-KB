# Cursor 扩展装上了却用不了:按这个顺序查

**铁则:先查禁用列表,再查其它。** 本次排查绕了 webview→代理→缓存一大圈,
最后发现根因只是扩展被禁用了。

## 排查顺序(从快到慢)

### 1. 扩展是否在「禁用列表」里 ⭐ 先查这个

Cursor 把扩展启用状态存在 SQLite 里,不是明文配置:

```python
import sqlite3, json
p = r'C:\Users\&lt;用户&gt;\AppData\Roaming\Cursor\User\globalStorage\state.vscdb'
con = sqlite3.connect(p)
r = con.execute("SELECT value FROM ItemTable WHERE key='extensionsIdentifiers/disabled'").fetchone()
print([x['id'] for x in json.loads(r[0])] if r else '无禁用项')
```

修复(移除条目,改前先 `shutil.copy2` 备份 `.vscdb`):

```python
new = [x for x in json.loads(r[0]) if x['id'] != '&lt;扩展ID&gt;']
con.execute("UPDATE ItemTable SET value=? WHERE key='extensionsIdentifiers/disabled'", (json.dumps(new),))
con.commit()
```

> `cursor --list-extensions` 只证明"装了",**不证明"启用了"**。
> `cursor --enable-extension` 不存在(Cursor 没这个参数,会报 not in known options)。

### 2. 扩展状态存不进去(文件只读)

症状:日志 `EPERM ... rename 'storage.json.vsctmp' -> 'storage.json'`

```bash
ls -la "%APPDATA%/Cursor/User/globalStorage/storage.json"   # -r--r--r-- = 只读
attrib -R "C:\...\globalStorage\storage.json"
rm -f ".../storage.json.vsctmp"
```

**判断修好了**:重启 Cursor 后该文件**时间戳会更新到当前**。时间戳长期不动 = 一直在写失败。

### 3. 命令面板"没反应"

- 命令面板按**标题**索引,**不认内部 ID**(`&gt;cline.plusButtonClicked` 搜不到)
- 扩展没定义 category 时标题**不带前缀**(是 `New Task`,不是 `Cline: New Task`)
- 输入 `&gt;&gt;xxx`(两个尖括号)会当字面量搜
- 同类命令要分清:`New Task`(插件) vs `Tasks: xxx`(VS Code 任务系统,点了报 not found)

### 4. webview 报 Service Worker 错误

```
Error loading webview: Could not register service worker: InvalidStateError
```

先清缓存(Cursor 完全关闭时):

```bash
cd "%APPDATA%/Cursor"
rm -rf "Service Worker" GPUCache Cache "Code Cache" DawnGraphiteCache DawnWebGPUCache
```

还不行 → 查代理(见下)。

### 5. Cursor 的代理层卡死一切

症状(webview / 扩展 / 模型请求全挂):

```
Failed to establish a socket connection to proxies: PROXY 127.0.0.1:XXXX
```

**注意**:即使 `curl -x 该代理` 是通的,Cursor 内部的 `@vscode/proxy-agent`
仍可能连不上。别在这里和我一样反复验证代理通不通。

**解决**:直接绕开代理层(前提:目标域名直连可达,先 `curl --noproxy '*'` 验证):

```json
"http.useLocalProxyConfiguration": false
```

> 这个设置是 Cursor 专有的(在 `resources/app/out/vs/workbench/workbench.glass.main.js` 里可查到)。

### 6. git 找不到(影响 @Codebase 检索)

GUI 启动的 Cursor PATH 里没有 git:

```json
"git.path": "D:\\Git\\mingw64\\bin\\git.exe"
```

路径用 `cygpath -w $(which git)` 取。

## 给 Cursor 接第三方模型(如 DeepSeek)

**Cursor 自带 Chat 接不了**:模型名有硬编码白名单(在 `workbench.glass.main.js` 里,
只有 claude-*/gpt-*/gemini-*),自定义 base URL 只能给白名单内的模型换路由,
填别的模型名会报 `Model name is not valid`。

**可行路径**:装 **Cline** 插件(或 Roo Code),它支持任意 OpenAI 兼容端点:

```bash
cursor --install-extension saoudrizwan.claude-dev
```

| Cline 字段 | DeepSeek 值 |
|---|---|
| API Provider | OpenAI Compatible |
| Base URL | `https://api.deepseek.com/v1` |
| Model ID | `deepseek-v4-pro` / `deepseek-flash` |

规则用 `.clinerules/*.md` 自动加载(不要用 Cursor 的 `.cursor/rules`,
那是给 Cursor 自带模型的)。

## 日志位置

```
%APPDATA%\Cursor\logs\<时间戳>\main.log        ← 扩展宿主/代理/webview 报错
%APPDATA%\Cursor\logs\<时间戳>\window1\exthost.log  ← 单个扩展的输出
```

排查时 `grep -rhiE "\[error\]" <最新日志目录>` 一把捞出所有错误。
