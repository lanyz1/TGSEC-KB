## 何时使用 / 何时不用

- 前置：**拿不准目标属于哪一个系统**（非 PE/ELF、OSABI 指向非主流系统、无标准容器）→ 先过 [[re-analyze/system-fingerprints]]
- 用：各平台内核态载荷与驱动（恶意驱动 / rootkit / 反作弊 / EDR 对抗 / 闭源驱动）的静态逆向与运行时验证
- 用：**capability 系统**（seL4 等微内核）的对象图 / capability 分布 / IPC 拓扑恢复，以及"行为为何与普通 OS 不同"的判定
- 用：**Fuchsia/Zircon** —— handle 与 rights 关系恢复、DFv2 驱动的 bind rules 匹配与 driver host 划分、同驻驱动通信的判定（[[zircon-kernel]]）
- 用：**FreeBSD / illumos·Solaris** —— linker set 注册的初始化（找不到调用者）与 KLD 生命周期（[[freebsd-kernel]]）；DDI/DKI 驱动骨架与 `dev_ops`/`cb_ops` 能力判读（[[illumos-kernel]]）
- 用：需要判断"内存里/内核里这份代码是什么、从哪来、是否被改过"
- 不用：UEFI / 引导阶段（bootkit）→ [[re-uefi]]；RTOS 内核对象 → [[re-rtos]]；eBPF 程序（BPF-64 指令集、progs/maps）→ [[re-ebpf]]；TEE / TrustZone → [[re-tee]]；仅内核调试与崩溃定位 → [[re-windbg]] / [[re-lldb]]
- 不用：只需要采集内存里的载荷（不分析内核结构）→ [[re-sample-acquire]]

