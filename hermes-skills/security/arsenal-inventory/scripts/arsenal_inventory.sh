#!/usr/bin/env bash
# arsenal_inventory.sh — 军火库清点：用磁盘事实回答「手里有多少漏洞」。
#
# 用法:  bash arsenal_inventory.sh [--json [out.json]]
#
# 为什么要有它：技能正文的条数是历史批次快照会过期，凭记忆报数会被当场拆。
# 口径分四层，缺一层就是误导：库存(情报库条目) / 可打(带公网PoC) / 现成武器(本地脚本) / 已验真(靶场打通)。
set -uo pipefail

OUT_JSON=""
if [ "${1:-}" = "--json" ]; then
  OUT_JSON="${2:-/root/.hermes/cache/scratch/arsenal_inventory.json}"
fi
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

SK=/root/.hermes/skills/security
OD=/root/security-suite/domains/0day-exploits
CR=/root/cve_recon
NT=/root/nuclei-templates

sec(){ printf '\n########## %s ##########\n' "$1"; }
kv(){ printf '%-32s %s\n' "$1" "$2"; printf '%s\t%s\n' "$1" "$2" >> "$TMP"; }
files(){ find "$1" -type f 2>/dev/null | wc -l | tr -d ' '; }
lines(){ if [ -f "$1" ]; then wc -l < "$1" | tr -d ' '; else echo 0; fi; }
# 唯一 CVE 号：-I 跳二进制(.pyc 会打 binary file matches 污染计数)，-o 逐个匹配，sort -u 去重
ucve(){ grep -rhoIE 'CVE-[0-9]{4}-[0-9]{4,7}' "$1" 2>/dev/null | sort -u | wc -l | tr -d ' '; }

printf '军火库清点  %s\n' "$(date '+%F %T %Z')"

# ---------------- 1) 技能库 ----------------
sec "1) 技能库  ($SK)"
kv "security 技能数"       "$(ls -d "$SK"/*/ 2>/dev/null | wc -l | tr -d ' ')"
kv "技能文件数"           "$(files "$SK")"
kv "技能内 md 文件"       "$(find "$SK" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
kv "技能内自建脚本"       "$(find "$SK" -type f \( -name '*.py' -o -name '*.sh' -o -name '*.go' \) 2>/dev/null | wc -l | tr -d ' ')"
kv "技能内唯一 CVE 号"     "$(ucve "$SK")"

