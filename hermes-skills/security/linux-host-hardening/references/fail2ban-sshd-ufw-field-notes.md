# fail2ban + sshd + ufw 实战笔记（2026-10-22，自有 VPS 收网后加固）

## 现场量级
- `grep -c 'Failed password' /var/log/auth.log` → 42,976 次
- 头部来源：176.53.159.198 (3874)、176.53.159.197 (3793)、77.239.124.45/39/32 (各 ~2440)、109.160.32.44/42/180/159/156 (各 ~1989)、216.36.112.159
- 加固前 `-P INPUT ACCEPT`：等于没防火墙；631 (CUPS) 对公网直接开着

## jail.local（可直接抄，改 ignoreip 网段）
```ini
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 <IP-REDACTED>/24 10.20.30.0/24
bantime  = 24h
findtime = 10m
maxretry = 4
banaction = iptables-multiport
banaction_allports = iptables-allports
backend = auto
bantime.increment = true
bantime.factor = 2
bantime.maxtime = 4w

[sshd]
enabled  = true
port     = ssh
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 3
findtime = 10m
bantime  = 24h

[sshd-ddos]
enabled  = true
port     = ssh
filter   = sshd      # 注意: 不是 sshd-ddos, 1.0.x 没这个 filter 文件
mode     = ddos
logpath  = /var/log/auth.log
maxretry = 6
findtime = 5m
bantime  = 12h

[recidive]
enabled  = true
logpath  = /var/log/fail2ban.log
banaction = iptables-allports
bantime  = 4w
findtime = 1d
maxretry = 4
```

## sshd drop-in（/etc/ssh/sshd_config.d/99-hardening.conf）
```
PermitRootLogin yes
PasswordAuthentication yes
PubkeyAuthentication yes
KbdInteractiveAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30
MaxStartups 10:30:60
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowAgentForwarding no
UseDNS no
LogLevel VERBOSE
```
`sshd -T` 复核（Ubuntu 24.04 实测输出）：`logingracetime 30 / maxauthtries 3 / maxstartups 10:30:60 / x11forwarding no / loglevel VERBOSE / permitrootlogin yes`。

## ufw 最终态（`ufw status numbered`）
```
[ 1] Anywhere                    ALLOW IN    10.20.30.0/24              # range-lab
[ 2] 22/tcp                      LIMIT IN    Anywhere                   # ssh-ratelimit
[ 3] 80/tcp                      ALLOW IN    Anywhere                   # nginx
[ 4] 22/tcp                      ALLOW IN    <IP-REDACTED>/24           # fleet-ssh
[ 5] 22/tcp (v6)                 LIMIT IN    Anywhere (v6)
[ 6] 80/tcp (v6)                 ALLOW IN    Anywhere (v6)
```
`iptables -S | grep '^-P'` → `-P INPUT DROP / -P FORWARD DROP / -P OUTPUT ACCEPT`；`iptables -S ufw-user-input` 里可见 recent 限速三条（`--set` / `--update --seconds 30 --hitcount 6` / `-j ufw-user-limit-accept`）。631 没有任何 allow 规则 = 外部不可达，服务本身仍绑 0.0.0.0 不影响实验网段。

## 口令轮换实录
```
printf 'root:<NEW>\n' | chpasswd            # rc=0
passwd -S root                              # root P 2026-10-22 0 99999 7 -1
python3 -c "import crypt,spwd;h=spwd.getspnam('root').sp_pwdp;print(crypt.crypt('<NEW>',h)==h)"
# hash_prefix: y  (yescrypt)   verify_new: True   verify_old_dummy: False
```
（python3.11 的 crypt/spwd 有 DeprecationWarning，能用；3.13 起被移除，届时改用 `openssl passwd -6` 或 `mkpasswd` 对照。）

## 验收命令原文
```
fail2ban-client status
  |- Number of jail:  3
  `- Jail list:  recidive, sshd, sshd-ddos
fail2ban-client status sshd
  |- Currently banned: 12
  `- Banned IP list: 109.160.32.140 216.36.112.159 176.53.159.198 ...
awk -v d="$(date -u -d '2 minutes ago' '+%b %e %H:%M')" '$0>=d' /var/log/auth.log | grep -c 'Failed password'
  0
```
paramiko 自测（新口令走 TCP 22）：
```python
import paramiko
c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('127.0.0.1',22,'root','<NEW>',timeout=8,allow_agent=False,look_for_keys=False)
print(c.exec_command('id -un')[1].read().decode().strip())   # root
```

## 三个坑的原始报错
1. `ERROR Found no accessible config files for 'filter.d/sshd-ddos' under /etc/fail2ban` → 改 `filter = sshd` + `mode = ddos`。
2. `fail2ban-client status` 只有 1 个 jail（apt 装完自动起过）→ `fail2ban-client reload` 后变 3 个。
3. `write_file('/etc/fail2ban/jail.local')` → `Refusing to write to sensitive system path` → 写工作目录再 `install -m 644 -o root -g root`。
