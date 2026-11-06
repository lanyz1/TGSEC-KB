#!/bin/bash
# prepush-secret-gate.sh — 推前脱敏闸（TGSEC public 仓）
#
# 装：bash prepush-secret-gate.sh --install /root/TGSEC-Qtzuu
# 跑：bash prepush-secret-gate.sh --check   /root/TGSEC-Qtzuu
#
# 装好后每次 git push 自动跑；命中字面量/真私钥/AKIA/ghp_/完整 xoxb/真 sk- 即 abort。
# 字面量表：<repo>/.git/secret-denylist.txt（一行一个，不入仓）
# 扫描根：默认 hermes-skills，可用 GATE_ROOT 覆盖。
set -u
MODE="${1:---check}"
REPO="${2:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

if [ "$MODE" = "--install" ]; then
  mkdir -p "$REPO/.git/hooks"
  cp "$0" "$REPO/.git/hooks/pre-push"
  chmod +x "$REPO/.git/hooks/pre-push"
  [ -f "$REPO/.git/secret-denylist.txt" ] || : > "$REPO/.git/secret-denylist.txt"
  echo "installed: $REPO/.git/hooks/pre-push（字面量表：$REPO/.git/secret-denylist.txt）"
  exit 0
fi

cd "$REPO" || exit 0
ROOT="${GATE_ROOT:-hermes-skills}"
[ -d "$ROOT" ] || { echo "pre-push 脱敏闸 SKIP（无 $ROOT）"; exit 0; }
BL="$REPO/.git/secret-denylist.txt"
hits=0

# 1) 明文口令黑名单回潮
if [ -f "$BL" ]; then
  while IFS= read -r lit; do
    [ -z "$lit" ] && continue
    n=$(grep -rlF -- "$lit" "$ROOT" 2>/dev/null | wc -l)
    if [ "$n" -gt 0 ]; then
      echo "BLOCK 明文字面量回潮: ${lit:0:6}*** 命中 $n 文件"
      grep -rlF -- "$lit" "$ROOT" 2>/dev/null | head -3
      hits=$((hits+n))
    fi
  done < "$BL"
fi

# 2) 真实私钥体（排除讲正则的文档：要求 BEGIN 后紧跟长 base64 行）
if grep -rEl "BEGIN [A-Z ]*PRIVATE KEY-----" "$ROOT" 2>/dev/null | while read -r f; do
     grep -qE "^[A-Za-z0-9+/=]{60,}" "$f" && echo "$f"
   done | grep -q .; then
  echo "BLOCK 检测到真实私钥块"
  hits=$((hits+1))
fi

# 3) 云端密钥样式（形状收全，避免误伤讲格式的文档）
for pat in "AKIA[0-9A-Z]{16}" "ghp_[A-Za-z0-9]{30,}" "xoxb-[0-9]{8,}-[0-9]{8,}-[A-Za-z0-9]{20,}" "sk-[A-Za-z0-9]{32,}"; do
  n=$(grep -rEl "$pat" "$ROOT" 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && { echo "BLOCK 云端密钥样式 $pat 命中 $n 文件"; hits=$((hits+n)); }
 done

if [ "$hits" -gt 0 ]; then
  echo "== 推送被拦：先脱敏成 [REDACTED] 再推；讲格式的文档误报就把完整 token 形状收紧（别用 xoxb-[0-9] 这类半截模式）= "
  exit 1
fi
echo "pre-push 脱敏闸 OK"
exit 0
