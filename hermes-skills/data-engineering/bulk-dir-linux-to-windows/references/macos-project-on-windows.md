# macOS 项目搬到 Windows:工具链复原

拿到一个从 Mac 同步过来的项目(仓库里有 `.cursor/skills/`、`arsenal-env.sh` 引用 `/opt/homebrew`、
路径写死 `/Users/<user>/...`)时,Python 那层通常直接能跑,**炸点全在外部工具**。

## 症状

```bash
$ nuclei -update-templates
/usr/bin/bash: /path/tools/arsenal/bin/nuclei: cannot execute binary file: Exec format error
```

看起来像工具没装,实际是 **PATH 里先命中了旧的 mac 二进制**。

## 先普查,别急着装

```bash
ls tools/arsenal/bin/ | wc -l          # 例:178 —— 别被数量骗,多数是断链

# 看真实二进制是什么平台(magic 判定,不靠扩展名)
head -c 4 tools/arsenal/bin/amass | od -An -tx1
#   cf fa ed fe / ce fa ed fe / fe ed fa cf / fe ed fa ce  -> Mach-O(macOS,Windows 跑不了)
#   7f 45 4c 46                                            -> ELF(Linux)
#   4d 5a                                                  -> PE(Windows,能用)
```

**mac 二进制无法"转"成 Windows**:格式(Mach-O/PE)只是表层,系统调用层完全不同
(libSystem/Mach trap vs Win32/NT API)。唯一出路是拿 Windows 官方构建或找替代品。

## 处理:归档,别删

把 Mach-O / ELF 和所有符号链接移到 `bin/_macos-archive/`,只留 PE 和真脚本。

```python
import os, shutil
BIN, ARC = r"...\tools\arsenal\bin", r"...\tools\arsenal\bin\_macos-archive"
os.makedirs(ARC, exist_ok=True)
MACHO = (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xfe\xed\xfa\xce")
for n in os.listdir(BIN):
    p = os.path.join(BIN, n)
    if os.path.isdir(p): continue
    if os.path.islink(p):        # 断链也要处理,否则照样 shadow 新工具
        os.remove(p); continue
    with open(p, 'rb') as f: h = f.read(4)
    if h in MACHO or h == b"\x7fELF":
        shutil.move(p, os.path.join(ARC, n))
```

**坑 1**:`islink` 为 True 的断链,`open()` 会抛异常 —— 先处理链接分支,再读文件头。
只处理"能读出 Mach-O 头的"会漏掉全部符号链接(本例 178 条里漏了 156 条)。

**坑 2**:`bin/` 里还可能有 mac 版 **bash 包装脚本**(`#!/bin/bash` 的 `sqlmap`、`nikto`、`Responder.py`,几十字节)。
它们同样是 PATH 里的 shadow —— `command -v sqlmap` 会指到这些废文件,把 pip 装的正版挡住。一并归档。

## 装 Windows 版:三条路

```bash
# winget(必须前台跑!后台/无 tty 会报 'stdin is not a tty')
winget search <tool>            # 先查 ID
winget install --id Insecure.Nmap --accept-package-agreements --accept-source-agreements

# GitHub releases(winget 没有的:ProjectDiscovery 全家桶)
#   不存在的 URL 形式:.../releases/latest/download/<name>_windows_amd64.zip   <- 404
#   正确形式:先拿版本号,再拼 URL
v=$(curl -sI https://github.com/<org>/<repo>/releases/latest | grep -i '^location:' | sed 's#.*/tag/##' | tr -d '\r\n')
ver=${v#v}
curl -sL -o t.zip "https://github.com/<org>/<repo>/releases/download/$v/<name>_${ver}_windows_amd64.zip"
#   下载偶发 302 + size=0,单独重试即可
```

装完实测版本号,别只看文件存在。

## 在 Hermes 类托管 Python 环境里装包:pip 会双重卡死

公共 venv(这里是 Hermes 自己的)装渗透工具时会连撞两个坑:

```
error: uninstall-no-record-file
× Cannot uninstall cryptography None      ← pip 想升级却卸不掉(无 RECORD 元数据)

OSError: [WinError 5] 拒绝访问。: '...\site-packages\charset_normalizer\md.cp311-win_amd64.pyd'
                                          ← --ignore-installed 硬来,又撞上文件被进程占用
```

**不要跟公共 venv 死磕**。正解:给项目建独立 venv,再用 PYTHONPATH 挂过去。

```bash
cd <项目根>
python -m venv .venv-engine
./.venv-engine/Scripts/pip.exe install --quiet impacket dirsearch smbmap
```

环境脚本里挂载 —— **务必转成 Windows 路径,git-bash 的 /d/... 形式 Python 不认**:

```bash
if [ -d "$ROOT/.venv-engine/Lib/site-packages" ]; then
  _SP="$ROOT/.venv-engine/Lib/site-packages"
  command -v cygpath >/dev/null 2>&1 && _SP="$(cygpath -w "$_SP")"
  export PYTHONPATH="$_SP${PYTHONPATH:+;$PYTHONPATH}"      # Windows 用 ; 分隔
fi
```

验证:`python -c "import impacket"` —— 别只看 pip 说 Successfully installed。

## 写一个 Windows 版环境脚本

原 `scripts/arsenal-env.sh` 引用 `/opt/homebrew`、`node-*-darwin-arm64`(mac 死代码)。
新写一份:把 `$ROOT/tools/arsenal/bin`、winget 的 `WinGet/Links`、`/c/Program Files (x86)/Nmap`、
`/c/Program Files/7-Zip` 挂进 PATH,并**分组逐项 `command -v` 自检**(基础 / 扫描测绘 / 逆向取证),
每次开终端 source 一次就一眼看出缺什么。

## 残留检查

```bash
grep -rl "/Users/" --include=*.py --include=*.sh . | head
```

本例只有 15 个文件写死 mac 路径,且都在边缘目录,主流程不受影响 —— **别一上来就批量替换**,先确认哪些真会被执行到。

## 不必管的

`bin/` 里大量条目其实是:binutils/gcc 工具链(28 个)、gettext(16)、postgres/mysql 客户端(26)、
ncurses/pcre2 —— 这些 Git Bash 自带或引擎根本不调用(`pymysql`/`redis-py` 就够)。
分类后再决定装什么,别按数量硬清单。
