## Core Workflow (static-first)
1. **Identify runtime**: PyInstaller (onefile → `_MEIxxxxx` temp dir, `main.dll` / `python3xx.dll`), Nuitka (native `main.dll`, `ufndata.*` string markers), native C++.
2. **Extract**: for PyInstaller onefile, run it and grab the temp-extracted `main.dll` (each launch re-extracts to a NEW dir — patch the currently-running instance's copy or use runtime memory patch).
3. **Strings**: search 卡密/license/会员已到期/VIP已到期/登录成功 in the DLL. Note: Nuitka strings are stored as `u`-prefixed constants in `.rdata`; direct RIP-refs are often **0** — they go through Nuitka object/constant tables, so xref hunting must look at pointer tables, not just `lea [rip+x]`.
4. **Find the check**: locate the login/verify function (e.g. `fndata.login`), the `Status` field comparison, the expiry string usage. Prefer static disasm (capstone/Ghidra) over blind runtime hooking.
5. **Patch**: equal-length byte patch (jump flips `JE↔JNE`, NOP failure branch, `mov eax,1; ret`), or runtime memory patch via Frida if disk patch is blocked.
6. **Repack**: PyInstaller → rebuild archive or swap patched DLL back into the bootloader layout.

