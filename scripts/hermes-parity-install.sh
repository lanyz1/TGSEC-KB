#!/bin/bash
# 把 TGSEC 的 Hermes 配置（SOUL + 全量技能 + 启用状态 + 检索栈）装到本机
#
# 一行用法（新机器）:
#   curl -fsSL https://raw.githubusercontent.com/lanyz1/TGSEC-Qtzuu/master/scripts/hermes-parity-install.sh | bash
#
# 可选参数:
#   --keep-soul     不覆盖已有 SOUL.md
#   --no-index      不重建 arsenal 检索库（省 ~80s）
#   --dir PATH      仓库落地目录（默认 ~/TGSEC-Qtzuu）
#   --repo URL      换成你自己的镜像
#
# 幂等: 重复跑就是增量更新。
set -euo pipefail

REPO_URL="https://github.com/lanyz1/TGSEC-Qtzuu.git"
DIR="$HOME/TGSEC-Qtzuu"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
KEEP_SOUL=0; BUILD_INDEX=1

while [ $# -gt 0 ]; do
  case "$1" in
    --keep-soul) KEEP_SOUL=1; shift ;;
    --no-index) BUILD_INDEX=0; shift ;;
    --dir) DIR="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "未知参数: $1"; exit 2 ;;
  esac
done

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[x]\033[0m %s\n' "$*"; exit 1; }

command -v git >/dev/null || die "缺 git：apt install -y git"
command -v rsync >/dev/null || die "缺 rsync：apt install -y rsync"
command -v python3 >/dev/null || die "缺 python3"

say "仓库 → $DIR"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only -q || say "pull 失败，用现有副本继续"
else
  git clone --depth 1 -q "$REPO_URL" "$DIR" || die "clone 失败"
fi
[ -d "$DIR/hermes-skills" ] || die "仓库里没有 hermes-skills/"

say "技能库 → $HERMES_HOME/skills"
mkdir -p "$HERMES_HOME/skills"
rsync -a --exclude='.curator_backups/' --exclude='.curator_ledger.jsonl' \
      --exclude='__pycache__/' --exclude='*.pyc' --exclude='*.pkl' \
      "$DIR/hermes-skills/" "$HERMES_HOME/skills/"

say "SOUL.md"
if [ -f "$HERMES_HOME/SOUL.md" ] && [ "$KEEP_SOUL" = 1 ]; then
  echo "    已存在，保留（--keep-soul）"
elif [ -f "$DIR/ai-config/hermes/SOUL.md" ]; then
  [ -f "$HERMES_HOME/SOUL.md" ] && cp -a "$HERMES_HOME/SOUL.md" "$HERMES_HOME/SOUL.md.bak-$(date +%Y%m%d%H%M%S)"
  cp -a "$DIR/ai-config/hermes/SOUL.md" "$HERMES_HOME/SOUL.md"
  echo "    已写入"
fi

say "检索栈 → $HERMES_HOME/arsenal"
mkdir -p "$HERMES_HOME/arsenal"
rsync -a --exclude='arsenal.db' --exclude='vuln.db' --exclude='repo.db' --exclude='__pycache__/' \
      "$DIR/arsenal/" "$HERMES_HOME/arsenal/"

if [ -f "$HERMES_HOME/config.yaml" ]; then
  say "启用状态对齐（只改 skills.disabled，其余不动）"
  python3 - "$HERMES_HOME/config.yaml" "$DIR/ai-config/hermes/skills-disabled.yaml" <<'PY' || echo "    跳过（源文件缺失）"
import re, sys, shutil, datetime
dst, src = sys.argv[1], sys.argv[2]
def sec(t, k="skills"):
    m = re.search(rf"^{k}:\s*$", t, re.M)
    if not m: return None
    n = re.search(r"^[A-Za-z_][\w-]*:\s", t[m.end():], re.M)
    return m.start(), (m.end() + n.start() if n else len(t))
s = open(src, encoding="utf-8").read()
d = open(dst, encoding="utf-8").read()
sb, db = sec(s), sec(d)
if not sb or not db:
    print("    目标无 skills 段，追加"); open(dst, "a", encoding="utf-8").write("\n" + s if not s.startswith("skills:") else "\n" + s)
else:
    shutil.copy2(dst, dst + ".bak-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    open(dst, "w", encoding="utf-8").write(d[:db[0]] + (s if s.endswith("\n") else s + "\n") + d[db[1]:])
print("    完成")
PY
else
  say "没有 config.yaml（Hermes 可能未装），跳过启用状态"
fi

if [ "$BUILD_INDEX" = 1 ] && [ -f "$HERMES_HOME/arsenal/arsenal_build.py" ]; then
  say "重建检索库（~80s）"
  ( cd "$HERMES_HOME/arsenal" && ARSENAL_SKILLS="$HERMES_HOME/skills" ARSENAL_DB="$HERMES_HOME/arsenal/arsenal.db" python3 arsenal_build.py 2>&1 | tail -1 )
fi

say "验收"
echo -n "    卡数     : "; find "$HERMES_HOME/skills" -name SKILL.md | wc -l
[ -f "$HERMES_HOME/SOUL.md" ] && { echo -n "    SOUL md5 : "; md5sum "$HERMES_HOME/SOUL.md" | cut -d' ' -f1; }
[ -f "$HERMES_HOME/arsenal/arsenal.db" ] && echo "    检索库   : $(du -h "$HERMES_HOME/arsenal/arsenal.db" | cut -f1)"
echo "    试一下   : python3 $HERMES_HOME/arsenal/skill_find.py \"JWT 伪造\" --phase auth"
say "完成。Hermes 开新会话即生效。"
