### 17.1 Windows 反调试技术矩阵

| 技术 | 检测方法 | 绕过方法 |
|------|---------|----------|
| **IsDebuggerPresent** | 读取 `PEB.BeingDebugged`(偏移 0x2) | patch PEB.BeingDebugged=0;ScyllaHide 自动 |
| **CheckRemoteDebuggerPresent** | 调用 `NtQueryInformationProcess(ProcessDebugPort)` | Hook NtQueryInformationProcess 返回 0 |
| **PEB.NtGlobalFlag** | 检测 `FLG_HEAP_ENABLE_TAIL_CHECK \| FLG_HEAP_ENABLE_FREE_CHECK`(0x70) | patch NtGlobalFlag=0 |
| **NtQueryInformationProcess** | `ProcessDebugPort=0x07`、`ProcessDebugFlags=0x1F`、`ProcessDebugObjectHandle=0x1E` | Hook 全部返回清洁值 |
| **DebugActiveProcess 自检** | 对自身 pid 调用,失败=被调试 | Hook 返回失败 |
| **时序检测** | `RDTSC`/`GetTickCount`/`QueryPerformanceCounter` 比较差值 | Hook RDTSC 返回固定差 |
| **硬件断点检测** | `GetThreadContext` 读取 DR0-DR7,非零=被设 HW BP | SetThreadContext 清除 DR0-DR3 |
| **软件断点检测** | 扫描代码段 `0xCC`(INT3)字节 | 使用 HW BP 替代;扫描时动态还原 |
| **父进程检查** | 期望父进程为 `explorer.exe`,非则报调试 | PEB 父 pid 伪造;parent spoofing |
| **NtSetInformationThread** | `HideThreadFromDebugger=0x11` 隐藏线程 | Hook 忽略调用 |
| **NtClose 句柄陷阱** | 传入无效句柄触发 `STATUS_INVALID_HANDLE` | VEH 中处理该异常 |

### 17.2 反反调试技术

**ScyllaHide** 是 x64dbg/OllyDbg 反反调试插件,在目标进程启动时注入并 Hook `ntdll.dll`、`kernelbase.dll` 中的反调试 API:

```ini
# ScyllaHide 配置(x64dbg 启动时自动加载)
[NtQueryInformationProcess] Hook=1
; ProcessDebugPort 返回 0;ProcessDebugFlags 返回 1;ProcessDebugObjectHandle 返回 NULL
[PEB] BeingDebugged=0;NtGlobalFlag=0;HeapFlags=0;HeapForceFlags=0
[NtSetInformationThread] HideThreadFromDebugger=0   ; 忽略线程隐藏请求
[NtClose] FilterInvalidHandle=1                     ; 屏蔽句柄陷阱异常
```

**Hook NtQueryInformationProcess** 返回清洁值(用户态 inline hook):

```cpp
typedef NTSTATUS(NTAPI* pNtQueryInformationProcess)(
    HANDLE, ULONG, PVOID, ULONG, PULONG);
pNtQueryInformationProcess origNtQIP;

NTSTATUS NTAPI HookNtQueryInformationProcess(
    HANDLE h, ULONG cls, PVOID buf, ULONG len, PULONG rlen) {
    NTSTATUS st = origNtQIP(h, cls, buf, len, rlen);
    if (st == 0) {  // STATUS_SUCCESS
        switch (cls) {
            case 7:    *(DWORD*)buf = 0; break;       // ProcessDebugPort
            case 0x1F: *(DWORD*)buf = 1; break;       // ProcessDebugFlags
            case 0x1E: *(HANDLE*)buf = NULL; break;   // ProcessDebugObjectHandle
        }
    }
    return st;
}
```

**时序绕过**:Hook `RDTSC`/`RDTSCP` 返回线性递增值使差值恒定(x64dbg 的 RDTSC 命令、ScyllaHide 的 Timing 模块)。**硬件断点清除**:检测到 DR 寄存器非零时,通过 `SetThreadContext` 清除 DR0-DR3 与 DR7:

```cpp
CONTEXT ctx;
ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
GetThreadContext(hThread, &ctx);
ctx.Dr0 = ctx.Dr1 = ctx.Dr2 = ctx.Dr3 = 0;
ctx.Dr7 = 0;
SetThreadContext(hThread, &ctx);
```

**TitanHide** 提供内核级隐藏(驱动),可绕过用户态 hook 检测——目标若检测 ntdll 是否被 patch,TitanHide 在内核态过滤 `NtQueryInformationProcess`、`NtSetInformationThread`,patch `EPROCESS`/`PEB`。

### 17.3 Linux/macOS 反调试对抗

**Linux ptrace 自附加**:目标调用 `ptrace(PTRACE_TRACEME, 0, 0, 0)`,已被调试则返回 -1(errno=EPERM),程序据此退出:

```c
if (ptrace(PTRACE_TRACEME, 0, 0, 0) < 0) { _exit(1); }  // 已被调试则退出
```

绕过:`LD_PRELOAD` hook `ptrace` 返回 0;目标静态链接时需 binary patch。

**/proc/self/status TracerPid 检测**:读取 `TracerPid:` 字段,非 0 即被调试。绕过:hook `open`/`read` 当路径含 `/proc/self/status` 时篡改返回内容。**inotify 监控**:目标对 `/proc/self/status` 建 watch,反检测到监控则判定为调试环境,需 hook `inotify_add_watch`。

**macOS PT_DENY_ATTACH**:通过 `sysctl` 的 `PT_DENY_ATTACH`(31)拒绝调试器附加,附加则进程被 SIGTRAP 终止。绕过:Hook `sysctl` 当 `CTL_KERN + KERN_PROC` 时清除 `P_FLAG` 中的调试标志。

**Frida 检测**:扫描 `/proc/self/maps` 中 `frida-agent`、`frida-gadget` 映射;检测线程名 `gum-js-loop`、`gmain`、`pool-frida`。

### 17.4 DBI 框架检测与绕过(2026)

动态二进制插桩(DBI)框架留下独特指纹:

- **Frida 检测**:TCP 端口 27042 扫描(frida-server 默认监听);`/proc/self/maps` 中 `frida-agent.so` 映射;D-Bus 协议探测(向 27042 发送 `AUTH` 字节,返回 `REJECT` 即 frida);检测 `gum-js-loop` 线程名;扫描内存中 `frida:rpc`、`gum` 字符串。
- **DynamoRIO 检测**:检查代码缓存特征(DR 将原始代码复制到独立 cache,存在 `dynamorio` 字符串与基本块重定位痕迹);检测 `ntdll.dll` 中 DR 注入的 hook stub。
- **QBDI 检测**:基于指令执行计数偏差——QBDI 模拟执行时 `RDTSC` 与真实 CPU 偏差巨大,目标比较两次 `RDTSC` 间执行的指令数即可判定。

**绕过策略**:frida-gadget 重命名为普通库名(如 `libtest.so`)并改 config.js 模块名;`frida-server -l 0.0.0.0:1337` 改用非默认端口;用 **Stalker 替代 Interceptor**(Stalker 不修改函数前 5 字节,对 INT3 扫描与 hook 检测免疫);DynamoRIO 用 `-stealth` 模式或进程外(out-of-process)模式减少特征。

```bash
# 修改 frida-server 默认端口与名称
cp frida-server frida-server-renamed
./frida-server-renamed -l 0.0.0.0:1337   # 改用非默认端口 1337
# frida 客户端连接:frida -H 127.0.0.1:1337 com.target.app
```



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-17-peb-veh-dbi-02.md")`