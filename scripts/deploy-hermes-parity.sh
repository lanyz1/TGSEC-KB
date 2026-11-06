#!/bin/bash
# 把本机 Hermes 的 SOUL.md + 技能库 + 启用状态 + arsenal 检索栈，一键推到任意远端 Hermes。
#
# 用法:
#   export FLEET_PASS='...'
#   bash scripts/deploy-hermes-parity.sh 1.2.3.4 5.6.7.8
#   bash scripts/deploy-hermes-parity.sh --hosts /root/hosts.txt
#   bash scripts/deploy-hermes-parity.sh --dry-run 1.2.3.4
#   bash scripts/deploy-hermes-parity.sh --pull 1.2.3.4          # 先收回远端独有产出，再推
#   bash scripts/deploy-hermes-parity.sh --key ~/.ssh/id_ed25519 1.2.3.4
#
# 认证: 默认用 $FLEET_PASS（sshpass 密码），--key 则用密钥。
# 源:   $HERMES_SRC（默认 /root/.hermes）
#
# 生效: SOUL/config 在建会话时读盘，机器人开新会话即生效；
#       已在跑的长会话要立刻换血，去远端自己重启 gateway。
set -uo pipefail

SRC_HOME="${HERMES_SRC:-/root/.hermes}"
SRC_SKILLS="$SRC_HOME/skills"
SRC_SOUL="$SRC_HOME/SOUL.md"
SRC_ARSENAL="$SRC_HOME/arsenal"
SRC_CFG="$SRC_HOME/config.yaml"
HELPER="$(cd "$(dirname "$0")" && pwd)/hermes_config_sync.py"
PORT=22; USER_=root; DRY=0; KEY=""; PULL=0; HOSTS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --pull) PULL=1; shift ;;
    --key) KEY="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --user) USER_="$2"; shift 2 ;;
    --hosts) mapfile -t HOSTS < "$2"; shift 2 ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) HOSTS+=("$1"); shift ;;
  esac
