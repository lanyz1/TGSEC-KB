# Disk-at-100% emergency — 2026-10-15 (shared multi-bot host, 48G disk)

Trigger: 用户「清理磁盘没有用的 都删除」 on a box that hit **100% full (367M free, 48G disk, 8G RAM)** while
several bots/teams share it. Result after two passes: **6.1G free / 88% — ~5.7G reclaimed, zero data loss, zero other-team impact.**

## Wave order (zero-controversy first, surgical last; `df -h /` after each wave)
1. **System logs (−2.8G, zero risk):** truncate `: > /var/log/{syslog,auth.log,btmp}`; `rm` rotated (`syslog.1`);
   `journalctl --vacuum-size=10M`; `apt-get clean`; snapd cache.
2. **Old sweep archives = junk-of-junk (−1.3G):** the previous teardown's `/root/stop_sweep/` held 5 large tars of
   `/tmp` leftovers. Delete the tars; keep manifests / audit reports / the disabled-cron files (those are the
   ownership index, below).
3. **Live IDE logs — truncate, never delete (−444M):** `.trae-server/manager-logs/…` 448M → 4.4M via `truncate`.
   O_APPEND writers just keep appending. **Apparent size ≠ real occupancy:** regrown/truncated logs and sparse
   files show huge `ls`/`find -size` numbers but little real disk — judge by `du`.
4. **Closed-case trimming, every delete gated by proof (−1.15G here; case 2.0G → 0.85G):**
   - **Superset proof via `sort`+`comm`:** `invite_pool v1` was deleted only after `comm -23 <(sort v1) <(sort v2)`
     returned 0 lines (626k rows fully ⊂ 914k-row v2).
   - **gzip-in-place for raw jsonl evidence:** `for f in adm_dump/*.jsonl; do gzip -9 "$f"; done` — path/name
     survive, 785M → ~100M; spot-verify `zcat file | head`. Same for `eastern_v9` (136M → 20M).
   - **Byte-md5 dir-vs-zip:** python `zipfile` loop over every member; delete the dir copy only on 6/6 equal.
5. **Misc caches:** `.npm/_npx` + `_logs` (in addition to `_cacache`); blutter `.gch` precompiled header (152M
   compile cache — the built tool at `build/` root untouched; keep `.o`/libs if incremental rebuild speed matters).
6. **Swapfile shrink (3G→2G, −1G) — last resort:** verify real size FIRST (`swapon --show` + `ls -lh`), check RAM
   headroom (`free -h`), then `swapoff /swapfile` → recreate smaller (`fallocate`/`dd`) → `mkswap` → `swapon` →
   confirm with `swapon --show`. Same-path fstab line stays valid.

## Ownership forensics — whose stuff is this?
- **Hash-slug dirs can be THE main active case.** `drfmud7h5b2n` read as a scratch dir; it was the main target
  case (delivery zips + project notes inside). Verdict by **content**: `NOTES.md` mtime, presence of `deliver/`,
  closeout/round reports — never by name.
- **`stop_sweep/cron.d_disabled/*` is the ownership index** once crons are silenced: reading `tato-emu` showed
  `zhitian.jtxlhs.com/recon/tato_*` → the 9.2G emulator/wine stack belongs to zhitian → hands off.
- **Closeout markers** (`…-CLOSEOUT-<date>.md`, `DISK-CLEANUP-*.md`) mark a case trimmable: keep the reports,
  trim/compress the raw.
- Untouched this run: main case 2.3G, zhitian stack 9.2G, qqmmjjkk/mark cases, `loot_archive/`, bot profiles,
  toolchain (uv tools/python). hashcat/pocl caches were kept for crack throughput in pass 1, then cut in the max pass (rebuildable). tor/redis/snap stayed.
- Final report shape: freed total + per-wave category list + 「一个没碰」keep-list + **explain the remaining 43G by
  name** — don't leave the user staring at "still 90%" wondering what's left.

## Numbers discipline (mistakes made this session — don't repeat)
A multi-section probe output came back **truncated inline** and two figures were misread: swap as "8G" (was 3G) and
RAM as "251G" (was 8G) — producing a false "6G reclaimable" claim corrected mid-task. Fix: `sh probe.sh >
/root/phase2.txt` then `read_file` it — quote no figure that was not read from a file. Keep probe + cleanup scripts
and phase logs on disk (`/root/clean_*.sh`, `/root/phase*.log`) as the run's evidence.

## Second pass — max tier + final survivor inventory (same day, 「还能清理更多吗」)

5.3G → **6.1G free** (+~0.9G). Order and receipts:
1. **Old-kernel purge, simulation-gated:** `apt-get -s purge -y linux-{headers,image,modules,modules-extra,tools}-6.8.0-48*` → collateral check `grep '^Remv' sim | grep -vE '6\.8\.0-48|libxnvctrl0'` = 0 lines → real purge (`PURGE_OK`; grub/initramfs auto-ran; only running 6.8.0-142 remains in `/usr/lib/modules`, `/boot`, `/usr/src`). Then `autoremove -y` + `apt-get clean`.
2. `/opt/android-sdk/clt.zip` legacy installer −147M.
3. Rebuildable caches: `/root/.cache/{hashcat,pocl}` −74M, venv `__pycache__`, `/root/.hermes/logs/*.log.{1,2,3}`, `cache/terminal-output` >3d, `uv cache clean`.
4. **uv layout — know before wiping:** `~/.local/share/uv` = `credentials` 4K + `python/` 99M + `tools/` 534M; `tools/` = uv CLI installs (browser-use 220M, pwntools 172M, frida-tools 114M, sqlmap 18M) = tooling; `uv cache clean` leaves them alone. Deleting "uv 632M" wholesale as cache would be a mistake.
5. **SQLite reality check:** main `state.db` 1.9G, freelist ≈73 pages → VACUUM reclaims nothing; all live history (bot2 392M same). Only a retention decision shrinks it — no mechanical lever.

**Final survivor table** (proof nothing else is reclaimable) — `find / -xdev -type f -size +300M -exec du -h {} + | sort -h`:
- **gated-ask:** tato stack ≈9G (`system.img` 4.1G + `tato.avd` qcow2 2.9G + emulator + wine; zhitian's, stopped 10-09) · `loot_archive/717kk_*` 1.6G (irreversible — reopening = re-farm) · TGSEC local material ~0.67G (remote has everything).
- **owned-elsewhere (never touch):** `qqmmjjkk/loot/dy_all.sql.gz` 1.6G, `k0/loot/apk/…REAL.apk` 534M.
- **system-live:** `/swapfile` 2.1G, snap `gnome-46/mesa` ~1G (chromium runtime), live `state.db`s.
- **Sparse ghost, no action:** `.trae-server/…/ai-agent_*_stdout.log` — `ls` regrew to 347M, `du`=1.8M, `fuser -v` = writer only.
- Closing message shape that landed: 「这刀落的 → 全盘300M+总表 → 三块待点头 → 动不了的别惦记 → 点哪块拔哪块」.
