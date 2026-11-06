#!/usr/bin/env bash
# probe-model-names.sh — 拿 provider 的权威可调用模型名清单 + 逐名探测
#
# 用法:
#   bash probe-model-names.sh <base_url> <api_key> [model_name ...]
#   bash probe-model-names.sh https://api.deepseek.com/v1 "$DEEPSEEK_API_KEY"
#   bash probe-model-names.sh https://api.deepseek.com/v1 "$DEEPSEEK_API_KEY" deepseek-flash deepseek-v4.1-flash
#
# 输出:
#   1) GET /models 的原始 body(官方"可调用名",但可能不含兼容别名)
#   2) 每个候选名一行: http 码 + 400 时的枚举消息(权威清单) + 200 时的 model 回显(判兼容路由)
#
# 关键点:
#   * 400 的 message 会枚举 provider 当前所有合法模型名 —— 这是最快的权威来源
#   * 200 响应里的 "model" 字段才是真正落地的模型(兼容路由会让它 != 请求名)
#   * 输出文件不要写 /tmp: native curl 不认 MSYS 路径,用 $LOCALAPPDATA/Temp

set -u

BASE="${1:?usage: probe-model-names.sh <base_url> <api_key> [model ...]}"
KEY="${2:?missing api_key}"
shift 2

# Windows(git-bash)优先用 $LOCALAPPDATA/Temp;Linux/macOS 退回 $TMPDIR 或 /tmp
if [ -n "${LOCALAPPDATA:-}" ]; then
  SCRATCH="$LOCALAPPDATA/Temp"
else
  SCRATCH="${TMPDIR:-/tmp}"
fi
OUT="$SCRATCH/model_probe.$$.json"
mkdir -p "$SCRATCH"

echo "== GET $BASE/models =="
curl -s -m 25 "$BASE/models" \
  -H "Authorization: Bearer $KEY" -H "Accept: application/json" \
  -o "$OUT" -w "http=%{http_code}\n"
cat "$OUT"; echo

# 未传候选名时,自动用 /models 返回的 id 逐个探活
if [ "$#" -eq 0 ]; then
  set -- $(grep -o '"id":"[^"]*"' "$OUT" | sed 's/"id":"//; s/"$//')
  echo "(no candidates given — probing ids from /models: $*)"
fi

for m in "$@"; do
  code=$(curl -s -m 25 -o "$OUT" -w "%{http_code}" "$BASE/chat/completions" \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -d "{\"model\":\"$m\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":1}")
  echo "--- $m | http=$code"
  # 400 → 枚举出的合法名(权威清单);200 → 真实落地的 model
  grep -o '"message":"[^"]*"' "$OUT" | head -1
  grep -o '"model":"[^"]*"'    "$OUT" | head -1
done

rm -f "$OUT"
