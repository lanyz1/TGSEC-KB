# bcrypt on CPU: john vs hashcat, restore, false negatives

## Which tool

- On a CPU-only host, `john --format=bcrypt --fork=N` is usually the better
  parallel path. A single OpenCL CPU device in hashcat is slower, and hashcat
  refuses to start a second instance on the same device.
- `hashcat -m 3200` is still useful for a GPU host. Do not run hashcat and john
  against the same CPU expecting a speedup; they compete for cores.
- bcrypt cost 12 is deliberately slow. A 7,000-10,000-line member password
  list is already a long run; plan for hours, not minutes.

## john command discipline

- `john --restore` must be run alone. `john --restore --format=bcrypt --fork=8`
  fails (the restore session already carries format/flags).
- Older john builds may not support `--pot=...`; use the default
  `~/.john/john.pot`. Check `john --list=build-info` if unsure.
- Start a long run in a background terminal with `notify=True`; the foreground
  tool timeout may cut at ~420s. Poll the process, then read the log and pot
  file after exit.
- For a four-digit suffix mask, generate a wordlist (e.g. base string + 0000
  through 9999) and run `john --format=bcrypt --fork=8 --wordlist=...` rather
  than a huge inline mask expression.
- If a job is killed or times out, the pot may be empty even though some
  candidates were tested; check the log for progress/restore points before
  rerunning from zero.

## False-negative self-check

Before reporting "0 cracked":

1. Put a known hash and its known plaintext in a small file.
2. Run the exact same john/hashcat command against it.
3. Confirm the known password appears in the pot.
4. Only then trust the negative result on the real hashes.

This catches wrong hash extraction, wrong `$2y$`/`$2a$` handling, and a command
that silently did nothing.

## What a negative result means

- If the self-check passes and the full list was consumed, the admin hashes do
  not reuse any tested member password, mask, or variant.
- Do not expand to online brute force after a negative offline result; admin
  lockouts are usually worse than the offline cost. Record the result and move
  to token/session, SQL write, or another control-plane surface.
