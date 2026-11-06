#!/usr/bin/env bash
# 造一个假 HOME 的最小技能树，用来测「首次安装/升级」分支（删卡 / 搬 refs / 首建库 / 写 disabled），
# 不碰真库。真机已升级过时，直接跑升级脚本只会走「无待删卡」那条路，其余分支全是未验证代码。
#
# 用法：
#   bash scripts/fake_home_fixture.sh [/tmp/fh]
#   HOME=/tmp/fh \
#     HERMES_SKILLS=/tmp/fh/.hermes/skills \
#     ARSENAL_DIR=/tmp/fh/.hermes/arsenal \
#     ARCHIVE_DIR=/tmp/fh/archive \
#     bash scripts/apply-arsenal-20261022.sh --no-purge
#
# 期望：备份 → 删卡 → 搬 refs → 重建 全部执行；门禁 FAIL（卡太少）但不许出 traceback。
set -euo pipefail

FH="${1:-/tmp/fh}"
case "$FH" in
  ""|"/"|"/tmp"|"/root"|"$HOME"|"$HOME/") echo "refuse: $FH 太危险，传一个专用子目录（默认 /tmp/fh）" >&2; exit 2 ;;
esac
case "$FH" in
  /tmp/*) ;;
  *) echo "warn: $FH 不在 /tmp 下，确认后重跑" >&2 ;;
esac
rm -rf "$FH"
mkdir -p "$FH/.hermes/skills/security/keep-card" \
         "$FH/.hermes/skills/security/redteam-ssrf-detail-pack" \
         "$FH/.hermes/skills/security/laravel-app-pentest" \
         "$FH/.hermes/skills/security/72stack-sec/references/h1-reports" \
         "$FH/.hermes/arsenal" "$FH/archive"

mk() { # $1=dir $2=name $3=description
  printf -- '---\nname: %s\ndescription: %s\ncategory: security\ntags: [fixture]\n---\n\n# %s\n\nfixture body for %s\n' \
    "$2" "$3" "$2" "$2" > "$1/SKILL.md"
}
mk "$FH/.hermes/skills/security/keep-card"               keep-card               "应保留的卡 fixture keep"
mk "$FH/.hermes/skills/security/redteam-ssrf-detail-pack" redteam-ssrf-detail-pack "应被删的模板卡 fixture template pack"
mk "$FH/.hermes/skills/security/laravel-app-pentest"      laravel-app-pentest      "应被删的重复卡 fixture dup"
mk "$FH/.hermes/skills/security/72stack-sec"              72stack-sec              "带胖 refs 的卡 fixture refs"
echo "h1 report sample" > "$FH/.hermes/skills/security/72stack-sec/references/h1-reports/a.md"

printf 'skills:\n  disabled:\n    - some-old-card\n' > "$FH/.hermes/config.yaml"

echo "fixture ready: $FH"
echo "next: HOME=$FH HERMES_SKILLS=$FH/.hermes/skills ARSENAL_DIR=$FH/.hermes/arsenal ARCHIVE_DIR=$FH/archive bash scripts/apply-<date>.sh --no-purge"
