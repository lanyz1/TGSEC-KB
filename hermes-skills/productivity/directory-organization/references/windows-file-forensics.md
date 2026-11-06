# Windows 文件取证速查(整理/移动类任务用)

整理过程中出现「文件移动失败」「文件凭空消失」时,先用这里的办法拿证据再下结论。

## 1 回收站:精确定位谁在什么时刻删了什么

回收站目录:`C:\$Recycle.Bin\<SID>\`(当前用户 SID 形如 `S-1-5-21-...-500`)。

每个被删项是一对文件:
- `$R<ID>` — 文件/目录的真实内容(括号里的扩展名是原始扩展名)
- `$I<ID>` — 元数据:原始路径 + 删除时刻

### `$I` 二进制结构(Vista+ / version 2)
```
offset 0   8 bytes  header(版本标识)
offset 8   8 bytes  文件大小
offset 16  8 bytes  删除时间(FILETIME, **UTC**)
offset 24  4 bytes  文件名长度(字节, 含结尾 NUL)
offset 28  ...      文件名(UTF-16LE, 绝对原始路径)
```

### 解析代码
```python
import os, struct, datetime

EPOCH = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)

def parse_I(path):
    raw = open(path, 'rb').read()
    size = struct.unpack('<Q', raw[8:16])[0]
    ft   = struct.unpack('<Q', raw[16:24])[0]
    nlen = struct.unpack('<I', raw[24:28])[0]
    name = raw[28:28+nlen].decode('utf-16-le', errors='replace').rstrip('\x00')
    dt   = EPOCH + datetime.timedelta(microseconds=ft / 10)   # FILETIME = 100ns 单位
    return size, dt, name
```

**时区坑**:`dt` 是 UTC。想显示北京时间要自己 `+8h` / `.astimezone(tz)`。
直接对 naive datetime 调 `.astimezone()` **不会**做 UTC→本地转换(它假设传入的就是本地时间),会得到错误的「删除时刻」——别用它。

### 还原
`$R` 就是原文件字节,直接复制回 `$I` 里记录的原始路径即可;之后可选清回收站记录。
比调 Shell 的「还原」动词可靠(后者受中文系统动词名/&锚点影响)。

### 一行列举(带原名)
```powershell
$sh=New-Object -ComObject Shell.Application; $sh.Namespace(10).Items() | ForEach-Object { '{0} | {1} | {2}' -f $_.Name,$_.Path,$_.ModifyDate }
```
注意:`ModifyDate` 是**原始修改时间**,不是删除时间;要判断何时被删必须解析 `$I`。

### 判断归属的判据
自己写的整理脚本只用 `shutil.move` / `shutil.rmtree`,**都不会进回收站**(`os.unlink`/`rmtree` 是直接删除)。
所以:回收站里出现 → 是 Shell 类批量删除(资源管理器 / 同步客户端 / 其他 agent 会话 / 清理工具)所为。
再看移动日志里有没有该条记录,两下对照就能把责任分清楚。

## 2 活跃会话窗口查询(共享主机)

Hermes 会话库:`<hermes>/profiles/<profile>/state.db`(SQLite),`messages` 表字段含 `session_id, role, tool_name, tool_calls, content, timestamp`(epoch 秒)。

```python
import sqlite3, time, datetime
db = r"...\state.db"
lo, hi = time.time()-400, time.time()-100          # 目标时间窗
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
for sid, c, a, b in con.execute(
    "SELECT session_id, COUNT(*), MIN(timestamp), MAX(timestamp) "
    "FROM messages WHERE timestamp BETWEEN ? AND ? GROUP BY session_id", (lo, hi)):
    print(sid, c, datetime.datetime.fromtimestamp(a).strftime('%H:%M:%S'),
                    datetime.datetime.fromtimestamp(b).strftime('%H:%M:%S'))
```
用 `content LIKE '%<关键词>%' OR tool_calls LIKE '%<关键词>%'` 过滤,即可看某时刻各会话在干什么。
多个 profile 都要查(用户可能并行开多个 profile)。

## 3 进程 / 占用 / 快捷方式

```bash
# 谁引用目标目录(工作目录被占 = 移不动)
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*<DIR>*' } | Select ProcessId,Name,CommandLine | Format-List"
# 进程存在性(用 tasklist 避开中文编码干扰)
python -c "import subprocess;print(subprocess.run(['tasklist','/FI','IMAGENAME eq <name>.exe'],capture_output=True,text=True,errors='replace').stdout)"
# .lnk 真实目标
powershell.exe -NoProfile -Command "Get-ChildItem '<DIR>\*.lnk' | ForEach-Object { \$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\$_.FullName); '{0} -> {1}' -f \$_.Name,\$s.TargetPath }"
```

## 4 用默认程序打开文件给用户看
```bash
cmd.exe /c start "" "D:\path\to\file.txt"      # 用默认关联程序打开(记事本等)
```
打开后用 `Get-Process notepad | Select Id,MainWindowTitle` 确认窗口标题,再把路径和内容摘要给用户,不要只说「已打开」。

## 5 只读残留清理
```python
import os, stat, shutil
for dp, dn, fn in os.walk(src):
    for f in fn:
        p = os.path.join(dp, f)
        if not (os.stat(p).st_mode & stat.S_IWRITE):
            os.chmod(p, stat.S_IWRITE)
shutil.rmtree(src)
```
只在**已验证源 ⊆ 目标**之后执行(见 SKILL.md 步骤 5)。
