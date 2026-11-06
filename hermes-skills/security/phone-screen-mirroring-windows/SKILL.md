---
name: phone-screen-mirroring-windows
description: >-
  测绘引擎·Use when 用户要把 iPhone/安卓投屏或远程控制到 Windows 电脑,或爱思投屏报错排查.
owned: true
tier: general
pack: survey-skill
---

# phone-screen-mirroring-windows（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/phone-screen-mirroring-windows/`

溯源（仅标记）：`hermes/productivity`

---

# 手机屏幕投屏 / 远程控制 Windows 电脑

## 先讲给用户的结论（三句话）
- **安卓**：直接 scrcpy（免费开源完美，USB 调试 + 有线/无线）。
- **iPhone 分两半**：**看屏幕** = 免费方案很多（爱思助手实时屏幕、LetsView、开源 AirPlay 接收端）；**操控** = Windows 下没有免费方案 —— 苹果私有协议锁死，所有能反控的都要「AirPlay 投屏 + 电脑蓝牙 BLE 模拟键鼠 + iPhone 开辅助触控」且收费（傲软投屏 ApowerMirror ¥88/年 < AirDroid Cast 会员 ¥30/月）。iOS 18 官方"iPhone 镜像"免费但**仅 Mac**。
- **微软 Phone Link（手机连接）对 iPhone 不支持看屏和操控**（只有通知/短信/电话），直接排除。

## 方案矩阵
| 需求 | 推荐 |
|---|---|
| 免费看屏（有线，可操控） | 爱思助手「实时屏幕」（i4.cn，免费，键鼠操控） |
| 免费看屏（无线） | LetsView 幕享 / 开源 AirPlay 接收端 |
| 反控 iPhone | 傲软投屏 ApowerMirror（蓝牙反控，¥28/360分钟 或 ¥88/年）；AirDroid Cast（高级会员） |
| 只看不控、零安装 | 开源接收端（见下） |
| 群控/批量 | 鹰眼中控（商用） |

## 开源方案（看屏免费，手机上零安装）
底层几乎都是 **UxPlay**（AirPlay 接收器内核）：
- **Airplay2OnWindows**：C#/.NET 8，`AirPlay-win-x64.zip` 免安装解压即用，国产中文文档，AirPlay 2 镜像+音频
- **1PhoneMirror**：`1PhoneMirror-x.y.z.msi`，手机形状窗口、自带截图/录屏，额外支持安卓 scrcpy 和 Miracast
- **pcairplay (AirPlayPC)**：PowerShell 封装 UxPlay，蓝牙模拟键鼠反控仅 Linux 版实验功能

用法：电脑跑接收端 → iPhone 控制中心 → 屏幕镜像 → 选电脑名。要求同一 WiFi + **Bonjour/mDNS 服务在运行**（iTunes 装过就有）。

## 系统诊断命令（Windows git-bash）
```bash
# 服务健康检查
sc query "Apple Mobile Device Service"
sc query state= all | grep -iE "i4|apple|bonjour"
# 蓝牙是否可用（反控前置条件）
powershell.exe -NoProfile -Command "Get-PnpDevice -Class Bluetooth | Select-Object Status, FriendlyName | Format-Table -AutoSize | Out-String -Width 120"
# GitHub 发布包探测（国内可达，确认开源项目有无现成 release）
curl -s https://api.github.com/repos/<owner>/<repo>/releases/latest | grep browser_download_url
```

## 坑位
- 投屏时手机必须**解锁亮屏**；锁屏密码 / FaceID / 部分系统设置页无法远程操作（苹果限制，非软件问题）。
- 数据线必须是 **MFi 认证/数据线**，纯充电线不行。
- 爱思投屏与**直播软件（抖音直播伴侣/视频号/快手/OBS）驱动冲突**是"初始化失败"类报错最常见根因。
- 台式机插**机箱后置 USB 口**。
- git-bash 里给 PowerShell 传复杂 `Where-Object {$_.xxx}` 会被 bash 引号吃掉、静默返回空 → 用 `Select-Object | Format-Table | Out-String` 代替。

## 详细步骤
- 傲软投屏反控 iPhone 6 步、AirDroid Cast 连接方式、爱思助手实时屏幕完整流程：见 references/ios-windows-mirroring-details.md
- 爱思助手 "-445 初始化失败" 官方排查顺序：见 references/aishou-445-troubleshooting.md
