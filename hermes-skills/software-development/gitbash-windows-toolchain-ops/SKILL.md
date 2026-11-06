---
name: gitbash-windows-toolchain-ops
description: Run Linux CLI tools under git-bash on Windows.
---

# 在 Windows 的 git-bash(MSYS)里跑 Linux 向工具

场景:用 git-bash 跑 Linux 向的 CLI 工具/脚本、装 Python 包、处理中文文件名。
下面每一条都是踩过并验证过修法的 —— 按顺序照做,别现场试。

## 1. 传给原生程序的路径必须是 `D:/...`,不能是 `/d/...`

| 场景 | 错误写法 | 正确写法 |
|---|---|---|
| pip 装本地目录 | `/d/proj/src` | `D:/proj/src` |
| python 程序读文件 | `/d/proj/a.zip` | `D:/proj/a.zip` |
| 任意 .exe 的参数 | `/d/...` | `D:/...` |
| bash 内建 cd/ls | `cd /d/proj` ✅ | (只有内建认) |

**为什么**:MSYS 的路径转换只面向 shell 内建命令;交给 pip / python / 原生 exe 的 `/d/...`
会被当成字面量,报 `Invalid requirement: '/d/...' Expected package name` 或
`No such file or directory`。

**这个错误的伪装性极强**:它看起来像「包装不上 / 依赖编译失败」,很容易误判成环境问题而放弃用工具。
看到包名/文件路径报错**先检查路径写法**,再怀疑依赖。

★ **最危险的变体是「静默跳过」**:Python 里 `os.path.exists('/d/...')` 与 `open()` 对错误路径**不抛异常**(只返回 False / 抛 FileNotFound),于是
「过滤掉不存在的文件再加载」这种写法会把**整个数据源悄悄丢掉** —— 不报错、不中断、后续逻辑照跑。
⇒ **任何批量加载都必须打印/断言加载条数**(与 `wc -l` 对不上就是路径 bug,不是「文件是空的」)。
实测:一份 1.3 万条的字典因路径写法只加载到 1237 条,正是靠条数对不上才发现。

同理,`PYTHONPATH` 要传 Windows 路径且用 `;` 分隔:

```bash
_SP="$ROOT/.venv/Lib/site-packages"
command -v cygpath >/dev/null && _SP="$(cygpath -w "$_SP")"
export PYTHONPATH="$_SP${PYTHONPATH:+;$PYTHONPATH}"
```

## 2. locale:`LANG=zh_CN.UTF-8` 会让 `grep -P` 和 Perl 系工具罢工

中文 Windows 默认 `LANG=zh_CN.UTF-8`,MSYS 工具里会报:

```
grep: -P supports only unibyte and UTF-8 locales
```

**修法**:跑之前覆盖成 UTF-8 英文 locale(MSYS 自带 `en_US.UTF-8` / `C.utf8`):

```bash
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
```

`LC_ALL=C` **不行**(同样不满足 `-P` 的要求；**但只做字节比较的 `sort`/`uniq` 反而必须 `LC_ALL=C`**,见 §9)。典型受害者:Perl / bash 写的扫描脚本、
任何内部用 `grep -P` 的工具。**给这类工具做一层包装脚本**,在包装里固定 locale,
比每次手敲环境变量可靠。

## 3. `winget` 必须前台跑

后台/无 tty 环境跑 winget 会报 `stdin is not a tty`,而且是**静默失败**(退出码 0)。
放到前台重跑立刻成功。装完后要**新开 shell** 或手动把
`%LOCALAPPDATA%\Microsoft\WinGet\Links` 加进 PATH 才能调到命令。

## 4. 杀进程用 PowerShell,`taskkill //F` 在 git-bash 里无效

```bash
powershell -NoProfile -Command "Stop-Process -Id <pid> -Force -ErrorAction SilentlyContinue"
```

git-bash 会把 `//F` 之类参数转义坏,报 `Invalid argument/option`。批量按名字杀:
`Stop-Process -Name <a>,<b> -Force`。

## 5. 带中文文件名的压缩包:别用 MSYS tar / bsdtar 解

两者都会把 tar 里的 **UTF-8 名按 GBK 解释**,解出 `娴嬬粯寮曟搸` 这种乱码目录,
部分条目还报 `Invalid empty pathname: Unknown error`。

用 Python tarfile 显式指定编码:

```python
import zstandard, tarfile
dctx = zstandard.ZstdDecompressor()          # pip install zstandard
with open(SRC, "rb") as f, dctx.stream_reader(f) as reader:
    tf = tarfile.open(fileobj=reader, mode="r|", encoding="utf-8")
    for m in tf:
        tf.extract(m, path=DEST, set_attrs=False)   # set_attrs=False 免权限报错
```

