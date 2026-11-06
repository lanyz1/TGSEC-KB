---
name: archive-extraction
description: "Use when extracting rar/zip/7z artifacts to read or study."
version: 1.0.0
---

# Archive extraction & verification

Users hand over archives (`.rar` / `.zip` / `.7z` / `.tar.*`) — often several at once, often with a
wrong or misleading extension — and expect the contents read. Extraction *appearing* to work is
not evidence the contents landed. Verify every time, by byte size.

## Procedure

1. **Identify the real format — never trust the extension.**
   ```bash
   file -b "<archive>"     # e.g. RAR archive data, v5 / Zip archive data / 7-zip archive data
   ```
   Mislabeling runs both ways: a `.go` member inside an archive can actually be C source, and an
   archive can be named after something unrelated to what it holds.

2. **Choose the extractor from the detected format, not from habit.**

   | Detected | Use | Why not the alternative |
   |---|---|---|
   | RAR (v4 **or v5**) | `unrar x -y <a> .` | p7zip ≤16.02 **lists RAR5 correctly but extracts 0-byte files**, exit 0, no error |
   | Zip | `7z x -y -o<dir> <a>` / `unzip -o <a> -d <dir>` | either is fine |
   | 7z | `7z x -y -o<dir> <a>` | — |
   | tar.* | `tar xf <a> -C <dir>` | — |

   `apt-get install unrar` provides `/usr/bin/unrar`. If RAR5 extraction yields empty files,
   re-extract with `unrar` — do **not** conclude the archive is corrupt.

3. **Extract each archive into its own fresh directory**, so a mixed batch cannot collide:
   ```bash
   for pair in "name1:<path1>" "name2:<path2>"; do
     k="${pair%%:*}"; f="${pair#*:}"
     mkdir -p "$k" && (cd "$k" && unrar x -y "$f" . >/dev/null 2>&1)
   done
   ```

4. **Verify by byte size — this is the step that catches silent failure.**
   ```bash
   find <dir> -type f -exec sh -c \
     'printf "%8s  %s\n" "$(stat -c%s "$1")" "$1"' _ {} \; | sort
   ```
   A 0-byte "source file" is a tool bug until proven otherwise. Then confirm each member's real
   type with `file -b` before reading it as code.

5. **Check for nesting before reading.** An archive-inside-an-archive is common — a plain outer
   container holding an encrypted or compressed inner layer. Recurse one level and re-run step 2
   on what comes out.

## Encrypted archives

A password prompt is not a dead end. Work it in this order:

1. **Check whether only the data is encrypted.** `unrar l <a>` listing member names ⇒ headers are
   *not* encrypted; only file data is (AES-256-CBC in RAR5). You keep the file inventory, which
   tells you what you are unlocking before you unlock it.
2. **Try candidate passwords, cheapest first** — loop `unrar` rather than reaching for a cracker:
   ```bash
   for pw in "$@"; do
     rm -rf /tmp/pwv; mkdir -p /tmp/pwv
     if unrar x -y -p"$pw" "$F" /tmp/pwv/ </dev/null >/dev/null 2>&1 \
        && [ -n "$(find /tmp/pwv -type f -size +0c)" ]; then echo "HIT: $pw"; break; fi
   done
   ```
   `</dev/null` stops `unrar` hanging on the interactive prompt; the **non-zero-size check is the
   verdict** — exit code alone is not (see Pitfalls).
3. **Include the literal channel/group handle, complete with any `@` or `#` prefix.** Community-shared
   archives commonly use the source channel handle verbatim, prefix included — `@name` and `name`
   are different passwords and only one works.

**Reverse-engineering the hash instead:** hashcat mode `13000` (RAR5) implements the check as the
PBKDF2-HMAC-SHA256 output folded down to 8 bytes; its OpenCL source ships at
`/usr/share/hashcat/OpenCL/m13000-pure.cl` — read it rather than guessing the field layout. Note that
naively assuming field order in the RAR5 encryption extra-area will not reproduce it (see the
`$rar5$` layout in `hashcat --example-hashes`), so validate any extractor against an archive you
created yourself with a known password.

