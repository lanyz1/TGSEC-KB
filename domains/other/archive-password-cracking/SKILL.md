---
name: archive-password-cracking
description: "Use when cracking a password-protected zip/7z archive."
version: 1.0.0
tags: [pentest, cracking, zip, bkcrack, wordlist, ops]
---

# Archive Password Cracking

Password-protected archives found on targets (tool bundles, deploy packages, loot backups).
Attack selection depends on BOTH the crypto and the per-entry compression method — read them
before spending any wordlist time.

## 1. Identify before attacking

- `unzip -v` prints the Method per entry (`Stored` vs `Defl:N` = Deflate) — this decides which
  attack can work (step 4).
- `zipinfo -v` shows general-purpose flags: bit 0 = encrypted, bit 3 = data descriptor (streamed
  zip). Data descriptors are fine for bkcrack — do not skip such zips.
- AES entries (WinZip AE-1/AE-2) are NOT ZipCrypto: bkcrack does not apply; only wordlists (or a
  converted hash for hashcat) can work.
- Grep the engagement's collected material first — `.bash_history`, configs and notes from
  compromised hosts sometimes hold the exact passwords/patterns the operator used for local
  archives (the same people made both).

## 2. Attack order

1. Context candidates from the same engagement (host passwords, `{name}{date}`-style patterns,
   project words).
2. rockyou pass (fast first sweep).
3. Regional list — `Pwdb_top-10000000` and locale common-password lists for Chinese-facing
   targets.
4. bkcrack known-plaintext (step 4) — small, fully-guessable entries only.
5. Other formats: rar/7z need a hashcat-format conversion (rar2john / 7z2hashcat) + the same
   wordlist order; bkcrack itself is ZipCrypto-only.

## 3. Wordlist sweep hygiene

- Cheap validation = the ZipCrypto check byte, BUT never report a hit from the check byte alone:
  it is one byte, so ~0.4% of wrong candidates pass it too (≈56k over a 14M list) and the false
  positive reaches the report unless you verify. Confirm every candidate by fully decrypting one
  entry and matching its CRC before declaring success.
- Run sweeps as background jobs that append progress to a log and write the found password to an
  out-file; poll the out-file for hits instead of scraping stdout.
- When you replace the sweep script with a fixed version, delete the old generation's out-files —
  a stale false-positive "hit" file reads as a live credential later.

## 4. bkcrack known-plaintext attack

Not packaged in distro repos — build:

    git clone https://github.com/kimci86/bkcrack
    cd bkcrack && mkdir build && cd build
    cmake -DCMAKE_BUILD_TYPE=Release .. && make -j4
    # binary: build/src/cli/bkcrack

Invocation:

    bkcrack -C archive.zip -c <entry> -p plain.bin -o <offset>
    # -x <offset> <hex>  adds extra scattered known bytes

Success prints the three internal keys — decrypt with `-k`/`-d`, or rewrite the archive under a
new password with `-U`.

**The plaintext must match the ENCRYPTED STREAM, not the file's plain content — the single
biggest trap:**

- Stored entries: ciphertext = raw file bytes → known file headers work (ELF/PNG/ZIP magic…).
  ~12+ contiguous known bytes suffice.
- **Deflate entries (`Defl:N`): the ciphertext is the COMPRESSED stream. Raw content bytes can
  never match it — feeding them always ends in "Could not find the keys".** Reproduce the
  compressed bytes yourself: deflate your guessed content (zlib raw deflate, `wbits=-15`) and
  pass THOSE bytes. The archiver's compression level is unknown — try levels 1/6/9 per guess.
- Deflate output depends on the whole input block, so only guesses of the ENTIRE entry are
  reliable (a ~200-byte Makefile, a short script, a small header). Partial prefix guesses (just a
  shebang) do not reliably reproduce a Deflate stream prefix — they still work for Stored entries.
- Cost: minutes per candidate per run → batch guesses in a background loop with a per-run timeout
  and a stop-marker on `Keys:`; log every attempt so nothing is lost.

## 5. High-value plaintext guesses

- Kernel-module Makefile: starts `obj-m += `; the classic `make -C …/build M=$(PWD) modules` body
  is near-standard — small files are fully guessable.
- Shell scripts: shebang + common prologue (Stored: direct; Deflate: only if the whole file is
  guessable).
- C headers: `#ifndef X_H` / `#define X_H` guards.
- Binaries: ELF header + program headers (Stored entries only).
