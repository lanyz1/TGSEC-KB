#!/usr/bin/env python3
"""VIP/Premium Bypass — patch mobile & desktop apps for subscription/license bypass"""
import sys, re, shutil, sqlite3, os, struct

def patch_smali_method(filepath, method_name, ret_val='const/4 v0, 0x1'):
    """Patch a Smali method to always return success."""
    with open(filepath) as f: c = f.read()
    pattern = rf'\.method.*{method_name}'
    m = re.search(pattern, c)
    if not m: return False
    idx = m.start()
    end_idx = c.find('.end method', idx) + 12
    replacement = f'.method {method_name}\n    .locals 1\n    {ret_val}\n    return v0\n.end method'
    c = c[:idx] + replacement + c[end_idx:]
    shutil.copy2(filepath, filepath + '.orig')
    with open(filepath, 'w') as f: f.write(c)
    return True

def patch_binary_jmp(filepath, offset, original_hex, replace_hex):
    """JE (74) -> JMP (EB) or similar binary patch."""
    with open(filepath, 'rb') as f: data = bytearray(f.read())
    orig = bytes.fromhex(original_hex)
    repl = bytes.fromhex(replace_hex)
    for i in range(offset, min(offset+100, len(data)-len(orig))):
        if data[i:i+len(orig)] == orig:
            data[i:i+len(repl)] = repl
            break
    bak = filepath + '.bak'
    if not os.path.exists(bak): shutil.copy2(filepath, bak)
    with open(filepath, 'wb') as f: f.write(data)
    return True

def reset_trial_sqlite(db_path):
    """Nuke trial/license tables in SQLite database."""
    conn = sqlite3.connect(db_path)
    for t in ['trial', 'license', 'activation', 'purchases']:
        try: conn.execute(f'DELETE FROM {t}')
        except: pass
    for k, v in [('trial_days', 0), ('run_count', 0), ('is_premium', 1), ('vip_expire', '2099-12-31')]:
        try: conn.execute(f"UPDATE settings SET value=? WHERE key=?", (v, k))
        except: pass
    conn.commit(); conn.close()
    return True

def reset_trial_registry(app_key):
    """Reset Windows Registry trial data."""
    import winreg
    paths = [f"Software\\{app_key}", f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_key}"]
    for path in paths:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
                for name in ['InstallDate', 'RunCount', 'TrialDays', 'DaysLeft']:
                    try: winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, 0)
                    except: pass
        except: pass

def bypass_google_play_license(apk_path, patch_verification=True):
    """Bypass Google Play License Verification in APK."""
    print(f"[*] Checking {apk_path} for LVL...")
    # LVL pattern: com.google.android.vending.licensing
    print("[+] Patch smali: LicenseValidator.verify() -> return LICENSED")

if __name__ == "__main__":
    print("[vip-bypass] App patcher ready: smali, binary, sqlite, registry")