**Creating your own test archive**: `rar` (the archiver) is a different package from `unrar`
(`apt-get install rar`, universe/multiverse). `unrar` cannot create archives.

## Creating archives (packaging deliverables)

Same problem in reverse: **a packer that exits 0 can silently omit members**. Verify by member count, never by exit code.

| Task | Use | Why |
|---|---|---|
| Dir with **non-ASCII / CJK names** | `zipfile.ZipFile(out, 'w', ZIP_DEFLATED)` (Python) | **7z with a recursive wildcard (`7z a out.7z "prefix_*"`) silently SKIPS non-ASCII-named files** — directories land, the CJK files do not. Spot-checking one explicitly-named file passes, so the failure hides |
| Huge tree, size matters | `tar --force-local -cf x.tar …`, then compress | GNU tar keeps UTF-8 names losslessly; a bare `C:/x.tar` is parsed as remote `host:path` ⇒ `Cannot connect to C: resolve failed` — pass `--force-local` (MSYS `/c/...` also works) |
| Cross-platform browsing | `.zip` | Windows Explorer and 7-Zip both open UTF-8 zips directly; `.tar.gz` costs an extra open step |

**Exclude dependencies, keep the buildable tree:** drop `vendor/`, `node_modules/`, `runtime/`, `.git/`,
`*.log`; keep `config/`, `migrations/`, `docs/`, `composer.json` / `package.json` so the receiver can
install their own deps.

**Account for every file — the step that catches the loss.** Build the on-disk list with the *same*
exclusions, list the archive, diff both sets, and print the non-ASCII member count:

```python
disk = sorted(...)                      # os.walk with the same SKIP rules
with zipfile.ZipFile(out) as z:
    inzip = z.namelist()
print(len(disk), len(inzip), sorted(set(disk)-set(inzip)), sorted(set(inzip)-set(disk)))
print(sum(1 for n in inzip if any(ord(c) > 127 for c in n)))   # proves CJK survived
```

Counts must be equal and both diff sets empty; the non-ASCII count is exactly what a naive packer
drops. Report the archive as verified only after this prints clean.

## Pitfalls

- **A packer's exit 0 says nothing about coverage.** Wildcard-driven archivers can skip whole classes
  of filenames (CJK/non-ASCII) without any error. Count members against the source and diff the sets
  before calling a deliverable done.
- **Exit code is not success.** Extractors exit 0 while writing empty or partial output. Verify
  with sizes (step 4) and member types. Conversely, when a tool *prints* a failure banner, still
  inspect the output directory — some extractors report an error and extract correctly anyway.
- **RAR5 is not RAR4.** Older 7-Zip/p7zip builds handle v4 and fail silently on v5. Detect the
  version from `file -b` (`RAR archive data, v5`) and route to `unrar`.
- **Never re-extract over an existing tree to "fix" a partial run.** Stale files from the first
  attempt make the second attempt look successful. Remove the target directory first; if a batch
  script re-runs, clear its output path at the start.
- **A large copied tree with near-zero real content is a symptom, not a size win.** If a clone or
  extract reports success but the member count is what you expected and the sizes are not, stop
  and re-check with steps 1 and 4 rather than proceeding to read nothing.
- **Extraction is not ingestion.** Once contents are readable, dedupe against what the destination
  library already documents instead of importing everything — follow that library's own
  ingestion rules for what counts as incremental.

## Verification checklist

- [ ] Format detected with `file -b`, not assumed from the extension
- [ ] RAR5 routed to `unrar`, not p7zip
- [ ] Every extracted member has non-zero size
- [ ] Member types confirmed; mislabeled extensions noted before reading as code
- [ ] Nested containers checked one level down
