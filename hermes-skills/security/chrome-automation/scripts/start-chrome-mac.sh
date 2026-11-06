#!/bin/bash
# 独立作业 profile，默认不拷个人 Chrome 主号（防漏 Cookie）。
set -euo pipefail
CHROME_AUTOMATION_DIR="${CHROME_AUTOMATION_DIR:-$HOME/Library/Application Support/Google/Chrome-SurveyEngine}"
CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT="${DEBUG_PORT:-9222}"
IMPORT_PERSONAL="${1:-}"

if [[ ! -x "$CHROME_APP" ]]; then
  echo "[!] 找不到 Google Chrome: $CHROME_APP" >&2
  exit 1
fi

if pgrep -f "remote-debugging-port=${DEBUG_PORT}" >/dev/null 2>&1; then
  echo "[ok] Chrome 已在调试口 ${DEBUG_PORT}"
  exit 0
fi

mkdir -p "$CHROME_AUTOMATION_DIR"
if [[ "$IMPORT_PERSONAL" == "--import-personal" ]]; then
  echo "[!] 按你的明确要求拷贝个人 Default，作业出口会带上个人 Cookie"
  SRC="$HOME/Library/Application Support/Google/Chrome/Default"
  if [[ -d "$SRC" ]]; then
    mkdir -p "$CHROME_AUTOMATION_DIR/Default"
    rsync -a --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' \
      "$SRC/" "$CHROME_AUTOMATION_DIR/Default/"
  fi
else
  echo "[ok] 使用空作业 profile（不拷个人主号）"
  echo "    会员态请用 session_pipeline.py 导入授权 Cookie"
fi

"$CHROME_APP" \
  --remote-debugging-port="$DEBUG_PORT" \
  --user-data-dir="$CHROME_AUTOMATION_DIR" \
  --no-first-run \
  --no-default-browser-check &
sleep 2
if pgrep -f "remote-debugging-port=${DEBUG_PORT}" >/dev/null 2>&1; then
  echo "[ok] 调试口 ${DEBUG_PORT}  profile=${CHROME_AUTOMATION_DIR}"
else
  echo "[!] Chrome 启动失败" >&2
  exit 1
fi
