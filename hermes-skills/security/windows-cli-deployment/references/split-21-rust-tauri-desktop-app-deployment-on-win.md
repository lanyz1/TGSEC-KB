## Rust / Tauri Desktop App Deployment on Windows

Building Rust desktop apps (Tauri 2) from source on a fresh Windows box needs more than Node. Full working sequence (Aug 2026, China network):

### 1. Toolchain install

```bash
# Node 22+ portable (system may have ancient Node 11 at D:\node.exe — do NOT overwrite it)
curl -sL -o node22.zip "https://nodejs.org/dist/latest-v22.x/node-vXX-win-x64.zip"
# verify sha256sum against SHASUMS256.txt from nodejs.org/dist/latest-v22.x/
# extract to D:\node22; use /d/node22/node.exe and /d/node22/npm.cmd directly
/d/node22/npm.cmd config set registry https://registry.npmmirror.com

# Rust — rsproxy.cn/rustup/rustup-init.exe 404s (NoSuchKey). Use official:
curl -sL -o rustup-init.exe "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe"
./rustup-init.exe -y --default-toolchain stable --profile minimal --no-modify-path
# cargo bin lands at C:\Users\<user>\.cargo\bin (cargo.exe -> rustup.exe symlink)

# Cargo mirror (China): write ~/.cargo/config.toml
# [source.crates-io] replace-with = 'rsproxy-sparse'
# [source.rsproxy-sparse] registry = "sparse+https://rsproxy.cn/index/"
```

### 2. MSVC Build Tools — MANDATORY (rustc msvc target needs the MSVC linker)

Symptom when missing (looks like a link error but is NOT):
```
error: linking with `link.exe` failed
= note: link: extra operand 'D:/...build_script_build-*.rcgu.o'
        Try 'link --help' for more information.
```
"extra operand" = **GNU coreutils `link.exe` from Git Bash** (`D:\Git\usr\bin\link.exe`) shadowing the MSVC linker. Fix = install VS Build Tools:

```bash
winget install Microsoft.VisualStudio.2022.BuildTools --accept-source-agreements --accept-package-agreements --override "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
# or direct bootstrapper: curl -sL -o vs_buildtools.exe "https://aka.ms/vs/17/release/vs_buildtools.exe" && ./vs_buildtools.exe --quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
```
Verify: `ls "/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/"*/bin/Hostx64/x64/cl.exe`

### 3. Building with vcvars64

bash cannot source .bat. Write a .cmd wrapper and invoke via `cmd.exe /c` (NOT `cmd //c` — bash mangles `//`):

```cmd
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d D:\project
set PATH=C:\Users\Administrator\.cargo\bin;D:\node22;%PATH%
set CARGO_TARGET_DIR=D:/target
cargo build -p core-crate 2>&1
echo DONE_EXITCODE:%ERRORLEVEL%
```
From bash: `cmd.exe /c "D:\\vcbuild.cmd"`.

### 4. Pitfalls (all hit in production)

- **`failed to create directory D:\project\..` Access denied (os error 5)**: project's `.cargo/config.toml` sets `target-dir = "../outside"` (to keep the repo clean). Relative resolution can fail. Fix: `export CARGO_TARGET_DIR="D:/abs/path"` overrides it.
- **bash swallows `$var` inside `powershell -NoProfile -Command "..."`** — every `$p` becomes empty → "The term '=' is not recognized". Fix: write the logic to a `.ps1` with write_file, run `powershell -NoProfile -ExecutionPolicy Bypass -File script.ps1`. Same for any inline PowerShell with variables (COM, env edits, shortcuts).
- **Persisting PATH**: read `[Environment]::GetEnvironmentVariable('Path','User')`, append `C:\Users\<user>\.cargo\bin` + `D:\node22`, write back. Verify with a second read split on ';'.
- **Tauri build ending with `A public key has been found, but no private key` is HARMLESS** — it's only the auto-updater signing step; MSI/NSIS installers still build fine. Set `TAURI_SIGNING_PRIVATE_KEY` only if you need signed updates.
- **Verify the built exe actually launches before installing**: run it, `sleep 8`, `Get-Process cc-panes | Select MainWindowTitle` must show the window title. NSIS silent install: `setup.exe /S`; locate install via start-menu .lnk (WScript.Shell COM → TargetPath).
- First `npm install` after adding a `node_modules`-size dep tree can be 500+ packages — set `--no-audit --no-fund` and the npmmirror registry to keep it fast.
- **Ask before killing the running app.** Rebuilding/reinstalling requires `Stop-Process` of the app + daemon + webview children, but the user may have live sessions under it. Announce what will be stopped and get OK first — the user explicitly demanded this ("以后要关闭我正在运行的东西提前和我说"). Check `Get-Process` for claude/codex/node children before touching anything.
- **NSIS reinstall does not clean old files** — stale `assets/main-*.js` accumulate in the install dir. Verify what `index.html` references, not the directory listing. A bundled web server (cc-panes-web) serves its own copy of dist and caches the old bundle until restarted.
- For extending/modifying a Tauri app (new settings fields, canvas layers, WASAPI audio), see the `tauri-app-modding` skill — settings whitelist must be synced across Rust `merge_missing_defaults` + frontend `clampWallpaper` + every `assetUrl !== null` gate, or features silently don't render.

