---
name: repo-credential-leak-audit
description: Use when checking if a repo leaked a specific credential.
version: 1.0.0
revision_date: 2026-10-17
license: MIT
platforms: [linux]
compatibility: Requires git, python3, curl
tags: [git, secret, credential, leak, audit, history, incident-response]
category: security
related_skills:
  - github-secret-hunting
  - source-leak-hunt
  - insecure-source-code-management
---

# Repository Credential Leak Audit

Defensive, negative-proof audit for one question: **did this repository ever contain credential X, and is it exposed?** This is the counterpart to public GitHub secret hunting. Use exact matching, not regex hit counts. Do not use dorking tools or third-party scanners on your own key — they cannot prove absence and may send the key to a remote service.

## When to Use

- User asks "did my repo leak my DeepSeek/OpenAI/cloud key?"
- A push guard or scanner reports exempted `sk` / `AKIA` / `ghp` hits and you must decide whether they are examples or live keys.
- You need to decide whether to rotate a key after a commit, amend, force-push, or accidental `.env` inclusion.
- You need a defensible "clean" result rather than a single `grep` that only covered HEAD.

## Non-Negotiables

1. **Never print the key.** Read it from its real source; report only `length` and `sha256(value)[:8]`. Do not put it in a shell argument, URL, `git grep` pattern, or chat message.
2. **Exact match is the verdict; regex is only candidate discovery.** A clean result means the exact bytes are absent from every scanned surface, not that `sk-` returned zero.
3. **All objects, not just reachable commits.** `git rev-list --all` misses unreachable objects left by resets, amends, rebases, and force-pushes. Enumerate with `git cat-file --batch-all-objects --batch-check`.
4. **Worktree means files, not `git grep`.** `git grep` sees only tracked files at HEAD; ignored `.env`, local backups, and untracked files need an `os.walk`-style scan excluding only `.git/`.
5. **Classify every regex candidate.** Map each unique `sk-` string to path + context; label example/test/live. Never accept a guard's exemption count as proof.
6. **Separate git from GitHub.** Git objects do not include issues, PR comments, Actions logs, release assets, or wiki pages. State that boundary if you did not have an API token to enumerate them.

## Procedure

### 1. Capture the needle safely

Parse the local config/file, compute the fingerprint, and keep the value in memory only:

```python
import hashlib
v = open('/path/to/secret').read().strip().encode()
print('length', len(v), 'sha256', hashlib.sha256(v).hexdigest()[:8])
```

Build scan needles: exact bytes, base64, urlsafe-base64, and hex if applicable. Include the trailing/leading whitespace variants only if the source file could contain them; otherwise normalize once.

### 2. Baseline the repository

```bash
cd "$REPO"
git remote -v
git branch -a
git rev-list --objects --all | wc -l
git cat-file --batch-all-objects --batch-check | awk '$2=="blob"' | wc -l
git fsck --full --unreachable --no-reflogs
git count-objects -v
```

Record commits, blobs, total objects, and whether unreachable objects exist. A large object count is normal; do not skip the all-object scan because it is slow.

### 3. Scan the worktree including ignored/untracked files

Walk from the repo root, prune `.git/`, and read every file in chunks. Use an overlap of `max(len(needle))-1` so a needle spanning a chunk boundary is not missed. Skip nothing based on `.gitignore`. Report file count and total bytes scanned.

### 4. Scan every git object

Enumerate all blobs, commits, and annotated tags via `git cat-file --batch-all-objects --batch-check`; stream contents with `git cat-file --batch` (not one process per object if the repo is large). Search blobs for exact/base64 needles and commit/tag messages for exact strings. Tree entry names are a separate filename surface; enumerate them with `git ls-tree -r --name-only` if the key could be a filename. The count includes unreachable objects; that is intentional.

### 5. Discover and classify `sk-` candidates

Use a boundary-aware regex: `(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}`. Collect unique values, but output only a masked form (`sk-ant...xxxx`) plus path and one context line. Common false positives: C# GUID fragments (`sk-Is-...`), URL slugs (`sk-run...`), and test fixtures (`sk-ant...xxxx`, `sk-ant...hort`, `sk-ant...-abc`). A candidate is only "live" if it is not a documented example and the exact value is not already explained by the source context.

### 6. Cover side channels

Archives (zip/tar/gz/tgz/7z/rar/jar/apk), PDFs (pypdf text extraction), symlinks, `.github/workflows` / CI configs, image binaries, `git config --show-origin`, `git stash list`, `git notes list`, `git replace -l`, and the runtime config outside the repo. A real `.env` is a hit; a `.env.example` with placeholders is not.

