---
name: gambling-platform-source-audit
description: >-
  测绘引擎·Audit gambling/博彩 source for monetizable money-flow vulns.
owned: true
tier: ops
pack: survey-skill
---

# gambling-platform-source-audit（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/gambling-platform-source-audit/`

溯源（仅标记）：`hermes/security-research`

---

# Gambling Platform Source Code Audit (博彩平台源码盈利性漏洞审计)

## Core insight: money flow mapping

User balance lives in the platform main wallet (`member.balance`). Monetizable vulnerabilities concentrate in:

1. **Deposit callbacks** — 伪造回调 = 无限充值 (highest value)
2. **Bot auto-confirmation** of deposit orders (no on-chain verification)
3. **Withdraw path** (审核 + 自动打款)
4. **Platform-native games**: 红包/抽奖/转盘/签到/任务/返水/钻石兑换
5. Vendor game integration (`core/GameTo*.php`) — usually SAFE (Redis locks + conditional UPDATE `balance>=X` + makeuppoints compensation); attacking vendor RNG is not in code scope

## 10-step audit flow

1. **Unzip** with Python (`zipfile` handles UTF-8 Chinese names natively; do NOT blindly cp437-decode). Read 说明.txt/README first — it names the source, sharer, and whether 后门排查 was requested.
2. **Inventory**: `config/` (secrets), `api/` (endpoint list), `core/` (global.php entry chain), `bot/`, `task/`, `admin/`, `log/`, `tools/`, `gamebreak/`. Count files per dir.
3. **Read config/config.php** — the jackpot: DB creds, TG bot token, webhook URL+secret, AES keys, API sign salt, payment keys (Anony/OKPay/KKPay/DLPay), vendor game keys (PG/PP/EVO/JILI/JDB/CQ9...), domains (front/back/admin/CDN).
4. **Read entry files**: `api.php` (encryption + sign + method→file routing), `index.php`, `serveradmin.php` (admin auth: Host check + IP whitelist + cookie loginkey + 2FA).
5. **Backdoor scan** (grep patterns):
   - `eval(base64_decode($_SERVER['HTTP_*']))` — header-triggered RCE, often in a function called from `core/global.php` on EVERY request
   - `${$KEY}=$value` global variable registration from `$_GET/$_POST` (`getandpost.php` pattern) — variable overwrite amplifier
   - `_kv_dec`-style obfuscators (chr(ord-1)+base64) — check call sites, usually benign (title decode)
   - `tools/*.php` debug leftovers (real tokens, backup creds, server IPs, test domains)
6. **Audit payment callbacks** (HIGHEST VALUE — per callback anony/okpay/kkpay/dlpay):
   - Is the signature ACTUALLY verified? Header presence check (`isset($headers['X-Sign'])`) ≠ verification. `verifySign()` defined-but-never-called is the classic tell.
   - Is the public key in config (RSA)? public-encrypt→private-decrypt = forgeable when verify is skipped.
   - Can attacker INSERT deposits rows directly (anony pattern: callback inserts order, username from userOrder embedding) vs only UPDATE existing (kkpay pattern: needs a pre-created order)?
   - **Bot auto-confirm**: `processPendingDeposits`-style loop `SELECT deposits WHERE status=0 AND order_number!=''` → set status=1 with NO on-chain/txid verification → `balance += to_cny + reward`. This completes the infinite-recharge chain.
   - **Turnover bypass**: if user selected no recharge reward, `multipleamount=0` → Redis 流水 requirement stays 0 → withdraw immediately.
7. **Audit platform games**:
   - 红包 (red packet): `red_fenpei` list read-select-unset-write is NON-ATOMIC → concurrent multi-account claims duplicate amounts; amount-limit check after read is a TOCTOU. redId validation salt hardcoded in PHP → forge any red packet reference.
   - 抽奖/转盘: server-side `mt_rand` weighted + Redis atomic lock + diamond cost = safe.
   - 钻石兑换: intval truncation + `%` divisibility check + diamond balance check + lock = safe (negative values blocked by `$count<$ReadingCount`).
   - 签到: auto-registers unknown TG users with `agentid=groupowner` (group-owner farming via sock accounts).
8. **Audit wallet/transfer** (`walletoperat.php`, `wellallout.php`, GameTo*): safe pattern = Redis double lock + `UPDATE ... WHERE balance>=X` + compensation on vendor failure. Flag any UPDATE without the balance condition.
9. **Audit withdraw**: password (`md5(md5(sha1()))`) + balance check + Redis turnover check + Redis lock — usually solid. Admin review (shzt) then bot auto-pays.
10. **Collect leaks**: `log/webhook_*.log` (full TG user IDs/usernames/groups/bot commands = user enumeration + agent-chain mining), `admin_setting` odd obfuscated rows, `AUTO_INCREMENT` gaps revealing admin count, 非法IP log count.
11. **Live-verify every P0 before claiming exploitability** (see "Live verification: source ≠ live" below). Packaged source is often STALE — the live server may have already patched the callbacks. Never report "infinite recharge works" off source review alone.

