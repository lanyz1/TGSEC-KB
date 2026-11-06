<!-- archived from /root/.hermes/skills/security/pyinstaller-exe-re/SKILL.md on 2026-10-21 -->

---
name: pyinstaller-exe-re
description: >-
  测绘引擎·Use when cracking PyInstaller-packed Python .exe files.
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/pyinstaller-exe-re`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/pyinstaller-exe-re/…')`，不要相对 `references/legacy/` 解析。

# pyinstaller-exe-re（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/pyinstaller-exe-re/`

溯源（仅标记）：`hermes/security-research`

---

# PyInstaller EXE 逆向与破解

对 PyInstaller 打包的 Python 可执行文件做逆向：提取字节码 → 定位授权/签名逻辑 → 破解密钥 → 伪造 license 或 patch 字节码 → 重建 exe。

## 识别 PyInstaller

```bash
# 字符串特征
strings xxx.exe | grep -E "_MEIPASS|pyi-|PYZ|PyInstaller|python3[0-9]+\.dll"
# 典型: PyInstaller bootloader 含 "Could not load PyInstaller's embedded PKG archive"
# python312.dll / libpython 存在 + 25MB+ 覆盖段 = PyInstaller onefile
```

## 提取（pyinstxtractor）

```bash
curl -L -o pyinstxtractor.py https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py
python pyinstxtractor.py target.exe
```

**关键 pitfall：PYZ 提取需要与目标相同的大版本 Python。** 用 `uv python install 3.12` 装匹配版本，否则 PYZ 提取被跳过（提示 "run this script in Python 3.12"）。入口通常是 `main.pyc`（bootloader 启动器）。

## 提取字符串（不依赖 dis，跨版本可用）

反汇编需要匹配版本的 `dis`（3.11 的 dis 解 3.12 字节码会 `IndexError: tuple index out of range`），但**提取字符串只需 marshal**，任何 Python 版本都行：

```python
import marshal
with open("app.pyc","rb") as f: code = marshal.loads(f.read()[16:])  # py3.12 头=16字节
def walk(co):
    for c in co.co_consts:
        if isinstance(c, str): strings.add(c)
        elif isinstance(c, tuple):
            for x in c:
                if isinstance(x, str): strings.add(x)
        elif isinstance(c, type(co)): walk(c)
```

重点搜索：`_LICENSE_SIGN_KEY`、`SOFTWARE_CODE`、`AUTH_SERVER`、`license`、`machine`、`http://`、base64 分片元组。

## 定位授权逻辑

模块级 `dis`（用匹配版本 Python）找 `STORE_NAME` 赋值，定位：
- `MACHINE_ID = get_machine_id()` — 机器码生成函数
- `LICENSE_FILE = get_data_path('license.json')` — license 存放路径
- `_compute_license_sig(data)` — 签名算法（通常 HMAC-SHA256）
- `_load_license_unlocked` / `verify_license_online` / `_heartbeat_loop` — 校验+吊销逻辑
- `_is_permanent_revoke_reason` — **永久吊销关键词列表**（"卡密不存在"等）。服务器对无效 key 返回这些词会触发删 license 文件

## 常见混淆：base64 分片

常量常被拆成 base64 分片元组运行时拼接解码：
```python
parts = ('emhp','eGlk','YQ==',...)  # base64.b64decode(''.join(parts)).decode()
```
**逐片解码确认内容**，注意 join 后整体解码可能因中间 `==` 截断——运行时实际密钥可能只是前半段（如 'zhixida'），以 Python 3.12 实测结果为准。

## 机器码算法复刻

典型 Windows 机器码 = `sha256('|'.join([...硬件ID...]))[:32]`：
- `wmic csproduct get UUID`（过滤全F/全0）
- `wmic diskdrive get SerialNumber`（过滤 vmware/virtual/qemu/vbox）
- `wmic bios get SerialNumber`、`wmic baseboard get SerialNumber`
- 兜底：`MAC:<uuid.getnode()>` 或 `RAND:<uuid4()>`（虚拟机/无有效硬件时走 MAC 兜底，稳定可复现）
- 直接在目标机器上跑复刻脚本算 MACHINE_ID（这是 license 里必须匹配的字段）

