#!/usr/bin/env bash
# 把案卷机的全量技能库导出成可搬运的 tar.gz + 逐卡 md5 清单。
# 目的：新机/克隆机要 full 基线（2146 卡）时，别再指望从 git 仓库拿到卡——
#       全量卡只在案卷机上，走这条搬运路径。
#
# 用法：
#   bash scripts/export-arsenal-library.sh                 # 导出到 ~/arsenal-export/
#   bash scripts/export-arsenal-library.sh /data/out       # 指定输出目录
#   bash scripts/export-arsenal-library.sh --diff a.tsv    # 拿目标机清单比差异（md5 判定，不看体积）
#
# 目标机导入（overlay，不删私有卡）：
#   rsync -avP hermes-skills-*.tar.gz root@HOST:/tmp/
#   ssh root@HOST 'cd ~/.hermes && tar xzf /tmp/hermes-skills-*.tar.gz --strip-components=0'
#   ssh root@HOST 'python3 ~/.hermes/arsenal/arsenal_build.py && python3 ~/.hermes/arsenal/post_rebuild_gate.py'
set -euo pipefail

SK="${HERMES_SKILLS:-$HOME/.hermes/skills}"
STAMP="$(date +%Y%m%d-%H%M)"

if [ "${1:-}" = "--diff" ]; then
  TARGET="${2:?用法: export-arsenal-library.sh --diff <target.manifest.tsv>}"
  python3 - "$SK" "$TARGET" <<'PY'
import glob, hashlib, os, re, sys
sk, tgt = sys.argv[1], sys.argv[2]

def card_name(p):
    try:
        h = open(p, encoding="utf-8", errors="replace").read(1200)
    except OSError:
        return os.path.basename(os.path.dirname(p))
    m = re.search(r"^name:\s*['\"]?([\w.\-]+)", h, re.M)
    return m.group(1) if m else os.path.basename(os.path.dirname(p))

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

local = {card_name(p): md5(p) for p in glob.glob(os.path.join(sk, "**", "SKILL.md"), recursive=True)}
remote = {}
for line in open(tgt, encoding="utf-8"):
    parts = line.rstrip("\n").split("\t")
    if len(parts) >= 2 and parts[0] != "name":
        remote[parts[0]] = parts[1]
missing = sorted(set(local) - set(remote))
extra = sorted(set(remote) - set(local))
changed = sorted(n for n in set(local) & set(remote) if local[n] != remote[n])
print("本机 %d 卡 / 目标 %d 卡" % (len(local), len(remote)))
print("目标缺 %d 张%s" % (len(missing), ("：" + ", ".join(missing[:10])) if missing else ""))
print("目标多 %d 张%s" % (len(extra), ("：" + ", ".join(extra[:10])) if extra else ""))
print("同名不同内容 %d 张%s" % (len(changed), ("：" + ", ".join(changed[:10])) if changed else ""))
PY
  exit 0
fi

OUT="${1:-$HOME/arsenal-export}"
mkdir -p "$OUT"
TAR="$OUT/hermes-skills-$STAMP.tar.gz"
MAN="$OUT/hermes-skills-$STAMP.manifest.tsv"

[ -d "$SK" ] || { echo "FATAL: 技能树不存在：$SK"; exit 1; }
N=$(find "$SK" -name SKILL.md | wc -l | tr -d ' ')
echo "[*] 导出 $SK（$N 张 SKILL.md）→ $TAR"

# 逐卡 md5 清单：增量/差异只认内容指纹，不认体积（体积会把「改了描述」判成没变）
python3 - "$SK" "$MAN" <<'PY'
import glob, hashlib, os, re, sys
sk, man = sys.argv[1], sys.argv[2]

def card_name(p):
    try:
        h = open(p, encoding="utf-8", errors="replace").read(1200)
    except OSError:
        return os.path.basename(os.path.dirname(p))
    m = re.search(r"^name:\s*['\"]?([\w.\-]+)", h, re.M)
    return m.group(1) if m else os.path.basename(os.path.dirname(p))

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

rows = []
for p in glob.glob(os.path.join(sk, "**", "SKILL.md"), recursive=True):
    rows.append((card_name(p), md5(p), os.path.relpath(os.path.dirname(p), os.path.dirname(sk))))
rows.sort()
with open(man, "w", encoding="utf-8") as f:
    f.write("name\tmd5\trelpath\n")
    for r in rows:
        f.write("%s\t%s\t%s\n" % r)
print("  manifest: %s（%d 行）" % (man, len(rows)))
PY

# 归档/启用分层随库走：把当前 config 的 skills.disabled 写进 skills/.disabled.json，
# 目标机 arsenal_build.py 会合并它，否则全量 2146 张全算 enabled，core 基线 94/96 → 88/96。
python3 - "$SK" <<'PY'
import json, sys, os
sk = sys.argv[1]
sys.path.insert(0, "/usr/local/lib/hermes-agent")
try:
    from hermes_cli.config import load_config
    d = (load_config().get("skills", {}) or {}).get("disabled") or []
except Exception:
    d = []
if not d:
    cfg = os.path.expanduser("~/.hermes/config.yaml")
    try:
        import yaml
        d = ((yaml.safe_load(open(cfg, encoding="utf-8")) or {}).get("skills", {}) or {}).get("disabled") or []
    except Exception:
        d = []
json.dump(sorted(set(d)), open(os.path.join(sk, ".disabled.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print("  disabled seed: %d 条 → skills/.disabled.json" % len(set(d)))
PY

tar czf "$TAR" -C "$(dirname "$SK")" \
  --exclude='.curator_backups' \
  --exclude='.curator_ledger.jsonl' \
  --exclude='*.pkl' \
  --exclude='__pycache__' \
  "$(basename "$SK")"
# 只数真正的卡文件（basename 恰为 SKILL.md）；references/upstream-*-SKILL.md 这类参考资料不算
IN_TAR=$(tar tzf "$TAR" | awk -F/ '$NF=="SKILL.md"' | wc -l | tr -d ' ')
echo "[✓] $TAR（$(du -h "$TAR" | cut -f1)），包内 $IN_TAR 张 SKILL.md / 磁盘 $N 张"
[ "$IN_TAR" = "$N" ] || { echo "[!] 包内数量与磁盘不一致，别拿去覆盖目标机"; exit 1; }
md5sum "$TAR" "$MAN" > "$OUT/$(basename "$TAR" .tar.gz).sha256"
echo "[✓] 校验: $OUT/$(basename "$TAR" .tar.gz).sha256"
echo
echo "目标机导入："
echo "  rsync -avP $TAR root@HOST:/tmp/"
echo "  ssh root@HOST 'cd ~/.hermes && tar xzf /tmp/$(basename "$TAR") --strip-components=0'"
echo "  ssh root@HOST 'ARSENAL_DIR=~/.hermes/arsenal python3 ~/.hermes/arsenal/arsenal_build.py'"
echo "  ssh root@HOST 'python3 ~/.hermes/arsenal/post_rebuild_gate.py'   # 应输出 tier=full"
echo "差异核对（不看体积，只比 md5）："
echo "  bash scripts/export-arsenal-library.sh --diff $MAN"
