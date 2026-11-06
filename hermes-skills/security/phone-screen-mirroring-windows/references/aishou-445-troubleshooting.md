# 爱思助手 实时屏幕 "-445 初始化失败" 排查

含义：投屏服务初始化失败（爱思官方归类为"有线投屏时提示初始化设备失败"，是已知经典报错）。
特征：软件、服务、驱动都在运行也可能报 -445。

## 排查顺序（官方口径，按成功率排）
1. **重启投屏服务**：爱思投屏/实时屏幕首页找"重启服务"按钮；或右下角托盘完全退出（含爱思投屏）后重开
2. **拔插线 + 重启手机**：拔 USB → iPhone 彻底关机开机 → 重插 → 弹"信任此电脑"点信任输密码；手机必须解锁亮屏
3. **关直播/投屏类软件**：抖音直播伴侣、视频号助手、快手直播、OBS 等全退；拔线等 10-15 秒重插再试（驱动冲突是头号根因）
4. **换 USB 口**：台式机插机箱后置口；确认线是数据线不是纯充电线
5. **临时关杀毒/防火墙**：360/电脑管家退出；防火墙弹窗点允许
6. **重装**：i4.cn 下最新版覆盖安装

## 机器侧快速诊断（git-bash）
```bash
sc query "Apple Mobile Device Service"          # 应 RUNNING
sc query state= all | grep -iE "i4|apple|bonjour"
tasklist | grep -iE "i4|airplay|apple|itunes"
```
健康参照（2026-08 实机）：Apple Mobile Device Service RUNNING、i4AirPlayerService/i4ToolsService/Bonjour Service 均在；安装目录 C:\Program Files\i4AirPlayer + C:\Program Files\i4Tools9；进程 i4Tools.exe + i4AirPlayer.exe + i4AirPlayerService.exe。→ 服务全活仍报 -445，基本就是驱动加载被拦/服务需重启，走上面顺序。

## 备用路线
- 修不好就别恋战：换 LetsView（免费看）/ 傲软投屏（付费反控）/ 开源 AirPlay 接收端（看）
- 反向线索：i4 系产品同源（实时屏幕/爱思投屏/爱思投屏Pro/爱思远控），同源问题可能同报错，不必重复试全套
