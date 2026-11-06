# PyInstaller onefile exe 修改字节码后完整重建（marshal patch + PYZ + CArchive）

来源：私信必达.exe 破解的终极方案。场景：**不只是提取分析，而是要把修改后的 .pyc 打回 exe**（例如把 `get_machine_id()` patch 成固定值、把授权服务器 URL 改成不可达地址），交付一个改动后的可执行文件。

完整链路：**marshal 层改 code object → 重建 PYZ.pyz → 重建 CArchive → 拼 bootloader**。全程手写格式，不依赖 CArchiveWriter 的编译路径（它有坑，见下）。

## Step 1: marshal 层 patch .pyc（改常量 / 换函数）

```python
import marshal, types
HEADER = open(src,'rb').read()[:16]           # 3.12 是 16 字节
code = marshal.loads(open(src,'rb').read()[16:])

# 递归重建 CodeType：替换字符串常量 / tuple 常量 / 整个子函数
def patch_code(co):
    new_consts = []
    for c in co.co_consts:
        if isinstance(c, str) and c in REPL_STRINGS:
            new_consts.append(REPL_STRINGS[c])
        elif isinstance(c, tuple) and c in REPL_TUPLES:   # base64 分片常量
            new_consts.append(REPL_TUPLES[c])
        elif isinstance(c, type(co)):
            if c.co_name == "get_machine_id":             # 换整个函数体
                new_consts.append(fixed_fn_code)
            else:
                new_consts.append(patch_code(c))
        else:
            new_consts.append(c)
    return types.CodeType(co.co_argcount, co.co_posonlyargcount, co.co_kwonlyargcount,
        co.co_nlocals, co.co_stacksize, co.co_flags, co.co_code, tuple(new_consts),
        co.co_names, co.co_varnames, co.co_filename, co.co_name, co.co_qualname,
        co.co_firstlineno, co.co_linetable, co.co_exceptiontable, co.co_freevars, co.co_cellvars)

# 构造新函数（编译源码取 code object）:
fn_src = f"def get_machine_id():\n    return '{FIXED_MID}'\n"
mod = compile(fn_src, "app.py", "exec")
fixed_fn = next(c for c in mod.co_consts if isinstance(c, types.CodeType) and c.co_name == "get_machine_id")
```

要点：
- **3.12 的 CodeType 签名**：`(argcount, posonly, kwonly, nlocals, stacksize, flags, code, consts, names, varnames, filename, name, qualname, firstlineno, linetable, exceptiontable, freevars, cellvars)` — 没有 `co_lnotab` 了，换 `co_linetable`。
- 修改 `get_machine_id()` → 固定返回值 = **license 变通用**（任何机器可激活），这是把绑定本机机器码的破解版变成全平台通用版的关键。
- 修改后重新 marshal 验证：`marshal.loads` 回来递归扫 `co_consts` 确认旧 URL 全无、新函数在。

## Step 2: 重建 PYZ.pyz（必须用 ZlibArchiveWriter + code_dict）

不能用简单 zip 重压——PYZ 是 zlib 单条压缩的 marshal code object 集合，带 TOC。

```python
from PyInstaller.archive import readers, writers
pyz_reader = readers.ZlibArchiveReader(pyz_path)
code_dict, entries = {}, []
for name, entry in pyz_reader.toc.items():
    obj = pyz_reader.extract(name)          # 默认返回 code object（非 raw）
    if obj is None:
        entries.append((name, "-", "PYMODULE")); continue   # namespace pkg
    code_dict[name] = obj
    is_pkg = (entry[0] == 1)                # PYZ typecode 1 = package
    if is_pkg:
        entries.append((name, os.path.join(*name.split("."), "__init__.pyc"), "PYMODULE"))
    else:
        entries.append((name, name.replace(".", os.sep) + ".pyc", "PYMODULE"))
code_dict["app"] = marshal.loads(patched_app[16:])   # 替换目标模块
writers.ZlibArchiveWriter(new_pyz_path, entries, code_dict=code_dict)
```

