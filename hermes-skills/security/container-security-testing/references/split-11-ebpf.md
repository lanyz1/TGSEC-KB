## 十、eBPF 攻击面与检测规避

### 10.1 eBPF 作为攻击面（跨容器攻击，CVE-2022-42150）

```
核心事实：eBPF 程序运行在内核态，容器 namespace 无法限制其对**其他容器/宿主机**的影响。
前提：容器内具备 bpf syscall（未被 seccomp 拦截）+ CAP_BPF（kernel>=5.8）或 CAP_SYS_ADMIN；
      或 /proc/sys/kernel/unprivileged_bpf_disabled=0（无特权也可用，高危）。
实测：Docker Hub 约 2.5% 容器镜像具备 eBPF 权限。

危险 helper：
- bpf_probe_write_user()   写入任意进程用户态内存（注入命令/篡改 read 结果）
- bpf_probe_read()         读取任意进程/内核内存（凭据/Token 窃取）
- bpf_override_return()    篡改内核函数返回值（隐藏 syscall 行为）
- bpf_send_signal()        向任意进程发信号（DoS/杀进程）
- BPF_PROG_TYPE_SOCKET_FILTER 等：旁路流量、劫持网络包
```

```bash
# 容器内检查 eBPF 可用性
cat /proc/sys/kernel/unprivileged_bpf_disabled   # 0=无特权可用(高危) 1=需CAP_BPF 2=禁用
grep -i Cap /proc/self/status                     # CapEff 含 0x2000000(CAP_BPF)/0x200000(CAP_SYS_ADMIN)
```

### 10.2 eBPF 攻击链（逃逸/集群攻击）

```
链1 跨容器逃逸：挂 kretprobe 到 sys_read/sys_openat → bpf_probe_write_user 篡改宿主 bash
    输入流注入恶意命令（经典 PoC 改写 read 返回内容 + override_return）→ 宿主 root shell
链2 集群攻击：eBPF 读 /proc/<pid>/environ 提取同节点其他 Pod 的 SA Token
    → 用 Token 操纵 API Server → 集群接管（跨节点利用高权 Pod 权限）
链3 云安全中心规避：bpf 屏蔽安全 Agent 的日志采集（抢占事件 hook），
    同时建立 eBPF 隐蔽 C2 通道（TCP/UDP 流量内核态过滤）
```

### 10.3 eBPF Rootkit 与检测规避

```
eBPF rootkit 能力（工具：TripleCross / 商业级木马）：
- 进程隐藏：hook getdents64/filldir 过滤自身 PID
- 文件隐藏：hook openat/stat 过滤路径
- 凭据收割：attach sys_read 到 sshd/PAM/终端 fd → 捕获明文密码
- 后门：内核态 TCP hook 实现隐藏端口监听（用户态 netstat/ss 不可见）
- 反检测：以更高优先级（更低 hook 优先级数值）挂同事件 hook，抢先消费事件
  → Falco/Tracee/Tetragon 的 ring buffer 收不到该事件 = 检测工具被内核态致盲
- 反取证：篡改 getpid 返回、伪造 /proc、覆盖审计日志写入

检测规避对抗：
- 静态面：禁止非可信进程加载 eBPF（LSM + BPF token + 内核 lockdown）
- 动态面：追踪 BPF 程序加载事件（auditd bpf 类规则 / Tracee）、监控 map 创建
- 现实结论：检测工具自身也跑在 eBPF 上，与 rootkit 是同一优先级竞争 → 分层检测（进程级+网络级+日志级）才是出路
```

```bash
# 检测与加固参考
# 内核参数（高危面关闭无特权 eBPF）
sysctl -w kernel.unprivileged_bpf_disabled=2
# K8s 侧：seccomp profile 拦截 bpf syscall（K8s 1.27+ 默认 seccompRuntimeDefault）
# 防御工具：Falco（eBPF 探针）/ Tetragon（内核态强制执行）/ Tracee
```

