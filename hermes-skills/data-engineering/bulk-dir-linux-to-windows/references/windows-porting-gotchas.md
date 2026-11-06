# Windows 移植:两个反复咬人的坑

## 坑 1:`pip` / 原生程序不认 git-bash 的 `/d/...` 路径

```
ERROR: Invalid requirement: '/d/cehui_pull/tools_dl/binwalk-src'
                                   ^ Expected package name
Cannot open file /d/cehui_pull/xxx.zip : [Errno 2] No such file or directory
```

看起来像"包装不上/依赖编译失败",**实际只是路径写法错**。

| 场景 | 错误写法 | 正确写法 |
|---|---|---|
| pip 装本地目录 | `/d/proj/src` | `D:/proj/src` |
| python 程序读文件 | `/d/proj/a.zip` | `D:/proj/a.zip` |
| bash 内建 cd | `cd /d/proj` ✅ | (内建才认) |

**判断口诀**:`cd`/`ls` 能用的 `/d/...` 路径,一旦传给 **pip / python / 任意 .exe**,
必须换成 `D:/...`(正斜杠也 OK)。

## 坑 2:Unix 专属模块(`pwd` / `grp` / `termios` / `fcntl`)在 Windows 不存在

```
ModuleNotFoundError: No module named 'pwd'
```

**别急着判"这个工具没 Windows 版"** —— 很多 Linux 工具只是顺手用了 POSIX 模块,
写个 shim 就能跑。binwalk 2.3.x 就卡在 `pwd`(extractor.py 里查当前用户名/家目录)。

丢一个 `pwd.py` 到 `site-packages/`:

```python
import os

class struct_passwd(tuple):
    def __new__(cls, n, p, uid, gid, gecos, d, sh):
        return super().__new__(cls, (n, p, uid, gid, gecos, d, sh))
    pw_name = property(lambda s: s[0]);  pw_passwd = property(lambda s: s[1])
    pw_uid  = property(lambda s: s[2]);  pw_gid    = property(lambda s: s[3])
    pw_gecos= property(lambda s: s[4]);  pw_dir    = property(lambda s: s[5])
    pw_shell= property(lambda s: s[6])

def _cur():
    n = os.environ.get("USERNAME") or "user"
    h = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return struct_passwd(n, "x", 1000, 1000, n, h, "cmd.exe")

getpwuid = getpwnam = lambda *a: _cur()
def getpwall(): return [_cur()]
```

同类可 shim 的:`grp`(无脑给空列表)、`fcntl`/`termios`(纯逻辑工具往往用不到真实现)。
**先看报错缺哪个模块、代码里到底用它干什么**,再决定 shim 还是放弃。

## 坑 3:装本地源码树时 `pip install <路径>` 会连带拉依赖

源码装的工具(如 binwalk 2.3.x)若依赖里含无法编译的包,先 `--no-deps` 装上,
再按报错一个个补缺的依赖 —— 比让它自动解析依赖链更快定位问题。

```bash
pip install --ignore-installed --no-deps "D:/proj/tool-src"   # 先装上本体
pip install pycryptodome ncompress capstone                    # 再补运行期依赖
```
