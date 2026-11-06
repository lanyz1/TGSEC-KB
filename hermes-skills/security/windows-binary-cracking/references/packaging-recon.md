# Packaging Recon — PE Entropy, Packer Signatures, PyInstaller/Nuitka Extraction

How to identify how a Windows EXE is packaged and get at the real program, learned cracking `轻云3.8-TXMyW.exe` (122 MB PyInstaller-onefile wrapper around Nuitka-compiled `main.dll`).

## PE section + entropy read (pure Python, no deps)

Read DOS header at `0x3C` → e_lfanew → `PE\0\0` → `machine, num_sections, timestamp` at +4 → optional header magic at pe+24 (`0x20b` = PE32+ x64). Sections at `opt + opt_size`, 40 bytes each:
`name(8) + vsize/vaddr/rawsize/rawptr(IIII at +8) + flags(I at +36)`.

Entropy per section: byte-frequency Shannon entropy. **Interpretation:**
- `.text` small (e.g. 144 KB) + `.rsrc` huge (e.g. 127 MB) with entropy ~8.0 → **onefile wrapper, real payload encrypted/compressed in resources**.
- `.rsrc` ~8.0 across the whole section = the payload is not plaintext; you will NOT find useful strings there.

## Packer / bundler signatures (scan whole file)

| Signature | Meaning |
|---|---|
| `MEI\014\013\012\013\016` cookie near EOF | PyInstaller onefile (legacy layout) |
| `MEI` anywhere | PyInstaller marker (noisy — can be random bytes; confirm with cookie or extraction dir) |
| `onefile_<pid>_<rand>` dir in `%TEMP%` | **PyInstaller 6.x onefile self-extraction** — the goldmine |
| `_MEI<pid>` dir in `%TEMP%` | PyInstaller 5.x onefile extraction |
| `UPX!` | UPX packed |
| `app.asar` | Electron |
| `NullsoftInst` | NSIS installer |
| RCDATA resource id 27 | PyInstaller CArchive container |

## Extraction workflow (fastest reliable path)

**Don't bother unpacking the archive — just run the exe and copy what it extracts.**

1. Launch the target; PyInstaller 6.x creates `%TEMP%\onefile_<pid>_<rand>\` containing the real program: `main.dll` (Nuitka-compiled main module), `python3xx.dll`, `.pyd` extension modules, package dirs (`nicegui/`, `res/`, `static/`), libs.
2. Note: the launcher parent process is a 1-thread no-window stub; the real process is its child (check via `Get-CimInstance Win32_Process -Filter "ParentProcessId=<pid>"`).
3. `main.dll` size ~106 MB ⇒ compiled Python + all deps. **No `.pyc` to decompile.**

## Nuitka identification strings (in main.dll)

- `gi_code is not writable in Nuitka`
- `Module '%s' was actively excluded from Nuitka compilation`
- `<compiled_frame at %p, file %R, line %d, code %S>`
- `u<module config>` style `u<module ...>` names, `a_func_<rand>`, `a_var_<rand>`, `a_tmp_<rand>` symbol naming

Nuitka keeps **Python string constants** (docstrings, format strings, function names) as readable ASCII/UTF-8 in the binary — this is the main intel source.

## String mining that worked

```python
# CJK runs (Chinese business logic, docstrings)
runs = re.findall(rb'(?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf]){2,}', data)
# ASCII strings
strs = re.findall(rb'[\x20-\x7e]{4,}', data)
```

Filter for: `卡密|验证|登录|注册|充值|到期|心跳|服务器|域名线路|请求` and ascii `Token|KEY|aes_key|CryptoKeyPublic|CryptoType|AppId|UserLogin|HeartBeat|GetToken|certificate_number|fnobj`.

Context trick: find a keyword's file offset, then dump `data[idx-8192:idx+8192]` and print nearby ASCII/CJK — module names, header names, and hardcoded values cluster together (e.g. `webview2_token=` right next to `验证请求是否来自合法的 WebView2 窗口`).

## What you get from a good string pass

- Server endpoint: `http://101.35.246.71:18888/Api?AppId=10013` + backup domain
- Hardcoded credentials: `Token: <REDACTED>, `KEY: Szl137976`, AES string `sDxmQP644fafnDK3tGZnFBjA`, full RSA public keys (PEM blocks)
- Local state paths: `C:\JLA\login_prefs.json`, `C:\Windows\winS` / `winSS`
- Module map: `core.auth`, `core.services`, `fndata`, `fndata_client`
