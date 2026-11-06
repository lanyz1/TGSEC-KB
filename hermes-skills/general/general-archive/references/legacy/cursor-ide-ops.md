<!-- archived from /root/.hermes/skills/autonomous-ai-agents/cursor-ide-ops/SKILL.md on 2026-10-21 -->

---
name: cursor-ide-ops
description: Configure and troubleshoot Cursor IDE for agentic work.
---

> 归档卡：原目录 `/root/.hermes/skills/autonomous-ai-agents/cursor-ide-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/autonomous-ai-agents/cursor-ide-ops/…')`，不要相对 `references/legacy/` 解析。

# Cursor 配置与排障

**定位**:让 Cursor 能通网、能调模型、能索引项目,从而驱动一个作业仓库。
管的是**接通与配置**;作业内容本身在各项目自己的 `.cursor/rules` 与 `AGENTS.md` 里。

## 铁则(先读这两条,它们决定你怎么排查)

### 铁则 1|用户说「找不到界面元素」超过一次 → 立刻截图看屏幕

不要继续用文字描述「在左下角找一下」。用 `computer_use` 的 `capture` 看真实界面;
先用 `Get-Process <App> | Select MainWindowTitle` 确认窗口是否真开着。

**用户找不到 ≠ 用户的问题** —— 多半是版本界面和你记忆里的不一样。
浪费的形态:连着三轮描述位置,用户连着三次「还是没有」。第二次「没有」就该截图。

### 铁则 2|下「不可能 / 不支持」结论前,先证明报错是谁发的

```bash
grep -c "<报错原文>" "<Cursor安装>/resources/app/out/vs/workbench/workbench.glass.main.js"
```

- 客户端**搜得到** → 本地校验,可绕过
- 客户端**搜不到** → **服务端返回**,结论才站得住

同类误判:判「某工具在 Windows 装不上」前,先排除**路径格式**这类低级原因
(`pip` / 原生 exe 不认 git-bash 的 `/d/...`,必须写 `D:/...`)。
过早下「不可能」,代价是用户在错路上多等好几轮。

## 0. 路径速查(排障先认路)

| 东西 | 位置 |
|---|---|
| 用户设置(proxy / git.path 都在这) | `%APPDATA%\Cursor\User\settings.json` |
| 工作区设置(多为 watcher/search 排除) | `<项目>\.vscode\settings.json` |
| **日志(排障第一现场)** | `%APPDATA%\Cursor\logs\<时间戳>\` |
| CLI | `<Cursor安装>\resources\app\bin\cursor` → 可直接 `cursor .` 开项目 |
| 项目规则 | `<项目>\.cursor\rules\*.mdc`(带 `alwaysApply: true` 的会被自动加载) |
| MCP 配置 | `<项目>\.cursor\mcp.json` |

## 1. 「登录不上 / Failed to fetch」→ 先查代理,别猜登录流程

**症状**:登录页转圈、`Failed to fetch`、模型调不动、插件市场装不上、`Failed to auto-install ... Failed to fetch`。

**机制**:Cursor 是 Electron,**网络全走代理**;代理来自**应用自己的 settings**,与 Windows 系统代理是两套。
所以「浏览器能上网」不代表 Cursor 能上网。

```bash
# a) 读应用自己的代理配置
 grep -i proxy "$APPDATA/Cursor/User/settings.json"
# b) 该端口到底有没有人监听
 netstat -ano | grep ":<port>"
# c) 日志里找真凶(最可靠,直接点名)
 grep -rhiE "proxies|Failed to fetch|ECONN|ENOTFOUND" "$APPDATA/Cursor/logs/" | tail -20
```

日志出现这句就是结论 —— **代理端口是死的**(旧代理工具留下的残值):
```
Failed to establish a socket connection to proxies: PROXY 127.0.0.1:<port>
```

处置:把 `http.proxy` 改成**实测可用**的代理,或整行删掉走直连。

**选代理要连测多次再定** —— 代理节点会抖动,单次 200 不能说明问题:
```bash
for i in 1 2 3 4; do curl -s -o /dev/null -m 10 -x http://127.0.0.1:<port> \
  -w "%{http_code} " https://api2.cursor.sh/; done
