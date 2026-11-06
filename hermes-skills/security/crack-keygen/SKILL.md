---
name: crack-keygen
description: Complete software cracking toolkit — key generation, license bypass, binary patching, DRM removal, serial generation, activation bypass, trial…
---

# Crack & Keygen — Complete Toolkit

## Scripts

- `scripts/keygen.py` — RSA/XOR/timed/HWID/name-based key generation
- `scripts/patch_binary.py` — Binary patching: JE→JMP, NOP sled, conditional bypass, hex editing
- `scripts/license_bypass.py` — Android/iOS/SQLite license DB patcher, trial reset, shared_prefs

## Workflow

```
1. Identify Target → strings/objdump/IDA locate check function (checkLicense/verifyKey/validateSerial)
2. Analyze Logic   → reverse key verification algorithm, extract constants/seeds/public keys
3. Bypass Strategy  → patch binary (JMP over check), generate valid keys, spoof server response
4. Implement        → write keygen/patch script, test on target, verify functionality
5. Package          → provide keygen binary or patch instructions
```

## License Verification Patterns

| Pattern | Detection | Bypass |
|---|---|---|
| Name/Serial | Serial derived from username via checksum/algo | Reverse algo, write keygen |
| Public Key (RSA) | License signed with private key, verified with embedded public | Replace public key with self-generated |
| Online Validation | POST license to server, check response | Patch HTTP response / DNS redirect to local |
| Hardware ID Lock | Hash of CPU/disk/MAC compared to license | Hook HWID function, return constant |
| Timestamp/Trial | Check file time / registry key / counter | Reset trial data, freeze time |
| Integrity Check | CRC/checksum of .text section | NOP check or recalculate after patch |
| Obfuscated Check | VMProtect/Themida wrapped, virtualized code | Dump after unpack, trace with x64dbg |

## Keygen Templates

```python
# === Name/Serial Keygen ===
import hashlib
def name_to_serial(name: str) -> str:
    """Generate serial from username via custom hash."""
    digest = hashlib.sha256(name.encode()).hexdigest().upper()
    chunks = [digest[i:i+4] for i in range(0, 16, 4)]
    return "-".join(chunks)  # XXXX-XXXX-XXXX-XXXX

# === RSA Key Replacement ===
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
def replace_rsa_key(original_pubkey_hex: str):
    """Generate new RSA keypair, replace embedded public key."""
    private = rsa.generate_private_key(65537, 2048)
    public = private.public_key()
    new_pubkey = public.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo).hex()
    # Patch binary: replace original_pubkey_hex with new_pubkey at offset found via hex search
    # Then sign licenses with private key
    return new_pubkey, private

# === HWID Spoof Keygen ===
def hwid_spoof_keygen(username: str, fixed_hwid: str = "1234-5678-9ABC-DEF0"):
    """Generate license that encodes a fixed HWID — hook GetVolumeInformation to always return this."""
    data = f"{username}:{fixed_hwid}"
    encoded = hashlib.sha256(data.encode()).hexdigest()[:20].upper()
    return f"{encoded[:5]}-{encoded[5:10]}-{encoded[10:15]}-{encoded[15:20]}"

# === Timed License Generator ===
import datetime
def generate_timed_license(username: str, days: int = 9999):
    """Generate license with far-future expiration."""
    expire = (datetime.datetime.now() + datetime.timedelta(days=days))
    payload = f"{username}|{expire.strftime('%Y%m%d')}|FULL"
    checksum = hashlib.md5(payload.encode()).hexdigest()[:8]
    return f"{payload}|{checksum}"

# === Product Key Generator (Windows-style) ===
import random
def gen_product_key():
    """Generate a CD-key in XXXXX-XXXXX-XXXXX-XXXXX-XXXXX format."""
    chars = "BCDFGHJKMPQRTVWXY2346789"  # No ambiguous chars
    key = "-".join("".join(random.choice(chars) for _ in range(5)) for _ in range(5))
    return key
```

