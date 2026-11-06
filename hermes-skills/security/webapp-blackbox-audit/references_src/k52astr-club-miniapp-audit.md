# K52 Club (k52astr.ru) — Telegram Mini App Audit Notes

FastAPI + nginx/1.18.0, Telegram bot `K52clubbot`, Russian offline poker club's
online auxiliary system (tournament registration / RP rating points / TG community).

## Three independent admin surfaces (the core lesson)

Same app exposed THREE separate operator APIs, each with its own auth header + error string:

| Surface | Auth header | Unauth error (RU) | Meaning | Compromised? |
|---|---|---|---|---|
| web-admin | `X-Admin-Token` | — (weak pw login) | full web panel | ✅ via `k52admin` |
| admin | `x-telegram-init-data` + `authorization` | `Требуется авторизация Telegram` | TG-admin dual-auth | ❌ |
| panel | `X-K52-Panel-Token` | `Неверный токен панели` | PIN/operator panel (bar, live table ops) | ❌ |

Also `Доступ только для администраторов` = role-gated (403) vs token-gated (401).

Enumeration recipe that worked:
1. `openapi.json` → per-path `parameters[]` listed the custom header per surface.
2. Unauth sweep of each → distinct error strings bucket the endpoints.
3. `admin_app.js` → `grep -oE 'api\("[^"]+"|api\(`[^`]+`'` gave the authoritative
   web-admin endpoint list (broadcast, club/upload, players/{id}/bonuses, etc.).
4. GET on POST-only route → 404/405 noise; POST `{}` → 422 with required field names
   (proves route exists + reveals body schema).

## Non-monetary platform — money-movement verification

User asked "can we withdraw?" — answer NO. The system:
- `rp` = rating points (3753.5, 2979...), ranking only
- `lifetime_bounties` = PKO tournament bounties, settled OFFLINE at the club
- `bonus_balance` = 0 for ALL 403 users → feature disabled
- No wallet / withdraw / deposit / balance / payment endpoints anywhere in openapi.json

Lesson: check for money endpoints BEFORE planning payment/withdraw attack paths on
non-financial apps; the asset here is admin access + user/tournament data, not funds.

## Upload surface (FastAPI multipart)

`POST /api/web-admin/club/upload` — fields `kind` + `file` (multipart).
- Response: `{"ok":true,"media":{"path":"gallery_<hex>.<ORIGINAL_EXT>","url":"/uploads/..."}}`
- Random hex prefix + ORIGINAL extension preserved; served statically at `/uploads/`.
- Strict server-side whitelist: SVG/HTML rejected with
  `{"detail":"Только JPG, PNG, WEBP, GIF"}` (JPG/PNG/WEBP/GIF only).
- No extension-bypass RCE on Python/FastAPI (no PHP execution); SVG XXE/HTML XSS blocked.
- Verdict: LOW severity, move on.

## Compromise chain (asset summary)

- Weak password `k52admin` on `POST /api/web-admin/login` → `X-Admin-Token`
- Token stored frontend as localStorage `k52_admin_token`, header `X-Admin-Token:` (NOT Bearer)
- Data pulled via web-admin: 403 players, 51 tournaments, 984 registrations (43 events),
  survey responses, club branding/schedule.
- Write confirmed: `PUT /api/web-admin/club` → 200 (branding/schedule tamper);
  broadcast endpoint exists (TG spam/phishing to 324 TG users) — not fully exercised.
- Exclusion results: BFLA not applicable across surfaces (each auths independently),
  mass-assignment `is_admin` filtered, TG initData forgery rejected, no user enum,
  payment/withdraw surfaces nonexistent.
