# PHP2Shell — three-source provenance triage (2026-10-21)

Question asked: which of the three is a real PoC usable in the field, not a lab?

**Answer: `blasty/php-8.5.4-apache-uaf-poc` is the only genuine exploit code; `dinosn` is a self-admitted lab; `jackalsyn` is a correction/debunk, not a weapon. None is blind-field-usable.**

## blasty/php-8.5.4-apache-uaf-poc — REAL, address-assisted

- README header: `PRIVATE / EMBARGOED SECURITY RESEARCH — do not make this repository public` (yet public = leaked/embargoed).
- Chain: stale `BG(unserialize)` state → reclaim context → overwrite `ps_serializers[1].decode` → libc `system()` during request startup, `application_function_call=none`.
- Receipt: `VALIDATION=PASS sapi=apache2handler pristine_source_files=7 runs=3 unique_module_heap_libc=3 same_worker=yes sink_symbols=absent natural_target=ps_serializers[1].decode target_offset=0x104a128 libc_system_offset=0x4c490 application_function_call=none`
- `apache_poc.py` raises `SystemExit('supply --stale-context/--heap-base, --decode-target/--module-base, and --system/--libc-base')` when any address is missing.
- Docker: one prefork worker, `memory_limit=4M`, `SYS_PTRACE`, `seed.php`; `docker/run.sh` retries up to 20 restarts for a suitable ASLR layout and runs `discover.py` (reads `/proc/<worker>/maps` + `nm`) inside the container.
- README limitation: "A non-lab remote path still requires equivalent PHP heap, module, and libc disclosures, same-worker affinity, and a legitimate way to establish the crafted session value."

## dinosn/php-cve-2026-10961x-lab-poc — LAB, self-admitted

- README: `Status: Proven — lab-assisted RCE`.
- `docs/PROOF-BOUNDARY.md`:
  - Lab-assisted: "The request includes heap, libphp, and libc addresses measured by host GDB for the current Apache parent."
  - Not proven: attacker-obtainable in-band address disclosure; portable no-debugger ASLR-independent chain; RCE with default Zend allocator; multi-worker reliability; PHP-FPM execution; universal PHP 5+ impact; official status of the CVE names.
- README: "Chain B's addresses come from `/proc` on the lab host".
- Environment: PHP 8.5.11 pinned image, exactly one prefork worker, `memory_limit=16M`; Chain A needs `USE_ZEND_ALLOC=0` (non-default).
- Chain B receipt prints `LIBPHP=0x... CHUNK=0x... HTDATA=0x... ZIF=0x...` — host-measured; `FIRE_GDB=0` only means no debugger attached at fire time.

## jackalsyn — CORRECTION / DEBUNK

- "Cached-pointer chain DEAD at the addref (session.c:3213 `Z_TRY_ADDREF` keeps array alive — no free, no RCE, CVSS 0.0)."
- "The real bug is a serialize-state cross-request UAF (ASAN-confirmed at var.c:756, `n+=1` on arrays/references, prefork-only, NOT code execution, CVSS 5.3 Medium)."
- "No `zend_fcall_info` forge, no `zend_call_function`, no `system()`, no code execution."
- Bundle `php2shell-reup.zip`, SHA-256 `74adf2c4eb82776553837d185bae165494288747b43437fd452021a6ff6a93f0` (matches blog).
- `poc_unserialize.py`: real socket client (http/https), but `--last` defaults to `0x4141414141414141`; docstring states a **leaked heap address** is required for the zval-write / `R:` route to `system()`. Default lab outcome = SIGSEGV at the marker.
- Video evidence on Ubuntu 26.04 / PHP 8.5.4 / glibc 2.39 shows `leak→call` with 288B spray, 1/8 and 1/6 success; **not reproduced** on Debian 12 / glibc 2.36.

## Mechanics correction (shared by all three)

The widely shared "cached zval pointer" story is dead. The real defect: `php_session_rfc1867_callback` runs pre-RINIT; a `memory_limit` bailout inside serialize/unserialize skips `PHP_VAR_*_DESTROY`, leaving `BG(serialize)` / `BG(unserialize)` at `level=1` with a dangling `data` pointer; the next request on the same child reuses the freed context (UAF). blasty weaponizes it via the serializer decode callback; dinosn's Chain B routes it to `zif_system` via a dangling `zend_reference`.

## SAPI survival

| SAPI | Survives R1 OOM | Chains reachable |
|---|---|---|
| Apache prefork + mod_php | yes | yes (lab-verified) |
| `php -S` | yes | untested / lab only |
| PHP-FPM / CGI | no (module shutdown + exit) | no (DoS at best) |
| LiteSpeed LSAPI | no | no |

## Decision tree

```
Repo claims RCE
├─ Driver reads /proc, uses gdb, or requires address args?
│   ├─ yes → address-assisted. Usable only after a leak (e.g. LFI → /proc/self/maps).
│   └─ no  → produce system() output on pristine build with fresh ASLR?
│             ├─ yes → real exploit code
│             └─ no  → crash/verification PoC
└─ README says lab / proof-boundary / not proven → believe it over the demo.
```
