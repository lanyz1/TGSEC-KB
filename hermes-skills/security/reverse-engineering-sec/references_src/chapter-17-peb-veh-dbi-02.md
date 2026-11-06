### 17.5 VEH(向量异常处理)反调试

`AddVectoredExceptionHandler` 注册的异常处理器优先级高于调试器。程序故意触发异常(INT3=0xCC、INT 2D、除零、非法指令),若被调试器接管则 VEH 不执行,据此判断是否被调试:

```cpp
LONG WINAPI VehHandler(PEXCEPTION_POINTERS ep) {
    if (ep->ExceptionRecord->ExceptionCode == EXCEPTION_BREAKPOINT) {
        // VEH 触发 = 未被调试,跳过 INT3
        ep->ContextRecord->Eip++;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

AddVectoredExceptionHandler(1, VehHandler);
__asm int 0x2d;   // 触发异常:被调试器接管则 VEH 不执行,程序通过全局标志判断
```

**绕过**:在 x64dbg/WinDbg 中配置 **"Pass exception to program"**(异常选项中将 `0x80000003`、`0x80000004` 设为 continue passing),使异常优先交予 VEH;或直接 patch 触发异常的指令为 NOP。

### 17.6 2026 新兴反调试技术

- **eBPF-based debugging detection**(Linux 6.x):程序通过 eBPF 挂载 `tracepoint/sched/sched_process_exec`、`raw_syscalls`,监控 `ptrace`、`process_vm_readv` 调用,即便用户态 hook 也无法绕过(内核态监控)。绕过需内核态 patch 或禁用非特权 eBPF(特权 eBPF 仍生效)。
- **Intel CET shadow stack**:控制流强制技术维护影子栈,若调试器通过 ROP/异常篡改返回地址,影子栈校验失败触发 `#CP` 异常。调试器需正确同步影子栈(2026 新版 gdb/WinDbg 已支持),否则被检测。
- **Hypervisor-enforced debugging detection**:基于 Hypervisor(Hyper-V、KVM)的调试在 VMExit 留下时序特征,目标通过 `RDTSC` 测量指令间延迟(VMExit 耗时数万周期)检测。需 Hook `RDTSC` 或使用硬件直通。
- **TPM-based attestation**:程序请求 TPM 远程证明,PCR(Platform Configuration Register)报告是否含调试器特征(已签名驱动、被 patch 的内核)。绕过需伪造 TPM 证明或物理替换 TPM。
- **AI-driven behavioral analysis**:通过机器学习模型分析进程行为(系统调用序列、内存访问模式、线程调度间隔),识别调试器/沙箱的"非人类"特征。2026 年已有商业 EDR 集成,逆向需模拟真实用户行为(随机化输入、引入人类节奏延迟),或对模型本身进行对抗样本攻击。

---



---
📖 本切片 2/2 结束。 本章节结束。