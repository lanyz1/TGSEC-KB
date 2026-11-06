---
name: pyinstaller-exe-reversing
description: >-
  测绘引擎·Reveal source from PyInstaller-packed .exe (Python).
owned: true
tier: ops
pack: survey-skill
---

# pyinstaller-exe-reversing（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/pyinstaller-exe-reversing/`

溯源（仅标记）：`hermes/security-research`

---

# PyInstaller EXE Reversing

## Step 0: Detect PyInstaller (before anything else)

```bash
python3 -c "
import re
data = open('target.exe','rb').read()
for name, sig in [('PyInstaller', b'Py_InitializeFromInitConfig'), ('MEIPASS', b'_MEIPASS'),
                  ('PyInstaller2', b'PyInitConfig_Create'), ('PyInstaller3', b'Failed to extract %s')]:
    if sig in data: print('FOUND:', name)
"
```

PyInstaller markers: `Py_InitializeFromInitConfig`, `PyInitConfig_Create`, `_MEIPASS`, `site_import`, `Failed to extract %s`. If found → it's a Python app; the .pyc files are recoverable.

`strings` is often missing in git-bash/MSYS → extract strings with Python regex instead:
```python
import re
strings = re.findall(rb'[\x20-\x7e]{6,}', open('target.exe','rb').read())
```

## Step 1: Extract the archive

```bash
python3 -m pip install pyinstxtractor-ng   # also pulls pycryptodome + xdis
python3 -m pyinstxtractor_ng target.exe
# → target.exe_extracted/  (CArchive files + PYZ.pyz_extracted/)
```

Output tells you: PyInstaller version, Python version, entry point (`main.pyc`), file count.

## Step 2: Load .pyc bytecode (marshal)

Python 3.12 pyc header is **16 bytes** before the marshal blob. Header sizes vary by version — loop:

```python
import marshal
data = open('main.pyc','rb').read()
code = None
for skip in [16, 20, 24, 28, 32]:
    try:
        code = marshal.loads(data[skip:]); print('OK skip', skip); break
    except Exception: pass
```

**CRITICAL PITFALL**: run this from a directory WITHOUT the extracted `struct.pyc` — the extracted `struct.pyc`/`os.pyc` shadow stdlib modules → `ImportError: bad magic number in 'struct'`. Run from `/tmp` or pass absolute paths.

## Step 3: Dump the structure

```python
def dump_funcs(c, indent=0):
    print('  '*indent + f'FUNC: {c.co_name} (args={c.co_argcount})')
    for const in c.co_consts:
        if hasattr(const, 'co_consts'): dump_funcs(const, indent+1)

def collect_strings(c, out):
    for const in c.co_consts:
        if isinstance(const, str): out.append(const)
        elif hasattr(const, 'co_consts'): collect_strings(const, out)
```

- `co_consts` strings → URLs, API paths, hardcoded keys, error messages (Chinese messages are gold for understanding purpose)
- `co_names` → identifiers, module imports, and **module-level constants referenced by functions** (e.g. `WS_BASE`, `APP_AID`) — their VALUES are in the top-level `co_consts`
- Function tree gives the full app architecture (classes, connection loops, signing algorithms)

## Step 4: Pivot to discovered infrastructure

1. Extract all IPs/URLs: `re.search(r'\d+\.\d+\.\d+\.\d+', s)` over collected strings
2. Check `data/` folder next to the exe — tools keep runtime config there (`settings.json`, `accounts.json`, `*.log`) revealing proxy APIs, intervals, account formats
3. Probe the license/update server the exe phones home to:
   - `nmap -sT -Pn -T4 -p 1-10000 <ip>` (many "open" low ports = possibly filtered/honeypot, verify with real connection)
   - Enumerate `/api/*` paths from the extracted strings
   - Update servers often expose: `GET /update/info?software_code=XX` (version + download URL), `POST /update/upload` — **frequently unauthenticated** → RCE on every client that auto-updates
4. Common Windows-tool patterns: machine-code + license_key auth, heartbeat endpoints, ECDSA-signed license files, proxy rotation APIs

## Pitfalls

- **PYZ extraction silently skipped on Python version mismatch.** pyinstxtractor/pyinstxtractor-ng prints `[!] Skipping pyz extraction` (or extracts PYZ as empty) when the running interpreter ≠ the build's Python version. Fix: `uv python install <build_ver>` (e.g. `3.12`), find the exe with `uv python find 3.12`, then rerun the extractor with that exact `python.exe`. You only get the app's custom modules (`app.pyc`, etc.) after PYZ is properly extracted.
- **Disassembling newer bytecode with older `dis` crashes.** Python 3.11 `dis` on a 3.12 pyc fails with `IndexError: tuple index out of range` (cmp_op table). Use the *matching* interpreter for `dis`; plain `marshal.loads` + recursive `co_consts` string walking is version-agnostic and works anywhere (good first pass for keys/URLs).
- **Never inline multi-line Python in `terminal()`** via `python3 -c "..."` — nested quotes break constantly (5+ failures this session). Write a `.py` file with write_file, then run `python3 file.py`. Applies to ALL Python-embedding, not just reversing.
- **docker exec runs INSIDE the container**: host `/tmp/foo` is invisible there. Use `docker cp host_file container:/tmp/` first; curl `-F "file=@..."` paths must be container paths.
- `pycdc` needs cmake+make (often absent on Windows) — fall back to marshal + constant/bytecode analysis instead of full decompilation.
- `pip install pyinstxtractor-ng` may downgrade pycryptodome (its pin) — harmless for extraction, reinstall 3.23 if other tooling needs it.
- Sanitize before analyzing: check VirusTotal-style hashes first, and if the tool is a spam/scam bot, treat its infrastructure as hostile (the "update server" may push malicious updates to thousands of victims).
- **Not every `.exe` is PyInstaller — verify first.** Check the PE machine field: PyInstaller Python apps can be x86 or x64, but if `pyinstxtractor` fails with "Missing cookie, unsupported pyinstaller version or not a pyinstaller archive", the exe is NOT PyInstaller. Also: an app whose folder contains a full `resources/app.asar` + Electron-style files may be a native app (Qt5/C++) with a **decoy asar from another product** — the exe never loads it. Confirm with: `app.asar` string count in the exe (0 = unrelated), rename-aside-and-run test, and PE arch (Qt/C++ native exes are often x86). See `electron-asar-reversing` SKILL.md "第一步先验证" section for the full checklist.
- PE section names may look corrupted/garbled in packed binaries — don't trust section parsing; the PyInstaller markers in raw bytes are the reliable signal.

## Support files
- `references/sixinbida-session.md` — worked example: 私信必达.exe (Douyin mass-DM bot) full analysis + its unauthenticated update-upload server.
- `references/license-crack-recipe.md` — license.json + machine_id 授权工具的破解还原配方：HMAC-SHA256 签名骨架、base64 拆碎常量的还原（含开发者拼接 bug 截断密钥的陷阱：以运行时实际值为准）、get_machine_id 算法复刻、伪造 license.json 步骤、运行时"吊销-自愈"循环（.bak 双份防删）、_license_guard 只查本地的验证技巧。
- `references/rebuild-patched-exe.md` — 修改字节码后**重建整个 onefile exe**：marshal 层 CodeType patch（改常量/换 get_machine_id 函数体 → license 变通用）→ ZlibArchiveWriter 重建 PYZ（package typecode 致命坑：src_path 必须指向 `__init__.pyc`，否则 importlib 相对导入崩）→ 手写 CArchive TOC+cookie（CArchiveWriter 的 's'/'m' 分支有编译/头部断言坑）→ bootloader 拼接。
