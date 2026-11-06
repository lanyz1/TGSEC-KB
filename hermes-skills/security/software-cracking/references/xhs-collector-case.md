# 案例:小红书直播评论采集工具(xhs-live-crawler-electron)破解

> CTF 考核目标,完整破解链,2026-08 实测成功。主程序名"小红书直播弹幕采集工具.exe"。

## 目标概况

| 项 | 值 |
|---|---|
| 包名 | xhs-live-crawler-electron v1.0.0,作者 baixiaolu |
| 结构 | 加壳 exe(VMProtect,.svmp1)+ main.dll(176MB,Electron 主程序改名)+ app.asar(111MB)+ SunnyNet.dll(49MB,未引用) |
| 功能 | playwright 内置 Chromium + WebSocket 劫持采集小红书直播间评论,导出 xlsx |

## 授权系统(逆向结果)

- 授权服务器:`http://49.233.127.44:13818`(`fu` 常量),`POST /api/check` body `{key: 卡密, machine: 机器码}`
- 机器码:node-machine-id → Windows 注册表 MachineGuid
- 启动令牌:main.js 第一行 `if(process.env.XHS_ANON_LAUNCH_TOKEN!=="XHS_ANON_LAUNCHER_20260705_9F2D7C31")process.exit(0)`
- 轮询:每 8 小时(`xu=8*60*60*1e3`),setInterval **启动后不立即执行**
- 存储:electron-store `license_key`,位于 `%APPDATA%\xhs-live-crawler-electron\config.json`
- **软验证缺陷**:无 key 时 UI 不锁定(渲染 JS 无 license 拦截,只在收到 license-expired 事件才 locked),8 小时内直接可用

## 破解改动(共 7 处核心 = 最终版)

1. 删启动令牌检查:`if(process.env.XHS_ANON_LAUNCH_TOKEN... )process.exit(0);` → 删除
2. 授权函数直通:`async function So(e){...}` → `async function So(e){return{code:1,msg:"ok",expire:"2099-12-31",days_left:99999,promote:""}}`
3. (可选)`fu` 改 `http://127.0.0.1:13818`(配合假服务器方案,最终版不依赖)

## 启动器问题与解法

- 加壳 exe **改名后启动静默退出**(壳自校验)→ 放弃
- `main.dll` 实为 PE32+ GUI executable(x64)→ `cp main.dll 最终结果.exe` 直接当主程序
- 主程序与 `resources/app.asar` 同目录即可被 Electron 加载

## 验证

- 日志 `%APPDATA%\douyin-ip-query\app.log`(目录名是作者旧项目"抖音IP查询"的残留!)出现 `Application started`
- 4 个 main.exe 进程(主+GPU+网络+渲染)
- 窗口标题"小红书直播间评论采集助手",直接进入采集界面

## 交付

- 目录清理:删 app_extracted、main.dll 副本、辅助脚本
- 打包:Python zipfile + ZIP_DEFLATED,685 文件 → ~500MB(STORED 模式 1.1GB)
- 提交物:解压后双击"最终结果.exe"直接进入,无需卡密/联网
