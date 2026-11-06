---
name: windows-file-forensics-and-migration
description: "文件被删/消失/回收站还原/批量移动报WinError5时用:回收站$I取证+安全迁移。"
---

# Windows 文件删除取证与安全批量迁移

两件事共用一套纪律：**(1) 事后判定"文件怎么没的、什么时候没的、能不能还原"；(2) 动大量文件时保证零丢失且能自证。**

触发场景：整理/归档一堆文件、文件凭空消失、回收站还原、`WinError 5 Access denied` 移动失败、需要证明"一个文件都没丢"。

## 0 铁律（先读）

1. **mtime ≠ 删除时间。** `$R` 文件的修改时间、以及 PowerShell `Shell.Application` 的 `ModifyDate`，都是文件的**原始修改时间**。真实删除时刻只存在于同名的 `$I` 文件里。拿 mtime 当删除时间会导出完全错误的结论（实测踩坑：回收站列表显示 9/9，实际删除就发生在 5 分钟前）。
2. **没做字节级比对，不许说"零丢失"。** 移动/整理后必须逐文件比对（相对路径 + 字节数），`源 ⊆ 目标` 才算复制完成。目录大小相近、文件数相近都不是证据。
3. **拿到精确删除时刻后立刻做并发归因**（进程表 + agent 会话库），否则会误判成自己的脚本干的。
4. **报失败要报对原因。** `WinError 5` 是 Access denied —— 先分清是**只读属性**还是**进程句柄**，两者处置完全不同。
5. **环境可能被并发使用。** 同机常同时跑多个 agent 会话（共享桌面、共享 memory，会互相覆盖/删除）。动任何共享路径前先查并发。

## 1 Windows 回收站取证（$I / $R 配对）

