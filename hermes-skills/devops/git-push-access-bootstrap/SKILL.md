---
name: git-push-access-bootstrap
description: Use when a host can't push to a git remote (no creds).
---

# git-push-access-bootstrap

Getting **write** access to a git remote from a host that has never talked to it.
The failure mode is almost never the crypto — it is registration (nobody added the
key) or scope (key added but read-only). Both are fixable in one round.

## When to use

- `ssh -T <EMAIL-REDACTED>` → `Permission denied (publickey)`
- `git ls-remote https://github.com/o/r.git` → `could not read Username for 'https://github.com': No such device or address`
- `gh auth status` → not logged in / `gh: command not found`, but you still must push
- A recurring fusion/sync workflow must push to a long-lived repo (e.g. a knowledge-base repo the user maintains) and the current box is fresh

## Step 1 — diagnose in one shot

```sh
ssh -T <EMAIL-REDACTED> 2>&1 | head -3          # Permission denied = key not registered
ls ~/.ssh/                                     # no id_* file = nothing to register
command -v gh git                              # gh may be absent; plain git over SSH is enough
git -C <repo> remote -v                        # https remote? switch it to SSH later
ip -4 addr | grep 'inet '                      # know your own footprint before touching remotes
```

Interpretation:

- `Permission denied (publickey)` → key missing **or** not registered upstream.
- `Host key verification failed` → `~/.ssh/known_hosts` empty; not a credential problem.
- `could not read Username for 'https://...'` → non-interactive shell has no credential helper. Switch the remote to the SSH form rather than chasing a token.

## Step 2 — generate + configure (no passphrase, for automation)

```sh
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
ssh-keygen -t ed25519 -C "$(hostname)-$(date +%s)" -f ~/.ssh/github_ed25519 -N ""
cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_ed25519
  IdentitiesOnly yes
EOF
cat ~/.ssh/github_ed25519.pub     # this is what the owner pastes
```

Use a per-host key file (never reuse a personal key). `IdentitiesOnly yes` stops the agent from offering unrelated keys.

## Step 3 — the one step only the account owner can do

You cannot register a key without account access. Do **not** ask for a password or a personal access token; hand over the public-key block plus the exact navigation path, then verify yourself.

**Option A — account-level (preferred: works for every repo)**
`github.com` → avatar → **Settings** → left rail **SSH and GPG keys** → *New SSH key*.

**Option B — repo-level Deploy key**
`repo` → **Settings** → *Security and quality* → **Deploy keys** → *Add deploy key*.
⚠️ **Tick “Allow write access.”** Unticked deploy keys are read-only: auth succeeds and `git push` is still rejected. This is the classic "it authenticated, so it must work" trap.

GitLab equivalents: *Preferences → SSH Keys* (account) or *Settings → Repository → Deploy keys* (project, same write-access checkbox).

## Step 4 — verify (do not trust the owner's "done")

```sh
bash scripts/git_push_access_check.sh git@github.com:OWNER/REPO.git
```

Expected: `Hi <user>! You've successfully authenticated` plus `ls-remote` returning a SHA. Only then mark the pending action complete.

## Pitfalls

- **Deploy key without write access** authenticates fine and pushes 403 — check the toggle.
- **HTTPS remote on a non-interactive host** can never prompt; `git remote set-url origin git@github.com:OWNER/REPO.git` first.
- **Secret scanning / push protection** frequently rejects these pushes when the repo carries harvested material; strip or redact tokens, keys and dumps before committing, then push. Expect it to recur — plan the redaction pass into the workflow.
- **Fresh/near-bare host**: a previous session's paths (`/root/cases/`, tool dirs, wordlists) may simply not exist here. Check the inventory before assuming a stored campaign can be resumed, and say so plainly instead of reporting phantom progress.
- Registration latency is the user's, not the key's: generate immediately, do the local wiring, and only then wait on the paste.

## Files

- `scripts/git_push_access_check.sh` — one-shot verification of SSH auth + remote write.
