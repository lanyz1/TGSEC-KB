# Scan Matrix and Scanner Recipes

Companion detail for `repo-credential-leak-audit`. All examples are placeholders; never paste a real key.

## 15-point matrix

Mark PASS / HIT / N/A with counts for each:

1. Worktree files, including ignored and untracked (exclude `.git/` only).
2. All git objects: blobs, commits, annotated tags (`git cat-file --batch-all-objects --batch-check`).
3. Commit and tag messages.
4. Every `sk-`-like candidate, mapped to path + context.
5. `.env` / `.env.*` (real values vs `.env.example` placeholders).
6. Archives: zip, tar, gz, tgz, 7z, rar, jar, apk.
7. PDFs: extract text, then scan.
8. CI/config: `.github/workflows`, `.gitlab-ci.yml`, Jenkinsfile, build configs.
9. Image binaries: PNG/JPEG/WebP/GIF (metadata and embedded text).
10. Symlinks: record targets; check outside-repo targets.
11. `git stash list`, `git notes list`, `git replace -l`.
12. `git fsck --full --unreachable --no-reflogs`; then scan unreachable objects.
13. `git config --list --show-origin` for credentials in remotes/URLs.
14. Runtime config outside the repo (confirm the key lives there and was not copied in).
15. Remote refs and visibility; compare target status with a known-public control.

## Worktree scanner

```python
import os, base64

REPO = '/path/to/repo'
KEY = b'PLACEHOLDER_KEY_BYTES'
needles = {
    'exact': KEY,
    'b64': base64.b64encode(KEY),
    'b64url': base64.urlsafe_b64encode(KEY),
    'b64_nopad': base64.b64encode(KEY).rstrip(b'='),
}
overlap = max(len(v) for v in needles.values()) - 1
files = 0
bytes_scanned = 0

for root, dirs, names in os.walk(REPO):
    dirs[:] = [d for d in dirs if d != '.git']
    for name in names:
        path = os.path.join(root, name)
        files += 1
        try:
            with open(path, 'rb') as fh:
                prev = b''
                while True:
                    chunk = fh.read(4 << 20)
                    if not chunk:
                        break
                    bytes_scanned += len(chunk)
                    buf = prev + chunk
                    for label, needle in needles.items():
                        if needle in buf:
                            print('HIT', label, path)
                    prev = buf[-overlap:] if overlap else b''
        except (IsADirectoryError, PermissionError, OSError):
            pass
print('files_scanned', files, 'bytes_scanned', bytes_scanned)
```

The walk deliberately does not consult `.gitignore`; ignored `.env` files are exactly what this audit must catch.

## All-object scanner

```python
import subprocess, base64

REPO = '/path/to/repo'
KEY = b'PLACEHOLDER_KEY_BYTES'
needles = {'exact': KEY, 'b64': base64.b64encode(KEY),
           'b64url': base64.urlsafe_b64encode(KEY)}

rows = subprocess.check_output(
    ['git', '-C', REPO, 'cat-file', '--batch-all-objects', '--batch-check'],
    text=True).splitlines()
blobs = [r.split()[0] for r in rows if r.split()[1] == 'blob']
commits = [r.split()[0] for r in rows if r.split()[1] in ('commit', 'tag')]

def stream(shas):
    p = subprocess.Popen(['git', '-C', REPO, 'cat-file', '--batch'],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for sha in shas:
        p.stdin.write(sha.encode() + b'\n')
        p.stdin.flush()
        header = p.stdout.readline().split()
        if len(header) < 3 or header[1] == b'missing':
            continue
        size = int(header[2])
        data = p.stdout.read(size)
        p.stdout.read(1)
        yield sha, data
    p.stdin.close()
    p.wait()

for sha, data in stream(blobs + commits):
    for label, needle in needles.items():
        if needle in data:
            print('HIT', label, sha)
```

Use `--batch-all-objects`, not `git rev-list --all`; the former includes unreachable objects. The stream covers blobs plus commit/tag messages; for filenames use `git ls-tree -r --name-only <sha>` separately. If the repo is huge, write hits to a file rather than flooding chat.

## Candidate taxonomy

`sk-` is a prefix family, not a key detector. Boundary-aware extraction:

```python
import re
candidates = set(re.findall(rb'(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}', data))
```

Mask before printing: first 6 + `...` + last 4. Classify by context, not by shape alone:

| Context | Usually | Action |
|---|---|---|
| `sk-ant...xxxx` in README | documentation placeholder | example |
| `sk-ant...hort` / `...-abc` in tests | test fixture | example |
| `sk-Is-...` inside a GUID-like token | false positive | exclude |
| `sk-run...` inside a URL/slug | false positive | exclude |
| 32+ hex after `sk-`, in `.env`/config | possible live key | investigate |

A candidate containing `EXAMPLE`, `XXXX`, `REDACTED`, `PLACEHOLDER`, `FAKE`, or `1234567890` is likely inert — but still record path and context.

## Guard exemption review

If a guard logs `AKIA=22 / ghp=5 / sk=3`:

1. Do not trust the totals.
2. Reproduce the extraction over the same object set.
3. Map every exempted candidate to blob/path and context.
4. Identify which exemption token caught it (e.g. `XXXX`).
5. Report why each is inert, or escalate if any is live.

A historical `sk=3` may be exactly three test strings — or three real keys hidden by an over-broad `XXXX` rule. Only the path/context review settles it.

## Visibility check

```bash
git -C "$REPO" ls-remote origin 'refs/pull/*' 'refs/heads/*' 'refs/tags/*'
curl -s -o /dev/null -w 'target=%{http_code}\n' "https://api.github.com/repos/OWNER/REPO"
curl -s -o /dev/null -w 'control=%{http_code}\n' "https://api.github.com/repos/torvalds/linux"
```

- target 404 + control 200 + working SSH push = private, not gone.
- only `refs/heads/master` = no PR refs/tags/orphan branches on the remote.
- Git objects still exclude issues/PR comments, Actions logs, release assets, and wiki pages.

## Reporting template

```
Verdict: no exact key / leak in history / inconclusive
Fingerprint: length=NN sha256=XXXXXXXX
Worktree: N files / X MB -> 0
Git: C commits / B blobs / O objects (including unreachable) -> 0
Archives: N; PDFs: N -> 0
Candidates: K unique sk- strings -> all example/test (paths...)
Guard: sk=K exemptions -> reproduced, all inert
Remote: only master=<sha>; target 404 vs control 200 = private
Boundary: issues/PR comments/Actions logs/release assets not enumerated
```

## Worked clean audit (2026-10-17)

A private repo, 35-char DeepSeek key:

- Worktree 29,914 files / 316 MB: 0 exact; 6 `.env.example`; no real `.env`.
- 85 commits / 27,227 blobs / 36,233 objects including unreachable: 0 exact; 0 `sk-`+32-hex; base64 variants 0; commit messages 0.
- 15 archives + 9 PDFs: 0.
- 119 files / 214 lines mention DeepSeek, all docs/rules/variable names.
- Only 3 unique `sk-` candidates; all were the guard's `sk=3` exemptions and all were test/example strings (`keyhunter/README.md`, `keyhunter/tests/patterns_test.rs`).
- Remote: only master; anonymous API/web 404 vs public control 200 = private.

This is the target shape: exact match absent everywhere, every regex candidate explained, guard exemptions reproduced, side-channel boundary stated.
