#!/opt/ad-tools-venv/bin/python
"""
Batch convert StringSession list -> .session files + JSON cards + manifest

Handles both:
  - Standard Telethon v1 format (binary IP, 263B for IPv4, 275B for IPv6)
  - Panel ASCII format (ASCII IP string with length prefix, 274-275B)

Usage:
  python batch_convert_stringsessions.py <list.json> <outdir> [api_id] [api_hash]

Input JSON format (from panel API):
  [{sessionString, name, phoneNumber, username, ...}]
"""
import json, os, sys, base64, struct, hashlib, sqlite3

def parse_stringsession(s: str) -> tuple:
    """Parse StringSession v1 -> (dc_id, ip_str, port, auth_key_bytes)
    Both standard binary and panel ASCII formats."""
    if not s or s[0] != '1':
        raise ValueError(f"Invalid version: {s[:2]}")
    raw = base64.urlsafe_b64decode(s[1:] + '===' if len(s[1:]) % 4 else s[1:])
    dc_id = raw[0]

    if len(raw) == 263:
        # Standard IPv4: dc(1) + ip(4) + port(2) + key(256)
        ip_bytes = raw[1:5]
        port = struct.unpack('>H', raw[5:7])[0]
        auth_key = raw[7:7+256]
        import ipaddress
        ip_str = str(ipaddress.ip_address(ip_bytes))
    elif len(raw) in (274, 275) and 0x30 <= raw[3] <= 0x39:
        # Panel ASCII: dc(1) + str_len(2) + ip_str(N) + port(2) + key(256)
        ip_str_len = struct.unpack('>H', raw[1:3])[0]
        ip_str = raw[3:3+ip_str_len].decode('ascii')
        port = struct.unpack('>H', raw[3+ip_str_len:3+ip_str_len+2])[0]
        auth_key = raw[3+ip_str_len+2:3+ip_str_len+2+256]
    elif len(raw) == 275:
        # Standard IPv6: dc(1) + ip(16) + port(2) + key(256)
        import ipaddress
        ip_bytes = raw[1:17]
        port = struct.unpack('>H', raw[17:19])[0]
        auth_key = raw[19:19+256]
        ip_str = str(ipaddress.ip_address(ip_bytes))
    else:
        raise ValueError(f"Unknown format: len={len(raw)}")

    return dc_id, ip_str, port, auth_key

def create_session_file(path: str, dc_id: int, ip: str, port: int, auth_key: bytes):
    """Create Telethon .session SQLite - exact DDL matching SQLiteSession v1.36."""
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('create table if not exists version (version integer primary key)')
    c.execute('insert or replace into version values (7)')
    c.execute('''create table if not exists sessions (
        dc_id integer primary key, server_address text,
        port integer, auth_key blob, takeout_id integer)''')
    c.execute('''create table if not exists entities (
        id integer primary key, hash integer not null, username text,
        phone integer, name text, date integer)''')
    c.execute('''create table if not exists sent_files (
        md5_digest blob, file_size integer, type integer,
        id integer, hash integer,
        primary key(md5_digest, file_size, type))''')
    c.execute('''create table if not exists update_state (
        id integer primary key, pts integer, qts integer,
        date integer, seq integer)''')
    c.execute('insert or replace into sessions values (?, ?, ?, ?, ?)',
              (dc_id, ip, port, auth_key, None))
    conn.commit()
    conn.close()

def create_json_card(safe_id: str, name: str, phone: str, username: str,
                     session_str: str, dc_id: int,
                     api_id: int, api_hash: str) -> dict:
    """Card matching /root/tg_assets/ format.
    twofa is None because panel APIs don't provide it - auth_key bypasses 2FA anyway."""
    card = {
        "api_id": api_id, "api_hash": api_hash,
        "device_model": "TelePanel-Export",
        "system_version": "Windows 10",
        "app_version": "4.9.5 x64",
        "system_lang_code": "en-US",
        "lang_pack": "tdesktop", "lang_code": "en",
        "pid": hash(safe_id) % (2**63),
        "user_id": 0,
        "phone": f"+{''.join(c for c in phone if c.isdigit())}" if phone else "",
        "twofa": None, "password": None,
        "session_string": session_str,
        "app_id": api_id, "app_hash": api_hash,
        "session_file": safe_id,
        "device": "TelePanel-Export",
        "username": username or name,
        "sex": None, "tz_offset": 0, "avatar": "img/default.png",
        "device_token": None, "package_id": "", "installer": "",
        "ipv6": False, "pref_cat": 2, "block": False,
        "SDK": "Windows 10", "sdk": "Windows 10",
        "system_lang_pack": "en-US",
        "premium": False, "reg_time": "",
        "name": name, "dc_id": dc_id
    }
    return card