### 7. Check remote refs and visibility

```bash
git ls-remote origin 'refs/pull/*' 'refs/heads/*' 'refs/tags/*'
curl -s -o /dev/null -w 'target=%{http_code}\n' "https://api.github.com/repos/OWNER/REPO"
curl -s -o /dev/null -w 'control=%{http_code}\n' "https://api.github.com/repos/torvalds/linux"
```

Only `refs/heads/master` means no PR/tag/orphan refs on the remote. `target=404` with `control=200` and a working SSH push usually means private, not deleted. If the remote accepts the push, the repo exists.

### 8. Write the verdict

State one of:

- **No leak:** exact key absent from worktree, all git objects, archives, PDFs, and commit messages; all regex candidates are examples; guard exemptions reproduced.
- **Leak in history but not current HEAD:** give blob path, commit SHA, whether the object is reachable, and whether it was ever pushed; recommend rotation and history rewrite only if the remote contains it.
- **Inconclusive:** name the unenumerated surface (issues/PR comments, Actions logs, release assets, remote unreachable objects) and what access is needed.

## Counterpart: mining a target's public repository (authorized)

When the repo belongs to the target and you need **candidate** credentials, not a negative proof:

```bash
git clone --mirror <repo> /tmp/repo.git && cd /tmp/repo.git
git log --all --diff-filter=A --name-only --pretty=format:'%h %ad %s' --date=short -- '*.env*' '*config*' '*docker-compose*'
git log -p --all -G 'APP_KEY|DB_PASSWORD|REDIS_PASSWORD|MAIL_PASSWORD|SECRET_KEY|API_KEY|TOKEN' -- '*.env*' '*config*' '*.yml' '*.yaml'
```

- Use `grep -RinE '(pass(word|wd)?|secret|token|api[_-]?key|app[_-]?key)'` — mixed-case YAML/PHP keys are common; case-sensitive grep misses them.
- `.env.example` / `config.example.yml` / `docker-compose.yml` may contain **real-format defaults**; classify demo vs live, then test once against the exact service.
- Repo defaults frequently do not work in production; do not re-run the same matrix across every service.
- When `read_file` refuses a secret-bearing `.env`, inspect keys only (`grep -E '^[A-Za-z_]+=' | sed 's/=.*/=[REDACTED]/'`).
- Never print values; apply the same fingerprint/redaction rules to candidate discoveries.
- Full case notes: `references/public-repo-candidate-mining.md`

## Pitfalls

- **`git rev-list --all` is not the object database.** Use `--batch-all-objects`; scan unreachable objects too.
- **`git grep` is not a worktree scan.** It misses ignored and untracked files.
- **A regex hit is not a leak.** `sk-` matches GUIDs, URL slugs, and test strings; inspect path/context.
- **Guard exemption counts are not evidence.** `sk=3` can be three test fixtures or three suppressed live keys. Reproduce the candidate list and map paths.
- **Never put the key on a command line.** Use config/file reads, compare hashes in memory, and mask output.
- **A 404 is not proof of deletion.** Compare with a known-public control repo; 404 + working SSH push usually means private.
- **Don't overclaim.** Git history being clean does not cover GitHub-side comments/logs/assets.

## Verification

- [ ] Key fingerprint recorded; raw value never printed.
- [ ] Worktree scan includes ignored/untracked files; file/byte counts recorded.
- [ ] All git objects scanned, including unreachable; blobs + commit messages covered.
- [ ] Archives, PDFs, CI configs, symlinks, stash/notes/replace checked.
- [ ] Every `sk-` candidate mapped to path/context and classified.
- [ ] Guard exemptions reproduced and explained.
- [ ] Remote refs/visibility checked; side-channel boundary stated.
- [ ] Recommendation (rotate / no action / rewrite) follows from the evidence.

## References

- `references/scan-matrix-and-scanner.md` — 15-point matrix, scanner code, candidate taxonomy, guard review, reporting template, and a worked clean-audit example.
- `references/public-repo-candidate-mining.md` — offensive counterpart: cloning an operator repo, git-history `-G` mining, case-insensitive config grep, demo-vs-live classification, and the case study where `postsort:postsort` did not work live.
- `github-secret-hunting` — public/third-party GitHub secret hunting (user-owned; do not treat it as an own-repo negative-proof procedure).
