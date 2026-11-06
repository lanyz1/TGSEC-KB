<!-- archived from /root/.hermes/skills/security/tauri-windows-build/SKILL.md on 2026-10-21 -->

---
name: tauri-windows-build
description: >-
  测绘引擎·Build/customize Tauri 2 apps on Windows (CC-Panes etc.).
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/tauri-windows-build`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/tauri-windows-build/…')`，不要相对 `references/legacy/` 解析。

# tauri-windows-build（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/tauri-windows-build/`

溯源（仅标记）：`hermes/software-development`

---

# Tauri 2 Windows Build & Customization

在 Windows 上从源码构建/定制 Tauri 2 桌面应用（实战：CC-Panes）。覆盖工具链、MSVC 链接、NSIS 部署、以及给应用加自定义功能（壁纸层/音频捕获）时**跨层白名单门控**的坑。

## 工具链（本机已装好）

| 组件 | 位置/版本 |
|---|---|
| Node | `D:\node22` (v22.23.2)，`npm config set registry https://registry.npmmirror.com` |
| Rust | `C:\Users\Administrator\.cargo\bin` (1.97)，crates 走 rsproxy 稀疏索引（`~/.cargo/config.toml`） |
| MSVC | VS2022 BuildTools `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools`（含 Windows SDK 10.0.26100） |
| CC-Panes 源码 | `D:\cc-pane`（GitHub wuxiran/cc-pane，Tauri2 + React19 + Rust workspace） |
| target 目录 | `D:\cc-book-target`（项目 `.cargo/config.toml` 指定 `../cc-book-target`，仓库外） |

## 关键：git-bash 下必须用 cmd 包装脚本编译

git-bash 的 `link.exe` 是 GNU coreutils 版（`D:\Git\usr\bin\link.exe`），rustc 找不到 MSVC 链接器会报 `link: extra operand`。**必须**先 `vcvars64.bat` 初始化环境。模板 `D:\vcbuild-check.cmd`（debug 快查）/ `D:\vcbuild-full.cmd`（release 打包）：

```bat
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d D:\cc-pane
set PATH=C:\Users\Administrator\.cargo\bin;D:\node22;%PATH%
set CARGO_TARGET_DIR=D:/cc-book-target
npm run tauri build 2>&1   &REM 或 cargo build -p cc-panes
echo BUILD_EXIT:%ERRORLEVEL%
```

调用：`cmd.exe /c "D:\\vcbuild-full.cmd"`（**不是** `cmd //c`，bash 会吞斜杠）。后台跑 + `notify_on_complete=true`。装完 `setup.exe /S` 静默安装。

## 部署后的"每装必改"：config.toml 会被重置

NSIS 安装**覆盖** `C:\Users\Administrator\.cc-panes\config.toml`，自定义壁纸 kind 会变回 `"none"`。装完必须重新 patch 成 `kind = "live"` **再启动**（应用启动时从该文件读设置，先改后启才生效）。设置权威源是 config.toml 不是 SQLite（data.db 无 settings 表）。日志：`AppData\Local\com.ccpanes.app\logs\cc-panes.log`（debug 版在 `~/.cc-panes-dev/`，dev/release 数据隔离）。

## 加自定义壁纸/功能类型时：5 处白名单/active 判断必须全改

给应用新增枚举值（如壁纸 `kind="live"`）时，**Rust 和前端各有一层校验**，漏一处就静默失效（启动被重置 / 渲染被挡）。逐处检查：

1. **Rust** `cc-panes-core/src/models/settings.rs` `merge_missing_defaults()` 的 `matches!` 白名单 —— 不在名单的 kind 启动时被重置为默认并写回 config
2. **前端** `web/utils/wallpaper.ts` `clampWallpaper()` 的 `oneOf` 白名单
3. **active 判断**：壁纸层 `resolved !== null && assetUrl !== null` 会排除无文件的类型（live 无文件）——凡出现此模式的都要加 `|| resolved.kind === "live"`：
   - `MainWallpaperLayer.tsx`（渲染层 active）
   - `MainViewSwitcher.tsx` `wallpaperActive`（**控制面板背景透明，漏了粒子被不透明面板盖死**——本会话最隐蔽的坑）
   - `TerminalView.tsx`（终端透明度）
   - `emptyStateShared.tsx`、`useWallpaperStore.ts`（渲染器选择）
4. 类型定义 `web/types/settings.ts` 的 `WallpaperKind` 联合类型

排查套路：`grep -rn "assetUrl !== null" web/` 一次找全所有 active 判断；`grep -rn '"none" | "image" | "video"' cc-panes-core/` 找 Rust 白名单。

## 前端改动后：清 WebView 缓存

改前端 JS 后桌面端可能加载旧 bundle（`main-*.js` 哈希变化）。步骤：停进程（含 `msedgewebview2`）→ 删 `AppData\Local\com.ccpanes.app\EBWebView\Default\Cache` 和 `Code Cache` → 重启。验证加载的 bundle：看安装目录 `resources\web-dist\index.html` 引用的 `main-*.js` 哈希，grep 该文件确认新特性字符串在。

## 交互层 canvas 的鼠标事件坑

装饰层 `pointer-events-none` 的 canvas **收不到任何鼠标事件**。交互必须监听 `window` 级 `pointermove/down/up/blur`，坐标用 `canvas.getBoundingClientRect()` 换算。失焦/移出要清光标状态，否则粒子卡在最后位置。

## 音频律动（WASAPI loopback）— 详见 references

浏览器只能读麦克风，读不到系统输出。戴耳机也要律动必须 Rust 侧 WASAPI loopback 回环捕获，emit 事件给前端。完整实现、windows crate API 坑、`0x80070057` 修复见 `references/wasapi-loopback-audio.md`。

## 用户偏好（重要）

- **动任何运行中的进程前必须先告知并获同意**（用户强杀 cc-panes 时爆过）——重启前说明"会关哪些、数据安全"
- 长构建任务要主动报进度 + 耗时预估
- 粒子壁纸调参（力度/速度/颜色）用户会要求微调，改 `LiveParticleWallpaper.tsx` 的常量即可，改完走完整构建-安装-改config-清缓存-重启流程
