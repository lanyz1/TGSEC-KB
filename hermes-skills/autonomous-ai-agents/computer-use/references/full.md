# computer-use — 全文续篇

> 主卡保留前 11 节；本文件从第 12 节起。原文件：`/root/.hermes/skills/autonomous-ai-agents/computer-use/SKILL.md`

## Failure modes — what to do when things go sideways

| Symptom | Likely cause + remedy |
|---|---|
| `cua-driver not installed` | Run `hermes computer-use install`, or `hermes tools` and enable Computer Use |
| Captures consistently return empty / "no on-screen window" | On Linux: DISPLAY may not be set (X11) or you're on pure Wayland — ask the user to run `hermes computer-use doctor`. On Windows: you may be in Session 0 (SSH session) instead of the interactive desktop — see the cua-driver `WINDOWS.md` deep-dive |
| Element index stale ("Element N not in cache") | SOM indices are only valid until the next `capture`. Re-capture before clicking. The wrapper carries opaque `element_token`s for stale-detection; you'll see an explicit error rather than a wrong click |
| Click had no effect | Read the structured verdict. `effect:"unverifiable"` → fresh capture/state before retry, even with an escalation hint. `effect:"suspected_noop"` or a structured refusal → climb the recommended ladder: coordinate (px), then foreground. Browser chrome/native prompts remain native; page content is a separate toolset. Don't conclude the app is undrivable |
| Type text disappears into a terminal emulator | cua-driver detects terminals (Ghostty, iTerm2, Terminal.app, Windows Terminal, mintty, etc.) and routes through key-event synthesis — should "just work" on a recent cua-driver. If it doesn't, ask the user to run `hermes computer-use doctor` |
| `blocked pattern in type text` | You tried to `type` a shell command matching the dangerous-pattern block list (`curl ... \| bash`, `sudo rm -rf`, etc.). Break the command up or reconsider |
| Anything else weird | **First action: ask the user to run `hermes computer-use doctor`.** It runs the cua-driver `health_report` MCP tool and prints a structured per-check matrix. Their output tells you (and them) exactly what's wrong |

## When NOT to use `computer_use`

- **Web automation you can do via separate headless `browser_*` tools** — those use a
  real headless Chromium and are more reliable than driving the user's
  GUI browser. Reach for `computer_use` specifically when the task
  needs the user's actual native apps (Finder/Explorer/Files, Mail/
  Outlook/Thunderbird, native chat clients, Figma, Logic, games,
  anything non-web).
- **File edits** — use `read_file` / `write_file` / `patch`, not
  `type` into an editor window.
- **Shell commands** — use `terminal`, not `type` into Terminal.app /
  Windows Terminal / gnome-terminal.

## Going deeper — read the cua-driver skill pack

Hermes intentionally keeps THIS skill focused on the Hermes-side
`computer_use` action vocabulary. The platform-specific deep dives
(macOS no-foreground contract, Windows UIA + Session 0, Linux AT-SPI +
X11/Wayland nuances, recording trajectory + video, browser-page
interaction, etc.) live in cua-driver's skill pack — same content the
cua-driver team ships and maintains for every other agent harness.

To link the cua-driver skill pack into your skill space:

```
cua-driver skills install
```

You'll then have access to:

- `SKILL.md` — the cross-platform core (snapshot invariant, no-
  foreground contract, click dispatch, AX tree mechanics)
- `MACOS.md` — macOS specifics (no-foreground contract, AXMenuBar
  navigation, SkyLight click dispatch, Apple Events JS bridge)
- `WINDOWS.md` — Windows specifics (UIA tree, UWP / ApplicationFrameHost
  hosting, Session 0 isolation, autostart pattern for SSH)
- `LINUX.md` — Linux specifics (AT-SPI tree, X11 / Wayland, terminal
  emulator detection)
- `RECORDING.md` — trajectory + video recording semantics
- `WEB_APPS.md` — browser page interaction tips
- `TESTS.md` — replay-by-trajectory workflow

These are platform deep dives, not duplicates — when the user reports
"on Windows the click landed on the wrong element," you read
`WINDOWS.md` for the UIA / UWP context that explains why and what to
do differently.

Hermes autodetection is a planned follow-up in trycua/cua. For now, the command
installs the pack under `~/.cua-driver/skills/cua-driver`; point Hermes at that
directory or symlink it into the user's skill space.

