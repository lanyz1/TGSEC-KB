---
name: v2rayn-tun-troubleshooting
description: >-
  测绘引擎·排查v2rayN TUN导致的慢上传/应用转圈(防封双核、MTU、应用级代理坑)。
owned: true
tier: ops
pack: survey-skill
---

# v2rayn-tun-troubleshooting（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/v2rayn-tun-troubleshooting/`

溯源（仅标记）：`hermes/networking`

---

# v2rayN TUN 网络排查(Windows/中国GFW环境)

用户环境:Windows + 桌面`新v2包`(v2rayN-windows-64-SelfContained),TUN 模式**常开不可关**(防 AI agent 封号),住宅节点。

## 架构速览(先背熟再动手)

- **v2rayN 管理两个核心(同秒启动的子进程,不是两个软件)**:
  - `xray.exe` → 监听 **127.0.0.1:10808**(主 SOCKS 代理,用户日常用)
  - `sing-box.exe` → 监听 **127.0.0.1:10814**(TUN 模式核心)
- **TUN 开启(`TunModeItem.EnableTun=true`)= 全局代理**:系统所有流量进 sing-box → 按规则走 `proxy`(127.0.0.1:10808 → xray → 节点)或 `direct`。
- 配置文件(全在 `桌面\新v2包\v2rayN-windows-64-SelfContained\`):
  - `guiConfigs/guiNConfig.json` — 主配置(TunModeItem/Inbound/节点选中)
  - `guiConfigs/guiNDB.db` — SQLite:ProfileItem(节点)/RoutingItem(路由组)/SubItem
  - `binConfigs/configPre.json` — sing-box 基础配置(inbounds/outbounds/rules)
  - `binConfigs/config.json` — xray 配置

## 核心坑(本次实战教训)

### 1. TUN 开启时,应用不要设 10808 自定义代理 ⚠️
sing-box 规则里有**防环路规则**:`process_name` 含 `xray.exe` 等代理进程的流量 → `direct`(直连)。
后果:应用设 10808 后,流量路径变成 `应用 → 10808(xray) → xray 出站 → 被识别为 xray.exe → 强制直连 → 被墙 → 无限转圈`。
**正确做法**:移除应用自定义代理,让流量自然走 TUN(sing-box 统一分流到 10808)。TUN 开启时应用级代理设置是多余且有害的。

### 2. MTU 9000 是坑
TUN 默认 `Mtu: 9000`(巨型帧),物理网卡通常 1500 → 小包卡顿/大包分片丢失,表现为"2kb 都转圈、大流量 0 B/s"。**改 1500**。

### 3. 上传慢 = 节点上行带宽,物理限制
TUN 全流量走节点 → 上传速度 = 代理节点上行带宽。住宅节点上行天然小(实测直连 12.5Mbps → 走节点 5.9Mbps)。不是电脑问题、不是双开问题、不是配置问题。

## 改配置流程(必须按序,否则配置被覆盖)

1. **备份**:`cp guiConfigs/guiNConfig.json guiConfigs/guiNConfig.json.bak_$(date +%Y%m%d_%H%M%S)`
2. **优雅关闭 v2rayN**(它退出时才落盘配置,直接改文件会被内存覆盖):
   `powershell -c "Get-Process v2rayN -ErrorAction SilentlyContinue | Stop-Process"`(子进程 xray/sing-box 会一起退)
3. **确认端口释放**:`netstat -ano | grep -E "10808|10814" | grep LISTENING` 无输出才安全
4. **改 JSON**:用 python 读改写(保持 UTF-8),如 `d['TunModeItem']['Mtu']=1500`
5. **重启**:`powershell -c "Start-Process -FilePath '<exe绝对路径>'"`,等 8 秒
6. **验证**:端口 LISTENING + curl 测试

## 诊断命令集

```bash
# 进程与端口
netstat -ano | grep -E "10808|10814" | grep LISTENING
powershell -c "Get-CimInstance Win32_Process -Filter \"Name='sing-box.exe'\" | Select-Object CommandLine"
# ↑ 实际运行配置的路径在命令行 -c 参数里

# 应用实际连接(确认代理设置是否生效)
netstat -ano | grep ESTABLISHED | grep 127.0.0.1:10808

# 上传速度对比(直连 vs 代理)—— 注意 git-bash 里 dd 生成文件不可靠,用 powershell fsutil
powershell -c "fsutil file createnew C:\Users\Administrator\Desktop\uptest.bin 10485760"
curl -s --noproxy "*" -o /dev/null -w "%{speed_upload}" --upload-file uptest.bin https://speed.cloudflare.com/__down
curl -s --proxy http://127.0.0.1:10808 -o /dev/null -w "%{speed_upload}" --upload-file uptest.bin https://speed.cloudflare.com/__down

# 出口 IP 验证(实测出口可能≠节点库里的地址!)
curl -s --proxy http://127.0.0.1:10808 https://ipinfo.io/ip

# 重要:curl -o /dev/null 报 0 B/s 可能是假象;下载到 /tmp 真实文件再判(退出码 23=写入失败,23 不是链路问题)
```

## 验证清单
- [ ] 端口 10808/10814 LISTENING
- [ ] `curl -x http://127.0.0.1:10808 https://www.google.com` 通(代理本体健康)
- [ ] 下载真实文件到 /tmp 成功(链路通,`-o /dev/null` 的 0 B/s 不可信)
- [ ] 应用走 TUN 正常(应用侧不要设 10808 自定义代理)

## 参考资料
- `references/session-2026-08-04.md` — 本次完整诊断记录(配置原文/规则转储/实测数据/Telegram案例)
