#!/usr/bin/env bash
# 通道「批前自检」：每条候选通道发 1 条最便宜的读端点，打印 状态码+耗时+形状 三元组。
# 批前先跑它，把被拉黑的通道划掉，再谈批量/爆破 —— 避免整批中段全空还误当成结果。
#
# 用法: ./channel_preflight.sh <ip或域名> <Host头> <路径> [POST_JSON]
#   ./channel_preflight.sh 203.0.113.10 example.com /api/shop/info '{"token":"x"}'
#   ./channel_preflight.sh example.com example.com /api/ping
# 多通道: 循环调用并把输出行追加到批次日志里。
#
# 判读（重要）:
#   code=000 且 time≈0.1s      => 该出口在 TCP 层被拉黑（RST/丢包），划掉这条通道，别改 payload
#   code=000 且 time≈--max-time=> 超时（丢包/黑洞），同样不是「端点不存在」
#   code=200 但 body 空/0 字节 => 预算耗尽静默丢 或 上游服务不在，需换通道做对照
#   code=200/401 带业务文案     => 通道可用，记进批次日志再上量
# 铁律: 一条通道的结论不算结论 —— 换一个干净出口/另一台源站节点发同一条请求做 A/B。
set -u
U="${1:?usage: $0 <ip|domain> <Host> <path> [json]}"
H="${2:?usage: $0 <ip|domain> <Host> <path> [json]}"
P="${3:?usage: $0 <ip|domain> <Host> <path> [json]}"
D="${4:-}"
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'
HDR=(-H "Host: $H" -H "User-Agent: $UA" -H 'Accept: application/json')
if [ -n "$D" ]; then
  HDR+=(-H 'Content-Type: application/json' -H "Origin: https://$H" -X POST --data "$D")
fi
out=$(curl -s -k -m "${PREFLIGHT_TIMEOUT:-12}" -w '\n%{http_code} %{time_total}\n' "${HDR[@]}" "https://$U$P" 2>&1)
meta=$(printf '%s' "$out" | tail -1)
body=$(printf '%s' "$out" | sed '$d' | tr -d '\r\n')
printf 'CH|%s|%s|%s|%s\n' "$U" "$P" "$meta" "$(printf '%s' "$body" | cut -c1-110)"
