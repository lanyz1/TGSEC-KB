# Playbook Library Index — webapp-blackbox-audit

Class-level playbook sub-skills under `references/playbooks/<name>/`, each with its own
`references/` (session cases, PoC detail) and `scripts/` (re-runnable tools).
Load via `skill_view('webapp-blackbox-audit', file_path='references/playbooks/<name>/SKILL.md')`.

## Framework stacks

| Playbook | Covers | Scripts |
|---|---|---|
| `python-webapp-pentest` | FastAPI/uvicorn (openapi.json mining, 405-vs-303 auth-model signal, urllib redirect pitfall, auth classification) + Flask/Werkzeug (timing enum, JSON-quote false positive, single-thread rate discipline) + JS-SPA recon | `fastapi-scan_auth.py` |
| `php-framework-pentest` | Laravel (Filament/Livewire login, Ignition CVE-2021-3129 RCE + failure-cause table), ThinkPHP (ThinkAdmin captcha plaintext leak, TP3 dual routing + Korean betting variant), Yii2 (debug/Gii/console chain), Discuz (mobile API IDOR), generic PHP RCE decision rules | `discuz-enumerate_mobile_api.py` |
| `messaging-platform-pentest` | TG account shops/发卡 (open-API HMAC, delivery-server unauth download, order monitor, OKPay aggregator), 群控 (session bulk export, send-code enum, proxy-SSRF oracle, yunkong family triage), Bot admin panels (broadcast/SPA, Playwright driving), WA/TG CRM (Whatcrm token lake) | `harvest_idor.py`, `account-shop-hmac_api_client.py`, `account-shop-order_monitor.py`, `account-shop-session_takeover.py`, `group-control-batch_relay_export.py` |
| `container-postexploitation` | Escape feasibility (CapEff bit-parse, seccomp, cgroup, eBPF, core_pattern, runc-FD) then data-side ARP MITM of PG/Redis (SCRAM sniff + offline verify) | — |
| `1panel-panel-pentest` | 1Panel RSA-login panel workflow | `1panel_rsa_login.py`, `ddddocr_brute_loop.py` |
| `elastic-stack-pentest` | Kibana/ES endpoint map & unauth sweeps | — |
| `betting-platform-pentest` | Casino/white-label lobbies (Next.js middleware gates, TP3 casino variants, TG-webapp gateways) | — |
| `mobile-monitor-backend-pentest` | Mobile-app monitor backends | — |

## Session case references (playbook root `references/`)

- `source-code-exposure-otc-case.md` — OTC USDT platform chain-mine case (package.json→scripts→server→data)
- `sourcemap-credential-lake-chain.md` — sourcemap credential-lake chain
- Per-target audit notes: `507ai-cloud-saas-audit.md`, `k52astr-club-miniapp-audit.md`,
  `kodbox-msgwarning-plugin-bypass.md`, `spicyworld-hongxing-reg2admin.md`,
  `mersobet-withdrawal-*.md`, `session-notes-node-store-audits.md`

> 2026-09-04 consolidation: formerly-standalone skills (fastapi/flask/laravel/thinkphp/yii2/discuz/
> php-rce/python-recon, tg shop/group-control/bot-panel/whatsapp-crm, container-escape-assessment,
> db-traffic-mitm-capture, source-code-exposure) were absorbed here; originals archived under
> `~/.hermes/skills/.archive/`.