## Binary Patching Patterns

```python
# x86/x64 Patch Templates
PATCHES = {
    # JE (74 XX) → JMP (EB XX) — always pass conditional check
    "je_to_jmp": ("74", "EB"),
    # JNE (75 XX) → NOP (90 90) — never take false branch  
    "jne_to_nop": ("75", "90"),
    # CMP + conditional → XOR EAX,EAX + NOP (always return 0/success)
    "return_zero": ("83 F8 01 75", "31 C0 90 EB"),
    # CALL check → NOP NOP NOP NOP NOP (remove check entirely)
    "nop_call": ("E8", "90 90 90 90 90"),
    # MOV [license_flag], 0 → MOV [license_flag], 1 (always licensed)
    "force_licensed": ("C6 05", "C6 05"),  # keep same, change byte after
    # RET at function start (skip all logic, return whatever is expected)
    "ret_early": ("55 48 89 E5", "C3 90 90 90"),
}

def apply_patches(target_file: str, patches: list):
    """Apply hex patches to binary."""
    with open(target_file, "rb") as f:
        data = bytearray(f.read())
    for offset, original, replacement in patches:
        if data[offset:offset+len(original)//2] == bytes.fromhex(original):
            data[offset:offset+len(replacement)//2] = bytes.fromhex(replacement)
    # Create backup then write
    import shutil
    shutil.copy2(target_file, target_file + ".bak")
    with open(target_file, "wb") as f:
        f.write(data)
    return True
```

## Online Validation Bypass

```python
# Method 1: DNS redirect (hosts file / mitmproxy)
# 127.0.0.1 license.example.com

# Method 2: HTTP response spoof (mitmproxy script)
from mitmproxy import http
def response(flow):
    if "license.example.com" in flow.request.pretty_host:
        flow.response = http.Response.make(200, '{"status":"valid","expires":"2099-12-31"}')

# Method 3: Hook WinHTTP/WinINet in target
# Replace InternetReadFile / WinHttpReceiveResponse return values
```

## Trial Reset Patterns

```python
# Registry-based trial
import winreg
def reset_registry_trial(app_name: str):
    keys = [
        r"Software\{app_name}",
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{app_name}",
    ]
    for key in keys:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE):
                winreg.SetValueEx(winreg.HKEY_CURRENT_USER, "InstallDate", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(winreg.HKEY_CURRENT_USER, "RunCount", 0, winreg.REG_DWORD, 0)
        except: pass

# File-based trial
def reset_file_trial():
    import os, shutil
    trial_files = [
        os.path.expandvars(r"%APPDATA%\AppName\trial.dat"),
        os.path.expandvars(r"%LOCALAPPDATA%\AppName\.trial"),
        os.path.expandvars(r"%PROGRAMDATA%\AppName\license.lic"),
    ]
    for f in trial_files:
        if os.path.exists(f):
            os.remove(f)

# SQLite trial DB
import sqlite3
def reset_sqlite_trial(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM trial_info")
    conn.execute("UPDATE settings SET value=0 WHERE key='days_used'")
    conn.execute("UPDATE settings SET value=datetime('now') WHERE key='install_date'")
    conn.commit()
    conn.close()
```

## Common DRM / Protector Bypass

| DRM | Method | Tools |
|---|---|---|
| SteamStub | Unpack with steamless, patch DRM check | steamless, x64dbg |
| Denuvo | VM dump after unpacking, trigger license check | VMPDump, kernel debug |
| VMProtect | Dump after virtualization, or TitanHide+ScyllaHide | x64dbg + plugins |
| Themida | FOX dielectric, x64dbg ScyllaHide | x64dbg + ScyllaHide |
| Enigma | Memory dump at OEP, rebuild IAT | OllyDbg + Scylla |
| ASProtect | Find stolen bytes, rebuild OEP | Stripper tools |
| Safengine | Unpack via hardware BP on VirtualAlloc | x64dbg |
| Obsidium | API redirection bypass, dump after decrypt | x64dbg |