`C:\$Recycle.Bin\<SID>\` 下每个被删对象有两个文件：

| 文件 | 内容 |
|---|---|
| `$I<6位随机>` | 元数据（原始完整路径 + FILETIME 删除时间） |
| `$R<6位随机>` | 文件实体本体（保留原后缀） |

`$I` 结构（Vista+ 版本 2）：

```
偏移  长度  含义
0     8     Header (版本号 2)
8     8     文件大小
16    8     删除时间 FILETIME (UTC)  ← 唯一可信的删除时刻
24    4     文件名长度 (字节, 含 \0)
28    ...   原始完整路径 (UTF-16LE)
```

- 列出全部被删对象 + 真实删除时间 + 原名：`scripts/recycle_probe.py`
- 按关键字还原回原位（绝不覆盖同名）：`scripts/recycle_restore.py`
- `ls -la "/c/\$Recycle.Bin/"` 的目录 mtime 只是粗粒度线索，**不能当证据**。

**FILETIME 换算的坑**：`datetime(1601,1,1) + timedelta(microseconds=ft/10)` 得到的是 **UTC**。必须 `.replace(tzinfo=timezone.utc).astimezone()`；对 naive datetime 直接 `.astimezone()` **不做换算**，会静默返回 UTC 值 —— 8 小时时差足以把"刚刚发生的删除"看成"三天前"。

## 2 "谁删的" 归因阶梯

按顺序排除，每级都要给可核验证据：

1. **自己的脚本**：查脚本日志。只用 `shutil.move` / `shutil.rmtree` 的脚本**不会**产生回收站记录（走 `unlink` / 直接删）。回收站里有条目 = 不是它们干的。
2. **外部进程占用/来源**：`Get-CimInstance Win32_Process` 过滤 `CommandLine`/`ExecutablePath` 含目标路径 —— 找谁正在使用、或从该目录启动（活进程从待移动目录启动是常见隐患）。
3. **agent 并发**：按时间窗查各 profile 会话库，看每个 session 那一刻执行了什么。
   DB：`<hermes>/profiles/*/state.db`，表 `messages`（`session_id / role / tool_name / content / tool_calls / timestamp`，timestamp 为 **epoch 秒**）。
   一条命令：`scripts/who_touched_path.py <关键字> <分钟数>`
4. **回收站 `$I`**：把精确到秒的删除时刻回填进上面的时间窗对齐。
5. 以上都排除，才轮到系统级候选（同步客户端 / 杀软 / 清理工具 / Shell 批量删除）。
   **判别特征**：5 秒内连删多个不同类文件 = 批量删除；单文件零星删除才更像人工。

### 2.1 杀软删除（Defender）：确认 → 还原 → 复验

**杀软删除不进回收站** —— 回收站是空的但文件没了，第一嫌疑就是 AV，别在 `$I` 上白费功夫。

确认（一次拿到精确被删路径 + 时刻，直接对得上归因时间窗）：

```powershell
Get-MpComputerStatus | Select RealTimeProtectionEnabled, AntivirusEnabled
Get-MpThreatDetection | Sort InitialDetectionTime -Desc | Select -First 8 InitialDetectionTime, Resources
```

`Resources` 给出被删的完整路径，`InitialDetectionTime` 就是删除时刻。被判为 HackTool 的成组工具
（frpc / chisel / 远程控制类）会**反复触发**：每重新落地一次就被再删一次，时间戳呈周期性 —— 不要把它
误读成“有多个进程在删”。

还原顺序**不能颠倒** —— 先把排除铺好再落地，否则恢复瞬间又被删：

```powershell
Add-MpPreference -ExclusionPath 'D:\DIR\tools\x\frpc','D:\DIR\tools\y\chisel'
Expand-Archive 'D:\DIR\_av_blocked_tools.zip' -DestinationPath 'D:\DIR' -Force
```

- 排除写**具体文件路径**而不是整个目录：只放开被拦的那几个，目录里其余工具仍受实时保护。
- 排除项**不要撤销** —— 撤了下次扫描照样删；不想要了就接受文件再次消失。
- 还原后等 ~8 秒再复查是否还在，然后**逐个 md5 与源头比对** —— 只比大小不够，AV 可能留半截文件。
- 源头本身不可达时：把被删文件单独存 zip 长期保留（Defender 不扫 zip 内部），随用随取。

## 3 安全批量迁移（移动文件而不丢证据）

**动手前**（这几步能避免砸掉用户正在用的东西）：

- 扫运行中进程的 `CommandLine`：凡从"待移动目录"启动的进程 → 该目录保持原位，或先征得同意（实例：代理客户端从桌面目录启动，一动就断网）。
- 找 `%~dp0` 相对依赖组：`.bat` + 同目录 `.py`/`.exe` 必须整组一起移动或一起留。
- 解 `.lnk` 的 `TargetPath`，判断是否会变死链（`WScript.Shell.CreateShortcut`）。
- 大目录/多分类的移动一律**先 dry-run 输出分类清单 → 用户确认 → 再执行**（`background=true`，跨盘 10GB 级要几分钟）。分类脚本按"规则表 → 未匹配落 `99_未归类`"，不要硬塞错类。
- 数量对不上账时用 `os.listdir` 复核，别信 `ls | wc -l`（漏隐藏文件，如 `desktop.ini`）。

**执行后**（失败项处置）：

- `WinError 5 [Access is denied]` 报在**源路径**上、且是**只读文件**（`.git/objects/*` 是典型 444）→ 真因是 `shutil.move` 跨盘回退 `copytree + rmtree`，而 **`rmtree` 删不掉只读文件**。此时目标往往已经复制完整。
- 正确顺序：**先验证目标完整**（逐文件比对源 ⊆ 目标，且目标文件数 ≥ 源残留数 ⇒ 复制已完成、源只是残留）→ 清只读属性 → 删残留。
- **不要**因为报错就重跑一遍复制；**更不要**在验证前删任何源文件。
- `scripts/verify_subset_then_clean.py SRC DST --clean` 就是干这个的。
- 收尾写 `_整理日志.txt`（逐条移动/失败记录）+ `_归档索引.md`（每类条目清单），让用户能自行核对。

## 4 Pitfalls

- 把 `$R` / `Shell.Application` 的 mtime 当删除时间（铁律 1）。
- FILETIME 不做显式 UTC 换算（§1）。
- 分类脚本里用 `if name in DIR_MAP` 判断"是不是目录"：`DIR_MAP` 的键是**目标目录名**，永远匹配不上 → 必须 `if isdir:` 再 `for sub, names in DIR_MAP.items(): if name in names`。这个 bug 会让整段分类逻辑静默失效（表现为全部落进"未归类"）。
- 只读 + 跨盘移动失败后直接删源 = 真丢文件。
- 归因只查 Hermes 会话库就下结论：外部进程（Shell/同步/杀软）根本不在库里，必须结合进程表 + 回收站时间戳；
  但**回收站空 ≠ 没人删** —— 杀软删除不入回收站，此时改查 `Get-MpThreatDetection`（§2.1）。
- 多 agent 会话并发时连 memory 都会被别的会话改写（本类任务亲历：写入因并发覆盖而 batch 失败）——写共享状态前先确认没有别的会话在同域作业。

## 5 支持文件

- `scripts/recycle_probe.py` — 枚举回收站，输出真实删除时间($I) + 原始路径 + 实体大小
- `scripts/recycle_restore.py` — 按关键字把 `$R` 还原回 `$I` 记录的原路径，不覆盖同名
- `scripts/verify_subset_then_clean.py` — 逐文件校验 源 ⊆ 目标，通过后才清理源残留（先清只读）
- `scripts/who_touched_path.py` — 进程表 + 全 profile 会话库：那一刻谁碰了这个路径
- `references/windows-move-pitfalls.md` — 跨盘移动/只读/占用/长路径 的行为细节与实测失败样本
