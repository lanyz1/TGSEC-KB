#!/usr/bin/env bash
# 推全量技能库前的可见性闸：public 一律拒绝（私钥/口令/案卷会永久留在 git history）。
# 用法：bash repo_visibility_gate.sh [repo_dir]；exit 0=private 可推，1=拒绝，2=无 remote
set -uo pipefail
REPO="${1:-$(pwd)}"
url="$(git -C "$REPO" remote get-url origin 2>/dev/null)" || { echo "FATAL: $REPO 没有 origin"; exit 2; }
slug="$(printf '%s' "$url" | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')"
json="$(curl -s -m 10 "https://api.github.com/repos/$slug" 2>/dev/null)" || json=""
vis="$(printf '%s' "$json" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception:
    print("unknown"); raise SystemExit
print(d.get("visibility") or ("private" if d.get("private") else "public"))' 2>/dev/null || echo unknown)"
echo "repo=$slug visibility=$vis"
case "$vis" in
  private) exit 0 ;;
  public)  echo "REFUSE: 公开仓禁止推入全量技能库（46 私钥块 / 8 AKIA / 114 明文口令 / 1858 份案卷）。"
           echo "        先转 Private，或只推脱敏子集。详见 tgsec-repo-publishing/references/full-library-push-gate-20261022.md"
           exit 1 ;;
  *)       echo "UNKNOWN: API 不可达/无权限，按 public 处理（宁可不推）"; exit 1 ;;
esac
