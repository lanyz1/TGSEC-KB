# CC-Panes live-particle wallpaper (kind="live")

Work done 2026-08: added a real-time interactive particle background to CC-Panes
(repo D:\cc-pane, install C:\Users\Administrator\AppData\Local\cc-panes\).

## Architecture (where wallpaper renders)

- Render layer: `web/components/layout/MainWallpaperLayer.tsx` — absolute inset-0 z-0
  pointer-events-none, aria-hidden, inside MainViewSwitcher panes container (NOT AppShell,
  so it doesn't cover TitleBar/ActivityBar/StatusBar).
- Type gate: `web/types/settings.ts` → `WallpaperKind = "none" | "image" | "video" | "live"`.
  Rust side (`cc-panes-core/src/models/settings.rs`) keeps `kind: String` — loose field, BUT
  **`WallpaperSettings::merge_missing_defaults()` has a `matches!(kind.as_str(), "none"|"image"|"video")`
  whitelist that RESETS unknown kinds to default** — see "⚠️ The 3-layer bug chain" below.
  This is the #1 trap: it looks like "only TS needs the new union member" but the Rust
  whitelist silently kills the value at startup.
- Store: `web/stores/useWallpaperStore.ts` — `resolveWallpaperAsset` must only run for
  image/video; live kind has no file. Patch its guard from `kind !== "none" && file` to
  `(kind === "image" || kind === "video") && file`.
- Config: `~/.cc-panes/config.toml` `[wallpaper]` section (enabled/kind/file/fit/opacity/
  blur/dim/terminalOpacity/glassBlur). **config.toml is NOT the source of truth — the app
  rewrites it from in-memory settings on boot & on every `Settings updated and saved`**.
  Editing config alone only works if the Rust whitelist already accepts the value (see bug
  chain below); always `cp config.toml config.toml.bak` before editing.

## ⚠️ The 3-layer bug chain (adding a new wallpaper kind — 3 failed rebuilds)

Symptom: new `kind="live"` never shows. Debugging surfaced THREE independent gates, all
of which must pass — frontend-only fixes were useless because the value died at boot:

1. **TS clamp whitelist**: `web/utils/wallpaper.ts` `clampWallpaper()` uses
   `oneOf(settings.kind, ["none","image","video"], "none")` → unknown kind forced back to
   `"none"`. Fix: add `"live"` to the whitelist array.
2. **TS render-layer active check**: `MainWallpaperLayer.tsx`
   `const active = resolved !== null && assetUrl !== null;` — live has no file ⇒ assetUrl
   null ⇒ layer never renders even when kind is correct. Fix:
   `active = resolved !== null && (assetUrl !== null || resolved.kind === "live")`.
3. **Rust merge_missing_defaults whitelist** (the sneaky one): `settings.rs`
   `merge_missing_defaults()` does `if !matches!(kind.as_str(), "none"|"image"|"video") { kind = default }`
   → at every startup the app resets live→none and **rewrites config.toml**, so your
   manual config edit is silently clobbered ~5s after launch (log shows `Settings updated
   and saved` right after boot). Fix: add `"live"` to the Rust `matches!` whitelist,
   rebuild the app binary (cc-panes-core change → full recompile), reinstall.

Diagnostic that isolates layer 3: set `kind="live"` in config, launch, then re-read config
~10s later — if it's back to `"none"` while the frontend code is already fixed, the Rust
whitelist is the killer (config.toml is being rewritten by merge_missing_defaults, NOT by
the installer — NSIS reinstall doesn't touch `~/.cc-panes/` user data).

Also: the NSIS silent install does NOT reset user config — the "config back to none after
reinstall" effect was entirely layer 3. Don't chase the installer; chase merge_missing_defaults.
- Wallpaper files live in `~/.cc-panes/wallpapers/` (data_dir/wallpapers, uuid filenames).

## Component: LiveParticleWallpaper.tsx

New file `web/components/layout/LiveParticleWallpaper.tsx`. MainWallpaperLayer returns it
early when `resolved.kind === "live"` (before the blur/scale container; it carries its own
dim overlay). Props: `opacity`, `color` (default "88,160,255").

Capabilities implemented:
- ~110 particles, adaptive count by area (min 40, area/16000), base speed 0.35.
- rAF loop, dt-clamped (0.05), canvas 2D (NOT WebGL — repo forbids WebGL/canvas for video
  frames due to live-context budget, docs/39), devicePixelRatio capped at 2.
- Audio reactivity: **system audio (WASAPI loopback) is the PRIMARY source — solves the
  headphone case.** Rust side (`src-tauri/src/services/audio_loopback.rs`) captures the
  default render device's PCM with `AUDCLNT_STREAMFLAGS_LOOPBACK`, analyzes bass/level
  (RMS + zero-crossing-rate median, no FFT), and emits `ccpanes-audio-level {level,bass}`
  at ~16 Hz. Frontend listens via `@tauri-apps/api/event`, smoothing
  `audioLevel += (sysAudioLevel - audioLevel) * 0.35`. Full recipe + windows-crate 0.62
  gotchas (feature flags, GUID consts, HRESULT-vs-Result) → `references/wasapi-loopback-audio.md`.
  Fallback chain: loopback → mic → free flow.
- Mic fallback (kept as backup, was the v1 source):
  `getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false}})`
  → AnalyserNode fftSize 256 → bass = bottom 25% bins drives particle size (×1+1.8·bass)
  and speed; overall energy drives link density + glow. Mic failure degrades silently to
  free-flowing particles. **Browser limitation that motivated loopback: only the MICROPHONE
  is reachable from the webview — system output audio (music through headphones) cannot be
  read from JS alone.**
- Mouse: pointermove on canvas — particles within 140px pushed away, 140–260px attracted,
  pulsing ring around cursor. pointer-events-none wrapper means events reach the canvas.
- Trail effect: fillRect with rgba(10,12,20,0.28) per frame (motion blur tail).

## Rebuild/install loop used

tsc --noEmit → npm run build → stop cc-panes + cc-panes-daemon + cc-panes-web (file locks,
else os error 32) → npm run tauri build via vcvars64 .cmd wrapper → NSIS /S → relaunch.

## "Still can't see it after reinstall" — stale bundle & view gate (2026-08, cost 2 cycles)

After the 3-layer bug chain was fixed, the user STILL reported no particles. Root causes
found on inspection (not config, not the whitelist):

- **Stale JS bundle being served.** `http://127.0.0.1:18080/` (cc-panes-web) referenced the
  OLD `assets/main-B7X3JDpc.js` even though `dist/` and installed
  `resources/web-dist/` had the new `main-DwCNyvHj.js` (grep for the feature marker,
  e.g. `live-particles`, to distinguish). The web-service process had been started before
  the reinstall and kept serving its old in-memory dist; the desktop WebView2 also caches.
  Fix: kill cc-panes + daemon + web + `msedgewebview2*`, delete
  `%LOCALAPPDATA%\com.ccpanes.app\EBWebView\Default\Cache` and `Code Cache`, relaunch.
- **NSIS leaves old assets behind** — installed `resources/web-dist/assets/` accumulated
  main-B1BpqNIv/main-B7X3JDpc/main-DwCNyvHj/main-T6HC5Plh.js. Check the hash the installed
  `index.html` references, not the directory listing.
- **View-gating**: `MainWallpaperLayer` mounts inside the panes container; `viewVisible`
  requires `appViewMode === "panes" | "orchestration"`. On the home/dashboard view the
  wallpaper layer is NOT rendered at all — user was looking at the dashboard. Ask which
  view they're on before chasing the code.

Quick verification loop: `curl -s 127.0.0.1:18080/api/settings` (confirm kind=live from the
backend), then check which bundle the served index.html pulls, then confirm the installed
index.html matches. All three green + user on a panes view = particles visible.

## Wallpaper sourcing (static image fallback)

wallhaven.cc API reachable from CN: `https://wallhaven.cc/api/v1/search?q=anime+dark&categories=010&purity=100&atleast=1920x1080`
→ parse JSON `data[].path` (w.wallhaven.cc CDN). For terminal-background suitability,
score candidates with PIL brightness analysis (avg + % pixels <60 = dark) — pick dark-edge
images so white terminal text stays readable; verify content via API tags before download.