**致命坑 — package typecode**：src_path 的 basename 必须是 `__init__`（即指向 `__init__.pyc`），writer 才把它标成 PYZ_ITEM_PKG(typecode 1)。如果所有模块都用 `name.pyc`，`importlib`、`importlib.metadata` 等包全变 module(0) → 启动直接 `ImportError: attempted relative import with no known parent package`。**必须按原 PYZ toc 的 typecode 判断 is_pkg 并分别构造 src_path**（本会话第 2 次构建就栽在这，importlib 崩）。

## Step 3: 重建 CArchive（手写，别用 CArchiveWriter）

CArchiveWriter 两个坑：
- `'s'` 类型条目（pyiboot01_bootstrap / pyi_rth_* / main）在 writer 里走 `get_code_object()` **编译源码**——但原始存档存的是裸 marshal code（`\xe3...` 开头），编译直接 `SyntaxError: source code string cannot contain null bytes`。
- `'m'` 类型条目存的是**裸 marshal**（无 16 字节 pyc 头），writer 的 'm' 分支 `assert data[:4] == BYTECODE_MAGIC` 会挂。

所以**手写 TOC + cookie**，字节级搬数据、只换 PYZ：

```python
import struct
COOKIE_MAGIC = b'MEI\x0c\x0b\x0a\x0b\x0e'
COOKIE_FMT = '!8sIIII64s'; COOKIE_LEN = struct.calcsize(COOKIE_FMT)
TOC_FMT = '!IIIIBc'; TOC_LEN = struct.calcsize(TOC_FMT)

# 1. 定位 cookie（文件尾部 rfind COOKIE_MAGIC）→ archive_start = cookie_pos+COOKIE_LEN-archive_length
# 2. bootloader = exe_data[:archive_start]  （原样保留）
# 3. 解析原 TOC: 每项 (entry_length, offset, data_length, uncompressed, compress, typecode) + name
# 4. 逐项: 读原数据(zlib解压 if compress) → 写入新位置 → 记录新 offset
#    PYZ.pyz 项用 Step 2 的新文件字节
# 5. 序列化 TOC: struct.pack(TOC_FMT + f"{name_len}s", ...)
#    name_len = len(name)+1, 且 entry 16 字节对齐 (TOC_LEN+name_len) % 16 == 0
# 6. cookie: struct.pack(COOKIE_FMT, MAGIC, archive_length, toc_offset, toc_len, pyvers, pylib)
#    archive_length = len(数据区) + len(TOC) + COOKIE_LEN
# 7. out = bootloader + 数据区 + TOC + cookie
```

TOC 项 `struct.pack(TOC_FMT + f"{name_length}s", entry_len, offset, comp_len, data_len, compress, typecode_byte, name_b)`——`Ns` 格式自动补 `\0`。name 编码 utf-8 + 结尾 0 字节。

## Step 4: 验证 + 测试

```bash
# 结构验证: 新 exe 能被 CArchiveReader 读、PYZ 里 app 模块在、patch 无残留
PYBUILD python -c "from PyInstaller.archive import readers; r=readers.CArchiveReader(new_exe); print(r.toc['PYZ.pyz']); pr=readers.ZlibArchiveReader(r.extract('PYZ.pyz')); app=pr.extract('app')"
# 运行验证: 启动 exe → 探本地 API（若 app 是 Flask 类，curl /api/<业务端点>）
# 全链路检查点: ①启动不崩(importlib 正常) ②license 状态 offline:true ③业务接口 success:true
```

## 环境要点
- 需 Python 3.12 + PyInstaller（`uv venv pybuild_env && uv pip install --python pybuild_env/Scripts/python.exe pyinstaller`）
- 系统 Python 若与打包版本不同，marshal.loads 会失败——**用与目标 pyc 相同版本的解释器**做 marshal 操作
- exe 被占用时 `PermissionError` → 先杀进程再重建
- 交付：patch 版 exe + 通用 license.json（固定机器码）+ .bak 双份 + README
