#!/usr/bin/env bash
# oob_hit_watch.sh <logfile> [marker] [interval_seconds]
# Alert-and-exit when a NEW marker line lands in the OOB log. Designed to run as a
# notify-on-exit background job: exit(0) + output == the user gets pinged only on a real hit.
# Marker filtering keeps internet scanner noise on a public port from firing the alarm.
# Usage: bash oob_hit_watch.sh /root/cases/<target>/oob_hits.log /HIT 120
#
# Counting note: awk|wc only. `grep -c ... || echo 0` captures "0\n0" on zero matches
# (grep prints 0 AND exits 1), which breaks every numeric compare below — symptom is
# `[: integer expression expected` spam and a watcher that never fires. Do not "fix"
# this back to grep -c.
LOG="${1:?usage: oob_hit_watch.sh <logfile> [marker] [interval]}"
MARKER="${2:-/HIT}"
IVL="${3:-120}"
MAX_WAIT_H="${MAX_WAIT_H:-12}"   # exit non-alert after N hours so the job cannot live forever
count() { awk -v m="$MARKER" 'index($0, m) > 0' "$LOG" 2>/dev/null | wc -l | tr -d ' '; }
mark_lines() { awk -v m="$MARKER" 'index($0, m) > 0' "$LOG" 2>/dev/null; }
LAST=$(count)
START=$(date +%s)
while true; do
  sleep "$IVL"
  NOW=$(count)
  if [ "$NOW" -gt "$LAST" ]; then
    echo "!!! OOB HIT ($MARKER x$NOW) !!!"
    mark_lines | tail -n $((NOW - LAST))
    exit 0
  fi
  if [ $(( ( $(date +%s) - START ) / 3600 )) -ge "$MAX_WAIT_H" ]; then
    echo "oob_hit_watch: no hit after ${MAX_WAIT_H}h, exiting"
    exit 0
  fi
done
