# Direct DB surface + wallet/mnemonic false friends

Field notes from kitjit2/juootyi (2026-09-18). Class pattern when the ask is「直接拿到数据库」or「有助记词/私钥吗」.

## DB name / paths
- Schema often **`bot_duihuan`**; webroot clues `/www/wwwroot/book4...` / `bot4...`
- Soft surfaces: `adminer.php` (401 Basic Auth common), phpMyAdmin, panel `:888`, MySQL `3306/3307`

## Soft probe order (no dictionary)
1. **Adminer/phpMyAdmin** — confirm status (401 ≠ 404). Known controlled passwords only; hydra/admin666 on CF often **false HIT** (curl still 401).
2. **Origin + Baota** — nmap open `:888` + foreign **403** = whitelist, not dead panel. Don't spray Baota login from off-allowlist egress.
3. **MySQL** — port open may still **gone-away** / firewall after handshake; SCJ CN egress sometimes reaches what local cannot — still need creds from config LOAD_FILE.
4. **book4 dayallqun window** — preferred dump path when CF 520 clears: LOC3 size-oracle / same-length LOCATE → LOAD_FILE config → plaintext DB/TG secrets. Ban `.sql` path hammer, `php://filter`, noisy `file=` (site-wide 520).
5. Deliver **partial** DB-shaped loot early (titles / userid maps / shell chats) and label gaps; don't invent full dump.

## Window watchers
- Keep soft sentries on book4/bot4: size-blind + window-smash + db_window dump.
- Always `background:true`; log lines `NO_WINDOW` / `B4=520|16` are expected while CF sits.
- Historical proof: LOC3 body-length **+54** ⇒ LOAD_FILE was readable — on next open window fire that payload first.

## Wallet / mnemonic hunt
Search loot for: `助记词|mnemonic|seed phrase|私钥|privkey|private_key|0x[a-fA-F0-9]{64}` and BIP39-looking 12/24-word runs.

### Reject as false friends
- Vendor docs: elliptic-php sample mnemonic `scheme spot photo card baby mountain device kick cradle pact join borrow`; tron-php empty `private_key_hex` stubs; Key.php exception strings.
- Oil `/10.php` / merged TRON address lists (multi-million) with **rich=0** / empty balances.
- Title-OSINT `T[33]` addresses without matching private material.

### Real key locations (same blockers as members)
- Live bot PHP / config via LOAD_FILE
- DB rows after Adminer/window dump
- Live webhook that still holds spendable material

If hunt returns only addresses + vendor samples → report **助记词/私钥=0** plainly; don't pad with README examples.
