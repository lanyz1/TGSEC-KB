#!/usr/bin/env bash
# Usage: check_exit_clean.sh <iface> <probe_url> [ban_pattern]
# Env:   METHOD (default GET) | BODY (json, default empty) | TOKEN (bearer) |
#        ORIGIN | REFERER | UA (override)
# Prints: exit IP, body length, verdict CLEAN | BANNED | SUSPECT_EMPTY | AUTH_WALL.
#
# ALWAYS sends the full browser header block. A bare `curl/x.y` UA is itself a
# common WAF trigger: it can return the ban code on a brand-new exit's FIRST
# request, which then gets mis-filed as "this IP was already blacklisted".
# Probe the path you actually intend to attack, not the static root: WAF rules
# are grouped per path, so a root that answers 200 / 135B proves nothing about
# the business prefix. Empty-body POST to that prefix is the best single request
# - it merges "is the exit clean" and "is the route live" into one probe.
set -u
IFACE="${1:-tun0}"
URL="${2:?usage: check_exit_clean.sh <iface> <probe_url> [ban_pattern]}"
PAT="${3:-40000}"
METHOD="${METHOD:-GET}"
BODY="${BODY:-}"
UA="${UA:-Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36}"

HDRS=(-H "User-Agent: $UA"
      -H 'Accept: application/json, text/plain, */*'
      -H 'Accept-Language: zh-CN,zh;q=0.9'
      -H 'Sec-Fetch-Site: same-site'
      -H 'Sec-Fetch-Mode: cors'
      -H 'Sec-Fetch-Dest: empty'
      -H 'X-Requested-With: XMLHttpRequest')
[ -n "${ORIGIN:-}" ]  && HDRS+=(-H "Origin: $ORIGIN")
[ -n "${REFERER:-}" ] && HDRS+=(-H "Referer: $REFERER")
[ -n "${TOKEN:-}" ]   && HDRS+=(-H "Authorization: Bearer $TOKEN")
[ -n "$BODY" ]        && HDRS+=(-H 'Content-Type: application/json' -d "$BODY")

exit_ip=$(curl -s --interface "$IFACE" -m 8 https://api.ipify.org 2>/dev/null || echo unknown)
body=$(curl -s --interface "$IFACE" -m 15 -k -X "$METHOD" "${HDRS[@]}" "$URL" 2>/dev/null || true)
len=${#body}

if printf '%s' "$body" | grep -qF -- "$PAT"; then
  verdict=BANNED
elif [ "$len" -lt 40 ]; then
  verdict=SUSPECT_EMPTY
elif printf '%s' "$body" | grep -qE 'Full authentication|未授权|请登录|登录已失效|Unauthorized'; then
  verdict=AUTH_WALL   # clean exit, route reached the gateway; auth is the answer
else
  verdict=CLEAN
fi

printf 'exit=%s method=%s len=%s verdict=%s url=%s\n' "$exit_ip" "$METHOD" "$len" "$verdict" "$URL"
printf 'body: %s\n' "$(printf '%s' "$body" | head -c 200)"