```
挑 4/4 全通的那个;同时**对比直连**(`curl --noproxy '*'`),常出现「直连慢但稳定、代理快但偶发超时」。

**改完必须重启 Cursor** —— settings.json 不热加载,在旧进程里反复试是白费。

## 2. 接自定义模型(DeepSeek 或任何 OpenAI 兼容端点)

Cursor 没有「自定义 provider」入口,但留了 Base URL 覆盖的口子。
Settings(`Ctrl+Shift+J`)→ **Models**:

1. 填 **OpenAI API Key**(填目标服务商的 key,不是 OpenAI 的)
2. **打开 `Override OpenAI Base URL`** → 填对方的 OpenAI 兼容端点(形如 `https://<服务商>/v1`)
3. **`+ Add model`** 逐个添加模型名 —— 名字必须与服务商 `/v1/models` 返回的完全一致
4. **关掉其它 OpenAI 模型**(GPT-4o / o1 / o3 / gpt-5 全关)

> 第 4 步最容易漏,不关就会拿新 key 去请求 OpenAI 官方模型名 → 必报错。

**先去命令行验证 key 与模型名,再点界面** —— 省得在 UI 里猜:
```bash
curl -s -H "Authorization: Bearer $KEY" https://<端点>/v1/models
```
用 python 的 `json.dumps` 构造 body 发一条最小对话请求(直接在 bash 里拼带中文的 JSON 会被编码搞坏,报
`invalid unicode code point`,那不是 key 的问题)。

**备选**:服务商若同时提供 Anthropic 兼容端点(如 `…/anthropic`),可走 Anthropic 那一栏,同样靠 Override Base URL。

**自定义模型的可用范围(按报错判)**:

| 报错 | 含义 | 出路 |
|---|---|---|
| `Named models unavailable` | Agent / Composer 只认 Cursor 目录内的命名模型 | 改用 Chat,或切回自带模型 |
| `Model name is not valid` | **服务端**不认这个模型名(该字符串在客户端代码里搜不到) | 这条路不通 → 走插件 |

两者都意味着:**别把多文件自动编排寄托在自定义模型上。**

**插件备选(自定义模型被服务端挡住时的可靠路径)**:装 **Cline**
(`<Cursor安装>/resources/app/bin/cursor --install-extension saoudrizwan.claude-dev`) ——
支持任意 OpenAI 兼容端点,且带真正的 Agent 能力(能读写文件 + 跑终端命令)。
首次引导选 **Bring my own API key**;规则放 **`.clinerules/*.md`**
(**不要**指望它读 `.cursor/rules/`,那是给 Cursor 自带模型的)。
注意 Cline 的**快捷键绑定写的是 mac 的 `cmd`**,Windows 上失效 —— 只能用命令面板或点图标。

两种入口可以并存(`.cursor/rules/` 与 `.clinerules/` 互不干扰)。分工:
自带模型规则遵从度高 → 正式作业;插件+便宜模型不限量 → 日常问答与只读侦察。

换 key、端点验证、两端分工的细节 → `references/third-party-model-wiring.md`

## 3. Git 索引 / @Codebase 失效

**症状**:`Failed to initialize GrepClient cannot index repository without Git`、`Error getting repo info: Failed to execute git`、`@Codebase` 搜不到东西。

**机制**:**从 GUI 启动的应用,其 PATH 常常不含 git**,即使命令行里 `git` 好好的。
在 settings.json 写死路径:
```json
"git.path": "D:\\Git\\mingw64\\bin\\git.exe",
"git.autofetch": false,
"git.ignoreLimitWarning": true
```
(路径用自己的:先 `cygpath -w $(command -v git)` 拿到真实 Windows 路径再填)

