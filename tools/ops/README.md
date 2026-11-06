# tools/ops — local execution layer

This directory is the **real** local execution layer for the enabled skills. It
now covers **112 of 124** enabled-card `tools/ops` names (including direct
`references/*.md`); it is still not a copy of every archived/disabled name.

## Supported adapters

These forward to the pure-stdlib tools in
`.claude/skills/pentest-redteam/scripts/tools/`:

| ops name | real tool | example |
|---|---|---|
| `test_subdomain_enum.py` | `subdomain_enum.py` | `python3 tools/ops/test_subdomain_enum.py -d example.com` |
| `port_admin_scan.py` | `port_scanner.py` | `python3 tools/ops/port_admin_scan.py -t host -p 80,443,8080` |
| `dirbrute_probe.py` | `dir_brute.py` | `python3 tools/ops/dirbrute_probe.py -u URL -w words.txt` |
| `waf_sqli_bypass.py` | `sqli_detector.py` | `python3 tools/ops/waf_sqli_bypass.py -u 'URL?id=FUZZ' --waf` |
| `bucket_probe.py` | `s3_bucket_enum.py` | `python3 tools/ops/bucket_probe.py -k keyword --check` |
| `redis_unauth_probe.py` | `redis_exploit.py` | `python3 tools/ops/redis_unauth_probe.py -H host check` |
| `js_secret_hunter.py` | `js_endpoints.py` | `python3 tools/ops/js_secret_hunter.py -u https://host/app.js` |
| `ssrf_probe.py` | `ssrf_probe.py` | `python3 tools/ops/ssrf_probe.py -u 'URL?url=FUZZ'` |

Each adapter uses `os.execv`, so `-h` and all underlying arguments are unchanged.

Additionally, 28 direct passthrough symlinks exist for the real stdlib tool names
(`jwt_attack.py`, `cms_fingerprint.py`, `xss_detector.py`, `idor_scanner.py`,
`port_scanner.py`, `subdomain_enum.py`, ...). They point at `_adapter.py`; the
target is the same basename under `.claude/skills/pentest-redteam/scripts/tools/`.
Verify with `python3 tools/ops/<name>.py -h`.

## Real orchestration

- `kit_run.py` — check/recon/scan/case/report
- `auto_campaign.py` — plan menu and thin `run` wrapper
- `scope_lint.py` — scope gate
- `case_report.py` — ledger → Markdown report
- `evidence_gate.py` — ledger verification gate
- `object_matrix.py` — object × role coverage bookkeeping
- `shizhan_pack_route.py` — skill name → card path
- `core_web_surface_probe.py` — web surface delegate to kit_run
- `reverse_skill_route.py` — file/hint → reverse skill
- `nday_route.py` — product/CVE → vuln_find
- `gambling_family_probe.py` — generic family GET + JS/domain inventory
- `pay_matrix.py` — payment endpoint × role × test class matrix
- `java_web_surface_probe.py` — actuator/swagger/druid read-only probe
- `apk_recon.py` — APK zip/strings URL/domain/key extraction
- `nday_family_probe.py` — vuln_find family lookup + optional web pass
- `hypothesis_route.py` — signal → cards + open case hypotheses
- `re_sample_triage.py` — sample file/zip/urls/hashes triage
- `host_ir_check.py` — local identity/listeners/cron/IR snapshot
- `scope_expand.py` — scope in_scope/add/list helper
- `heap_cred_scan.py` — heap/dump URL/token/JWT regex scan
- `case_triage.py` — all local case ledgers board
- `case_facts.py` — ledger-backed facts/evidence pointers
- `auth_brute_probe.py` — small capped auth probe (default 20)
- `origin_recon.py` — DNS/crt.sh/headers origin recon
- `actuator_probe.py`, `jwt_forge_probe.py`, `pack_surface_probe.py` — compat launchers
- `coverage_gate.py` — strict tools/ops dead-reference gate

## 2026-10-21 high-coverage batch

