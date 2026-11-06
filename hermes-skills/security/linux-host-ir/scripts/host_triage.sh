#!/bin/bash
# 只读主机入侵快检。不做任何修改，输出可按段截取。
# 用法: bash host_triage.sh [可疑pid...]
set -u

sec() { echo; echo "===== $* ====="; }

sec "1. 进程总览（按启动时间倒序，前 40）"
ps -eo pid,ppid,user,etime,pcpu,pmem,stat,args --sort=start_time | tail -40

sec "2. memfd / 已删除 可执行进程（无落地载荷）"
found=0
for p in /proc/[0-9]*; do
  exe=$(readlink "$p/exe" 2>/dev/null) || continue
  case "$exe" in
    *memfd*|*"(deleted)"*)
      found=1
      echo "SUSPECT pid=${p#/proc/} exe=$exe cmd=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null | cut -c1-110)"
      ;;
  esac
done
[ $found -eq 0 ] && echo "none"

sec "3. 指定的可疑 pid 详情"
for pid in "$@"; do
  echo "--- pid $pid ---"
  ps -o pid,ppid,lstart,stat,args -p "$pid" 2>/dev/null
  echo "exe:   $(readlink /proc/$pid/exe 2>/dev/null)"
  echo "cwd:   $(readlink /proc/$pid/cwd 2>/dev/null)"
  tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -aE 'SSH_CONNECTION|SSH_CLIENT|_ID=|PWD=' | sed 's/^/env:   /'
  echo "fd(memfd): $(ls -l /proc/$pid/fd 2>/dev/null | grep -c memfd)"
  grep -aE 'Threads|CapEff|Seccomp:' /proc/$pid/status 2>/dev/null | sed 's/^/status: /'
  echo "children/zombies:"
  ps -o pid,stat,args --ppid "$pid" 2>/dev/null | tail -n +2 | sed 's/^/  /'
done

sec "4. 监听与已建立连接"
ss -tlnp | tail -n +2
ss -tnp state established | tail -n +2 | awk '{print $4, $5, $6, $7}' | head -20

sec "5. 近期改动的 systemd 单元"
find /etc/systemd/system -maxdepth 3 \( -name '*.service' -o -name '*.timer' -o -type l \) -newermt '-14 days' \
  -printf '%TY-%Tm-%Td %TH:%TM %p -> %l\n' 2>/dev/null | head -20
for f in /etc/systemd/system/*.service; do
  [ -f "$f" ] || continue
  grep -qaE 'Restart=always' "$f" && echo "RESTART-ALWAYS $f :: $(grep -a '^ExecStart' "$f" | head -1)"
done

sec "6. cron / 启动脚本 / 动态链接 / SSH"
echo '--- root crontab ---'; crontab -l 2>/dev/null | grep -v '^#'
echo '--- /etc/cron.d ---'; ls -la /etc/cron.d/ 2>/dev/null | tail -n +4
for f in /etc/rc.local /root/.bashrc /root/.profile; do
  [ -f "$f" ] && echo "--- $f (tail) ---" && tail -6 "$f"
done
echo "--- ld.so.preload ---"; cat /etc/ld.so.preload 2>/dev/null || echo 'absent'
echo "--- authorized_keys ---"; wc -c /root/.ssh/authorized_keys 2>/dev/null || echo 'absent'
echo "--- sshd 关键项 ---"; grep -rhE '^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication)' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/ 2>/dev/null

sec "7. 账号面"
awk -F: '$3==0 {print "UID0: "$1}' /etc/passwd
stat -c '%y %n' /etc/passwd /etc/shadow 2>/dev/null
ls -la /etc/sudoers.d/ 2>/dev/null | tail -n +4

sec "8. 包完整性（c=配置文件改动，属正常；无 c 的行才是二进制被换）"
dpkg -V 2>/dev/null | head -25

sec "9. 近 3 天在系统目录新增/改动的文件"
find /usr/bin /usr/sbin /usr/local /opt /etc -xdev -type f -newermt '-3 days' \
  -printf '%TY-%Tm-%Td %TH:%TM %10s %p\n' 2>/dev/null \
  | grep -vE '/(apt|ssl/certs|ca-certificates|ld.so.cache|mtab|resolv.conf|hosts|machine-id|systemd/system/multi-user)' | head -30

sec "10. 临时目录与 home 隐藏项"
find /tmp /var/tmp /dev/shm -maxdepth 2 -name '.*' -newermt '-7 days' -printf '%TY-%Tm-%Td %TH:%TM %10s %p\n' 2>/dev/null | head -15
ls -la /root/.cache/ 2>/dev/null | grep -E '^d' | grep -E ' \.' | head

sec "11. auth.log：成功登录 + 爆破规模"
grep -ahE 'Accepted (password|publickey)' /var/log/auth.log* 2>/dev/null \
  | sed -E 's/.*T([0-9:]+).*for ([a-z]+) from ([0-9.]+).*/\1 \2 \3/' | sort | tail -25
echo "root 失败次数: $(grep -ac 'Failed password for root' /var/log/auth.log 2>/dev/null)"
echo "全部失败次数: $(grep -acE 'Failed password|Invalid user' /var/log/auth.log 2>/dev/null)"
echo '--- Top 来源 ---'
grep -aE 'Failed password|Invalid user' /var/log/auth.log 2>/dev/null | grep -oE 'from [0-9.]+' | awk '{print $2}' | sort | uniq -c | sort -rn | head -8

sec "12. 防爆破组件是否在跑"
systemctl is-active fail2ban 2>&1
systemctl is-enabled netfilter-persistent 2>&1
