---
name: public-poc-provenance-triage
description: Use when judging if a public PoC is real or lab-only.
---

# Public PoC provenance triage

When the user drops two or three GitHub/blog links and asks **"到底哪个才是真实的 PoC、能在实战环境用，而不是靶场"**, the deliverable is a per-source verdict with evidence — not a CVE summary and not a status report on your current campaign.

## Answer shape (user preference)

1. **First line names the winner outright**: "三个里只有 X 是真的，另外两个不是。" If none is field-usable, say that in the same breath — but still name which one is *real code*.
2. Per source: **one verdict word + one-line reason + the verbatim evidence line** (file, function, receipt). No adjectives without a quote.
3. Close with the discriminator that decides field usability (address leak, SAPI, worker model) — not with unrelated target-pool progress. A bare "？" after a buried answer means: lead with the verdict, drop the detour.

## Verdict taxonomy

| Class | Fingerprint | Field-usable? |
|---|---|---|
| **Real field weapon** | Network-only driver, no debugger/`/proc`, no address args, target-side execution proof | yes, if preconditions hold |
| **Address-assisted real exploit** | Same chain, but requires leaked heap/module/libc addresses (CLI args or seed endpoint) | only after you obtain a leak |
| **Lab harness** | Addresses measured by host gdb/`/proc`, single worker, docker-only bridge, pinned image | no |
| **Crash / verification PoC** | Default marker addresses (`0x4141…`), output is SIGSEGV/500, no call primitive | no |
| **Analysis / debunk** | Writeup + reproductions, may refute the popular PoC | no (but read it first) |
| **Repackaged unrelated bug** | Old technique wearing the CVE name (e.g. 2016 `session.upload_progress` + LFI) | only if that precondition exists |

## Evidence ladder (run in this order)

1. **Read the proof boundary, not the demo.** `PROOF-BOUNDARY.md`, "What this repository does NOT prove", `## Reproduction scaffolding and limitations`. Lines like `lab-assisted`, `in-band address sourcing remains open`, `no portable ASLR-independent chain`, `single worker` are the author's own honest scope — believe them over any video.
2. **Grep the driver for address sourcing.** `grep -nE '/proc|gdb|ptrace|nm |maps' *.py *.sh`. If the exploit process itself reads them → lab. If a separate `discover.py`/`seed.php` only runs in Docker → address-assisted lab.
3. **Check the CLI contract.** Missing-argument branches like `SystemExit('supply --heap-base ...')` prove the tool cannot run blind. A `--stale-context` / `--libc-base` / `--dtor <leak>` flag is the confession.
4. **Inspect default args.** `--last 0x4141414141414141` or `MARKER` defaults mean the shipped run is a crash receipt; RCE needs a real pointer substituted in.
5. **Check the precondition surface.** SAPI (prefork vs FPM), worker count, `memory_limit`, allocator (`USE_ZEND_ALLOC=0` is non-default), pinned image digest, seed endpoint. Any of these that a live target won't have = not field-usable.
6. **Look for the honest validation line.** `VALIDATION=PASS ... runs=N unique_*_bases=N` is strong evidence the chain is real — but read the command that produced it: `SYS_PTRACE`, `seed.php`, or `docker exec gdb` downgrade it to lab.

## Red flags

- `PRIVATE / EMBARGOED` header on a public repo = leaked research, not vendor-blessed; unverified until you reproduce.
- `FIRE_GDB=0` does **not** mean no addresses — it means the addresses were measured *before* firing and are baked into the body.
- `VALIDATION=PASS` + `SYS_PTRACE` + `seed.php` is still a lab recipe.
- "500 / connection drop / `Allowed memory size exhausted`" proves the arm landed, never RCE. RCE proof = `system()` output or a marker file written by the target.
- A video showing 1/8 success is not a reproducible exploit; note the glibc/kernel dependency.
- Absence of a public weapon ≠ absence of the bug. Say "no public blind exploit yet", not "not exploitable".

## Worked example

PHP2Shell (CVE-2026-109618/109619), 2026-10 — three sources, verdict **blasty real / dinosn lab / jackalsyn debunk**. Full quotes, receipts, SAPI matrix and decision tree: `references/php2shell-2026-10.md`.

## Pitfalls

- Don't let a paywalled "full exploit" claim count as evidence either way — classify by code you can read.
- Don't conflate "needs a leak" with "fake". An address-assisted chain is real exploit code with an unmet prerequisite; the correct sentence is "real, but not blind".
- When the user's wording is "实战 / 不是靶场", the deciding question is **what the attacker must already possess** (leak, seed, single worker, non-default allocator), not whether the code is well-written.
- If a PoC's root-cause story contradicts another researcher's corrected writeup, read both before judging: one may be debunking a *different* primitive (e.g. cached-pointer vs context-global UAF) while the other's chain still works.