## 伪造 license.json

```python
import hmac, hashlib, json
payload = '|'.join([license_key, machine_id, activated_at, SOFTWARE_CODE])
sig = hmac.new(SIGN_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
# license.json = {license_key, machine_id, activated_at, expiry, ..., _sig: sig}
```

**关键：同时写 license.json 和 license.json.bak** —— 在线吊销只删主文件不删 .bak，`_load_license_unlocked` 会从 .bak 自动恢复（自愈循环）。

## Patch 字节码（终极方案）

把 AUTH_SERVER_URL/UPDATE_SERVER_URL 改成不可达地址（127.0.0.1:59999），所有在线验证走 ConnectionError → 离线模式，license 永久有效、不吊销、不强制更新：

```python
import marshal, types
def patch(co):
    new = []
    for c in co.co_consts:
        if isinstance(c, str) and c in REPL: new.append(REPL[c])
        elif isinstance(c, tuple): new.append(tuple(REPL.get(x,x) if isinstance(x,str) else x for x in c))
        elif isinstance(c, type(co)): new.append(patch(c))
        else: new.append(c)
    return types.CodeType(co.co_argcount, co.co_posonlyargcount, co.co_kwonlyargcount,
        co.co_nlocals, co.co_stacksize, co.co_flags, co.co_code, tuple(new), co.co_names,
        co.co_varnames, co.co_filename, co.co_name, co.co_qualname, co.co_firstlineno,
        co.co_linetable, co.co_exceptiontable, co.co_freevars, co.co_cellvars)
```
URL 可能藏在 base64 分片里（patch 分片元组），先逐片解码确认。

## 通用化机器码（跨机器交付）

伪造的 license.json 绑定的是**本机** MACHINE_ID，交付给第三方（如 CTF 验证方）会报"机器码不匹配"。解决：不只 patch 常量，而是**用 `compile()` 构建一个返回固定值的函数，替换整个 `get_machine_id` code object**：

```python
def _make_const_fn():
    fn_src = f"def get_machine_id():\n    return '{FIXED_MACHINE_ID}'\n"
    mod_code = compile(fn_src, "app.py", "exec")
    for c in mod_code.co_consts:
        if isinstance(c, types.CodeType) and c.co_name == "get_machine_id":
            return c  # 提取新函数体

fixed_fn = _make_const_fn()
# 在 patch_code 的递归里，当 co.co_name == '<module>' 且子 const 是 get_machine_id 的 CodeType 时：
if co.co_name == "<module>" and hasattr(c, "co_name") and c.co_name == "get_machine_id":
    new_consts.append(fixed_fn)
```

配套：license.json 的 machine_id 也改成同一个固定值（用 forge_license_universal 重新生成）。效果：任何机器运行 patch 后 exe，MACHINE_ID 恒为固定值 → license 通用。**交付打包**：`私信必达_patched.exe` + `data/BD/license.json` + `.bak` 打成 zip（含 README 说明"解压即用，license 已内置"）。注意 exe 数据目录是 `exe同目录/data/<SOFTWARE_CODE>/`，license 必须放对位置。

## 重建 exe（⚠️ 首选：pyinstaller 全量重编译，见\"全量重编译\"节；CArchiveWriter 仅当无法重编译时）

**更正（2026-08 第三关实测）：手动 CArchive 重建（writer 或手写）5+ 轮均产出 bootloader 起不来的 exe，最终靠 pyinstaller 从源码全量重编译成功。** 以下 CArchive 细节保留备查，但**优先走全量重编译**。

