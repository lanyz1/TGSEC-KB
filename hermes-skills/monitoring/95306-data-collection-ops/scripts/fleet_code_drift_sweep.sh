#!/bin/bash
# 95306 机队体检 / 代码漂移核对 —— 在主控上执行,纯只读;名单现读 /opt/v6/jumpers.json(pwd 一律不打印)
#
# 用法(在主控上):bash fleet_code_drift_sweep.sh <targets16> <api16> <tickets16> <http16>
#   基线取法(本机源码树):sha256sum D:/95306c/collector/{targets,api,tickets,http}.py | cut -c1-16
# 判定: 每台 collector/ 四文件哈希与基线逐字相同 = 零漂移(比内容哈希,不看 rel 名/版本戳)
# 边界: 只验「服务在跑 + 代码同源」;数据面新鲜度另看 /data_raw 与 cstats.json(见 SKILL.md 机队体检段)
set -u
REG=/opt/v6/jumpers.json
KEY=/root/.ssh/id_ed25519
if [ $# -lt 4 ]; then echo "用法: $0 <targets16> <api16> <tickets16> <http16>"; exit 2; fi
BT=$1; BA=$2; BK=$3; BH=$4

echo "=== 编队名单($REG,只取 shard/ip/port/name)==="
python3 -X utf8 - "$REG" <<'PY' > /tmp/_fleet_list.tsv
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
cols = d.get("collectors") if isinstance(d, dict) else d
n = 0
for c in (cols or []):
    if not isinstance(c, dict):
        continue
    print("%s\t%s\t%s\t%s" % (c.get("shard", n), c.get("ip", ""), c.get("port", 22), c.get("name", "")))
    n += 1
PY
echo "台数: $(wc -l < /tmp/_fleet_list.tsv)"
cut -f2,3,4 /tmp/_fleet_list.tsv

echo
echo "=== 逐台核对(svc / 发布树 / collector 四文件裁决)==="
while IFS=$'\t' read -r SH IP PORT NAME; do
  [ -n "${IP:-}" ] || continue
  # ★循环里 ssh 必须 -n:否则 ssh 会吃掉 while read 的标准输入(= 名单文件),循环只处理第一台
  R=$(ssh -n -p "$PORT" -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=12 \
      "root@$IP" 'S=$(systemctl is-active v6collector 2>/dev/null || echo none); T=$(readlink -f /opt/v6/current 2>/dev/null); echo "svc=$S tree=$(basename ${T:-none}) tgt=$(sha256sum $T/collector/targets.py 2>/dev/null | cut -c1-16) api=$(sha256sum $T/collector/api.py 2>/dev/null | cut -c1-16) tkt=$(sha256sum $T/collector/tickets.py 2>/dev/null | cut -c1-16) http=$(sha256sum $T/collector/http.py 2>/dev/null | cut -c1-16)"' 2>&1 | tail -1)
  TG=$(printf '%s' "$R" | sed -n 's/.*tgt=\([0-9a-f]*\).*/\1/p')
  if [ -z "$TG" ]; then
    V="不可达/无文件"
  elif [ "$TG" = "$BT" ] && printf '%s' "$R" | grep -q "api=$BA" && printf '%s' "$R" | grep -q "tkt=$BK" && printf '%s' "$R" | grep -q "http=$BH"; then
    V="同源OK"
  else
    V="★漂移(与本机源码树不同源)"
  fi
  printf '%s:%-5s sh%-3s %-8s | %s | %s\n' "$IP" "$PORT" "$SH" "$NAME" "$R" "$V"
done < /tmp/_fleet_list.tsv
echo "(只读:未动任何进程/文件;判定口径 = 四文件内容哈希相同)"
