# ToDesk 远控驱动（无 computer_use 工具时的 PowerShell 方案）

场景：用户说"帮我看朋友电脑 / 我把他电脑的 ToDesk 发你"。当本机 ToDesk 已连上目标机时，用 PowerShell 输入合成 + 截图 + vision 循环驱动远程桌面。前提：ToDesk 窗口在主屏可见、用户同意接管鼠标键盘（路线 B；路线 A = cua-driver 装好后 `/reset` 用 computer_use 工具，见 hermes-agent 技能）。

## 关键事实

- **ToDesk 主窗口标题 = 远程电脑名**。本机 `hostname` ≠ 窗口标题时 = 正处于远程会话中（如本机 DESKTOP-MGAFFC3，窗口标题 Windows-R4P7U7）。
- ToDesk 窗口类 `H-SMILE-FRAME`（自定义渲染），**UIA 树无可用元素**——元素级点击不可行，只能坐标点击（截图→vision 读坐标→SetCursorPos+mouse_event）。
- **剪贴板默认共享**：本机 `Set-Clipboard` → 远程窗口 Ctrl+V 即粘贴。这是传长命令/API key 的最稳方式（SendKeys 里 `{} % ^ + ()` 全是特殊字符，命令带括号/引号必翻车）。
- 输入法坑：远程打字前确保英文输入法（任务栏"中"→按 Shift 变"英"），否则打出的字母变拼音候选，回车无效。
- SendKeys 不支持 Win 键：用 `^{ESC}`（等效 Ctrl+Esc 开开始菜单）→ 输入应用名 → **用鼠标点搜索结果**（回车焦点易丢，点了没反应）。
- `Test-NetConnection` 对未开端口很慢，别用它探测端口列表；用 `netstat -ano | findstr <port>` 或 curl。

## 打开远程 PowerShell 的可靠流程

1. `foreground`（SetForegroundWindow ToDesk 句柄）→ `key ^{ESC}` → `type powershell` → `shot`
2. vision 读搜索面板里 "Windows PowerShell" 结果坐标 → `click X,Y`（窗口相对坐标）
3. `shot` 确认黑色终端出现 → 之后本机 Set-Clipboard 命令 + 远程 Ctrl+V + Enter，循环执行诊断

## 边界（重要）

- 远程 GUI 盲驱动又慢又脆（截图→vision→点击每步 5-15s），适合少量短命令；长流程直接放弃。
- **用户一旦说"不要远程了，直接告诉我，我来搞" → 立即停止远程驱动**，切换为编号复制粘贴命令交给目标机执行（见本技能 Delegate-and-Execute 规则 9）。不争论、不把当前步做完。
- 用户说"不是我的电脑，别搞错"时：所有操作先分清本机 vs 远程机，别在本机跑给远程准备的命令。
- 驱动脚本 `scripts/todesk_ctl.ps1`：actions = foreground / click X,Y（窗口相对）/ clickabs / type / key / shot / winrect。
