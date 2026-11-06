<!-- archived from /root/.hermes/skills/autonomous-ai-agents/hermes-localization/SKILL.md on 2026-10-21 -->

---
name: hermes-localization
description: "Use when 把 Hermes 斜杠命令/菜单的硬编码英文汉化成中文。"
version: 1.0.0
---

> 归档卡：原目录 `/root/.hermes/skills/autonomous-ai-agents/hermes-localization`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/autonomous-ai-agents/hermes-localization/…')`，不要相对 `references/legacy/` 解析。

# Hermes 本地化 / 汉化

把 Hermes 硬编码的英文文本（斜杠命令描述、命令菜单）改成中文的完整流程与陷阱。官方 `display.language` 明确**不**覆盖命令描述，所以汉化必须改源码。

## 关键事实（always-on）

- 斜杠命令描述硬编码在 `/usr/local/lib/hermes-agent/hermes_cli/commands.py` 的 `COMMAND_REGISTRY`（`CommandDef(name, description, ...)`）。Telegram/Discord 菜单用 `setMyCommands` 直接渲染这串源码原文，聊天里「翻译给你看」改不了 Telegram 实际显示。
- `display.language: zh` 只翻译一小撮静态消息（审批提示、restart 通知），**明确排除斜杠命令描述**（官方文档原文如此）。
- 技能命令描述来自各 `SKILL.md` 的 frontmatter `description:` 字段；菜单只显示前 `max_commands`（默认 60）条核心命令，技能命令超量时被 hidden，用 `/commands` 翻页才看得到。
- 源码 + venv 在 `/usr/local/lib/hermes-agent/`，用 `./venv/bin/python` 跑验证脚本。

## 工作流

### 1. 改核心命令描述（commands.py）

备份后按 **name** 精确替换，不要复制英文原文去匹配——name 匹配更稳（原文含引号、破折号时容易失配）。

```python
import re
pat = re.compile(r'(CommandDef\(\s*"([a-z0-9_-]+)",\s*")[^"]*(")', re.S)
# 回调：name -> 中文映射表，m.group(1)+中文+m.group(3)
```

描述字符串是单行双引号字面量，不含内嵌双引号（只有单引号如 `'here [N]'`），`[^"]*` 安全。102 条命令一次性映射替换后，用 `ast.parse` 校验语法。

### 2. 改技能命令描述（SKILL.md）

遍历 `/root/.hermes/skills` 和 `/usr/local/lib/hermes-agent/skills` 下所有 `SKILL.md`：先匹配 `^name:\s*(.+?)\s*$` 确认技能名，再匹配 `^description:\s*(.+?)\s*$` 替换。

**陷阱：`>-` YAML 折叠块。** 部分技能（如 ai-llm-attack-surface、supply-chain-attacks）的 description 用折叠块标量——`description: >-` 后跟多行缩进内容。行级正则把 `>-` 替换成单行字符串后，原缩进行会残留在 frontmatter 里变成孤儿行，导致 YAML 解析失败。替换后必须清理 description 行之后残留的缩进行，再用 `yaml.safe_load` 校验每个 frontmatter：

```python
residue_re = re.compile(r'(^description:\s*"[^"]*"\s*\n)(?:[ \t].*\n)+', re.M)  # -> \1
```

### 3. 验证

```bash
./venv/bin/python -c "from hermes_cli.commands_platforms import telegram_menu_commands; print(telegram_menu_commands(max_commands=60))"
./venv/bin/python -c "from hermes_cli.commands_platforms import _iter_gateway_skills; print(list(_iter_gateway_skills('telegram')))"
```

判断残留英文别用「首字符是 ASCII 字母」——产品名/缩写（AI、ASCII、GitHub、IoT、Linux）开头的中文描述会被误判。要看是否还有 `Use when`/`Use for`/`Delegate coding to` 这类纯英文句式开头。

### 4. 生效（重启 gateway）

**陷阱：Hermes 禁止从 gateway 进程内部重启自己。** gateway 重启会 SIGTERM 传播杀子进程，terminal 工具会拦截 `systemctl --user restart hermes-gateway` 和 `nohup ... sleep N && restart`，报 "cannot restart/stop/uninstall the gateway from inside the gateway process"。正确做法：让用户在聊天里发 `/restart`（gateway 内置命令，优雅重启），或 SSH 独立 shell 跑 `systemctl --user restart hermes-gateway`。

## 陷阱汇总

- **`hermes update` 覆盖源码 + 内置技能目录改动。** `commands.py` 和 `/usr/local/lib/hermes-agent/skills/` 下的汉化升级即丢；`/root/.hermes/skills/`（用户目录）不受影响。**深度修复（持久化）**：`git update-index --skip-worktree hermes_cli/commands.py`，再对 `git status --porcelain skills/` 列出的每个汉化 SKILL.md 同样 skip-worktree——git 不再追踪这些文件的改动，`git pull`（update）不会覆盖它们。汉化脚本持久化到 `/root/hermes-hanli-localize/`（幂等 `run.sh`：先 `--no-skip-worktree` 取消冻结 → 重跑 zh_commands/zh_skills/fix_folded → 重新冻结），update 后若中文被重置，跑 `bash run.sh` 一键恢复。注意 `hermes update` 用 git pull 且 REFUSES dirty working tree：其他未冻结的改动（如破限注入的 agent/*.py、tools/*.py 及其 .bak-break 备份）仍会让 update 拒绝。
- **`>-` 折叠块**：改 SKILL.md frontmatter 最容易踩的坑，见工作流第 2 步。
- **gateway 不能内部重启**：见工作流第 4 步，任何需要重启 gateway 的操作都受此限制。
