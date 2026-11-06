# Post-teardown disk cleanup — reports-only retention and the loose-file trap

Session: 2026-10-21, closed case `case_kdz`. The teardown had already stopped processes/listeners/cron and archived the working tree; the owner then said 「先清理磁盘」.

## Result

- Available: **7.1G → 10.4G**, used **86% → 79%**, freed **~3.4G**.
- Bulk archive destroyed: `/root/loot_archive/case_kdz_20261021` — **2.3G / 27,794 files** (victim rows, APK/WGT/source extracts).
- Retained evidence shell: `/root/case_kdz_reports_20261021/` — **672K**, `go-rwx`: `STOPPED.txt`, `TEARDOWN_20261021.md`, `MANIFEST.txt`, `SHA256SUMS.txt`, `DELETED_MANIFEST.tsv.gz`, teardown logs/scripts.
- Second-pass loose-file find: `/tmp/case_kdz_full.tgz` — **686,727,410 bytes** (plus a 45-byte `case_kdz_mini.tgz`). Deleted after hashing. `/tmp`: **791M → 136M**.
- Safe caches: uv 188.9MiB, npm ~78M, apt 127M, pocl/hashcat ~150M (~0.57G total).
- Final checks: `0` case processes, `0` attack listeners, `0` cron jobs; `1080/2222` (SSH control forwards) and system `3306/6379` deliberately untouched.

## Recipe used

1. Read-only audit first: `date -u`, `df -h /`, `du -x -h -d2 /root` → `DISK_AUDIT.txt`.
2. Create reports shell + `MANIFEST.txt`; verify it is readable.
3. Delete the known bulk archive; write `disk_cleanup_case_kdz.out` and before/after `df -P /` snapshot (`DISK_FINAL.txt`).
4. Clean only rebuildable caches; do not touch `/root/cases`, toolchains, models, or browsers.
5. **Second pass over regular files:**
   ```sh
   find /tmp -xdev -type f -size +100M -printf '%s %p\n' | sort -rn | head -20
   find /root -xdev -maxdepth 2 -type f \( -name '*.tgz' -o -name '*.tar*' -o -name '*.zip' \) -size +100M -print
   ```
   Hash each hit (`sha256sum`) into the receipt, record size/mtime, then delete. Do not rely on `du -sh /tmp/*/`: the glob matches directories only.
6. Patch the teardown report so the receipt distinguishes `ARCHIVE:` (retained reports) from `BULK_ARCHIVE:` (destroyed path + UTC time). Regenerate `SHA256SUMS.txt` after patching. Attach the report via MEDIA.

## Pitfalls

- **A stopped case can still hold a multi-hundred-MB loose archive in `/tmp`.** The first inventory listed `/tmp` directories and only searched `/root` for case names; the 686M tarball was invisible. The loose-file find is mandatory before claiming the disk pass is complete.
- Do not confuse the retained reports with the bulk archive: deleting the archive is fine, deleting the only `STOPPED.txt`/teardown receipt is not.
- Do not re-verify internal file edits by re-reading; verify external state (df, paths, listeners) and keep the receipt on disk.
- A large report can remain useful at a few hundred KB; there is no need to retain victim rows or unpacked APKs just because the case is closed.