顺带配 autoSave,让 agent 改完的文件立刻落盘,便于外部脚本/校验读到:
```json
"files.autoSave": "afterDelay",
"files.autoSaveDelay": 2000
```

## 4. 打开超大目录项目(几万~几十万文件)

**先在 `.vscode/settings.json` 配排除,再打开** —— 否则 watcher 与索引会卡死/吃满内存。

```json
"files.watcherExclude": {
  "**/exports/**": true, "**/node_modules/**": true,
  "**/.git/objects/**": true, "**/__pycache__/**": true, "**/.venv/**": true
},
"search.exclude": { "**/exports/**": true, "**/node_modules/**": true, "**/.venv": true }
```

项目若自带这份配置就沿用,不要覆盖。排除的是**索引**,不删文件,不影响命令行工具读它们。

## 5. MCP 起不来

`.cursor/mcp.json` 里的 `command` / `args` 常写死原机器的绝对路径 —— 换机器后**先核对路径存在**,再动别的。
启动脚本依赖的东西(API key 环境变量、Docker、原生 binary)缺一个就起不来。
**MCP 起不来不影响主体使用**:技能卡、规则、终端照样跑 —— 告诉用户这点,别让他以为整个 IDE 废了。

## 6. 扩展装了却不生效(命令不注册 / 面板打不开 / 点了没反应)

**按这个顺序查——不要先翻 webview 和代理**,本类问题九成出在前两条:

| # | 查什么 | 判据 / 处置 |
|---|---|---|
| 1 | **扩展禁用列表**(存在 SQLite,不是明文配置)⭐ | 命令不注册、面板打不开、点了没反应 |
| 2 | 扩展状态写不进去(`storage.json` 只读) | 日志 `EPERM ... rename 'storage.json.vsctmp'` |
| 3 | **Cursor 3.x 拆成两套窗口** | 图标是有的,只是不在你当前那套壳里 |
| 4 | 命令面板搜法不对 | 它按**标题**索引,**不认内部 ID** |
| 5 | webview Service Worker 报错 | `Could not register service worker` → 清缓存 |
| 6 | 代理层(见 §1) | `Failed to establish a socket connection to proxies` |

关键判据:

- `--list-extensions` 只证明**装了**,**不证明启用了**;`--enable-extension` 在 Cursor 上
  不存在(Warning 后忽略)→ 只能改数据库
- **对照法**:某扩展**在日志里完全没出现** = 根本没被加载 → 去查禁用列表;
  出现了但报错 = 加载了但初始化失败 → 去查它报的那条
- 改 SQLite / 清缓存 / 改 settings **一律先完全关闭应用**,改完必须重启才生效

**完整命令、SQLite 键名、缓存目录清单、两套窗口的辨认 → `references/extension-not-working.md`**

## 7. 无害噪音(知道就行,别去修)

- `Failed to patch code.sh launcher: ENOENT ... resources\app\bin\code` —— 包里只有 `cursor` / `cursor.cmd`,缺 `code` 属正常
- `No browser view available`
- `punycode module is deprecated` (DEP0040)
- `Extension Host` 的各类 Canceled

## Pitfalls

- **代理死端口的症状和「登录流程有问题」一模一样** → 先读日志再动手。日志里的 `PROXY 127.0.0.1:<port>` 已经把元凶点名了,不要从登录方式(user/password、OAuth、SSO)开始排查
- **改任何应用配置前先备份**:`settings.json.bak_<时间戳>`,写错了能一键回滚
- **改完 settings.json 一定要重启应用**才能在下次确认,别在旧进程里反复试并据此下结论
- 用户描述故障时给的字符串/短句可能是复制串行或误粘 → **不要硬猜它的含义**,先按日志里的真实错误定位;需要澄清就直说看不懂
- `.cursor/mcp.json` 与其它配置里的原机器绝对路径是「换机残留」的重灾区 —— **照搬项目时优先扫一遍 `.cursor/` 和 `.vscode/`**
