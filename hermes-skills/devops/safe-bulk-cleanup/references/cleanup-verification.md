# Cleanup verification matrix (closed case)

Use after a stop order. Produce **two independent claims**: local runtime is clean; target-side residue is known.

## 1. Seven-layer local sweep

| Layer | Command | Pass criterion |
|---|---|---|
| Processes | `pgrep -af '<case patterns>'`; `process` list | Only unrelated cases; print PID + cmd |
| Listeners | `ss -lntp \| grep -E ':(<ports>)\b'` | No case port listening |
| Service manager | `systemctl list-unit-files \| grep -Ei '<keywords>'`; `list-timers --all` | No case unit/timer; disabled units report false |
| Scheduler | `cronjob list`; `crontab -l` | No case job; remove, don't pause |
| Terminal | `screen -ls`; `tmux ls` | No case session |
| `/etc/hosts` | `grep -nE '<domain\|ip>' /etc/hosts` | No temporary origin mapping |
| Temp/creds | `find /tmp -maxdepth 1 -name '<prefix>*'`; token/cookie/pkl find | No payload/session/secret files |

Run `ss` even when `ps` is empty; run `process` as an independent view, not a replacement.

## 2. systemd respawn

```bash
systemctl list-unit-files | grep -Ei 'warp|tor|se_relay|sing-box|<case>'
systemctl is-active warp-svc tor; systemctl is-enabled warp-svc tor
ss -lntp | grep -E ':(9050|9051|40000)\b'
systemctl disable --now warp-svc tor   # only if campaign-started
then re-check is-active/is-enabled + ss
```

Observed: killing the PIDs was undone by `enabled` units; `warp-svc`/`tor` came back on `9050`/`40000`. For a pre-existing unit, stop it and record the enable-state change rather than silently disabling user infrastructure.

## 3. Credential/script sanitation

- grep `*.py`, `*.sh`, `*.md`, `*.txt`, `*.json` for `Bearer`, `password`, `passwd`, `secret`, `APP_KEY`, `BEGIN .*PRIVATE KEY`.
- Delete `*token*`, `*cookie*`, `*.pkl`, `*.session`, `*.key`, `*.pem`; do not archive live secrets.
- Replace exact secret values in reports with `[REDACTED]`; **do not put short/common strings (especially the case domain) in a blind replacement list**. A domain/password-candidate collision turned every `hutaocards` into `[REDACTED]` and broke all report URLs. Use context patterns and re-check titles/URLs.
- Extract snippets into the report, then delete probe scripts (one case had 438); count them in the receipt.
- Check `~/.bash_history`; remove only offending lines, not the whole history.

## 4. Target-residue register

After stop order, target deletion is a fresh production write. At most probe one documented route, then record. Example:

```text
ID | type | attempted | result | original captured? | action
users/29 R22 Tester | test account | DELETE /admin/users/29 | 405 | n/a | /edit 404, no UI -> residual
product 1 description | overwritten field | n/a | not captured | no | set empty; irreversible
footer | overwritten field | n/a | 24 chars not captured | no | set empty; irreversible
storage/*.jpg | uploaded test image | no delete API | unknown | no | possible residual
```

Closeout:

```text
Local: 0 processes / 0 listeners / 0 jobs; systemd <units> disabled; /tmp & /etc/hosts clean.
Target: N residuals — <id> (why undeletable), <field> (original lost), <file> (no API).
```

If the target line is non-empty, never say “all clean”.

## 5. False positives / scope

- `pgrep -f` / `ps | grep` can match the shell running the scan; print PID + full cmd and exclude self.
- A broad scan finds other cases; name and leave them (e.g. a `45790` handler belonging to another engagement is not this case's).
- `systemctl list-unit-files` catches units `ps` misses; `ss` catches sockets `ps` misses.
- If a kill or delete route is refused (405/404), record it; do not loop against production.