done
[ ${#HOSTS[@]} -eq 0 ] && { echo "没有目标主机。用法见 --help"; exit 2; }

if [ -n "$KEY" ]; then
  SSH_E="ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p $PORT"
  AUTH="key:$KEY"
else
  : "${FLEET_PASS:?需要 export FLEET_PASS 或传 --key}"
  SSH_E="sshpass -p $FLEET_PASS ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o ConnectTimeout=10 -p $PORT"
  AUTH="password"
fi
RS_FLAGS=(-az --exclude='.curator_backups/' --exclude='.curator_ledger.jsonl'
          --exclude='__pycache__/' --exclude='*.pyc' --exclude='*.pkl')
[ "$DRY" = 1 ] && RS_FLAGS+=(-n -c --itemize-changes)

rs() { if [ -n "$KEY" ]; then rsync -e "$SSH_E" "${RS_FLAGS[@]}" "$@"; else sshpass -p "$FLEET_PASS" rsync -e "$SSH_E" "${RS_FLAGS[@]}" "$@"; fi; }
sh_() { $SSH_E "$USER_@$1" "${@:2}"; }
scp_() { if [ -n "$KEY" ]; then scp -i "$KEY" -P "$PORT" -o StrictHostKeyChecking=no "$@"; else sshpass -p "$FLEET_PASS" scp -P "$PORT" -o StrictHostKeyChecking=no -o PubkeyAuthentication=no "$@"; fi; }
sha() { md5sum "$1" | cut -d' ' -f1; }

LOCAL_SOUL=$(sha "$SRC_SOUL")
LOCAL_CARDS=$(find "$SRC_SKILLS" -name SKILL.md | wc -l)
LOCAL_DIS=$(python3 -c "import yaml;print(len((yaml.safe_load(open('$SRC_CFG')).get('skills') or {}).get('disabled') or []))")
echo "源: SOUL=$LOCAL_SOUL 卡=$LOCAL_CARDS disabled=$LOCAL_DIS 认证=$AUTH"

FAIL=0
for H in "${HOSTS[@]}"; do
  echo "──────────────── $H ────────────────"
  if ! sh_ "$H" 'test -d ~/.hermes' 2>/dev/null; then
    echo "  ✗ 连不上或缺 ~/.hermes，跳过"; FAIL=$((FAIL+1)); continue
  fi

  if [ "$DRY" = 0 ]; then
    sh_ "$H" 'TS=$(date +%Y%m%d%H%M); cp -a ~/.hermes/SOUL.md ~/.hermes/SOUL.md.bak-$TS 2>/dev/null; cp -a ~/.hermes/config.yaml ~/.hermes/config.yaml.bak-$TS 2>/dev/null; echo "  · 备份 $TS"'
  fi

  if [ "$PULL" = 1 ]; then
    echo "  · 收回远端独有文件"
    sh_ "$H" 'cd ~/.hermes/skills && find . -type f ! -path "*/__pycache__/*" ! -name "*.pyc" ! -name "*.pkl" ! -path "*/.curator_backups/*" ! -name ".curator_ledger.jsonl" | sed "s|^\./||" | sort' > /tmp/rem_files.txt
    ( cd "$SRC_SKILLS" && find . -type f ! -path "*/__pycache__/*" ! -name "*.pyc" ! -name "*.pkl" ! -path "*/.curator_backups/*" ! -name ".curator_ledger.jsonl" | sed 's|^\./||' | sort ) > /tmp/loc_files.txt
    comm -13 /tmp/loc_files.txt /tmp/rem_files.txt > /tmp/only_remote.txt
    N=$(wc -l < /tmp/only_remote.txt)
    echo "    远端独有 $N 个文件"
    if [ "$N" -gt 0 ]; then head -5 /tmp/only_remote.txt | sed 's/^/      + /'
      rs --files-from=/tmp/only_remote.txt "$USER_@$H:/root/.hermes/skills/" "$SRC_SKILLS/"
    fi
  fi

  echo "  · 技能库 ${LOCAL_CARDS} 卡"
  rs "$SRC_SKILLS/" "$USER_@$H:/root/.hermes/skills/"
  echo "  · SOUL.md"
  rs "$SRC_SOUL" "$USER_@$H:/root/.hermes/SOUL.md"
  echo "  · arsenal 栈"
  rs --exclude='arsenal.db' --exclude='vuln.db' --exclude='repo.db' "$SRC_ARSENAL/" "$USER_@$H:/root/.hermes/arsenal/"

  if [ "$DRY" = 0 ]; then
    echo "  · 启用状态对齐"
    scp_ "$HELPER" "$SRC_CFG" "$USER_@$H:/tmp/" >/dev/null 2>&1
    sh_ "$H" 'python3 /tmp/hermes_config_sync.py /root/.hermes/config.yaml /tmp/config.yaml'
    echo "  · 重建索引"
    sh_ "$H" 'cd ~/.hermes/arsenal && python3 arsenal_build.py 2>&1 | tail -1'
  fi

  echo "  · 验收"
  sh_ "$H" 'echo -n "    SOUL md5 : "; md5sum ~/.hermes/SOUL.md | cut -d" " -f1
            echo -n "    卡数     : "; find ~/.hermes/skills -name SKILL.md | wc -l
            echo -n "    disabled : "; python3 -c "import yaml;print(len((yaml.safe_load(open(\"/root/.hermes/config.yaml\")).get(\"skills\") or {}).get(\"disabled\") or []))"'
  REMOTE_SOUL=$(sh_ "$H" 'md5sum ~/.hermes/SOUL.md | cut -d" " -f1')
  [ "$REMOTE_SOUL" = "$LOCAL_SOUL" ] && echo "  ✓ SOUL 一致" || { echo "  ✗ SOUL 不一致"; FAIL=$((FAIL+1)); }
done

echo "════ 完成: $(( ${#HOSTS[@]} - FAIL ))/${#HOSTS[@]} 台对齐 ════"
[ "$FAIL" = 0 ] || exit 1
