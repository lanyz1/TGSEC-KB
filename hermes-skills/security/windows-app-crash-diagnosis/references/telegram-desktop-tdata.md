# Telegram Desktop 闪退案例 (0xc0000409)

## 症状
- 用户报告"Telegram 一直闪退"
- 实际表现:能用,但打开**特定聊天**时崩溃(不是启动即崩)

## 证据链 (本次诊断顺序)

### 1. 事件日志 (决定性证据)
```
Event Id 1000 (Application Error), ProviderName: Application Error
Faulting application name: Telegram.exe, version: 7.0.6.0
Exception code: 0xc0000409          ← STATUS_STACK_BUFFER_OVERRUN
Faulting module: Telegram.exe        ← 崩在自身代码,非外部 DLL
Faulting application path: D:\Telegram Desktop\Telegram.exe
```
- Id 1001 (WER bucket) 同时出现,Event Name: **BEX64**
- 近 7 天只有 2 次,都在同一分钟(14:52/14:53)→ 刚发生,不是长期反复崩
- 加载模块只有 Telegram.exe + ntdll/kernel32/msvcrt 等系统 DLL → 排除 DLL 注入、输入法/杀软劫持

### 2. 资源排查 (排除法)
- C: 盘 168G 空闲,内存 25.8G/61.6G → 不是资源问题

### 3. 版本时间线 (关键线索)
- `D:/Telegram Desktop/` 下 Telegram.exe + Updater.exe 时间戳 = **2026-07-27 18:16** (刚自动更新)
- 其余文件 (unins000.* 等) = 2026-06-13 → 旧版安装时间
- → 崩溃在 7.0.6 自动更新后出现 → 新版与旧本地缓存的兼容问题

### 4. 应用自身日志 (定位到聊天)
`D:/Telegram Desktop/log.txt` 崩溃前后出现大量:
```
History::unknownMessageDeleted. Peer ID: 3931449353, Message ID: 38440.
```
→ 本地历史数据库与服务器同步时,特定聊天(Peer 3931449353)的记录删除/重建异常

### 5. 环境冲突 (附带发现,与闪退无关但值得提醒用户)
- v2rayN + xray + sing-box 三个代理同时在跑
- Todesk / 向日葵(OrayIddDriver) / GameViewer 三套远程桌面虚拟显卡
- 建议用户只保留一个代理、一个远程软件

## tdata 目录结构 (Telegram Desktop 本地数据)

| 路径 | 内容 |
|---|---|
| `tdata/user_data/` | 本地聊天历史/媒体数据库(本例 1.1G) |
| `tdata/user_data#2/` | 第二账号数据(397M),存在即有第二个账号 |
| `tdata/key_datas`, `tdata/*s` 文件 | 登录凭据(在 tdata 根目录,不在 user_data 里) |
| `tdata/emoji/` | emoji 缓存 |
| `tdata/settingss` | 用户设置 |
| `tdata/dumps/` | 崩溃转储(本例为空) |

**关键**:登录状态在 tdata 根目录,重命名/删除 user_data 不会要求重新登录。

## 修复 (rollback-safe)

```bash
# 1. 杀进程(可能已死,忽略失败)
taskkill //F //IM Telegram.exe 2>/dev/null || powershell.exe -NoProfile -Command "Stop-Process -Name Telegram -Force -ErrorAction SilentlyContinue"

# 2. 重命名备份(同卷 mv 秒级完成,不复制)
cd "D:/Telegram Desktop/tdata"
mv user_data user_data.bak.$(date +%Y%m%d_%H%M)
mv user_data#2 user_data#2.bak.$(date +%Y%m%d_%H%M)

# 3. 启动(用 PowerShell Start-Process,cmd start 在 git-bash 会挂)
powershell.exe -NoProfile -Command "Start-Process -FilePath 'D:\Telegram Desktop\Telegram.exe'"

# 4. 验证:进程存活 + 日志显示重建
sleep 15 && tasklist 2>/dev/null | grep -i telegram
tail -5 "D:/Telegram Desktop/log.txt"   # 应显示重新同步 History::unknownMessageDeleted
```

## 结果
- 重启后进程存活(332MB → 479MB 内存,正常加载),日志显示从云端重新同步历史
- 登录状态保留,无需重新输验证码
- 修复验证标准:让用户打开之前闪退的那个聊天,不再崩 = 成功

## 教训
- "一直闪退"可能是特定动作触发(打开某聊天),不是启动即崩 — 用 clarify 问清触发场景,能大幅缩小排查范围
- BEX64 + 0xc0000409 + faulting module = 应用自身 → 首选本地缓存重建,而非重装
- 先备份(重命名)再动手,可随时回滚;用户确认修复后再清理备份
