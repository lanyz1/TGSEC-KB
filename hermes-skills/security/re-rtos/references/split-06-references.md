## 平台分支（references）

以下四个平台的"驱动/服务模型"与通用任务表方法差异足够大，单独成篇——**先读分支判定运行模型，再回到本主文档做任务与对象分析**：

- [[qnx]] —— **用户态 server 模型**：resource manager（`dispatch_create` → `resmgr_attach` → `dispatch_block/handler`，底层是 `MsgReceive`）、`connect`/I/O 两张函数表与 `iofunc_*` 默认实现的区分、`devctl` 与 `_IO_DEVCTL`、**io-pkt 与 `devnp-*.so`（含单线程栈上下文）**、消息驱动的**优先级继承**与 server boost、`MsgSend` 同步阻塞 vs pulse
- [[vxworks]] —— **DKM（`.out`，内核态）vs RTP（`.vxe`，用户态）**、DKM 与**全局符号环境**的链接关系、`undefined symbol` 的真实成因（VIP 未含组件）、独立模块 unresolved 属常态、VSB/VIP 与"同版本不同 ABI 环境"
- [[zephyr]] —— **编译期设备图**：`DEVICE_DEFINE`/`DEVICE_DT_DEFINE` 与 linker section、`SYS_INIT` 的 level/prio 与**返回值后果**、**iterable sections**（规则排列的结构体未必是混淆表）、`/chosen` 与 `/aliases` 不是硬件节点、map 文件裁决归属、**LLEXT**（导出符号表、`llext_unload` 后指针失效、User Mode 下需 `llext_add_domain`）
- [[rtems]] —— **单地址空间 + 构建期配置**：`confdefs.h` 与 `CONFIGURE_INIT` 唯一性、`rtems_driver_address_table` 六入口与 **major = 表索引**、`rtems_io_register_name`、**运行时链接器不是 Unix 共享库模型**（`libfoo.a:bar.o`、懒/立即绑定等价、未解析不报错、重名即错误、基镜像需 `rtems-syms`）
- [[partitioned-rtos]] —— **分区系统（INTEGRITY / ARINC 653 / VxWorks 653 / PikeOS）**：**major frame + partition window** 的两层调度（PikeOS 三层）；分区模式 IDLE/COLD_START/WARM_START/NORMAL（进程"不跑"常是还没进 NORMAL）；**采样端口 vs 队列端口**的覆盖语义；INTEGRITY 的固定 CPU/内存预算与静态启动表；PikeOS 的 **APEX 固定地址服务表**与 POSIX guest 的 system thread 映射
- [[nuttx]] —— **FLAT / PROTECTED / KERNEL 三种构建**：同一 API 产物完全不同；PROTECTED 的**自动生成 syscall proxy**（极短函数 + 立即 trap，不是 hook）；**双堆**（user heap / kernel heap）；驱动的 **upper half / lower half** 分层
- [[freertos-context]] —— **ISR 与任务上下文**：task 版 vs `...FromISR()` 版 API、`pxHigherPriorityTaskWoken` 与 `portYIELD_FROM_ISR`（真正的切换发生在中断退出后）、`configMAX_SYSCALL_INTERRUPT_PRIORITY`（更紧急的 ISR 一个 API 都不能调，且优先级数值方向相反）；**FreeRTOS-MPU** 的受限任务与运行期改区
- [[threadx-modules]] —— **module preamble**（必在第一个地址、properties 位决定特权/MPU）+ **request ID 经软件 dispatch 调用常驻 Module Manager**（本质是 syscall table，不是混淆）+ XIP 与拷贝装载
- [[ecos]] —— **运行期**：ISR / DSR / thread 三层、三种同步级别与各自的锁（**ISR 不能用 DSR 级锁；DSR 能 signal 条件变量但不能 wait**）、三种驱动模型；**构建期**：CDL 配置系统决定编入项与构建目标、HAL 向量表（VSR）与虚拟向量、RedBoot 启动顺序与**构造函数在向量表初始化之后运行**（区域重叠会被冲掉）、调试桩的去向
- [[ucos-sysbios]] —— **中断进出参与调度**：µC/OS 的 `OSIntEnter`/`OSIntExit` 成对协议与"只有最后一个嵌套 ISR 退出才判断切换"；SYS/BIOS 的 **Hwi > Swi > Task** 分层、**`Swi_disable()` 连带禁用 Task 调度**、Hwi/Swi 共用 ISR 栈
- [[safertos-rtx5]] —— **认证 RTOS 的隔离特性**：SAFERTOS ESM 的 **API 访问策略 / 对象访问策略 / 间接对象 ID / per-task 区域**；RTX5 的 **Safety Class / MPU 保护域 / 线程看门狗 / 对象与 SVC 指针检查**、**ISR FIFO 延迟队列**（溢出时系统状态已不一致）
- [[tkernel-toppers]] —— **上下文合法性**：T-Kernel 的任务/准任务/任务独立三种上下文与设备驱动（准任务部分、必须可重入、不保证互斥）；**TOPPERS 的四个家族**（ASP3 / HRP3 / FMP3 / HRMP3）与静态配置生成
- [[ose-oseck]] —— **信号模型**（不是 POSIX 信号；**信号号不唯一，需配合次级 id**；先注册后发送否则丢；一次事件可能关联多个信号要取空）+ **进程/块/段/池的内存所有权**（只能在**自己的池**里分配，跨域发送会被拷贝）+ 监督与错误处理器（含"结尾标记能检出什么、检不出什么"）+ OSE 与 OSEck 的差异与**异构边界**（信号跨 core/CPU/DSP/节点；系统信息接口可看信号空间与保存的寄存器/栈）
- [[nucleus]] —— **线性内存映射 + 受保护区域 + entitlement**（MMU 在 Cortex-A、MPU 在 Cortex-M；**不是每进程独立 VA**）；**`NU_PARTITION_POOL` 是固定块内存池**（与隔离域同名的术语坑）；`NU_SUSPEND` 下池空则任务本就挂起；**模块可动态 reload/restart/update 而不停机**

