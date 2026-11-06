# Whole case-root purge after an explicit 「全部都清」 — 2026-10-21

## Why this file exists

A shared host's `/root/cases` looked like "other bots' cases, don't touch". The owner was shown the per-case inventory, warned that ~9G belonged to other operators, and replied **「全部都清」**, then confirmed the explicit choice **「整个 /root/cases 12G 全删（包括别人的案卷）」**. That is a scope escalation, not a request to re-list or to delete only our own cases.

Default remains: **own cases only** on a shared host. This file records the exception protocol and the exact execution.

## Authorization protocol

1. Build the read-only per-case inventory first (`du`, top-level names, file count, mtimes; reports only by first lines — no PII dump).
2. Present ownership groups: our old cases / other operators / shared data. State the default "others untouched".
3. If the owner answers with an unqualified 「全部」/「全部都清」, ask **one** scope question with exact consequences:
   - own cases only (~2.6G; others kept)
   - entire `/root/cases` (~12G, including other operators)
   - own data deleted, reports/hashes kept
   - cancel
4. After the answer, execute. Do not re-confirm, and do not silently downgrade a whole-root answer to own-only. The clarification answer is the authorization record; put it in the purge README.

## Read-only preflight (before any delete)

Run `scripts/roots_purge_preflight.sh /root/cases` (or equivalent) and read the file back:

```bash
df -P /
du -sh /root/cases
find /root/cases -mindepth 1 -maxdepth 1 -printf '%f\t%y\n' | sort
find /root/cases -xdev -type f | wc -l

# running tasks whose cwd is inside the tree
for p in /proc/[0-9]*; do
  c=$(readlink "$p/cwd" 2>/dev/null) || continue
  case "$c" in /root/cases|/root/cases/*)
    echo "PID ${p#/proc/} CWD $c CMD $(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)";;
  esac
done

# references from cron/path config
crontab -l 2>/dev/null | grep -F '/root/cases' || true
grep -RslF '/root/cases' /etc/cron.d /etc/crontab /var/spool/cron 2>/dev/null || true
```

Record top-level dirs + sizes + file count + mtimes into a manifest **outside** the tree. Do not hash the 12G payload; hash only the small retained report files. A cwd hit means a task owns the tree: stop only your own task; never kill an unattributed other-bot PID.

## Execution and observed result

```bash
rm -rf -- /root/cases
test ! -e /root/cases && echo CASES_GONE
df -P /
```

Observed on 2026-10-21 (this host):

- Before: **12G**, **95,077 files**, **20+ top-level case dirs**; `df -P /` = `50620216 37785700 12818132 75% /`.
- Delete: `rm -rf` completed in **3.94 s**; no process cwd hits; no cron references; no bot process killed.
- After: `/root/cases` gone; `df -P /` = `50620216 25703108 24900724 51% /`; free **12.8G → 24.9G**, usage **75% → 51%**; freed ≈**12.1G**.
- Included active/live cases (e.g. `famous-smoke-2026`) and other operators' dirs; that was the confirmed scope. Data-dependent bots may error afterwards; do not touch their PIDs.
- Outside the deleted root and intentionally untouched: `.hermes`, tools/models/browser binaries, cache, and sibling `case_*`/reports dirs. `case_kdz_reports_20261021` stayed at 720K.

## Audit outside the tree

Put these under `<case>_reports_<date>/TEARDOWN/CASES_PURGE_<date>/`, never inside `/root/cases`:

- `README.txt` — authorization quote, before/after `df`, size/file count, what was included, process/cron result, what stayed outside.
- pre-delete manifest — top-level names, sizes, file count, mtimes; no payload/PII.
- delete log — timestamps, exact command, `CASES_GONE`, final `df`.

Permissions: `700` dir, `600` files. Regenerate the case report's `SHA256SUMS` if its own files changed.

## Reporting

- Exact numbers: before/after available space, percent, freed GiB, file count, elapsed.
- Name dominant dirs and note cross-tenant/active cases were included by explicit confirmation.
- State that no process was killed and that deleting files is not a stop order.
- Name what remains outside the root and why; never say "everything clean" if `.hermes`, tools, or sibling cases remain.
- No follow-up question; the owner will name the next root if any.

## Pitfalls

- `/root/cases` is not one case. `ls` can look like a single target while 20+ tenants/campaigns are stacked inside; inventory first.
- `du -sh` and `find | wc -l` are different facts; report both. A fast `rm` of 95k files is normal; background only for millions or slow storage.
- Do not `rm -rf /root/cases/*`; dotdirs survive and the audit is less clear. Use the named root and prove it is gone.
- Do not preserve reports when the owner said the whole root goes. If they ask to keep reports, put them **outside** the root and say so.
- Do not treat 「全部都清」 as authorization for `/root` itself, `.hermes`, toolchains, models, or unrelated sibling case dirs.
- If free space does not rise as expected, check open fds (`/proc/*/fd`) — unlinked-but-open files still hold blocks; do not blindly rerun `rm`.
- Keep victim data/PII out of the manifest and final report; names/sizes only.