~4000 entries/s。后续还要处理 Windows 非法文件名(`\ : * ? " < > |` +
0x00–0x1F 控制字符 → `_`,净化后撞名的加 `~N` 后缀),否则会静默互相覆盖。

## 6. 装 Windows 版工具的三条路(按优先级)

```bash
# ① winget(先 search 拿准确 ID;必须前台跑)
winget install --id Insecure.Nmap --accept-package-agreements --accept-source-agreements

# ② GitHub releases(winget 没有的)
#   不存在的 URL 形式:.../releases/latest/download/<name>_windows_amd64.zip   ← 404
#   正确形式:先拿版本号再拼 URL
v=$(curl -sI https://github.com/<org>/<repo>/releases/latest | grep -i '^location:' | sed 's#.*/tag/##' | tr -d '\r\n')
curl -sL -o t.zip "https://github.com/<org>/<repo>/releases/download/$v/<name>_${v#v}_windows_amd64.zip"

# ③ pip(注意公共 venv 可能装不进去)
```

- **git 不走系统代理**:`git clone` / pipx 内部 git 报
  `Failed to connect to github.com port 443` 而 curl **同时是通的** ⇒
  curl 是靠显式 `-x` 才通,git 得靠环境变量:`export HTTP_PROXY=... HTTPS_PROXY=...`。
- **上游仓库搬仓**:报 404 或 clone 下来只有一个 `Moving home` 提交 ⇒ 换镜像源
  (例:exploitdb 从 GitHub 搬到 GitLab),别当成网络问题。
- **公共 venv 装不进包**时不要死磕(报 `uninstall-no-record-file` 或
  `WinError 5 拒绝访问 ...\*.pyd` = 无 RECORD 元数据 / 文件被占用):
  给项目建独立 venv,再用上面的 `PYTHONPATH` 挂过去。

## 7. 后台任务通知会延迟到达

同一个批次的下载/安装任务,完成通知可能**晚几十分钟陆续到达**,内容是早已处理完的
中间失败日志。看到这类通知**先核对当前终态**,别当成新问题重新排查一遍。

## 8. 批量自检(语法/编译检查)不要写盘

`py_compile.compile(f, cfile=os.devnull)` 在 Windows 上**必然失败**(`nul is a non-regular file`),
于是批量语法检查会报 **100% 失败** —— 看着像所有脚本都坏了,其实检查器本身坏了。

```python
import glob
for f in sorted(glob.glob("scripts/*.py")):
    src = open(f, encoding="utf-8", errors="replace").read()
    compile(src, f, "exec")        # 纯内存语法检查, 不写盘、不产 __pycache__
```

**元规则:一批检查里「全部失败」且在客户端就失败,先怀疑检查器/路径,再怀疑被检对象。**
实测:412 个脚本被判「全部编译失败」,换 `compile()` 后 **0 错误**。

**同类 —— 探针/抓取脚本不要把响应丢 `/dev/null`**:MSYS 下 `curl -o /dev/null` 实测过 exit 23 与失真读数;一律**把每个响应落盘到真实文件**再判读 —— size/body 都要用于复判,真实文件还支持批量结束后复算,不必重发请求。

## 9. 交付 zip:条目分隔符是硬指标,打包别用 Compress-Archive

- PowerShell `Compress-Archive` 在 Windows 上会把条目名写成 **`src\utils\request.ts`**(反斜杠):
  该包在 Linux/macOS 解压会得到一堆带反斜杠的怪文件名 ⇒ **不可交付**。且它**不支持排除目录**
  (想剔 `node_modules` 只能手列路径,必漏)。
- 正解:Python `zipfile` + `os.walk`,条目名一律 `/`:
  ```python
  import os, zipfile
  EXCLUDE = {"node_modules", ".git", ".vite"}
  with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
      for dp, dns, fns in os.walk(ROOT):
          dns[:] = [d for d in dns if d not in EXCLUDE]
          for fn in fns:
              full = os.path.join(dp, fn)
              z.write(full, os.path.relpath(full, ROOT).replace(os.sep, "/"))   # ★
  ```
  并在脚本里自证 `[n for n in z.namelist() if "\\" in n] == []`。
- **换工具视角验包**(别只跑自己的打包脚本):
  ```bash
  export LC_ALL=C                     # 中文名会让 sort 报 multibyte 错(§2 注)
  unzip -Z1 pkg.zip | head -3         # 看分隔符与顶层名
  unzip -Z1 pkg.zip | wc -l           # 条目数
  unzip -Z1 pkg.zip | grep -cF '\'    # 反斜杠残留,须 0
  unzip -Z1 pkg.zip | grep -c '^node_modules/'
  ```
  **用 `-Z1` 不要用 `-l`**:`-l` 的列切分遇空格/中文名会错位。