# ---------------- 2) 产品 0day RCE 库 ----------------
sec "2) 产品 0day RCE 库  ($OD)"
if [ -d "$OD" ]; then
  kv "产品目录数"         "$(find "$OD" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
  kv "漏洞条目 analysis.md" "$(find "$OD" -name analysis.md 2>/dev/null | wc -l | tr -d ' ')"
  kv "summary.md"         "$(find "$OD" -name summary.md 2>/dev/null | wc -l | tr -d ' ')"
  kv "exploit 脚本数"     "$(find "$OD" -path '*exploit*' -type f \( -name '*.py' -o -name '*.sh' -o -name '*.go' -o -name '*.rb' -o -name '*.pl' -o -name '*.c' \) 2>/dev/null | wc -l | tr -d ' ')"
  kv "exploitarium 文件"   "$(find "$OD" -path '*/exploitarium/*' -type f 2>/dev/null | wc -l | tr -d ' ')"
  kv "poc-catalog 文件数"   "$(files "$OD/poc-catalog")"
  for d in "$OD"/poc-catalog/*/; do
    [ -d "$d" ] && kv "  - $(basename "$d")" "$(files "$d")"
  done
  kv "poc 摘要卡 jsonl"     "$(lines "$OD/poc-catalog/from-poc-db/pocs-summary.jsonl")"
  kv "本库唯一 CVE 号"      "$(ucve "$OD")"
else
  printf '  (目录不存在: %s)\n' "$OD"
fi

# ---------------- 3) 情报 / PoC 库 ----------------
sec "3) 情报 / PoC 库  ($CR)"
if [ -d "$CR" ]; then
  python3 - "$CR" <<'PY'
import csv, json, os, sys
cr = sys.argv[1]
def L(*p): return os.path.join(cr, *p)
def jl(p):
    try:
        with open(L(p), errors='ignore') as f: return json.load(f)
    except Exception: return None
n = c9 = c7 = 0
if os.path.isfile(L('nvd2026_all.jsonl')):
    with open(L('nvd2026_all.jsonl'), errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            n += 1
            try: v = json.loads(line).get('cvss')
            except Exception: continue
            if isinstance(v, (int, float)):
                if v >= 9.0: c9 += 1
                if v >= 7.0: c7 += 1
print(f"{'NVD 2026 全量归档':<32} {n}")
print(f"{'  其中 CVSS>=9.0':<32} {c9}")
print(f"{'  其中 CVSS>=7.0':<32} {c7}")
K = jl('kev.json')
kev = len(K['vulnerabilities']) if isinstance(K, dict) and 'vulnerabilities' in K else (len(K) if K else 0)
print(f"{'CISA KEV 全量':<32} {kev}")
row = 0
if os.path.isfile(L('edb.csv')):
    with open(L('edb.csv'), errors='ignore', newline='') as f:
        for _ in csv.reader(f): row += 1
print(f"{'Exploit-DB 全库 EXP':<32} {max(row - 1, 0)}")
for p in ('trickest_index.json', 'poc_available.json', 'cve_verified.json', 'product_index.json'):
    d = jl(p)
    print(f"{p.replace('.json',''):<32} {len(d) if d is not None else 0}")
pu = jl('poc_unified.json') or {}
poc = sum(1 for v in pu.values() if v.get('poc_all'))
links = sum(len(v.get('poc_all') or []) for v in pu.values())
kev2 = sum(1 for v in pu.values() if v.get('kev'))
hi = sum(1 for v in pu.values() if (v.get('cvss') or 0) >= 9.0)
hi_poc = sum(1 for v in pu.values() if (v.get('cvss') or 0) >= 9.0 and v.get('poc_all'))
ver = sum(1 for v in pu.values() if v.get('versions'))
print(f"{'统一PoC索引 条目':<32} {len(pu)}")
print(f"{'  带公开 PoC(可打层)':<32} {poc}")
print(f"{'  PoC 链接数':<32} {links}")
print(f"{'  KEV 标记':<32} {kev2}")
print(f"{'  CVSS>=9.0':<32} {hi}")
print(f"{'  >=9.0 且带 PoC':<32} {hi_poc}")
print(f"{'  带精确影响版本':<32} {ver}")
tm = jl('technique_map.json') or {}
c = tm.get('cves')
print(f"{'technique_map.cves':<32} {len(c) if hasattr(c, '__len__') else 0}")
PY
else
  printf '  (目录不存在: %s)\n' "$CR"
fi

# ---------------- 4) 火力工具 / 靶场 ----------------
sec "4) 火力工具 / 靶场"
kv "nuclei 模板数"         "$(find "$NT" -name '*.yaml' 2>/dev/null | wc -l | tr -d ' ')"
kv "已打通专用脚本(cve-*)"  "$(ls "$SK"/0day-exploit-library/scripts/cve-*.py 2>/dev/null | wc -l | tr -d ' ')"
if command -v docker >/dev/null 2>&1; then
  kv "运行中的靶场容器"     "$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l | tr -d ' ')"
  docker ps --format '  - {{.Names}}  {{.Image}}  {{.Ports}}' 2>/dev/null
fi

# ---------------- 分层总账 ----------------
sec "总账（分层，别混报）"
printf '库存     = 情报库条目数（NVD/KEV/EDB/trickest 等）\n可打     = 带公网 PoC（poc_unified 的 poc_all 非空）\n现成武器 = 本地 exploit 脚本 + 技能自建脚本\n已验真   = 靶场亲手打通（见 0day-exploit-library/references/lab-validated-exploits.md）\n'

if [ -n "$OUT_JSON" ]; then
  python3 - "$TMP" "$OUT_JSON" <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
d = {}
for line in open(src, encoding='utf-8'):
    if '\t' not in line: continue
    k, v = line.rstrip('\n').split('\t', 1)
    v = v.strip()
    d[k.strip()] = int(v) if v.lstrip('-').isdigit() else v
json.dump(d, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\n[json] -> {dst}")
PY
fi