```python
from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.archive.writers import CArchiveWriter

reader = CArchiveReader(SRC)                      # 读原包
raw = open(SRC, 'rb').read()
raw_pkg = reader.raw_pkg_data()                   # 注意是方法不是属性！
pkg_start = len(raw) - len(raw_pkg)               # bootloader 长度
bootloader = raw[:pkg_start]

entries = []
for name, (pos, c_len, u_len, uncompressed, typecode) in reader.toc.items():
    data = reader.extract(name)
    fpath = os.path.join(TMPDIR, name.replace('/', os.sep))
    os.makedirs(os.path.dirname(fpath) or TMPDIR, exist_ok=True)
    # ⚠️ 'm'/'M'/'s'/'s1'/'s2' 条目 extract 出来是裸 marshal(无 pyc 头)!
    # 'm' 必须补 16 字节 pyc 头(见下方 typecode 处理), 否则 writer 断言失败
    open(fpath, 'wb').write(data)
    entries.append((name, fpath, 1, typecode))    # compress=1, 保留原 typecode

# ⚠️⚠️ 关键: CArchiveWriter 内部用 open(filename, "wb") —— 会覆盖整个文件!
# 预写 bootloader 再调用 writer = bootloader 被清掉 (输出变成纯 package, 无 MZ 头, exe 起不来)。
# 正确流程: 先 writer 写到临时文件 → 手工拼接 bootloader + package + cookie:
CArchiveWriter(TMP_PKG, entries, 'python310.dll')  # TMP_PKG = package + cookie(88字节)

pkg_raw = open(TMP_PKG, 'rb').read()
pmi = pkg_raw.rfind(b'MEI\x0c\x0b\x0a\x0b\x0e')
w_package = pkg_raw[:pmi]                          # package 数据(含TOC)
# 读 writer 写出的 cookie 字段, 重拼大端 cookie(见下节格式), 或直接沿用
out = bootloader + w_package + w_cookie            # cookie 的 pkg_length 必须 = len(w_package)+88
open(OUT, 'wb').write(out)
```

**Cookie 格式（大端!）—— 最坑的坑，解析错直接浪费 5+ 轮**：
```python
# cookie 在文件尾 88 字节, 大端网络字节序:
#   !8sIIII64s = magic(8) + pkg_length(4) + toc_offset(4) + toc_length(4) + pyver(4) + pylib_name(64)
mi = raw.rfind(b'MEI\x0c\x0b\x0a\x0b\x0e')
magic, pkg_length, toc_offset, toc_length, pyver, pylib = struct.unpack_from('!8sIIII64s', raw, mi)
pkg_start = len(raw) - pkg_length                  # = bootloader 长度
# pkg_length 包含 cookie 自身(88字节): 手工拼接时 new_pkg_length = len(package数据)+88
# 小端 <I 解析会得到巨大垃圾值且不报错, 极易误判"文件损坏"
```
python310.dll 明文就藏在 cookie 的 pylib_name 字段里（文件尾），是快速识别 PyInstaller + 版本的信号。

**TOC 条目布局**（`!IIIIBc` = offset(4)+length(4)+ulen(4)+comp(1)+type(1)，后跟 name 以 \0 结尾、条目总长 16 字节对齐）：
- 每条 = `entry_len(4) + offset(4) + length(4) + ulen(4) + comp(1) + type(1) + name\0 + padding`
- `struct` 条目 entry_len=32（14 字节头 + 'struct\0' + 11 padding）；长名字条目对齐到 16 倍数
- 手写重建时**保留原 TOC 字节流、只改每条前 12 字节的 offset/length/ulen**，name/padding 原样贴回，最不易错

**typecode 语义**（`_write_entry` 源码确认）：
- `'s'/'s1'/'s2'` → writer 用 `get_code_object(dest_name, src_name)` **重新编译源码** → marshal。src 给 .py 路径即可
- `'m'/'M'` → 读 pyc 文件，**断言 `data[:4] == BYTECODE_MAGIC`**（必须带 pyc 头），跳 16 字节头后 marshal。给裸 marshal 会 AssertionError
- `pyi_rth_*` / `pyimod*` / `struct` 等 's'/'m' 条目在包里是裸 marshal，直接写文件喂给 writer：
  - 'm' → 补头 `PYC_MAGIC + b'\0'*4 + b'\0'*4 + struct.pack('<I', len(data))`（PYC_MAGIC=6f0d0d0a 为 3.10）
  - 's' → 若提取出的是裸 marshal 字节而 writer 尝试按源码编译 → 报 `source code string cannot contain null bytes`。改为补 pyc 头 + 以 'm' 类型写入
