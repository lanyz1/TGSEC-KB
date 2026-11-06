#!/bin/sh
# Read-only preflight for deleting a case root. NEVER deletes.
# Usage: sh roots_purge_preflight.sh [/root/cases] [/root/CASE_ROOT_PREFLIGHT.txt]
set +e
ROOT=${1:-/root/cases}
OUT=${2:-/root/CASE_ROOT_PREFLIGHT.txt}

{
  echo "=== DATE ==="
  date -u
  echo
  echo "=== DF BEFORE ==="
  df -P /
  echo
  echo "=== ROOT ==="
  ls -ld "$ROOT" 2>&1
  echo
  echo "=== SIZE ==="
  du -sh "$ROOT" 2>&1
  echo
  echo "=== FILE COUNT ==="
  find "$ROOT" -xdev -type f 2>/dev/null | wc -l
  echo
  echo "=== TOP-LEVEL (name<TAB>type) ==="
  find "$ROOT" -mindepth 1 -maxdepth 1 -printf '%f\t%y\n' 2>/dev/null | sort
  echo
  echo "=== PROCESS CWD HITS ==="
  for p in /proc/[0-9]*; do
    c=$(readlink "$p/cwd" 2>/dev/null) || continue
    case "$c" in
      "$ROOT"|"$ROOT"/*) echo "PID ${p#/proc/} CWD $c CMD $(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)" ;;
    esac
  done
  echo
  echo "=== CRON / PATH REFERENCES ==="
  crontab -l 2>/dev/null | grep -F "$ROOT" || true
  grep -RslF "$ROOT" /etc/cron.d /etc/crontab /var/spool/cron 2>/dev/null || true
  echo
  echo "=== DF AFTER PREFLIGHT (unchanged) ==="
  df -P /
} > "$OUT" 2>&1

echo "WROTE $OUT"
