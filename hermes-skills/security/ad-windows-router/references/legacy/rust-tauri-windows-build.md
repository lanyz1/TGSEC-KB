<!-- archived from /root/.hermes/skills/security/rust-tauri-windows-build/SKILL.md on 2026-10-21 -->

---
name: rust-tauri-windows-build
description: >-
  测绘引擎·Deploy/build Rust/Tauri 2 desktop apps on Windows.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/rust-tauri-windows-build`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/rust-tauri-windows-build/…')`，不要相对 `references/legacy/` 解析。

# rust-tauri-windows-build（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/rust-tauri-windows-build/`

溯源（仅标记）：`hermes/software-development`

---

# Rust/Tauri Windows Build & Deploy

Trigger: user clones a Rust workspace / Tauri 2 desktop app (e.g. cc-pane) and asks to deploy it on Windows. Full flow: toolchain (rustup + VS Build Tools + Node 22) → frontend build (npm) → Rust workspace + helper binaries → NSIS/MSI bundling → install & verify.

## 0. Preflight
```bash
node --version   # Tauri 2 needs 22+; old Node 11 breaks vite build
cargo --version  # needs 1.83+
```
Missing pieces → install (below). Check user PATH persistence too: `powershell -File` script adding `~/.cargo/bin` + Node dir to User PATH (see §3 for ps1 pattern — bash eats `$var` in `-Command`).

## 1. Toolchain install (China / GFW notes)

**Rust** — rustup-init must come from **static.rust-lang.org**; rsproxy.cn does NOT host it (returns XML `NoSuchKey` error):
```bash
curl -sL -o /d/rustup-init.exe "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe"
/d/rustup-init.exe -y --default-toolchain stable --profile minimal --no-modify-path
# verify: ls ~/.cargo/bin/ ; export PATH=~/.cargo/bin:$PATH && cargo --version
```

**Node** — portable zip, no admin needed:
```bash
curl -s "https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt" | grep "win-x64.zip"   # get exact version + sha
curl -sL -o /d/node22.zip "https://nodejs.org/dist/latest-v22.x/node-v22.23.2-win-x64.zip"
sha256sum /d/node22.zip   # MUST match SHASUMS256.txt
python -c "import zipfile; zipfile.ZipFile('/d/node22.zip').extractall('/d')" && mv /d/node-v*-win-x64 /d/node22
/d/node22/npm.cmd config set registry https://registry.npmmirror.com
```

**Cargo mirror** — write `~/.cargo/config.toml`:
```toml
[source.crates-io]
replace-with = 'rsproxy-sparse'
[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"
[net]
git-fetch-with-cli = true
```

**npm install** (fast on npmmirror, ~15s for 650 pkgs):
```bash
export PATH="/d/node22:$PATH" && export npm_config_registry=https://registry.npmmirror.com
npm install --no-audit --no-fund
```

## 2. CRITICAL: MSVC link.exe missing → "link: extra operand"

Symptom: cargo build fails on EVERY crate with `link: extra operand '...rcgu.o'` + `Try 'link --help'`. Cause: no Visual Studio Build Tools installed → rustc resolves **Git Bash's GNU `link.exe`** (`/usr/bin/link`) instead of MSVC's linker.