- 报错 `not enough values to unpack (expected 4, got 3)` = entry 少了 src_name/compress 字段
- 报错 `assert data[:4] == BYTECODE_MAGIC` = 给 'm' 类型传了无头数据（应改传 .py 源码 + 's'，或补 pyc 头）

**重建后必须端到端实测**（结构可解析 ≠ bootloader 能跑）：
```bash
# 1) 结构验证: CArchiveReader(new) 能列出条目 + extract('launcher') marshal.loads 成功
# 2) 运行验证: 用 cmd 启动(见下), 观察 %TEMP%/_MEI* 是否新建 + python 子进程出现
#    ⚠️ 若无新 _MEI 目录 = bootloader 解包阶段就退出 = 包结构/bootloader 版本不兼容
# 3) 最终: 输入任意卡密 → 应 Popen 内层 app_core（%LOCALAPPDATA%/<品牌>/ 下）
```
- **git-bash 里直接 `./xxx.exe` 会把 PE 当 bash 脚本执行**（报 "line 1: MZ...: No such file" 乱码）→ 必须 `cmd //c start "" "C:\\path\\exe"` 或用 PowerShell 启动
- exe 起不来时先查 `Get-CimInstance Win32_Process | Where CommandLine -like '*_MEI*'` 确认解包是否发生

手写重建（第一关方案，writer 不可用时兜底）：
1. `rfind(COOKIE_MAGIC)` 定位 cookie（`MEI\x0c\x0b\x0a\x0b\x0e`），`archive_start = cookie_start + 88 - archive_length`
2. bootloader = exe_data[:archive_start]
3. 解析 TOC：`!IIIIBc` 固定 21 字节头 + 变长 name（16字节对齐）
4. 重建 PYZ：`ZlibArchiveReader` 读原 PYZ（`extract(name, raw=True)` 拿原始字节），替换 app 模块，`ZlibArchiveWriter` 写回。**必须保留 package typecode**（原 TOC typecode==1 的条目用 `__init__.pyc` 作为 src 才能被 writer 识别为 package）
5. 重建 CArchive：按原顺序重写所有条目数据 + TOC + cookie，cookie 里 archive_length/toc_offset/toc_length 重新计算
6. 拼接 bootloader + CArchive → 新 exe

## 全量重编译（最可靠方案，优先于手动重建）

**实测结论（第三关 Dy全域追踪）：手动 CArchive 重建 5+ 轮全部产出\"结构可解析但 bootloader 起不来\"的 exe（无新 _MEI 目录）。放弃手动重建，改用 pyinstaller 从修改后的源码全量重编译，一次成功。** 前提：你有还原/重写后的 launcher 源码 + payload 文件都提取出来了。

```python
# build.py —— 用 pyenv 里的 pyinstaller
import PyInstaller.__main__
PyInstaller.__main__.run([
    r'C:\...\launcher_patched.py',        # 修改后的入口源码
    '--name=目标名_patched',
    '--onefile',
    '--noconsole',                        # GUI 程序无黑框；调试时可先去掉看报错
    '--add-data=C:\...\payload;payload',  # 内层 exe/资源打包为 data (Windows 用分号分隔)
    '--add-data=C:\...\app.ico;.',        # 图标等根级资源用 ;.
    '--icon=C:\...\app.ico',
    '--clean', '--noconfirm',
])
# 输出 dist/目标名_patched.exe
```

