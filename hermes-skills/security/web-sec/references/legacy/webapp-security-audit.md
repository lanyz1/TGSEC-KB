<!-- archived from /root/.hermes/skills/security/webapp-security-audit/SKILL.md on 2026-10-21 -->

---
name: webapp-security-audit
description: "Audit webapp auth bypass, CSRF, brute-force; verify live."
---

> 归档卡：原目录 `/root/.hermes/skills/security/webapp-security-audit`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/webapp-security-audit/…')`，不要相对 `references/legacy/` 解析。

# Web Application Security Audit (login/auth focus)

Use when asked to audit a web application's login/authentication/authorization code for exploitable vulnerabilities (auth bypass, arbitrary-account login, CSRF, SQL injection, privilege escalation) — especially PHP apps (admin/, user/, controllers, models, Dispatcher/router). Also use when verifying a suspected auth flaw against a live deployment.

## Workflow

1. **Map the app**
   - Entry points: `index.php`, `admin/`, `user/`, API endpoints, payment callbacks; router/Dispatcher (check for LFI via controller/plugin name sanitization); `config.php` (hunt for secrets/keys); auth service class; user models; login controllers.
   - Note the DB layer: if all queries go through a prepare/bind layer (PDO/mysqli prepared statements), SQLi in login paths is unlikely — confirm quickly, then move on. Only chase raw-concat queries.

2. **Auth checklist** (priority order for admin takeover):
   - **CSRF**: read the token verification. Watch for a *cookie dual-submit fallback* (validate() that ALSO checks a cookie). If the cookie is `token.hmac`, find the HMAC secret derivation. **Degradable/default secrets are the jackpot**: e.g. `secret = <REDACTED> ?? app.secret ?? base64_encode(csrf_key)` — when config lacks a secret, the key is a known constant and every token is forgeable.
   - **Rate limiting**: determine storage dimension — session vs IP vs DB. Session-based throttle = trivially bypassed by rotating PHPSESSID (or omitting the cookie so PHP starts a fresh session). Check login forms for captcha (absence = brute-force viable).
   - **Admin entry guards**: entry-key / secret-path checks — and whether they're actually active on the live site (test response code, don't trust source alone).
   - **Role isolation**: admin login must filter `role='admin'`; front login `role='user'`; distinct session keys (`em_admin_auth` vs `em_front_user`).
   - **Session handling**: `session_regenerate_id` after login (fixation); PHPSESSID cookie flags (missing HttpOnly = session theft via any XSS).
   - **Remember-me**: token randomness + DB lookup; password reset/change flows (often weakest); IDOR in user-area endpoints; mass-assignment whitelists in profile handlers.
   - **Registration**: auto-login after register, CSRF coverage, invite/attribution params.

3. **Verify against the live site — safely** (never attempt a real login or destructive action; wrong-password probes only):
   - **Differential response oracle**: POST with a *forged* CSRF token; if the reply is the password/auth error (e.g. `账号或密码错误`) rather than the CSRF error (`请求已失效`), the forgery passed validation.
   - Prove default-secret assumptions by recomputing the HMAC of a cookie observed in the live `Set-Cookie` header — this confirms the deployment did NOT override the secret via env/config.
   - Confirm throttle bypass with N consecutive wrong-password attempts, each with a fresh session; expect zero lockouts.
   - Read the login page HTML to confirm captcha absence / entry-key presence.

4. **Report** per finding: file path + line, vuln type, trigger (URL/params), payload example, impact. Prioritize chains that reach admin. Mark code-confirmed vs live-confirmed.

## Pitfalls

- MSYS/Windows path mismatch: on this host bash `/tmp` = `C:\Users\<user>\AppData\Local\Temp`, but write_file resolves `/tmp/x.py` to `C:\tmp\x.py`. When running native Windows python3 on a file created via MSYS paths, convert with `cygpath -w /tmp/x.py`.
- Prefer standalone script files (write_file) over inline `python3 -c` inside shell loops — avoids smart-approval friction and is cleaner.
- Don't assume source config == deployed config. A live cookie HMAC or response code is ground truth for whether a guard/secret is active (e.g. `.env` overrides).
- CSRF forgery alone does NOT enable cross-site attacks when the cookie is SameSite=Lax (cross-site POST sends no cookie). Its real impact: automated attacks without token pre-fetch (brute force, spam), and any same-site context (subdomains, XSS). Report it accurately.
- Missing captcha + session-rotation bypass + forgeable CSRF = fully automatable online brute-force of admin credentials — the P0 chain. Rate the impact accordingly.
- phpass/PasswordHash with iteration count 8 is fast (~10k+ hashes/sec); online brute-force is practical for dictionary attacks, don't dismiss it.

## Support files

- `scripts/csrf_forge_probe.py` — forge a dual-submit CSRF cookie/token (`token.hmac` with known/derivable secret) and POST it to a target; print response for the differential oracle.
- `references/emshop-audit-2026.md` — full EMSHOP v1.3.15 audit (findings, file+lines, live-verified results, payloads, throttle test recipe).