def batch_convert(accounts: list, outdir: str, api_id: int, api_hash: str):
    """Convert account list to session files + JSON cards + manifest."""
    os.makedirs(outdir, exist_ok=True)
    used_ids = set()
    manifest, errors = [], []

    for i, acct in enumerate(accounts):
        try:
            ss = acct.get('sessionString') or acct.get('session_string') or ''
            if len(ss) < 50:
                continue

            dc_id, ip_str, port, auth_key = parse_stringsession(ss)

            # Generate unique file id
            name = acct.get('name', acct.get('username', '')) or f'u{i}'
            safe_name = ''.join(c for c in name if c.isalnum() or c in '-_') or f'u{i}'
            phone_part = ''.join(c for c in acct.get('phoneNumber', acct.get('phone', '')) if c.isdigit())[:8]
            safe_id = f"{phone_part}_{safe_name}" if phone_part else f"{i:03d}_{safe_name}"

            # Deduplicate: same phone+name gets _N suffix
            if safe_id in used_ids:
                n = 2
                while f"{safe_id}_{n}" in used_ids:
                    n += 1
                safe_id = f"{safe_id}_{n}"
            used_ids.add(safe_id)

            # Write .session file
            sess_path = os.path.join(outdir, f"{safe_id}.session")
            create_session_file(sess_path, dc_id, ip_str, port, auth_key)
            sha256 = hashlib.sha256(auth_key).hexdigest()

            # Write JSON card
            card = create_json_card(safe_id, name,
                                    acct.get('phoneNumber', acct.get('phone', '')),
                                    acct.get('username', ''),
                                    ss, dc_id, api_id, api_hash)
            with open(os.path.join(outdir, f"{safe_id}.json"), 'w') as f:
                json.dump(card, f, indent=2, ensure_ascii=False)

            manifest.append({
                "index": i, "id": safe_id,
                "name": name, "username": acct.get('username', ''),
                "phone": acct.get('phoneNumber', acct.get('phone', '')),
                "session_file": f"{safe_id}.session",
                "json_file": f"{safe_id}.json",
                "session_sha256": sha256, "dc_id": dc_id,
                "addr": ip_str, "port": port
            })
        except Exception as e:
            errors.append(f"#{i} {acct.get('name','?')}: {type(e).__name__}: {str(e)[:80]}")

    # Verify all files with sqlite3 (NOT Telethon SQLiteSession - it modifies files)
    import sqlite3
    for m in manifest:
        p = os.path.join(outdir, m['session_file'])
        conn = sqlite3.connect(p)
        r = conn.execute("SELECT length(auth_key) FROM sessions").fetchone()
        conn.close()
        assert r and r[0] == 256, f"{m['session_file']}: bad key"

    with open(os.path.join(outdir, "manifest.json"), 'w') as f:
        unique_phones = len(set(m['phone'] for m in manifest))
        json.dump({
            "total": len(manifest),
            "unique_phones": unique_phones,
            "errors": len(errors),
            "accounts": manifest
        }, f, indent=2)

    print(f"Converted: {len(manifest)} session+json pairs")
    print(f"Unique phones: {unique_phones}")
    print(f"Errors: {len(errors)}")
    if errors:
        for e in errors[:5]:
            print(f"  ERROR: {e}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.json> <outdir> [api_id] [api_hash]")
        sys.exit(1)

    api_id = int(sys.argv[3]) if len(sys.argv) > 3 else 2040
    api_hash = sys.argv[4] if len(sys.argv) > 4 else "b18441a1ff607e10a989891a5462e627"

    with open(sys.argv[1]) as f:
        data = json.load(f)
    if isinstance(data, dict):
        accounts = data.get('accounts', data.get('data', data.get('items', [])))
    else:
        accounts = data

    batch_convert(accounts, sys.argv[2], api_id, api_hash)
