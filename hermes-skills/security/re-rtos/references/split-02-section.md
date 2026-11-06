## 失败模式决策表（本技能的主入口）

**当"找不到调用关系""这段代码像死的""模块加载不了"时，按这张表先怀疑、再排除**：

| 症状 | 优先怀疑 | 处理方向 |
|---|---|---|
| 某个 init / 设备对象**没有直接 xref** | 注册机制：iterable section / `SYS_INIT` / `DEVICE_DEFINE`（Zephyr） | 到 linker section 与 map 文件里裁决，**别标 dead code**（[[zephyr]]） |
| 一整段**规则排列**的函数指针或结构体 | 同上：linker 生成的注册表 | 先按注册表理解，再考虑 vtable / jump table / 混淆（[[zephyr]]） |
| early init 里不调用内核服务 | `PRE_KERNEL_*` 阶段服务尚不可用（设计如此） | 别判"被裁剪"；反之出现线程/互斥/睡眠应先怀疑阶段判错（[[zephyr]]） |
| 一个进程**没有内核模块却控制硬件** | QNX 用户态 resource manager | 找 `resmgr_attach` / `dispatch_*` / `MsgReceive` 与注册的 pathname（[[qnx]]） |
| 网络驱动**既不是进程也不是模块** | 被 io-pkt 加载的 `devnp-*.so` | 找加载它的 io-pkt，确认原生还是经 shim 的旧驱动（[[qnx]]） |
| 线程优先级在采样中**突然变化** | QNX 消息驱动的**优先级继承** / server boost | 不是主动调 `pthread_setschedparam`（[[qnx]]） |
| 线程**长时间阻塞在 IPC** | `MsgSend` 本就同步等待（正常状态） | 找"谁该 reply"；pulse 才是非阻塞那类（[[qnx]]） |
| 独立模块里**大量 unresolved symbols** | VxWorks DKM 链接到**目标镜像的全局符号环境** | 先定位 image 与 VSB/VIP 配置，别判 malformed（[[vxworks]]） |
| 模块在**同版本** VxWorks 上不工作 | 具体 image configuration 不同 | 核对 VSB/VIP 而不是版本字符串（[[vxworks]]） |
| `dlopen()` 行为**不像 Unix 动态库** | RTEMS 运行时链接器 | 重定位进当前地址空间；对象名可为 `libfoo.a:bar.o`（[[rtems]]） |
| 找不到设备回调的 `file_operations` | RTEMS 设备驱动表（major = 表索引） | 恢复 `rtems_driver_address_table` 与 `rtems_io_register_name`（[[rtems]]） |
| 任务数/调度器**找不到运行期创建点** | RTEMS 构建期配置生成 | 找定义 `CONFIGURE_INIT` 的那个翻译单元（[[rtems]]） |
| 高优先级线程**不运行**（分区系统） | **分区级调度**：当前没有它所属分区的执行窗口 / 预算，或分区还没进 NORMAL | 先对齐 major frame 与 partition window，再看线程优先级（[[partitioned-rtos]]） |
| "连写 A B C 只读到 C" | **采样端口**的覆盖语义 | 对队列端口才是异常（[[partitioned-rtos]]） |
| 固定地址函数表被当成混淆 | APEX 服务表一类的 ABI | 先当服务表核对（[[partitioned-rtos]]） |
| 同一个 API 反编译结果在不同样本里完全不同 | NuttX 的 **FLAT/PROTECTED/KERNEL** 构建差异 | 先判构建模型；极短 API + 立即 trap 是自动生成的 syscall proxy（[[nuttx]]） |
| 某地址"用户能访问 / 用户 fault" | 可能分别来自 **malloc 与 kmalloc**（双堆） | 分清 user heap 与 kernel heap（[[nuttx]]） |
| 找不到真正操作硬件的地方 | NuttX 的 **upper half / lower half** 分层 | 硬件实现常在 `arch/` 或 `boards/`，不在 `drivers/`（[[nuttx]]） |
| ISR 里调用了 task 版 API | 上下文判定或符号识别有误（FreeRTOS） | 先判任务/ISR 上下文与 API 变体（[[freertos-context]]） |
| 某地址"有时能访问、有时不能" | **MPU 受限任务**或运行期改了 MPU 区域（FreeRTOS-MPU） | 查区域配置与运行期改区调用（[[freertos-context]]） |
| ISR 只清状态位就返回 | eCos 的 **DSR** 承担真正工作 | 查 ISR 返回值是否调度 DSR（[[ecos]]） |
| 大量「填 request ID → 跳公共 dispatcher」 | ThreadX Module 的 ABI | 建 request ID → 服务名映射，别判混淆（[[threadx-modules]]） |
| 代码地址不在模块内存区内 | **XIP** 模块（指令在 Flash、数据在 RAM） | 别判控制流劫持（[[threadx-modules]]） |
| ISR 尾部发生切换 / task 已就绪却不切换 | **中断进出参与调度**（µC/OS 的进入退出协议；SYS/BIOS 的 `Swi_disable` **连带禁用 Task 调度**） | 把中断进出算进调度时机（[[ucos-sysbios]]） |
| 同一地址在不同 task 下可访问性不同 | **per-task MPU 区域 / 保护域**（SAFERTOS、RTX5） | 查区域配置与安全等级，别判内存损坏（[[safertos-rtx5]]） |
| 句柄不像内存指针 | **间接对象 ID + 交叉引用表**（SAFERTOS ESM） | 别指望从它推出对象布局（[[safertos-rtx5]]） |
| ISR 里调用的 API 没立即生效 | **ISR FIFO 延迟队列**（RTX5） | 对象状态在 IRQ 退出后才变化，属正常（[[safertos-rtx5]]） |
| 服务调用"非法"或被拒 | **上下文类型**（T-Kernel 任务/准任务/任务独立；TOPPERS 任务/非任务/ISR/循环/闹钟） | 对照规范的有效上下文表，别按 API 名推测（[[tkernel-toppers]]） |
| 消息/信号的对端找不到 | **消息可跨 core / CPU / DSP / node**（OSE 的分布式透明传输层） | 别假定对端在本地，也别只查本地 syscall（[[ose-oseck]]） |
| 模块被替换但系统继续运行 | **Nucleus 的动态 reload/update**（线性内存映射 + MMU/MPU 子系统隔离） | 见运行模型表；别先判劫持 |