关键点：
- **payload 先精简再打包**：原 payload 里的 `.bak_*` 备份（多个 84MB exe）会让 onefile 解包负担过重甚至启动即退。删掉备份只留 app_core.exe + assets + db 等，322MB → 81MB。exe 从 103MB 降到 33MB 且能跑
- **`--noconsole` + onefile + 大 payload 时 exe 可能静默退出**：先去掉 `--noconsole` 或用带日志的 launcher 确认流程走到哪一步（写 log 到 `%LOCALAPPDATA%/<品牌>/xxx.log` 是最快的定位手段）
- 重编译后 `_MEIPASS/payload` 路径不变（`Path(getattr(sys, "_MEIPASS", ROOT)) / "payload"`），launcher 源码里的 `ensure_runtime_files()` 逻辑无需改动
- 用 `pyenv/Scripts/python.exe`（装 pyinstaller 的 venv）跑 build.py；**编译用的 Python 版本要 ≥ 目标 pyc 版本**（3.10 目标就装 3.10 venv）

## 免登录直启改造（CTF 交付要求：双击直接进主程序）

用户/考核方常要求\"双击 exe 直接进入软件内部，无登录框\"。把 Tk 卡密窗 launcher 改造成无 GUI 直启版：

```python
def main():
    save_config(token="<REDACTED>", remember_card=False, card="")  # 预写 license 保证状态完整
    ensure_runtime_files()                       # 复制 payload → %LOCALAPPDATA%/<品牌>/
    if not CORE.exists(): return
    proc = subprocess.Popen([str(CORE)], cwd=str(APP_DIR))  # 直接拉起内层主程序
    threading.Thread(target=apply_window_brand, args=(proc.pid,), daemon=True).start()
    while proc.poll() is None:                   # 守护：主程序退出后自动重启（原版行为）
        time.sleep(5)
    time.sleep(2)
    if proc.returncode != 0:                     # 意外退出重启一次
        try: subprocess.Popen([str(CORE)], cwd=str(APP_DIR)).wait()
        except Exception: pass

if __name__ == "__main__": main()
```
要点：删掉 `tk.Tk()` 窗口与登录按钮；`--noconsole` 打包；启动即 ensure_runtime_files + 拉起内层。验证时**用 Python `subprocess.Popen` 启动测试**（git-bash 的 `cmd //c start` 对 GUI exe 常不显示窗口/进程，subprocess 方式最可靠），再查 `%LOCALAPPDATA%/<品牌>/` 与 `Get-Process -Name 'app_core'` 确认主程序窗口出现。

**最终交付版实测更优（第三关）：用 `os.startfile` 让内层成为独立进程，launcher 干净退出**——Popen+守护循环版在 launcher 退出后内层偶发不存活（数据目录生成了但 tasklist 里没有 app_core）；`os.startfile(str(CORE))` 版本 launcher 返回 rc=0、内层窗口稳定出现：

```python
def main():
    ensure_runtime_files()                       # 内部含预写 license.json
    if not CORE.exists(): return
    try:
        os.startfile(str(CORE))                  # 内层独立进程, launcher 立即退出
    except Exception:
        try: subprocess.Popen([str(CORE)], cwd=str(APP_DIR))
        except Exception: pass

if __name__ == "__main__": main()
```
配套：`ensure_runtime_files()` 里顺手 `CONFIG_FILE.write_text(json.dumps({"token":"...","card":""}))` 预写授权文件，保证内层状态完整（纯 startfile 启动时不会再弹任何验证）。

## 双层 PyInstaller：launcher.pyc 壳 + payload/app_core.exe（第三关模式）

不是所有 PyInstaller 工具都是单层 onefile。**"登录器/壳 + 功能体"双层结构**：外层是薄 PyInstaller（launcher.pyc，只有卡密验证 + 拉起内层），内层是独立 exe（可能又是 PyInstaller，或原生程序），真正功能在内层。

识别特征：
```bash
# ① 入口不是 main.pyc 而是 launcher.pyc / login.pyc / gate.pyc 之类
# ② 解包目录里有 payload/ 子目录, 内含 app_core.exe + app.ico + 数据文件
ls extracted/payload/   # app_core.exe (84MB) + douyin_system.db + config.dat + assets/
# ③ payload 里多个 .bak_fanspro/_fg_addaccount_gate/_visible 备份 = 作者迭代痕迹
# ④ app_core.exe 无 MEI magic = 非 PyInstaller (原生 x64), 或再次 pyinstxtractor
```

