<!-- archived from /root/.hermes/skills/productivity/directory-organization/SKILL.md on 2026-10-21 -->

---
name: directory-organization
description: Use when tidying a cluttered dir (desktop/downloads).
---

> 归档卡：原目录 `/root/.hermes/skills/productivity/directory-organization`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/productivity/directory-organization/…')`，不要相对 `references/legacy/` 解析。

# 目录整理 / 桌面归档

用户说「整理桌面 / 整理文件夹 / 归档一下 / 清理下载目录」时用本技能。

## 铁律(先读,违反必返工)

1. **原地整理优先**。默认在目标目录**内部**建分类文件夹,不要把文件搬去别的盘。
   - 为什么:搬到外部归档目录后用户找不到文件,会回头要你重新出清单——一次都别犯。
   - 只有用户明确要求移出时才移出;移出时**必须**同时交付可检索的索引文件,并在报告里写清新位置。
2. **运行依赖与日常入口永不归档**:
   - 快捷方式 `.lnk` 默认全部留在顶层(用户天天点)。
   - 有活进程以该目录为程序目录/工作目录的(例如代理客户端跑在 `目录\客户端\`)。
   - `%~dp0` 启动器:`.bat` 与它同目录调用的脚本是**一组**,必须整组同处。
   - 凭据/私钥/交接文档:留在顶层伸手可及处,不要埋进文件夹。
3. **交付层不是杂物**。该用户的渗透报告约定是「存 `D:\渗透\<目标>_recon\` 并复制桌面」——桌面上的报告是有意的交付/展示位,清理时不能扫走。
4. **计划 → dry-run → 确认 → 执行 → 对账**。执行前给出「目标目录 → 项数/大小」的分类预览;结束后项数必须对账(整理前 == 移走 + 保留 + 自己新增的索引/日志)。
5. **拿不准的不硬塞分类**。宁可进 `99_未归类` 并在报告里列出,也不要归错——归错的报告比没归的更难找。

## 流程

### 1 盘点
- 顶层逐项统计:类型 / 文件数 / 大小 / mtime。按 mtime 分桶(今天 / 近 3 天 / 更早)找出活跃与陈旧。
- 单独看最大的 N 项:GB 级目录通常是数据导出或交付包,策略要和文档分开。
- Windows 上跑 Python 脚本,开头写 `sys.stdout.reconfigure(encoding='utf-8')`,否则中文输出乱码;脚本文件存 `$LOCALAPPDATA/Temp`,用 `python <native-forward-slash-path>` 调用。

### 2 依赖侦察(动任何东西之前)
```bash
# 活进程引用了目标目录(工作目录被占 = 移不动)
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*<DIR>*' } | Select ProcessId,Name,CommandLine"
# 快捷方式的真实目标(判断是否指向目录内部)
powershell.exe -NoProfile -Command "Get-ChildItem '<DIR>\*.lnk' | ForEach-Object { \$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\$_.FullName); '{0} -> {1}' -f \$_.Name, \$s.TargetPath }"
# 脚本里硬编码的绝对路径(移动后必须同步改写)
grep -rn --include='*.py' --include='*.bat' --include='*.cmd' -e 'Desktop' -e '<DIR>' .
```
- 被活进程占用的目录:**不动**,报告用户。绝不为了移动而 kill 进程。
- `.bat` 用 `%~dp0` 时,配套脚本一起移动或一起留下。
- 侦察到的硬编码路径,移动后**同步改写**(见步骤 5),否则用户下次跑脚本直接报错。

### 3 分类(dry-run)
- **按内容定归属,不只看文件名**:批量读文档前 3 行标题,确认它属于哪个项目/目标再归档。同一台机器常同时跑多个目标,文件名往往不带目标名(同一批 `作业报告_第N轮.md` 可能全属同一个案子)。
- **按项目/目标聚合,而不是按扩展名散开**:同一个目标的报告(md)、数据(csv)、目录放一处——用户找东西的心智是「这个项目的东西在哪」。
- 大目录(GB 级订单/导出数据)单独一类。
- 空文件、系统残留(`~$*`、`._cache_*`、`__pycache__`)、疑似重复的 zip:进 `_待清理\`,**不要直接删**,等用户确认。
- dry-run 打印「目标 / 项数 / 大小 + 逐项清单」给用户过一眼,再执行。

### 4 执行
- 同盘移动是 rename,秒级;跨盘是复制+删源,GB 级会明显慢——这是优先原地整理的另一个理由。
- 目标同名时改名 `_dup2`,不要覆盖。
- 每一步写移动日志(`OK <name> -> <target>` / `FAIL <name> : <err>`):对账和排错全靠它。

### 5 核对(必做,不许跳过)
- **项数对账**:整理前项数 == 移走 + 保留 + 你新增的索引/日志文件。对不上就查,别放过。
- 每个 FAIL 都要查因,不要当噪音:
  - **`WinError 5 Access is denied` 且路径指向源** = 只读文件。跨盘 `shutil.move` 走 `copy2` + `rmtree`,而 Windows 上 `os.remove` 对只读文件拒绝,于是**副本已完整、源残留一部分**,表象是「移动失败」。git 的 `.git/objects` 默认只读,最容易踩。
  - 处理:递归比对 **源 ⊆ 目标**(相对路径相同 + 字节大小一致)之后,才清掉源的只读属性(`os.chmod(p, stat.S_IWRITE)`)并删残留。**不要盲目重试,也不要重新复制**。
- 移动后发现文件「凭空消失」:先查回收站再下结论(见 `references/windows-file-forensics.md`)。
- 移动了带硬编码路径的脚本目录:同步 `str.replace` 修好路径,并在报告里说明「脚本依然可跑」。

### 6 索引(交付的一部分)
- 生成 `_索引.md`:顶层结构 + 各文件夹三层明细,让用户 **Ctrl+F 搜文件名就能定位**。这是防止「找不到文件」的关键交付物。
- 最终报告给:结果对比表(项数/大小/磁盘变化)、最终结构树、保留清单及理由、待用户确认项(如 `_待清理\`)。
- 报告里如实区分「我做的」和「不是我做的」(例如整理前后发现的环境状态变化)。

## 共享主机上的并发会话风险
多 agent 会话并行跑同一台机器时,它们共享桌面/工作目录/memory:
- 整理期间文件可能被**别的会话**改写或删进回收站;memory 条目也可能被别处改写(能把你刚写的冲掉)。
- 开工前侦察:查最近活跃会话(`state.db` 的 `messages` 按 timestamp 分组),确认没有别的任务正在写同一目录;最近数小时无改动才是安全窗口。
- 异常删除取证:回收站 `$I` 元数据能给出**精确删除时刻 + 原始路径**。判断归属的判据——**自己的脚本只用 move/rmtree,不进回收站**;回收站里出现 = 外部进程所为。
- 越权改动如实报告并还原,不要静默处理。

## 支持文件
- `references/windows-file-forensics.md` — 回收站 `$I` 解析、活跃会话窗口查询、进程/快捷方式取证命令。
- `templates/organize_dir.py` — dry-run/`--go` 两段的整理脚本骨架(KEEP 集 + 关键词分组 + 对账 + 日志 + 索引),复制改配置即可。
