<!-- archived from /root/.hermes/skills/security/tauri-app-modding/SKILL.md on 2026-10-21 -->

---
name: tauri-app-modding
description: >-
  测绘引擎·Use when extending a Tauri 2 desktop app from source.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/tauri-app-modding`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/tauri-app-modding/…')`，不要相对 `references/legacy/` 解析。

# tauri-app-modding（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/tauri-app-modding/`

溯源（仅标记）：`hermes/software-development`

---

# Tauri App Modding (Windows)

Extending a Tauri 2 app (Rust backend + React/TS webview) from source. Companion to `windows-cli-deployment` (which covers toolchain/build/install); this skill covers **changing app behavior**.

## THE #1 failure mode: settings whitelist sync

When you add a new value to an existing settings enum (e.g. wallpaper `kind = "live"`), the value must be whitelisted in **every** validation site or it silently resets / the feature silently doesn't render. A single missed site = hours of "why is my feature not showing". Sites found in cc-panes (all bit us):

| Site | What it does | Missed-site symptom |
|---|---|---|
| Rust `WallpaperSettings::merge_missing_defaults` (`matches!(self.kind, "none"\|"image"\|"video")`) | On app load, resets unknown kind to default **and saves config back** | config.toml flips back to `"none"` after every restart |
| Frontend `clampWallpaper` `oneOf(kind, ["none","image","video"])` | Sanitizes settings in the store | resolved.kind forced to none, layer never renders |
| Every `active` gate that requires `assetUrl !== null` (MainWallpaperLayer, MainViewSwitcher `wallpaperActive`, TerminalView terminal opacity, emptyStateShared, store's renderer-provider) | Controls panel/terminal background transparency | **Particle layer renders but is covered by an opaque panel background — totally invisible** |

Search pattern after adding a value: `grep -rn 'assetUrl !== null' web/` and `grep -rn 'matches!(self.kind' cc-panes-core/` plus every `oneOf(...)` on the field. Update all of them to `assetUrl !== null || kind === "live"`.

**Why it's invisible (the worst symptom)**: the z-0 wallpaper layer is below the panel background. If `wallpaperActive` (which drives `--app-panel-bg-effective: transparent`) uses the old gate, the panel stays opaque and covers the layer. Code runs fine, no console errors, feature just never appears.

## config.toml is NOT authoritative at runtime

Rust `SettingsService::new_with_config_path` runs `merge_missing_defaults()` on load and **rewrites the file** (atomic write). Editing config.toml while the app runs, or without updating the Rust whitelist, is futile — the app overwrites it at next start. Fix the Rust whitelist FIRST, then the config file survives.

Also: NSIS reinstall (`setup.exe /S`) does not clean old files — old `assets/main-*.js` accumulate in the install dir. Verify by reading what `index.html` references, NOT by directory listing. And a separate web server process (cc-panes-web) serves its own copy of dist (`resources/web-dist`) and **caches the old bundle until restarted** — restart it, don't trust `curl` against it until then.

## WebView2 cache staleness after frontend rebuild

Symptoms: new bundle confirmed on disk and in `index.html`, but the app still runs old JS. Fix:
```bash
# kill app + daemon + webview children, then clear cache
powershell -NoProfile -Command "Stop-Process -Name cc-panes,cc-panes-daemon,cc-panes-web -Force -ErrorAction SilentlyContinue; Get-Process msedgewebview2 -ErrorAction SilentlyContinue | Stop-Process -Force"
rm -rf "$LOCALAPPDATA/<app-id>/EBWebView/Default/Cache" "$LOCALAPPDATA/<app-id>/EBWebView/Default/Code Cache"
```
Data dir (settings, sessions) lives outside EBWebView, so clearing cache is safe.

## Debug vs release build split (use debug for iteration)

Tauri dev/release builds are fully isolated (different data dirs + identifiers). Debug: `~/.cc-panes-dev/`, identifier `com.ccpanes.dev`. Release: `~/.cc-panes/`, `com.ccpanes.app`. Logs: `AppData/Local/com.ccpanes.app/logs/cc-panes.log` (release) vs `~/.cc-panes-dev/` (debug). For fast iteration on Rust changes, build debug (`cargo build -p <main-crate>`), run `target/debug/<app>.exe` foreground to see stdout logs, fix, then only build the release package when stable. Release packaging via `npm run tauri build` with vcvars64 — see `windows-cli-deployment` for the wrapper script.

Note: the app's panic hook writes `crash.log` into its data dir; if you run the debug exe with `>/dev/null 2>&1`, a fern stderr logger panic may crash it — run it foreground (or keep stderr attached) when debugging.

## Process-kill consent rule (user preference)

Rebuilding/reinstalling requires stopping the running app + daemon. **Never kill the user's running processes without telling them first and getting the OK.** The user was angered by a silent `Stop-Process` of CC-Panes while they had sessions open (they may have Claude/Codex/reclaude sessions under it — check `Get-Process` for claude/codex/node before touching anything). Always announce what will be stopped, confirm, then proceed. This rule was explicitly demanded: "以后要关闭我正在运行的东西提前和我说".

## Overlay layers + mouse interaction: pointer-events-none trap

Wallpaper/overlay layers are `pointer-events-none` (so they don't block terminal/panel
interaction). Consequence: **a canvas inside them NEVER receives pointer events** — binding
`pointermove` on the canvas silently never fires, and the "cursor interaction" feature just
doesn't work while the render loop runs fine.

Fix: listen at `window` level and convert coordinates with `getBoundingClientRect()`:

```ts
const onPointerMove = (e: PointerEvent) => {
  const rect = cvs.getBoundingClientRect();
  cursor.x = e.clientX - rect.left;
  cursor.y = e.clientY - rect.top;
  cursor.active = true;
};
window.addEventListener("pointermove", onPointerMove, { passive: true });
window.addEventListener("pointerdown", onPointerDown, { passive: true });
window.addEventListener("pointerup", onPointerUp, { passive: true });
window.addEventListener("blur", () => { cursor.active = false; }); // don't leave particles stuck
```

Bonus: window-level listening means interaction works even when the mouse is over the
terminal content, not just over bare background. **Always remove listeners in the effect
cleanup.** Also: `pointer-events-none` is a CSS trap invisible in DevTools console — when a
canvas feature "runs but has no interaction", check the layer's CSS class first.

## Particle/overlay interaction patterns (verified on cc-panes)

- **Hover push/pull**: per-particle force toward cursor — push inside radius R1
  (`force * 2.2`), gentle pull between R1..R2 (`force * 1.1`). Force must be ~3x stronger
  than it feels like it needs (0.22 not 0.06) or it's imperceptible; raise the speed clamp
  too (`maxSpeed 1.4 + energy*2.4`), or the limit caps the push before it's visible.
- **Hold-to-accumulate vortex (长按聚集)**: on `pointerdown` record press point; per frame
  apply centripetal pull (`min(1, d/420)*0.16 + 0.02` toward center) + tangential orbit
  force (`(-dy/d, dx/d) * orbit` where orbit scales with audio energy) → particles spiral
  into a rotating cluster. On `pointerup`, burst outward (`(1-min(1,d/320))*3.2 + 0.6` away
  from center) so they disperse naturally. Dragging while held moves the center (update
  press point in pointermove when `pressing`).
- Draw a pulsing double-ring marker at the cluster center so the user sees where it is.

## Test loop for audio-driven features

To verify system-audio capture end-to-end without external speakers: run a beep loop in PowerShell (`[console]::beep(880, 300)` repeated) while the app runs, then check the log for `level=`/`bass=` values > 0. See `references/wasapi-loopback-capture.md` for the full capture recipe and windows-crate quirks.