- 三个校验假阴性(全踩过):
  1. 中文名在终端乱码 ⇒ **不要用 `grep -Fxq` 精确比对中文名**(会假报「缺失」);
     改数 `^docs/` 这类前缀的条目数,或只对 ASCII 名逐项校验。
  2. 别假定包里有外层文件夹前缀(`-Path 'ROOT\*'` 与 `zipfile` 打的包都**不带** wrapper 目录)。
  3. `sort` 前先 `export LC_ALL=C`,否则中文名直接报
     `sort: string comparison failed: Invalid or incomplete multibyte or wide character`。

### 交付包内容自检(包交给客户前)

```bash
cut -d= -f1 .env.production | head -30      # 只列键名;值永不打印到终端
grep -rlE "accessKeyId|accessKeySecret|secretKey|LTAI|AKID|-----BEGIN|privateKey|jwtSecret" \
  src --include=*.ts --include=*.vue
```

命中要看**上下文定性**:表单字段名(如短信通道 `*_secret_id`/`*_secret_key`)不是凭据值;
README/交付说明里写明「本包不含口令 / token / AccessKey / 私钥 / 证书」;
内部脚本与中间报告统一归进 `_internal/`,包体保持干净。

## 10. 内联 `-Command` / `node -e` 里的 `\`、`$`、正则会被 bash 改写

bash 会先吃一层转义:`node -e "...\\w..."` 里的 `\\w` 到 JS 手上变成 `w`
(正则失效、**静默 0 处改动**,看起来像「没有匹配项」);
`powershell -Command "... -replace '\\' ..."` 会变成非法正则报「正则表达式模式 \ 无效」;
`$var` 未转义时被 bash 先展开成空串。

**这类命令不是「偶尔不稳」而是必坏** ⇒ 把逻辑写成 `.py` / `.js` / `.ps1` 文件再执行,
命令行长什么样都不影响语义;`$`/反斜杠/正则多的活得直接落脚本。

## 11. 改 Windows 上的文本文件:先判换行风格,写入后独立复核

Windows 侧反复编辑过的文本文件**换行风格不统一**(同一目录下有的 LF、有的 CRLF),而 `patch` 是字面匹配:

- **多行 `old_string` 必须匹配目标文件真实的换行**:对 CRLF 文件用 `\n` 拼 old_string ⇒ **静默不匹配**;而**单行**修改仍然成功 ⇒ “部分成功”极易被误读成“整批都成了”。动手前先判风格:
  `raw = open(p, "rb").read()` 比 `raw.count(b"\r\n")` 与 `raw.count(b"\n")`;CRLF 就把 old/new 全用 `\r\n` 拼(用 `chr(13)+chr(10)` 拼,避开多层转义里把转义符写丢)。
- **判“写入成功”不许看返回值的真值**:`patch()` 返回 dict(**恒为真**),`if patch(...): print("ok")` 永远打印成功 —— 实测因此漏报“整段小节根本没插进去”。改判 `r.get("success")` / `r.get("diff")`,并**再 grep 一次刚插入的锚点字符串**(或 `wc -l`/`wc -c` 对增量)独立复核。
- 元规则:**“批量写入成功”必须由目标的最终状态自证,不能由调用方的返回摘要自证。**

## Pitfalls

- 改写 Windows 上的文本文件前先判换行风格:多行 `patch` 用 `\n` 拼 old_string 对 CRLF 文件静默不匹配(单行修改照样成功)。
- 判写入成功不许看工具返回值的真假(`patch()` 返回 dict 恒为真):查 `success`/`diff` 字段,并再 grep 一次刚插入的锚点独立复核。

- 路径写法错会被误读成「包装不上/依赖编译失败」—— 看到路径出现在报错里,先查写法。
- `LC_ALL=C` 并不能修 `grep -P`,必须 `en_US.UTF-8` / `C.utf8`。
- winget 的静默失败没有报错声 —— 退码 0 但什么都没装,必须核实版本号。
- 中文名解压后立刻 `find`/`du` 统计可能拿到中间态,等多几秒再统计。
- 打包交给客户/下游的一律用 Python `zipfile`(`Compress-Archive` 的 zip 在 Linux 上条目名带反斜杠,且不能排除目录)。
- 中文名 + `grep -Fxq` 比对 = 假「缺失」;`unzip -l` 列切分不可靠 ⇒ 用 `-Z1` 再数前缀条目。
- 带 `\` / `$` / 正则的命令别内联(`node -e`、`powershell -Command`),落脚本文件再跑。
