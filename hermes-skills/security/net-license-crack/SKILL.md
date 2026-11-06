---
name: net-license-crack
description: >-
  授权样本上的网络验证 / 卡密 / 许可绕过：天盾、fndata、Nuitka、PyInstaller、
  RSA 公钥替换、假认证服务器、HWID、试用复位、JE→JMP。
  触发：天盾、fndata、Nuitka 破解、卡密验证、keygen、假认证、license bypass、
  checkLicense、序列号、VIP 本地旗标（服务端 VIP 仍走 client-state-skip）。
  游戏外挂 / IL2CPP 走 client-crack-cheat。发卡站走 faka / acg-faka。
---

# 网络验证与卡密（测绘引擎）

目标须在 scope，或案卷里的 **授权本地样本**。  
授权内默认打到 **L2**：抽出认证 URL + 校验算法/RSA，或恢复卡密格式。  
先问只剩：对他人发行版做注册机散播、改原超管密。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 认出 Nuitka/PyInstaller/天盾/fndata 或 checkLicense | 只 `strings` 到 UPX |
| L2 | 认证 URL + RSA/符号，或样本卡密同构，或 XOR 钥流 | 随机生成假 CD-Key |
| L3 | 授权样本补丁（有 .bak）或假认证响应被客户端吃 | 没备份就写盘 |

## 立刻跑

```bash
python3 tools/ops/net_license_probe.py drive --path <样本.exe|.apk|.bin> --case <案>
python3 tools/ops/net_license_probe.py format --sample 'ABCD-1234-WXYZ' --sample 'EFGH-5678-QRST'
python3 tools/ops/net_license_probe.py xor --plain known.bin --cipher enc.bin
python3 tools/ops/net_license_probe.py patch-plan --path <PE>
# 授权样本才 --apply（先备份）
python3 tools/ops/net_license_probe.py patch-plan --path <PE> --apply --case <案>
# 假认证（只给授权样本指 127.0.0.1）
python3 tools/ops/net_license_probe.py serve --host 127.0.0.1 --port 8765
# Nuitka/PyInstaller 先认 TOC
python3 tools/ops/py_pack_reverse.py drive --path <样本> --case <案>
```

产物：`测绘/net_license/surface.json`。

六步：

```text
① drive 认壳 / 天盾 / fndata / Nuitka
② 抽 license/activate URL 与 RSA PEM
③ 有真卡密样本 → format 恢复格式，禁止瞎编 Windows 风格 Key
④ 已知明文 → xor 抽钥流
⑤ 在线验证：hosts/mitm 假 200（仅授权样本）
⑥ 短 JE 计划；--apply 才写，必须 .bak
```

## 交接

| 认到 | 走 |
|------|----|
| Unity / IL2CPP / 外挂 | `client-crack-cheat` |
| H5 isPaid / 前端 VIP | `client-state-skip` |
| 发卡站 / 卡密商城 | `faka-card-shop-pentest` / `acg-faka` |
| 反调试自毁 0xc000041d | 本卡认面后 `anti-debugging-techniques` |
| Electron asar | `thick-client` |

## 真源

- 手法：`docs/playbooks/测绘引擎网络验证与卡密作业手法.md`
- 探针：`tools/ops/net_license_probe.py`

---

<!-- 补充视角: crack-keygen (兄弟技能库 2026-09-12) -->


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

---

<!-- 补充视角: fndata-auth-bypass (兄弟技能库 2026-09-12) -->

---
name: fndata-auth-bypass
description: Bypass fndata auth via RSA pubkey swap + fake server.
version: 1.0.0
author: SurveyEngine Agent
license: MIT
platforms: [windows]
metadata:
    category: security
---

# fndata 网络验证平台绕过

fndata(飞鸟数据类)是中文软件常用的第三方网络验证平台:客户端 RSA+AES 混合加密调 API,服务器校验卡密/账号/VIP 到期。已在轻云3.8(PUBG 辅助,AppId=10015)上实战验证。本技能专注 **fndata 平台本身**,与打包方式(Nuitka/PyInstaller)无关——见 `python-pack-reverse` 技能处理壳识别。

## When to Use

- 目标程序登录请求形如 `POST /Api?AppId=NNNN`,body 是 `{"a":..., "b":...}`(RSA 加密 AES 密钥 + AES 加密请求体)
- 字符串含 `fndata`、`GetToken`、`UserLogin`、`HeartBeat`、`会员已到期`、`UserClassMark`、`VipTime`
- 需要绕过:登录、卡密校验、VIP 到期

## Prerequisites

- Python3 + `pycryptodome` + `requests` + `frida` + `psutil`
- 已用 Frida 抓到过真实请求格式(或用下方协议直接构造)
- 目标视为已授权资产

## fndata 协议速查(已逆向确认)

```
API:    http://<server>:18888/Api?AppId=NNNN   (轻云: 101.35.246.71:18888, AppId 10013/10015/10016)
请求:   headers {Token: <GetToken返回值,动态>}
        body {"a": RSA-PKCS1v15加密(AES密钥), "b": AES-192-CBC加密(JSON), IV=key[:16], PKCS7}
响应:   {"a": AES加密(JSON), "b": MD5(明文).upper()}
业务:   fnobj 字段 = UserLogin / HeartBeat / GetAppUserInfo / GetAppGongGao / LogOut ...
登录响应字段: User, Key, LoginIp, LoginTime, UserClassMark, UserClassName, VipNumber, VipTime, NewAppUser, Token
3 份 RSA-1024 公钥硬编码(每份含头尾 271 字节,PEM body 219 字节)
```

## 决策树:到期校验在哪一侧?

**挂时间回拨后重新登录,若仍提示"已到期" → 服务器端校验,时间回拨无效。**(轻云实证:挂满 5 个时间源回拨 2 年,登录仍被拒。)

- **客户端校验** → Frida 时间回拨(hook GetSystemTimeAsFileTime/Precise/msvcrt time/GetSystemTime/GetLocalTime,回拨 2 年)
- **服务器端校验** → 用下面的公钥替换 + 本地模拟服务器,或 Python C-API hook


## 全文导航（已拆分）

主卡保留前 15 节；其余 11 节在 `references/full.md`：

- 第一检查:代理/TUN 透明接管(最大坑,必须先排)
- 方向切换铁律:用户问"服务器 shell"= 立即切换攻击面(用户明确纠正)
- 重大修正:Windows 出站防火墙 block 规则可能实测无效
- 服务器端攻击面
- Frida connect 重定向
- 更狠的一招:Frida getaddrinfo 重写(源码级重定向,治 keep-alive 时序)
- 更稳的绕路:hosts + 防火墙 fallback(绕开连接时序,轻云实测打通到本地)
- 终局方案:Python C-API hook(去验证的正路)
- Pitfalls(全部来自实战)
- 一键启动器要点
- Verification

加载：`skill_view(name='net-license-crack', file_path='references/full.md')`
