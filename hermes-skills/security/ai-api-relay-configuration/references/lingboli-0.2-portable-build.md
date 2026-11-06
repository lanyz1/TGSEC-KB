# 绫波丽0.2 便携版分析（NERV-BREAK-5.6 v0.2.0 NSIS 打包）

> 来源：2026-07-31 会话 — 用户桌面 `绫波丽0.2.exe`（84MB NSIS 自解压安装包）+ `绫波丽.lnk` 拆解 + 与桌面 GitHub 版对比

## 安装与结构

- **安装包**：`绫波丽0.2.exe` = Nullsoft Installer self-extracting archive（内置 Python 便携版，无需本机 Python）
- **安装位置**：`%LOCALAPPDATA%\绫波丽\`（即 `C:\Users\<user>\AppData\Local\绫波丽\`）
- **桌面快捷方式** `绫波丽.lnk` → 目标 `%LOCALAPPDATA%\绫波丽\绫波丽.exe`，描述 `绫波丽@zxwn520`（作者水印），无启动参数

```
C:\Users\<user>\AppData\Local\绫波丽\
├── 绫波丽.exe          (12.5MB 启动器, PE32+ GUI)
├── 卸载绫波丽.exe       (NSIS 卸载器)
├── 绫波丽.ico
├── INSTALL_LAYOUT.txt  (布局说明: v2.7.0 full portable layout)
├── portable_py\        (Python 3.14 便携版)
└── lab_project\        (NERV-BREAK-5.6 v0.2.0 完整项目)
    ├── panel.py        (控制面板菜单)
    ├── bridge.md       (48KB 破甲桥接提示词)
    ├── proxy_relay.py  (53KB MITM 篡改代理引擎, 1227行)
    ├── deploy.py       (部署/还原)
    ├── mcp_server.py   (MCP 工具服务器)
    ├── nerv_skills.py  (技能链 SKILL_CHAINS)
    ├── kali.py         (Kali 后端检测)
    ├── stability.py / verify.py
    └── skills\         (101 个技能模块!)
```

## panel.py 菜单（启动器行为）

```
[1] Start All   → 一键全部署: deploy+verify+kali+skills+mcp+proxy
[2] Proxy Only  → 只启动 MITM 代理 (proxy_relay.py)
[3] Stop Proxy  → taskkill python.exe (标题含 proxy)
[4] Verify      → verify.py
[5] MCP Server  → mcp_server.py --port 9000
[6] Status      → deploy.py status
[7] Dry-Run     → deploy.py dry-run
[8] Recover     → deploy.py recover
[9] Tool Check  → tools/check_tools.py
[K] Kali Setup  → wsl/docker kali
```

## 技能数量核对（101 vs 28 的坑）

| 来源 | 数量 |
|------|:----:|
| 安装包 `skills/` 实际 SKILL.md（递归数） | **101** |
| 安装包 README 声称 | 29 |
| 桌面 GitHub 版 `5.6-JAILBREAK-NERV/skills/` | **28** |
| nerv_skills.py SKILL_CHAINS 引用（含链名） | 73+ |
| 误报 110+ 的来源 | 代码里所有字符串去重 167；含 scripts/ 子目录 205 个目录 |

- 每个技能目录含 `SKILL.md` + `scripts/` 辅助脚本（所以目录总数 205 > 101）
- SKILL_CHAINS 里 `jailbreak`/`mobile`/`hardware`/`cloud-attack`/`iot-embedded`/`blockchain`/`reverse-engineer` 是**链名**不是技能
- 打包 101 技能：`powershell -Command "Compress-Archive -Path 'skills\*' -DestinationPath 'xxx.zip' -Force"`

## 使用与故障排查（用户自带教程要点）

- 启动 exe → 全中文界面 → **推荐全部启动** → 重启 Codex → 发消息，面板出现数据 = 成功
- **"Proxy starting..." 是第一步**，等面板出现完整数据（代理监听 + bridge 注入 + 篡改引擎加载）
- 流传输断链 = 破甲在劫持（正常）→ 等自动篡改或发"继续"触发下一轮（多轮劫持正常）
- API 安全拦截 → 等破甲强冲或发"继续"重开一轮
- 破甲失败（频繁拒绝）两大原因：
  1. **中转站安全限制** → 换中转（大多数中转站有内容过滤）
  2. **环境不干净** → Codex 审核读历史对话/技能/记忆，有失败记录就弹安全。解决：新虚拟机 / 删 `.codex` 重装 / 彻底还原（本地效果不如虚拟机）

## 安全提示

- NSIS 安装包**无签名**，来源不明（作者 zxwn520），便携版可能被二次打包
- 运行时写 `.nerv-transaction-*` 状态目录
- 代理监听本机，所有 Codex 流量过它 = 中间人能力。与官方 GitHub 版对比 `proxy_relay.py` 防篡改