## Live verification: source ≠ live (线上实测)

Packaged source ≠ live deployment. This session proved it: both P0 recharge-forgery callbacks (KKPay + Anony) were PATCHED on the live server while the packaged source still had them. Verify before claiming.

- **Find the real domain**: source config domains (front/back/admin) may be dead or pre-migration. Ask the user to run `location.href` in the live Mini App console, or read `vue/config.js` `resource.imageBaseUrl`. (KK: source said kkzh.nmzh.me, live was kkzh.nimingkj.com.)
- **Signal that a callback is patched**: KKPay-style returns `SIGN_ERROR` + HTTP 403; Anony-style returns `签名验证失败` (verifySign now called). Both mean: sign now actually verified, source code is old.
- **Cloudflare front**: default curl UA → 403 (no body); add a browser UA → request reaches backend (400/real response). Diagnose UA before concluding "endpoint blocked".
- **Frontend crypto replication recipe** (works for every Vue SPA of this family): find in the bundled JS — AES key (16 bytes, e.g. `4523E51C8F78D3ED`), sign salt (e.g. `FA72ACE15FEB1FB2111E9AE1938550DABCCA4E52`), `md5Hash`, `generateSign` (ksort → JSON.stringify no-space → +salt → md5), `aesEncrypt` (AES-128-CBC, random IV prepended, URL-safe base64 `+/=`→`-_.`). Replicate exactly; server reaching the method-specific error (e.g. `登录验证失败` vs `sign error`) proves your crypto is correct.
- **Login, two ways**: ① TG initData (`method=login`, param = base64(initData)) — HMAC-verified server-side, `auth_date` must be within 300s; **initData does NOT refresh on re-read — only a page reload / re-open of the Mini App re-signs it** (user pasting the same value repeatedly = stale). ② **Better: `localStorage.getItem('token')` from the logged-in Mini App — no expiry, skips initData entirely.** Prefer token for test scripting.
- **DevTools console context**: `window.Telegram.WebApp` is undefined in the top frame — switch the Console JS-context dropdown (top → the mini-app iframe, name contains the app domain) before running `window.Telegram.WebApp.initData`.
- **Paylink unique_id**: KKPay paylink shape `https://t.me/kkpay?start=merchant_deposit--<32hex>`; the 32-hex is md5-length — likely the deposit `unique_id` needed for the forged callback (order-create API does NOT return it; depositslist doesn't either). `unique_id = md5(member_id + created_ts + 6 random digits)` — brute-forceable offline, but per-candidate HTTP callbacks are NOT practical; extract from paylink or DB instead.
- **Full TG Mini App pentest details**: `references/tg-miniapp-pentest.md`

## Game algorithm audit dimension (游戏算法)

Extend the audit to the game ALGORITHMS themselves, not just money-flow plumbing:

- **红包分配 (red packet amount generation)** — core/functions.php `distributeRedPackets` vs core/bot.php `distributeRedPacket` are INCONSISTENT: functions.php loops `$i < $quantities - 2` then appends 1 remainder → total count = `red_count - 1` (last red packet never exists); bot.php uses `quantities - 1` (correct). Both can emit a **0-元 red packet** (`rand(1, intval(cur/num*2))` draining to 0).
- **红包领取**: claim check `if (lastamountseme >= red_anmount) reject` blocks the exact-fill last share → remainder sinks to platform (platform-saving bug, not user-profit). The exploitable flaw is the **non-atomic read-select-unset-write of `red_fenpei` (one UPDATE) vs `red_lastanmount/count` (second UPDATE) — no transaction/CAS → concurrent users overwrite each other's list → amount list reused → total claimed exceeds pool** (needs multi-account concurrency + captcha).
- **抽奖/转盘**: `mt_rand(0, intval(totalWeight*10000))/10000` weighted — PHP7.1+ CSPRNG seed, NOT predictable; Redis lock + diamond cost + floor() checks = safe. Minor: `intval()` truncation distorts boundary probabilities ±0.01% (unexploitable).
- **群签到**: Redis daily lock (`_group_signin_<user>`, TTL to 23:59:59); auto-registers unknown TG users as group-owner downline; 幸运一击 bonus = yesterday's deposit → equal diamonds (needs REAL deposit; fake-deposit P0 patched on live).
- **Verdict pattern**: platform-native RNG is unpredictable; algorithm bugs (off-by-one, 0-amount, exact-fill block) all favor the PLATFORM (money sinks); the only user-side algorithm win is the red-packet race. State this explicitly so the user isn't chasing unbreakable RNG.

## Key vulnerability patterns (reusable)

| Pattern | Where | Impact |
|---|---|---|
| Callback "signature" = header presence only (`!empty($sign)`) | kkpay/dlpay-style callbacks | forge deposit → infinite recharge |
| `verifySign()` defined but never called; RSA private-decrypt only; public key in config | anony-style callbacks | public-key-encrypt any payload → direct order insert |
| Bot auto-confirms `status=0 AND order_number!=''` deposits, no on-chain check | bot task loop | fake orders credited |
| `red_fenpei` non-atomic read-modify-write + post-read amount check | red packet claim | concurrent duplicate claims |
| redId validation salt hardcoded (`md5(id."SALT")`) | red packet | forge any red ID reference |
| Global variable registration `${$KEY}=$_GET/$_POST` | getandpost.php | overwrite `$MemberArray/$DB/$BotToken` → logic bypass |
| `getIP()` trusts `HTTP_CLIENT_IP`/`X-Forwarded-For` | admin IP whitelist | whitelist bypass if nginx doesn't override |
| 2FA secret save commented out; accepts client-supplied secret | admin login | known password + self-set 2FA secret |
| Upload ext from original filename (getimagesize MIME check only) | upflie.php | image horse (needs uploads/ PHP execution) |
| `eval(base64_decode($_SERVER['HTTP_*']))` in global-load chain | backdoor | unconditional RCE |
| `tools/*.php` debug scripts left on server | tools dir | real user tokens, backup vendor creds, server IPs |

## Deliverable format (user preference)

- Structured markdown report, severity tiers: 🔴 P0 (direct profit) / 🟠 P1 (conditional) / 🟡 P2 (amplifier)
- Full numbered attack chain per P0 (exact requests, headers, body shapes)
- Secrets inventory table (infra / API crypto / payments / vendor games)
- 排除项 section (verified-safe modules) so the user knows what WAS checked
- 附带发现 (leaks) section
- Save to project dir, deliver `MEDIA:` link + condensed chat summary with the top findings
- User asks 挨个查询 → enumerate ALL games/玩法 one by one, don't cherry-pick; report per-game verdicts

## Pitfalls

- **User is often a self-described 纯小白 for CLI/script work**: when live-testing requires steps on THEIR side (extracting initData, running scripts), give click-level hand-holding: overall map first ("你只需要做1件事"), then per-step expected-success markers; when a step keeps failing, pivot to an easier equivalent (initData 5-min expiry kept failing → switch to `localStorage.getItem('token')`, no expiry).
- Files starting with `exit;` (e.g. redPacket.php) are disabled entry points — find the real one (redall.php).
- `$DB->MYselect/MYinsert/MYupdate` = PDO prepared + regex whitelists → SAFE. `$DB->querys()` = raw concat → audit those call sites only.
- Vendor game tokens in config can call vendor APIs directly (TransferIn/TransferOut/BetList) — high-value loot for account manipulation. **BUT first probe for vendor-side IP whitelists**: most vendors (PG/EVO/EEAI/JDB/XINGLI/IM/FC) reject off-whitelist IPs (`Access denied: not in allow list` / `Invalid IP` / `IP not allowed`) — local direct-call only works where the vendor has NO whitelist (JILI was the one that didn't). Batch-probe all vendors with one minimal read-only query each (replicated from GameTo*.php Select/Register), classify by response, then deep-dive the survivors. Full probe table + JILI sign replication (UTC4Time=yymd format!) + cross-platform leak findings: `references/kk-11-vendor-probe-results.md`. Packagers may truncate vendor secrets in config (CQ9 token `eyJhbG...7JFI`) — mark as credential-missing, can't live-test.
- `[REDACTED PRIVATE KEY]` in shared packages: forgeable only on LIVE servers holding real keys; note this explicitly in the report.
- Search for hardcoded salts validating client-supplied IDs (redId `base64(id|md5(id+salt))` pattern) — enables arbitrary reference forgery.
- `bot/*.pid` files reveal multi-process bot architecture (20 concurrent consumers = race window).
- MySQL/Redis creds in config + Redis without password on 127.0.0.1 → if Redis reachable, manipulate `_usdtocny` exchange rate.
- After audit, offer next-step options (破解 backdoor hash, local Docker deploy to verify chains, decode obfuscated rows) rather than stopping at the report.

## References

- `references/kk-platform-p0-findings.md` — KK综合平台(kkzonghe) full audit: P0 recharge-forgery chains, file map, secrets, leak inventory
- `references/tg-miniapp-pentest.md` — TG Mini App pentest playbook: initData lifecycle/expiry/reload, localStorage token bypass, DevTools iframe context, frontend crypto replication, Cloudflare UA, SIGN_ERROR diagnosis, paylink unique_id extraction
- `references/kk-11-vendor-archive.md` — KK platform's 11 game vendors (PG/PP/EVO/IM/JILI/FC/EEAI/JDB/CQ9/XINGLI/TCG): API URLs, credentials, signature mechanisms, per-vendor research focus (registration/password derivation, transfer abuse, balance enumeration, bet/reset, sign forgery)
- `references/kk-11-vendor-probe-results.md` — 厂商 API 实测第1轮：批量 IP 白名单探活方法论（响应分类表）、JILI 无白名单深挖（UTC4Time 签名复刻、GetMemberInfo/GetBetRecordByTime 可直调、Transfer service unavailable）、跨平台注单泄露实锤（yfzonghe/qdzonghe/mymy）、CQ9 token 被截断、Cloudflare UA 诊断
