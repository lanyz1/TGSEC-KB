---
name: apple-device-automation
description: Use for Apple Notes/Reminders/iMessage/Find My automation.
---

# Apple Device Automation (macOS)

One umbrella for driving the four native Apple apps an agent is asked about most:
Notes, Reminders, Messages (iMessage/SMS), and Find My. Each app has its own CLI
or automation path and its own macOS permission grant — the tool-specific
quick references live in `references/`.

## Routing (pick the sub-tool by app)

| User intent | App | CLI / method | Reference |
|---|---|---|---|
| create/view/search notes, cross-device sync | Notes.app | `memo` CLI | [references/apple-notes-memo-cli.md](references/apple-notes-memo-cli.md) |
| add/list/complete to-dos, due dates & alarms | Reminders.app | `remindctl` CLI | [references/apple-reminders-remindctl.md](references/apple-reminders-remindctl.md) |
| send/read iMessage or SMS | Messages.app | `imsg` CLI | [references/imessage-imsg-cli.md](references/imessage-imsg-cli.md) |
| locate device/AirTag, track over time | Find My | AppleScript + `peekaboo` + screenshot | [references/findmy-tracking.md](references/findmy-tracking.md) |

## Shared rules (apply across all four)

1. **Confirm before side-effecting actions**: sending messages, creating or
   deleting notes/reminders — always confirm recipient/content or item text
   with the user first. Never send to unknown numbers without explicit approval.
2. **Permission grants are per-app and per-capability**: Automation (Notes,
   Messages), Reminders access, Full Disk Access (Messages history), Screen
   Recording (Find My screenshots). If a CLI errors with `-1743` or empty
   results, suspect the missing grant (System Settings → Privacy) before
   debugging the command.
3. **Interactive CLIs need a PTY**: `memo -e/-d/-m`, selection prompts — set
   `pty=true` or prefer non-interactive flags.
4. **"Remind me" ambiguity**: if the user says "remind me", clarify whether they
   mean Apple Reminders (syncs to iPhone) or an agent cronjob alert — the
   surface differs (`remindctl` vs the cronjob tool).
5. **Don't use this umbrella for**: Obsidian vaults (`obsidian` skill),
   Google Calendar/Gmail (`google-workspace`), Telegram/WhatsApp
   (gateway channels), cross-platform todo boards (Notion/GitHub Issues).
6. Install shortcuts: `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`;
   `brew install steipete/tap/remindctl`; `brew install steipete/tap/imsg`;
   `brew install steipete/tap/peekaboo` (optional, for Find My UI automation).

## Pitfalls

- `memo notes -a` opens `$EDITOR`; it does not take the note text as an argument.
- `remindctl --due` (due time) and `--alarm` (notification trigger) are separate
  fields — set `--alarm` explicitly for early nudges, then verify with
  `remindctl today --json` (`dueDate` vs `alarmDate`).
- AirTags only update location while the Find My window is open and in the
  foreground — cron-driven background tracking must keep the app visible.
- AppleScript UI paths can break across macOS versions; prefer the CLI tools
  over UI scripting whenever one exists.

## 失效条件

1. **非 macOS 平台**：四款 App 与四个 CLI（memo/remindctl/imsg/peekaboo）均依赖 macOS + 已登录 iCloud；Linux/Windows 会话直接失效，改用对应跨平台替代（Google Workspace、网关频道）。
2. **目标 App 不属于四款**：Obsidian（→ `obsidian`）、Gmail/Calendar（→ `google-workspace`）、Telegram/WhatsApp/Discord（→ 网关渠道）、跨平台任务板（→ Notion/GitHub Issues）时本技能不适用。
3. **隐私权限未授予**：CLI 报错 `-1743`（Automation 被拒）、Messages 历史为空（缺 Full Disk Access）、截图黑屏（缺 Screen Recording）——先引导用户到 System Settings → Privacy 授权，命令层调试无效。
4. **用户意图为 agent 自身提醒**：用户说「remind me」但实际要 cronjob 定时告警而非同步到 iPhone 的 Apple Reminders——先澄清再动手，用错面即失效。
5. **批量/群发场景**：向多人群发 iMessage 或批量改 Notes 属高风险副作用操作，必须逐条用户确认；无确认时本技能流程不允许执行。

Details, command tables, and per-app limitations: see the four reference files.
