<!-- archived from /root/.hermes/skills/software-development/ai-ide-ops/SKILL.md on 2026-10-21 -->

---
name: ai-ide-ops
description: Use when configuring or debugging Cursor/Cline AI IDEs.
---

> 归档卡：原目录 `/root/.hermes/skills/software-development/ai-ide-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/software-development/ai-ide-ops/…')`，不要相对 `references/legacy/` 解析。

# AI IDE 运维(Cursor / Cline / VS Code 系)

把自备模型接进 AI IDE、修 IDE 的网络与索引故障、装扩展。
**结论先行:想用自备 key(DeepSeek 等)驱动 IDE,不要跟 IDE 自带的模型选择器死磕 ——
先确认这一层能不能接第三方模型,不行就装一个支持任意 OpenAI 兼容端点的扩展。**

## 1. 先判定:这个 IDE 能不能接第三方模型

| IDE | 能否 | 依据 |
|---|---|---|
| Cursor 3.x | **不能** | 主程序里写死模型名白名单。可自查:`grep -ohE '"(gpt-4[a-z0-9.-]*\|claude-[0-9a-z.-]+)"' /d/cursor/resources/app/out/vs/workbench/*.main.js`。发送前本地校验,不在白名单直接报 `Model name is not valid: "<name>"` |
| Cline(扩展) | **能** | API Provider 选 `OpenAI Compatible`,填 Base URL + Key + Model ID,无白名单 |

`Override OpenAI Base URL` **不是**接第三方模型的入口 —— 它只给白名单内的 OpenAI 模型换路由
(走 Azure/企业代理),模型名仍须在白名单里。**先判定能不能接,再花时间配 key**,否则失败留到最后一步。

## 2. 接模型的标准流程

1. **先验 key,再配 IDE** —— 真实调一次,别只看 key 存在:
   ```bash
   curl -s -H "Authorization: Bearer $KEY" https://api.deepseek.com/v1/models
   ```
   再发一条最小对话。**用 python 发,别在 bash 里拼中文 JSON** —— 会因编码报
   `Failed to parse the request body as JSON: ... invalid unicode code point`,看起来像 key 或接口坏,其实只是编码。
2. **参数落到本地 txt 供复制粘贴**(Base URL / key / 模型 id),**聊天里不重复粘 key**。
3. IDE 里配:Provider = `OpenAI Compatible`,Base URL 带 `/v1`,Model ID 用 key 实测返回的 id。
4. **从 IDE 自己的日志证明真打通**,别看 UI 状态(见第 4 节)。

## 3. IDE 网络故障:先查它自己的代理设置

Electron 系 IDE(Cursor 等)走 `%APPDATA%\<IDE>\User\settings.json` 里的 `http.proxy`,
**不是系统代理**。该端口失效时症状是「登录不进去 / 模型无响应 / 扩展市场打不开」——
看着像登录路径问题,实际是全部请求发进了黑洞。

```bash
grep -rh "proxy" "$APPDATA/Cursor/User/settings.json"      # 看 http.proxy 指向哪
grep -rhiE "failed to establish a socket connection to proxies" \
     "$APPDATA/Cursor/logs/"*/main.log | tail -5            # 日志里的实锤
```

修法:改成本机**实测在听的**端口,或整行删掉走直连。
**选端口要多次采样**再决定(同通道 4 次里可能挂 1 次),不要凭单次测量:

```bash
for i in 1 2 3 4; do curl -s -o /dev/null -m 10 -w "%{http_code} " \
  -x http://127.0.0.1:PORT https://api2.cursor.sh/; done
```

**别把"端口没有 LISTENING 条目"直接判成死的** —— 有些客户端只留 ESTABLISHED 照样能通。
**以实际请求返回码为准,不以内核 socket 状态为准。**

## 4. 验证一律以日志为准

```bash
LOGDIR=$(ls -dt "$APPDATA/Cursor/logs/"*/ | head -1)
grep -rhiE "buildRequestedModel|catalogModelId" "$LOGDIR" | tail -3
#   matchingSelectedModel=true 只说明本地选中了,不代表请求成功
grep -rhoiE "https://api[a-z0-9.]*\.(openai|deepseek)\.[a-z]+" "$LOGDIR" | sort -u
#   这里为空 = 请求根本没出去,base URL / 代理没生效
```

**UI 显示"已配置"与请求真正成功是两回事。**

## 5. Cursor 装扩展 + 必补的设置

```bash
export PATH="$PATH:/d/cursor/resources/app/bin"
cursor --install-extension saoudrizwan.claude-dev      # Cline
```
装完 **重启 IDE** 扩展才加载(落在 `~/.cursor/extensions/`)。

**`settings.json` 里必补**:
```json
"git.path": "D:\\Git\\mingw64\\bin\\git.exe",
"git.autofetch": false,
"files.autoSave": "afterDelay"
```
GUI 启动的 Cursor **不继承 shell 的 PATH**,找不到 git 就报
`Failed to initialize GrepClient cannot index repository without Git`,`@Codebase` 全瘫。

`extensions.json` 里 path 形如 `/c:/Users/...` 是 **URI 规范形式,不是损坏** —— 别去"修"它。

## 6. Cline 的 Windows 坑

- **快捷键全废**:package.json 里绑的是 mac 的 `cmd`(`cline.addToChat -> cmd+'`),
  Windows 没有 cmd 键。**用 `Ctrl+Shift+P` 命令面板**(命令 id 如 `cline.plusButtonClicked`)
  或点侧边栏图标(容器 id `claude-dev-ActivityBar`;看不见就让用户右键活动栏勾选)。
- **配置不可手写**:API 配置存在 IDE 的 `globalStorage/saoudrizwan.claude-dev/`(非明文)。
  该目录下只有 `settings/cline_mcp_settings.json`、没有其他东西 = **还没配过** —— 只能让用户在 UI 里填,
  你无法代写。
- 项目规则放 `.clinerules/<topic>.md`(等价 `.cursor/rules/`),Cline 自动读。
  从 mac 迁过来的项目要先改掉里面写死的旧机器路径。

## 7. 迁移过来的项目:IDE 配置里也有旧机器路径

`.cursor/mcp.json` 常写死 `/Users/<user>/...`,不改则 **IDE 启动时 MCP server 全部起不来**。
残留检查要覆盖配置文件,不只 .py/.sh:
```bash
grep -rl "/Users/\|/opt/homebrew" --include=*.json --include=*.mdc --include=*.yaml . | head
```
但别一上来就批量替换,按"会不会真被执行到"分级 —— 边缘脚本可以不管,IDE 配置必须改。

## Pitfalls

- 怀疑请求打错地方时,先找**证据**再改配置:日志里有 URL 说明请求出去了,只有本地文案
  (`Model name is not valid`)说明**根本没发出去**。两者修法完全不同。
- 用户说"找不到入口"时,先查 IDE 日志的 extension host 段确认扩展真的加载了,**再**给操作步骤。
- 用户发来的报错可能是复制串行的乱码,看不懂就问,别硬猜着改配置。
- 接入第三方模型后功能会缩水:Chat 可用,但 Tab 补全 / Agent 编排 / 语义索引通常不可用
  (那些依赖 IDE 自家模型路由)。**先把取舍说清楚再动手**。
- 用自备模型跑重度任务(多工具编排、长链路)时规则遵从度普遍低于 IDE 自带模型,
  容易停在半步不往下走;关键流程建议切回 IDE 自带模型。
