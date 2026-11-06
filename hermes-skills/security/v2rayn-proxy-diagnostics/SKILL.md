---
name: v2rayn-proxy-diagnostics
description: >-
  测绘引擎·Use when diagnosing v2rayN proxy/TUN slowdowns on this PC.
owned: true
tier: ops
pack: survey-skill
---

# v2rayn-proxy-diagnostics（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/v2rayn-proxy-diagnostics/`

溯源（仅标记）：`hermes/networking`

---

# v2rayN Proxy Diagnostics (Windows)

User's proxy is v2rayN at `C:\Users\Administrator\Desktop\新v2包\v2rayN-windows-64-SelfContained` (shortcut "v2rayN.exe - 快捷方式"). Core facts:

- Two cores run simultaneously, started together: **xray** (SOCKS inbound **127.0.0.1:10808**, the everyday proxy) and **sing-box** (**10814**, used by TUN). Both live under the v2rayN `bin\` folder.
- **TUN mode is ON** (`guiConfigs\guiNConfig.json` → `TunModeItem.EnableTun=true`, StrictRoute=true). TUN = system-wide proxy: ALL traffic goes through the proxy chain. **User REQUIRES TUN to stay on (防封, avoids AI-agent bans) — never propose turning it off.**(2026-10-02 实测: 平时运行时 EnableTun=false、系统代理键 ProxyEnable=0 两个开关都关着——开关状态按用户习惯随手切,别擅自改。)
- Node pool (2026-10-02 换血): 6 条「二狗」VLESS+REALITY 节点 (191.40.0.0/24:443, remarks 二狗·美国/香港/日本/英国/美国2/韩国) stored in `guiConfigs\guiNDB.db` (SQLite, table `ProfileItem`). 关键列: ConfigType=5(VLESS)、StreamSecurity=reality、Flow=xtls-rprx-vision、Sni=download-installer.cdn.mozilla.net、PublicKey/ShortId/Fingerprint。旧 ga6x 中转账号(q0_*.ga6x.com)已被上游清号全灭——勿再依赖; 全节点延迟 -1ms = 节点全死的正常显示,不是软件故障。
- **Upload bottleneck is the residential node's uplink** — proxy upload ≈ half of direct (measured: direct ~12.5 Mbps, via proxy ~5.9 Mbps). Not a PC/config fault.

## 节点全灭判定与换血 (2026-10-02 实证)

1. 症状: 全部节点延迟 -1ms + 外网不通。先判「本机故障」还是「上游清号」: 用自带内核(bin\xray\xray.exe)离线逐个实测节点——能建 TCP 但握手中被拒 ≠ 本机问题 → 服务商清号。
2. 换血: 实测可用的 VLESS+REALITY 分享链接 → 写库脚本(默认 dry-run、APPLY 才写、自动备份 guiNDB.db) → 重启 v2rayN → 实测。
3. 关 v2rayN 要点: `taskkill /IM v2rayN.exe`(不加 /F) 它只缩到托盘不退; 必须补 `taskkill /F /IM`。内核可能残留——查 `netstat -ano | grep ":10808 "` 的 PID 补刀。
4. 重启后 30~90s 自动恢复核心并监听 10808(会自动恢复上次活动节点)。验证三件套: ① curl --proxy http://127.0.0.1:10808 https://api.ipify.org ② 看 binConfigs/config.json 是否编译出 "protocol":"vless"+"reality" ③ 出口 IP 变化。
5. ★持久启动法: 用 agent 工具直接 Start-Process 启动的 v2rayN 会挂进 agent 进程树——agent/运行环境整体重启时会把它一起带走(实测: 日志 MyAppExitAsync 优雅退出,同刻其它会话进程同时被杀)。要让它独立: `powershell -NoProfile -Command "Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='<v2rayN.exe全路径>'; CurrentDirectory='<目录>'}"`(实测 ReturnValue=0, SessionId=1, 父进程=系统服务, 不受树杀影响)。
6. 交付前监控 ≥2 分钟(:10808 + 进程存活), 防「拉起后 1 分钟又没」的假成功。

## Diagnosis steps (slow upload / network issues)

1. Top connections: `netstat -ano | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head` → note high-count PIDs (xray, sing-box, WXWork/企业微信, chrome, node, python are all normal residents).
2. Map PID→process: `powershell -c "(Get-Process -Id PID -ErrorAction SilentlyContinue).Name"`; full path via `powershell -c "Get-CimInstance Win32_Process -Filter \"Name='xray.exe' or Name='sing-box.exe'\" | Select Name,ProcessId,CreationDate,ExecutablePath | Format-List"`.
3. Measure upload direct vs proxied (10MB file):
   - Create file: `powershell -c "fsutil file createnew C:\path\t.bin 10485760"` (`dd` is unreliable in git-bash)
   - Direct: `curl -s --noproxy "*" -o /dev/null -w "%{speed_upload}" --upload-file f.bin https://speed.cloudflare.com/__down`
   - Proxied: same with `--proxy http://127.0.0.1:10808`
4. Inspect v2rayN config: `guiConfigs\guiNConfig.json` (RunningCoreType, TunModeItem, Inbound[0].LocalPort) and `guiNDB.db` via python sqlite3 (ProfileItem = nodes, RoutingItem = rules).
5. **Never kill xray/sing-box directly** — v2rayN respawns them and it cuts the net. Change settings in the v2rayN UI or config instead.

## Fixes (TUN must stay on)

- **Split-routing exemption**: add a rule so specific programs/domains (upload targets: 网盘/服务器) go `OutboundTag=direct` while everything else keeps TUN. Edit routing rules (guiNDB.db `RoutingItem` or v2rayN UI).
- Accept the residential-node uplink limit for general uploads.
- WXWork & chrome holding many connections is normal — verify with an actual speed test before blaming them.

## IPP printer interference (known symptom, verified 2026-08)

- v2rayN running blocks/hangs USB printer jobs driven by **Microsoft IPP Class Driver** (it speaks HTTP internally; TUN/system-proxy hijacks the requests) → jobs stuck "Printing, Retained" 0 pages, partial prints, blank pages.
- Verified: user closed v2rayN → Windows test page printed normally; reopened v2rayN → jobs stuck again.
- When any print job is stuck on this PC, check `Get-Process` for v2rayN/xray/sing-box FIRST and flag it; user closes v2rayN themselves to print (they keep it on for 防封 by default — do not force, just flag).
- `netsh winhttp show proxy` can read "Direct access" while v2rayN still interferes — interception is at TUN/route level, not WinHTTP.
- Printer may STILL fail with v2rayN off (separate IPP-stack issue on this PC; printer verified working on another computer). See skill `windows-printer-troubleshooting` for the full diagnostic ladder.

## Pitfalls

- Do not kill any process without explicit user consent (hard user rule).
- v2rayN config writes: xray binds 10808, sing-box binds 10814 — verify with `netstat -ano | grep LISTENING`.
- Chinese path (`新v2包`) breaks some tools — always quote paths: `"/c/Users/Administrator/Desktop/新v2包/..."`.