- Auth/API: `param_abuse_probe.py`, `rbac_bypass_probe.py`, `jwt_gql_probe.py`, `api_dispatcher_enum.py`, `frontend_auth_probe.py`, `reset_token_surface_probe.py`
- Infra: `ad_surface_check.py`, `linux_lpe_checker.py`, `windows_lpe_checker.py`, `middleware_unauth_probe.py`, `cdn_ranges.py`, `cdn_tracer.py`, `cdn_ip_collector.py`, `cdn_origin_monitor.py`, `proxy_classifier.py`
- Web surfaces: `admin_access_probe.py`, `panel_surface_probe.py`, `aspnet_surface_probe.py`, `nextjs_surface_probe.py`, `wp_plugin_unauth_probe.py`, `ginvue_admin_probe.py`, `yudao_appapi_probe.py`, `llm_surface_probe.py`, `vite_fs_probe.py`, `source_extract.py`, `http_probe_batch.py`, `sensitive_dir_dump_probe.py`
- Payload/crypto: `tpl_inject_probe.py`, `crypto_decode.py`, `stego_lsb_probe.py`, `ws_probe.py`, `fastjson_probe.py`, `logic_vuln_probe.py`, `stored_xss_probe.py`
- Comms/CI/LLM/captcha: `email_sec_probe.py`, `cicd_surface_probe.py`, `oauth_oidc_surface_probe.py`, `session_import.py`, `litellm_badhost.py`, `nextcaptcha_solver.py`, `capmonster_solver.py`
- Mobile/desktop: `apk_recon.py`, `ios_surface_probe.py`, `wxmini_static_probe.py`, `py_pack_reverse.py`
- Ops/meta: `case_ledger.py`, `case_review.py`, `skill_catalog.py`, `skill_index.py`, `skill_own.py`, `skill_store_sync.py`, `skill_store_adopt.py`, `engine_distill.py`, `intel_ingest.py`, `cve_daily_probe.py`, `absorption_audit.py`, `callability_gate.py`, `resolve_asset_paths.py`, `css_query.py`
- Seventh batch (active-surface closure): _none retained_; 8 narrowed implementations and `_ops_http.py` were deleted after operator correction.

## Quarantined after operator correction

Five names from the EDR/C2/anti-forensics/identity cards and eight narrowed
active-surface implementations were removed without authorization. On
2026-10-21 they were moved to:

- Deleted by operator request on 2026-10-21; no quarantine copy retained.

They are not part of `tools/ops`; the original card text was not modified.
No weaponized replacement is provided. Treat these names as `manual`.

## Callability and asset paths

`callability_gate.py` checks that each script compiles and that runnable
entrypoints answer `--help`; adapter shims are resolved to their target, and
shared helpers with no `__main__` are reported as `library`, never counted as
manual. It never runs business actions. Current result: **152 ready /
2 library / 0 manual / 0 broken** (150 scripts).

`resolve_asset_paths.py` creates symlinks for `docs/learning/*` references whose
last path component exactly matches a local skill card. The 2026-10-21 run
resolved **284 of 317** historical paths, generated **20** index/state pages; **6** missing source cards remain
(no local counterpart for those six cards). Dry-run is
the default; `--apply` creates links.

```bash
python3 tools/ops/callability_gate.py --strict
python3 tools/ops/resolve_asset_paths.py --top 5
```

## CyberSecurity-Skills data

`css_query.py` is a local adapter over `docs/learning/cybersecurity-skills/skill_query.py`.
The data pack was imported as a full directory (39 modules / 195 skills, MIT); see
`docs/learning/cybersecurity-skills/SOURCE.md` for upstream and commit.

```bash
python3 tools/ops/css_query.py list-modules
python3 tools/ops/css_query.py search --keyword 无线
python3 tools/ops/css_query.py get --id 05-002
python3 tools/ops/css_query.py doctor
```

## Not implemented

The other 106 historical `tools/ops/*.py` names referenced only by disabled/legacy
skill cards or active gaps (231 unique total, 125 implemented; 1,264/1,539
references = 82.1%) do **not** exist here. **Enabled-card coverage is 114/123
names, 227/241 references = 94.2%; nine names remain deleted/manual.** Do not run the 106
archived names blindly. Check with:

```bash
python3 tools/ops/coverage_gate.py --active --strict   # enabled surface: exit 1
python3 tools/ops/coverage_gate.py --top 20            # all cards: 106 missing
```

If a disabled name is re-enabled, implement its script first or use the
equivalent real script above, an installed binary (`nuclei`, `ffuf`, `sqlmap`,
`whatweb`, `wpscan`, ...), or `tool_get`.
`coverage_gate.py --active --strict` is the active-surface closure gate;
the full `--strict` gate remains red only because of archived cards.