launcher 职责（反汇编确认的通用骨架）：
1. `ensure_runtime_files()`：把 `_MEIPASS/payload/app_core.exe` 拷到 `%LOCALAPPDATA%/<品牌>/`（**运行位置是 LOCALAPPDATA，不是 exe 同目录**）
2. 显示 Tk 卡密输入框（`tk.Tk()` + Entry + "验证并启动"按钮）
3. `call('/api/activate', {card, machine_id})` → `{ok, token}` → 存 token → `Popen([CORE])` 启动内层
4. 心跳线程：每 30s `call('/api/heartbeat', {token, machine_id})`，非 ok 则 **kill 内层进程 + 弹"授权已失效"**——比单层工具的吊销更狠（直接杀功能进程）

**破解 = patch launcher 的 `call()`**（不动内层 app_core，因为内层本身不做验证）：
```python
def call(path, payload, timeout=6):
    if path == "/api/activate":  return {"ok": True, "token": "CTF-BYPASS", "message": "激活成功"}
    if path == "/api/heartbeat": return {"ok": True}
    return {"ok": False}
```
配合：入口脚本替换用 's' typecode 源码编译（见上节）。machine_id 变体：`sha256(COMPUTERNAME + "|" + PROCESSOR_IDENTIFIER)`（无硬件 ID，跨机器稳定，天然可交付）。

**服务端协议探测**（判断卡密是服务器校验还是本地）：直接 POST 假卡密，响应语义即协议：
```bash
curl -X POST http://<server>:4001/api/activate -H 'Content-Type: application/json' -d '{"card":"test","machine_id":"x"}'
# {"success":false,"ok":false,"code":"NOT_FOUND","msg":"卡密不存在","forceExit":true}
# code 语义: NOT_FOUND=卡密不存在 / TOKEN_INVALID=token失效 / NO_KEY=缺卡密; forceExit 控制客户端是否退出
```
卡密在服务器数据库 → 爆破无意义，直接走 call() patch。

## 验证

```bash
# 结构验证（用 pybuild_env 的 PyInstaller）
reader = CArchiveReader(new_exe); pyz = ZlibArchiveReader(extract('PYZ.pyz'))
# 确认 app 模块内无残留原 URL
# 运行新 exe，curl 本地 API: /api/auth/status 应显示 licensed:true, offline:true
# 等一个心跳周期（通常60s）确认 license.json 存活、不被吊销
```

## Pitfalls 清单

