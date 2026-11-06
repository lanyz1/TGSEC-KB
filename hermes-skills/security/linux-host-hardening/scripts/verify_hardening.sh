#!/usr/bin/env bash
# 只读复验：不改任何状态。用法: bash verify_hardening.sh [测试口令]
# 给口令则额外做一次本机 TCP/22 真认证测试（需 paramiko）。
set -u
PASS="${1:-}"

echo "=== 1. 防火墙策略 ==="
iptables -S 2>/dev/null | grep -E '^-P' || echo "(读不到 iptables)"
ufw status numbered 2>/dev/null | sed -n '1,20p'

echo
echo "=== 2. fail2ban 监房 ==="
fail2ban-client status 2>/dev/null | sed -n '1,10p'
for j in sshd sshd-ddos recidive; do
  echo "--- $j"
  fail2ban-client status "$j" 2>/dev/null | grep -E 'Currently banned|Total banned|Banned IP list' || echo "  (jail 未启用)"
done
echo "--- 开机自启"
systemctl is-enabled fail2ban 2>/dev/null; systemctl is-enabled ufw 2>/dev/null

echo
echo "=== 3. sshd 生效值 ==="
sshd -T 2>/dev/null | grep -iE '^(permitrootlogin|passwordauthentication|maxauthtries|logingracetime|maxstartups|x11forwarding|loglevel)' || echo "(sshd -T 失败)"

echo
echo "=== 4. 最近 5 分钟爆破 ==="
if [ -r /var/log/auth.log ]; then
  awk -v d="$(date -u -d '5 minutes ago' '+%b %e %H:%M')" '$0>=d' /var/log/auth.log 2>/dev/null | grep -c 'Failed password'
  echo "--- 全量失败总数 / 头部来源"
  grep -c 'Failed password' /var/log/auth.log 2>/dev/null
  grep 'Failed password' /var/log/auth.log 2>/dev/null | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn | head -5
else
  echo "(无 /var/log/auth.log，可能是 journal-only 系统)"
fi

echo
echo "=== 5. 对外监听面 ==="
ss -tlnp 2>/dev/null | tail -n +2 | awk '{print $4}' | sort -u | tr '\n' ' '; echo

echo
echo "=== 6. 进攻族名残留 ==="
HITS=$(pgrep -af 'nuclei|ffuf|sqlmap|masscan|hydra|chisel|ligolo' 2>/dev/null | grep -v verify_hardening || true)
if [ -n "$HITS" ]; then echo "$HITS"; else echo "0"; fi

echo
if [ -n "$PASS" ]; then
  echo "=== 7. 口令认证实测 (TCP/22) ==="
  python3 - "$PASS" <<'PY'
import sys, paramiko
pw = sys.argv[1]
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect('127.0.0.1', 22, 'root', pw, timeout=8, allow_agent=False, look_for_keys=False)
    print('AUTH_OK', c.exec_command('id -un')[1].read().decode().strip())
except Exception as e:
    print('AUTH_FAIL', type(e).__name__, e)
finally:
    c.close()
PY
else
  echo "(未给口令，跳过认证测试；需要时: bash verify_hardening.sh '<口令>')"
fi
