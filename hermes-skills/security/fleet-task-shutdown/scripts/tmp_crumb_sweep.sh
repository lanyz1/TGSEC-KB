#!/usr/bin/env bash
# tmp_crumb_sweep.sh — 收网时的 /tmp 碎屑清扫（keep-list 法）。
# 只删「不属于 keep 名单」的常规文件；系统件与其他案卷文件存活。
# 用法:  bash tmp_crumb_sweep.sh        # 干跑：只列会删什么
#        bash tmp_crumb_sweep.sh --go   # 真删
# 执行前先 `ls /tmp` 过一眼，把识别到但不确定归属的文件补进 KEEP_EXACT 再开删。
set -u
GO=""; [ "${1:-}" = "--go" ] && GO=1
# 系统/平台件前缀（保留）——对应「前缀清单全失配」那类坑的教训：
KEEP_RE='^/tmp/(systemd-private-|snap-private-tmp|safe-rm-source-flag-|sandbox-source-flag-|org\.chromium|\.org\.chromium|hermes-|node-compile-cache|xvfb-run|\.ICE-unix|\.X11-unix|\.XIM-unix|\.font-unix)'
# 其他案卷 / 平台显式文件基线（按需增删）：
KEEP_EXACT='^(qb|fx|lsm\.xml|yfs|toolkit_index\.json|wh\.json|whr\.json)$'
del=0; kept=0
for f in /tmp/*; do
  b="${f#/tmp/}"
  if [ -d "$f" ] || [[ "$f" =~ $KEEP_RE ]] || [[ "$b" =~ $KEEP_EXACT ]] || [[ "$b" == .* ]]; then
    kept=$((kept+1)); continue
  fi
  if [ -z "$GO" ]; then echo "DRY would-delete: $f"; else rm -f -- "$f"; fi
  del=$((del+1))
done
echo "candidates=$del kept=$kept mode=$( [ -n "$GO" ] && echo GO || echo dry-run )"