- PYZ 提取必须匹配 Python 大版本（`uv python install 3.12`）
- 3.11 dis 解 3.12 字节码报 IndexError → 用 3.12
- base64 分片 join 后整体解码可能因中间 `==` 截断，密钥实际值以实测为准
- 永久吊销关键词（"卡密不存在"等）→ 服务器响应会删 license 文件 → 必须有 .bak 自愈
- 在线验证接口可达时伪造 license 会被吊销 → 必须改 URL 走离线模式或屏蔽网络
- **`/api/auth/status` 等状态接口会主动 POST /api/heartbeat 触发在线验证** —— 启动后立刻 curl 该接口就可能被服务器"卡密不存在"永久吊销并删 license 文件。验证时优先 curl 业务接口（如 `/api/accounts`），或等 URL patch 生效后再碰 status
- 吊销后 `_load_license_unlocked` 会尝试 `[license.json, license.json.bak]` 两个路径，从 .bak 加载成功后 `shutil.copy2` 还原主文件 —— 这就是自愈循环，实测确认主文件会恢复
- 防火墙规则对出站拦截在 profile OFF 时无效；route 添加常因权限失败 → patch URL 是最可靠方案
- **CArchiveWriter 可用，前提是 entry 格式对**：4 元组 `(dest_name, src_name, compress, typecode)`，src 给文件路径；'s' 给 .py 源码、'm' 给带头的 pyc。3 元组 → `expected 4, got 3`；'m' 给裸 marshal → `assert data[:4] == BYTECODE_MAGIC`
- **CArchiveWriter 内部用 "wb" 打开输出文件**——预写 bootloader 再调 writer 会被清掉。先 writer 生成到临时文件，再手工拼 bootloader + package + cookie（见上节）
- **Cookie 是大端 `!8sIIII64s`**（magic+pkg_length+toc_offset+toc_length+pyver+pylib_name(64)，共 88 字节，文件尾）。小端解析得到巨大垃圾值且不报错，极易误判。pkg_length 含 cookie 自身，手工拼接时 new_pkg_length = len(package)+88
- **'m'/'s' 条目 extract 出来是裸 marshal**（无 pyc 头）——'m' 需补 16 字节 pyc 头（PYC_MAGIC 6f0d0d0a=3.10）；'s' 若当源码喂 writer 报 `source code string cannot contain null bytes`（pyi_rth_* 就是这种，改补头 + 'm' 类型）
- **git-bash 直接 `./xxx.exe` 会把 PE 当 bash 脚本执行**（报 "line 1: ...: No such file" 乱码）→ 用 `cmd //c start "" "C:\\path\\exe"` 或 PowerShell 启动
- **结构可解析 ≠ 能运行**：CArchiveReader 能读 TOC 只说明包格式对；bootloader 与 writer 生成的 TOC 结构不兼容时 exe 在解包阶段静默退出（无新 _MEI 目录）。重建后必须实测 + 查 `_MEI*` 临时目录确认解包发生
- **手动 CArchive 重建 5+ 轮失败后别再死磕——直接 pyinstaller 全量重编译**（`--onefile --add-data payload;payload --noconsole`，从还原/修改后的源码打包），一次成功。重编译产物的 bootloader 与包结构由官方工具保证一致
- **payload 里多个 `.bak_*` 备份（每个几十MB）会让 onefile 启动即退**：`--add-data` 前先精简（322MB→81MB），exe 从 103MB 降到 33MB 后能跑
- **`--noconsole` 打包的 exe 静默失败时**：先去 `--noconsole` 或给 launcher 加日志（写 `%LOCALAPPDATA%/<品牌>/xxx.log`）定位执行到哪一步
- **验证 GUI 程序用 Python `subprocess.Popen` 启动**：git-bash 的 `cmd //c start` 常不显示窗口/进程导致误判\"起不来\"
- **免登录直启版交付用 `os.startfile` 而非 Popen+守护循环**：Popen 版在 launcher 退出后内层进程偶发不存活；`os.startfile(str(CORE))` 让内层独立运行、launcher 干净退出（rc=0），且应在 `ensure_runtime_files()` 里预写 license.json 保证内层状态完整
- **PYZ 提取必须匹配 Python 大版本**（`uv python install 3.12`；3.10 目标装 `uv python install 3.10`）
- **双层结构**：入口 launcher.pyc + payload/app_core.exe 时，先确认哪层做验证——通常 launcher 验证后 Popen 拉起内层，内层不再验证；patch 外层 call() 即可
- **运行位置可能是 %LOCALAPPDATA%/<品牌>/ 而非 exe 同目录**（launcher 负责拷贝 runtime 文件），交付/测试时别找错目录
- PYZ 重建丢 package typecode → importlib 相对导入报错 "attempted relative import with no known parent package"

## 环境

- 构建环境：`uv venv pybuild_env && uv pip install --python pybuild_env/Scripts/python.exe pyinstaller`
- 本机 Python: python3=3.14, python=3.11, `uv python install 3.12` 可装 3.12（路径 `~/AppData/Roaming/uv/python/cpython-3.12*/python.exe`）
- 3.10 目标：`uv python install 3.10`（路径 `~/AppData/Roaming/uv/python/cpython-3.10.20-windows-x86_64-none/python.exe`）

## 相关
- 双层 launcher+payload 实战全程见 `references/dy-quanyu-tracking-session.md`（Dy全域追踪 第三关：Tk 卡密窗、call()/activate/heartbeat 反汇编、服务器 code 语义、call() patch → 手动重建 5 轮失败 → pyinstaller 全量重编译成功 → 免登录直启版交付）
