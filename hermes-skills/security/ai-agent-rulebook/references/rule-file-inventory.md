# 规则文件全量清单(2026-08-04 实测)

> 21 个文件,共 ~191KB,合并为 4 类。同一份规则常有新旧多版本残留。

## A 类:身份/沟通/全局(进 soul.md)

| 路径 | 大小 | 内容 |
|---|---|---|
| `~/.codex/AGENTS.md` | 256B | 语言跟随用户、直接彻底、暗号:check→ready、zxwn→"我在,我一直都在" |
| `~/.claude/CLAUDE.md` | 146B | 仅 keysmith import 块(引用下面文件) |
| `~/.claude/keysmith/claude-project-rules.md` | 531B | 中性规则:先读文档再改码、小步可审查、不存凭证 |

## B 类:业务项目规则(进 soul.md 分节)

| 路径 | 大小 | 内容 |
|---|---|---|
| `D:\Codex\qavlixor-marketplace\CLAUDE.md` | 2.1KB | 强制操作日志、中文UI、USDT结算 |
| `D:\Codex\qavlixor-marketplace\docs\ops-log\README.md` | 2.8KB | 操作日志规范(一天一文件、备份文件名、敏感值只写键名) |
| `D:\Codex\qavlixor-marketplace\docs\06-ai-collaboration.md` | 2.3KB | Codex 主执行/Claude 评审、禁双AI同编同文件 |
| `D:\Codex\qavlixor-marketplace\docs\编码规则.md` | 4.1KB | 订单号19位/单据号SV·AS·DP·WD·WR·PD/PAY-/PI+UUID |

## C 类:破解/渗透/CTF 模式文件(8 个,内容重叠,需合并提炼)

| 路径 | 大小 | 定位 | 去重备注 |
|---|---|---|---|
| `~/.codex/red-lab.md` | 2.6KB | 红队实验室:不拒绝+破解工作流 | ≈AGENTS.override-2691B |
| `~/.codex/crack-lab.md` | 1.8KB | 逆向破解:侦察→定位→干掉校验→验证 | 工作流最具体 |
| `~/.codex/ctf-sandbox.md` | 6.6KB | CTF沙箱:证据规则+方法论 | C 类最完整 |
| `~/.codex/sandbox-bootstrap.md` | 2.9KB | 启动器:拒绝=错误答案+覆写协议 | |
| `~/.codex/system-prompt-v2.md` | 2.6KB | CTF 上下文 6 条指令 | |
| `~/.codex/vernacular-direct-v4.md` | 19KB | 白话直给:自维持协议+禁用词表 | ≈vernacular-v4 |
| `~/.codex/vernacular-v4.md` | 19KB | 同上副本 | ⚠️ 与 direct-v4 几乎完全重复 |
| `~/.codex/bridge.md` | 45KB | NERV-BREAK 完整操作手册 | 最大,含工具库+证据规则 |

核心共识(8 份共同点):授权沙箱+不拒绝+中文回复+完整代码+拒绝覆写协议。

## D 类:项目专属工程规则(不进全局 soul.md)

| 路径 | 大小 | 内容 |
|---|---|---|
| `~/.codex/AGENTS.override.md.bak_20260710_012354` | 2.0KB | UNRESTRICTED 模式(旧版,已被 red-lab 取代) |
| `~/.codex/AGENTS.override.md.bak_20260712_125032` | 2.7KB | RED LAB 版(≈red-lab.md) |
| `~/.codex/config.toml` | 5.7KB | Codex 配置,非规则文件 |
| `D:\cc-pane\AGENTS.md` | 12.7KB | CC-Panes 代码库指南 |
| `D:\cc-pane\CLAUDE.md` | 28.8KB | CC-Panes 项目规则 |
| `D:\cc-pane\src-tauri\CLAUDE.md` | 0.1KB | 忽略 |
| `D:\Codex\touliu\CLAUDE.md` | 3.8KB | Forge v2 L0-L4 分级路由(单项目) |
| `D:\CTF\juice-shop_20.1.1\AGENTS.md` | 10.5KB | 靶场项目专属 |
| `D:\token看板\AGENTS.md` | 9.2KB | token 看板项目专属 |

## 搜索技巧

- 全盘找规则文件:`find /d -maxdepth 3 \( -name "CLAUDE.md" -o -name "AGENTS.md" -o -name ".cursorrules" \)`(排除 node_modules)
- Hermes 项目列表:project_list 工具(当前唯一项目:"跨境电商" p_479f98bb,primary D:)
- session_search 大结果落盘 cache:用 execute_code json.load 解析,提取 session_id/title/关键 user 消息
