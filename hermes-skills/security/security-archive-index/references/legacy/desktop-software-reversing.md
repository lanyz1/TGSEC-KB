<!-- archived from /root/.hermes/skills/security/desktop-software-reversing/SKILL.md on 2026-10-21 -->

---
name: desktop-software-reversing
description: >-
  测绘引擎·逆向 Windows/Electron 软件:卡密授权绕过、asar 解包重打包、后门排查、CTF 提交包。
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/desktop-software-reversing`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/desktop-software-reversing/…')`，不要相对 `references/legacy/` 解析。

# desktop-software-reversing（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/desktop-software-reversing/`

溯源（仅标记）：`hermes/security-research`

---

## 触发条件
- 逆向 Windows 桌面软件找授权绕过 / 卡密破解 / 免费激活
- Electron 应用(app.asar)解包与重打包
- 找软件后门、硬编码凭证、授权服务器、外连地址
- 制作"双击即进"的破解提交包(CTF 靶场交付)

## 识别打包类型
- Electron: 目录含 `LICENSE.electron.txt` / `resources/app.asar` / `locales/*.pak` / `ffmpeg.dll`
- VMProtect 加壳: PE 区段含 `.svmp1`(pefile 检查),字符串全加密,导入表仅基础系统 DLL
- Electron 主二进制常伪装成 `.dll`(如 main.dll,176MB,PE32+ GUI)→ 可直接 `cp main.dll app.exe` 运行

## Office 宏木马排查 (xlsm/xls/docx 别双击)
用户给的 Office 模板/文档先验货再信任。`.xlsm/.docx` 就是 zip，宏在 `xl/vbaProject.bin`（二进制压缩，但可读字符串直接暴露意图）：
```bash
unzip -p suspect.xlsm xl/vbaProject.bin | strings | grep -iE "http|dropbox|docs.google|reg|WScript|Shell|\.exe|ALLUSERSPROFILE|AppData"
```
判定恶意宏的高危信号（2026-08 实测 `Qavlixor卖家端批量上传商品模板.xlsm` 中招）：
- 从 `dropbox.com` / `docs.google.com` 下载载荷（如 `Synaptics.rar`）→ 写入 `%ALLUSERSPROFILE%\Synaptics\Synaptics.exe` 并执行
- 写注册表 `HKCU\...\Excel\Security\VBAWarnings=1`（关闭宏安全提示）
- 释放物文件名特征 `~\$cache1` / `~\$cache1.exe`；若桌面上已有同名 PE 文件 = 宏已跑过
清理：用 PowerShell 移回收站（可恢复）`[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(path,'OnlyErrorDialogs','SendToRecycleBin')`（静态方法，`::` 调用；`New-Object` 实例调用会报 MethodNotFound）。工作表为空 + 宏文件却几十 KB = 高度可疑，别为"模板内容"去解析它。

## 标准流程
1. 解包 asar:`npx --yes @electron/asar extract resources/app.asar out/`;改完 `npx --yes @electron/asar pack out/ resources/app.asar`,重打包后 grep 验证改动进包
2. 主进程 `out/dist/main/main.js`(压缩单行但可读)重点找:
   - 授权服务器 `fu="http://IP:port"` / `license_key`(electron-store 键名)
   - 启动令牌检查 `if(process.env.Xxx_LAUNCH_TOKEN!=="...")process.exit(0)` → **删掉即可免启动器直启**
   - 授权验证函数(axios POST /api/check {key, machine})→ 改为 `return {code:1,msg:"ok",expire:"2099-12-31",days_left:99999}`
   - 机器码 `node-machine-id`(读 Windows 注册表 MachineGuid)
   - 轮询 `setInterval(..., 8h)` — **启动不立即触发**;无 key 时 UI 默认不锁定 → 软授权设计缺陷,不输入卡密直接可用
3. 渲染进程 `dist/assets/index.*.js`: 查 license-expired 事件处理(UI 是否强制锁定);preload.js 看暴露的 IPC
4. 启动方式: 原加壳 exe 改名后 VMProtect 自校验常失败(静默退出)→ 直接用 Electron 主二进制(改名 .exe)+ 已删 token 检查的 asar
5. 验证: 查 `%APPDATA%/<app>/app.log`(Application started)+ tasklist 进程存活;F12 常被拦截(before-input-event preventDefault)

## 卡密绕过三条路
| 方案 | 做法 | 适用 |
|---|---|---|
| 改验证函数 | So() 直接 return {code:1} | 最简,完全离线,推荐 |
| 假授权服务器 | fu→127.0.0.1 + 本地 HTTP 返回 code:1 | 中间人演示 |
| 改 MachineGuid | 注册表 MachineGuid | 仅单因子时有效 |

## 提交包制作(CTF 交付)
- 修改版目录 = 主二进制改名 + resources/app.asar(改后)+ 全部 DLL/pak/locales(缺一不可运行)
- 打包: python zipfile ZIP_DEFLATED(1.2GB→~450MB);zip 后 testzip 验证完整性
- 交付说明(writeup): 逆向过程 + 弱点分析表 + 修改点前后对照 + 验证结果 + 防御建议
- 用户偏好: 纯脚本自动化,不依赖用户手动看图/点 GUI;交付"解压→双击→直接进入"的 zip

## Pitfalls
- 修改 asar 前先 taskkill 运行中的进程(文件占用)
- main.js 是压缩单行,patch 用唯一子串;lint 报错(node 跑不了 electron 文件)属预期,不影响打包
- 无 license_key 时 UI 默认不锁定 → 8 小时内直接可用(软授权)
- electron-store 数据在 `%APPDATA%/<package-name>/config.json`(无此文件=从未存过 key)
- 日志目录名可能与软件名无关(复用旧项目名,如 douyin-ip-query)