Fix — install VS Build Tools (winget in background bash may exit 0 having done nothing → use the direct installer):
```bash
curl -sL -o /d/vs_buildtools.exe "https://aka.ms/vs/17/release/vs_buildtools.exe"
/d/vs_buildtools.exe --quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
```
Verify (paths differ for BuildTools — it's under `Program Files (x86)`):
```bash
"/c/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe" -latest -products '*' \
  -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
ls "/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/"*/bin/Hostx64/x64/cl.exe
```

## 3. Build via vcvars64 wrapper (.cmd file — Git Bash cannot source vcvars)

cargo needs the MSVC env; write a `.cmd` wrapper with write_file, run with `cmd.exe /c` (NOT `cmd //c` — Git Bash mangles `//c`):
```bat
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d D:\<proj>
set PATH=C:\Users\<user>\.cargo\bin;D:\node22;%PATH%
set CARGO_TARGET_DIR=D:/<proj>-target
npm run tauri build 2>&1
echo FULLBUILD_EXIT:%ERRORLEVEL%
```
Run with `cmd.exe /c "D:\\\\vcbuild-full.cmd"`; long builds → terminal(background=true, notify_on_complete=true). First build of a Tauri workspace: ~3-4 min compile + bundling (downloads wix/nsis from GitHub). **When starting any build that will take minutes, give the user a time estimate up front and report progress as it goes — this user explicitly asked for a "进度条" (progress bar) mid-build ("重新构建要多久").** Incremental builds (Rust unchanged, only frontend edited) are ~3 min; fresh toolchain builds 10-30 min. Don't leave the user staring at a silent build.

## 4. target-dir pitfalls

- Projects sometimes set `target-dir = "../xxx"` in their own `.cargo/config.toml` (keep target out of repo). If that path can't be created: `failed to create directory D:\proj\..` Access denied → override with `CARGO_TARGET_DIR=D:/<proj>-target` env var (set it in the wrapper too).
- Always export CARGO_TARGET_DIR yourself; don't rely on the project's relative config.

## 5. Tauri-specific

- `npm run tauri build` runs beforeBuildCommand (frontend build + helper binary compile + resource copy) then bundles MSI + NSIS.
- End-of-build error `A public key has been found, but no private key. Make sure to set TAURI_SIGNING_PRIVATE_KEY` = **benign** — author's private key isn't in the repo; app still builds & installs, only auto-update signing is absent. Don't treat as failure.
- Artifacts: `<target>/release/<name>.exe` (portable), `bundle/nsis/*_setup.exe`, `bundle/msi/*.msi`.

## 6. Install & verify

```bash
# portable first: launch, then check window title
./<name>.exe & sleep 8
powershell -NoProfile -Command "Get-Process <name> -ErrorAction SilentlyContinue | Select-Object Id,MainWindowTitle"
# NSIS silent install:
cmd.exe /c "D:\\...\\*_setup.exe /S"   # installs to %LOCALAPPDATA%\Programs\<name>\ + Start Menu .lnk
```

## 7. ⚠️ STOP AND ASK: never kill the user's running processes without permission

**User correction (2026-08, burned trust):** force-killing `cc-panes.exe` with `Stop-Process` to swap config mid-session triggered an angry rebuke — the app was hosting the user's live Claude/Codex sessions. **Rule: before stopping/restarting any app the user is running (especially one hosting their work sessions), announce it first and get explicit consent.** Rebuilds and config edits often require the app stopped — say so BEFORE killing, not after.

## 8. Rebuild loop (frontend-only change → new installer)

Common iteration: user wants a UI/feature change → edit `web/` → rebuild → reinstall. Fast path:

1. `npx tsc --noEmit` — TS check first; catches null-closure and type-union errors cheaply.
2. `npm run build` — frontend only (~20s).
3. **Stop ALL related processes first** — running daemon/web/main binaries hold file locks on `binaries/` and `cc-panes.exe` in target dir, and `npm run tauri build` dies with `The process cannot access the file because it is being used by another process. (os error 32)`. Kill `cc-panes`, `cc-panes-daemon`, `cc-panes-web` together (per §7: tell the user first). Note: killing only the main exe is NOT enough — daemon + web hold the locks.
4. `npm run tauri build` via the vcvars wrapper — Rust unchanged ⇒ ~3 min (frontend rebuild + bundle), not 15+.
5. Silent reinstall `/S` + relaunch. The `TAURI_SIGNING_PRIVATE_KEY` warning every build is benign (§5).

**If the UI still doesn't show your change after reinstall → stale-bundle / view-gate checklist (hit 2026-08, cost 2 extra rebuilds):**
1. **WebView2 serves the OLD JS bundle from cache.** Symptom: config/API returns the new value, `dist/` and installed `resources/web-dist/` contain the new `main-<hash>.js` (grep it for your feature string), yet the app still looks old. The web-service process (`cc-panes-web`) was started before the reinstall and keeps serving the old bundle; the desktop WebView2 also caches aggressively. Fix: kill `cc-panes`, `cc-panes-daemon`, `cc-panes-web` AND `msedgewebview2*`, delete `%LOCALAPPDATA%\com.<app>.app\EBWebView\Default\Cache` + `Code Cache`, relaunch.
2. **NSIS incremental installs accumulate old assets** — `resources/web-dist/assets/` ends up with several `main-*.js` generations. Don't judge by the directory listing; read which bundle `index.html` actually references (`grep -oE "assets/main-[A-Za-z0-9]+\.js" <installed>/resources/web-dist/index.html`) and confirm it matches the fresh `dist/assets/main-*.js`.
3. **Verify the served bundle, not just the files**: `curl -s http://127.0.0.1:<webport>/ | grep -oE "assets/main-.*\.js"` — the web service serves from ITS loaded dist; a still-running old process returns the old hash (see #1). Also `curl http://127.0.0.1:<webport>/api/settings` to confirm the backend value end-to-end.
4. **Feature may be view-gated**: components conditionally rendered only in certain app views (`viewVisible = appViewMode === "panes" || "orchestration"` etc.). A background layer mounted inside the panes container does NOT appear on the home/dashboard view — test it from a workspace/terminal view before concluding the feature is broken. Ask the user which view they're looking at; first report of "看不到" was in the dashboard view.

Frontend type-union extension pattern (adding a new wallpaper kind, a new launcher, etc.):
- Rust-side settings fields are often **loose `String`** (e.g. `kind: String` with `#[serde(default)]`) — but **check for a `merge_missing_defaults()` whitelist BEFORE assuming only TS needs touching** (see next bullet — this session lost 3 rebuild cycles to it).
- **⚠️ Rust-side whitelist gate (the one that bites):** `AppSettings::merge_missing_defaults()` (called in `SettingsService::new_with_config_path`) often validates enum-ish Strings with `matches!(kind.as_str(), "none"|"image"|"video")` and RESETS unknown values to default — then the app **rewrites config.toml on startup/exit**. Symptom: you edit config.toml to the new kind while app is stopped, launch, and config is back to `kind = "none"` (or the app's own settings-save lines appear in the log right after boot). Frontend changes alone can NEVER fix this — the value never survives startup. Fix: add the new value to the Rust `matches!` whitelist in the model's `merge_missing_defaults`, rebuild, reinstall. See `references/cc-panes-wallpaper.md` for the full 3-layer bug chain.
- The TS `WallpaperKind` union in `web/types/*.ts` is a SECOND gatekeeper; add `"live"` there, then hunt every consumer (store asset resolution must exclude the new kind from file resolution, render layer gets a branch).
- TS closure narrowing: `canvas`/`ctx` are `possibly null` inside rAF closures even after the early-return guard — alias them (`const cvs = canvas; const c2d = ctx`) after the guard.
- When sed-bulking `ctx.` → `c2d.` inside a file, the initializer line `const ctx = canvas.getContext("2d")` gets mangled too — re-check the guard block after sed.

CC-Panes-specific live-particle wallpaper work (system-audio-reactive via WASAPI loopback + mic fallback, pointer interaction, config keys): see `references/cc-panes-wallpaper.md`. Generic Windows system-audio capture recipe (WASAPI loopback, windows-crate 0.62 feature flags/GUIDs/HRESULT pitfalls, **the 0x80070057 E_INVALIDARG fix — Initialize needs the full WAVEFORMATEXTENSIBLE byte-copy, not the 18-byte header**, RMS+ZCR analysis without FFT, Tauri emit→listen wiring, log-based verification): see `references/wasapi-loopback-audio.md`.
Resolve .lnk target & launch via a .ps1 file (bash eats `$var` inside `powershell -Command "..."` — history expansion strips `$p` etc.):
```powershell
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut('C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\<name>.lnk')
Write-Host "Target: $($lnk.TargetPath)"
Start-Process $lnk.TargetPath
```
Run: `powershell -NoProfile -ExecutionPolicy Bypass -File "D:\launch.ps1"`.

First-boot console logs confirm health: daemon/web/orchestrator bind to 127.0.0.1 ports, "setup complete" line; benign noise like `HotKey already registered` (shortcut collision) is expected.

## Pitfalls
- **Git Bash eats `$var` in `powershell -Command "..."`** → always write .ps1/.cmd files and use `-File` / `cmd.exe /c`.
- `cmd //c` → use `cmd.exe /c`.
- Background `winget install` in bash can exit 0 having done nothing → verify with vswhere/Get-Process before assuming.
- Don't conclude "toolchain missing" from `where link.exe` alone — Git Bash's GNU link.exe shadows MSVC; check vswhere + cl.exe instead.
- Keep the `.cmd`/`.ps1` helper scripts on D:\ — they're reusable across projects on this machine.
