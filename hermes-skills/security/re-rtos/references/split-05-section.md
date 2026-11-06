## 操作步骤

按顺序执行，每步结果存档（任务清单、内核对象表、Ghidra 工程）。

1. **前置：镜像提取与格式识别（衔接 [[re-fw-extract]] 流程）**：
   - 先按 [[re-fw-extract]] 完成：binwalk 解包 / dd 按偏移切分 / `file` + `readelf -h` 确认架构与字节序（大端 ARM/MIPS 固件常见）
   - 产物通常是裸镜像（raw binary）或单个 ELF；记录 reset handler 入口与 RAM 基址（从链接脚本/启动代码推断）——任务表与 TCB 都在 RAM 区，按链接地址解读
   - 确认字节序与架构后再导入 Ghidra，避免整个分析白做

2. **RTOS 识别：启动代码链 + 特征串/符号搜索**：
   - 启动链形态：reset handler → 时钟/外设/内存初始化 → 创建任务（`xTaskCreate` / `osThreadNew` / `tx_thread_create` / `k_thread_create` / `rt_thread_create` / VxWorks `taskSpawn`（6.x 及更早常用；7 中仍存在，内部实现为 taskCreate+taskActivate）或 `taskCreate`（7 起，创建挂起任务需显式 taskActivate）/ QNX `ThreadCreate` / INTEGRITY ARINC 653 APEX `CREATE_PROCESS`）→ 调度器启动（`vTaskStartScheduler` / `osKernelStart` / `tx_kernel_enter` / `rt_system_scheduler_start` / VxWorks `kernelInit` / QNX 启动脚本拉起系统进程 / INTEGRITY `START` 进入运行态）。调度器启动调用点之前的代码全是初始化，不属于任何任务
   - 特征串：strings 搜内核名（"FreeRTOS"）、任务名（"Idle" 等）、版本/断言串；ELF 未 strip 时直接搜符号（`nm` / Ghidra Symbol Table：`pxCurrentTCB`、`_tx_thread_created_list`、`_kernel`、`rt_thread_ready_priority_group`）
   - 商业 RTOS 特征串：VxWorks 任务名（"tIdle" 空闲任务（VxWorks 6.x+）、"tRootTask" 根任务）与版本串；QNX 内核/镜像名（"procnto"、"imagefs"）与系统进程名（资源管理器惯用命名 `io-*`/`devb-*`/`devc-*`）；INTEGRITY 分区名/进程名与 ARINC 653 APEX 服务名
   - ThreadX 无版本串可搜，靠调度入口 `tx_kernel_enter` + TX_THREAD 魔数 ID（步骤 3）确认
   - 不确定内核时：找 3-4 个任务创建调用点与调度入口的调用形态，对照各内核公开结构逐个排除

3. **任务表定位**（按内核选结构；用 Ghidra 定义结构体后逐字段还原优先级/状态/栈指针/任务名）：
   - **FreeRTOS**：TCB（tskTaskControlBlock）关键字段——pxTopOfStack（栈顶指针）、uxPriority（优先级）、pcTaskName（任务名数组，默认 16 字节）、pxStack（栈起始，新版另有 pxEndOfStack）；任务链表在静态区——pxReadyTasksLists[优先级数]（按优先级索引的链表数组）、xDelayedTaskList1/2、xSuspendedTaskList；当前任务指针 pxCurrentTCB。定位方法：在上下文切换代码里找对 TCB 字段的读写（保存/恢复栈指针、更新当前任务指针），交叉引用回静态区
   - **ThreadX**：`_tx_thread_created_list` 全局双向链表（每个 TX_THREAD 经 created_next/created_previous 字段互链），配 `_tx_thread_created_count` 计数；TX_THREAD 关键字段——tx_thread_id（魔数 0x54485244 'THRD'，用于确认结构）、tx_thread_name（任务名）、tx_thread_priority、tx_thread_state、tx_thread_stack_start/end/ptr（栈区）、tx_thread_entry（入口函数）
   - **Zephyr**：`_kernel` 全局结构（新版本为 struct _cpu，老版本为 struct _kernel）——current（当前线程指针）、ready_q（就绪队列：优先级位图 + 按优先级索引的队列数组）、timeout_q（超时队列）、idle 线程指针；另有 slist 全局线程链链着所有 k_thread；k_thread 关键字段——base.prio（优先级）、stack_info.start/size（栈区）、name（线程名）
   - **RT-Thread**：rt_thread_ready_priority_group（优先级位图）+ rt_thread_priority_table[RT_THREAD_PRIORITY_MAX]（按优先级索引的链表数组）；rt_thread 结构关键字段——name、priority、stack_addr/stack_size、entry（入口函数）
   - **VxWorks**：WIND_TCB 关键字段——td_name（任务名，字符串指针指向字符串池，非内联数组）、td_sp（保存的栈指针）、td_priority（优先级 0-255，0 最高）、td_status、td_options、td_entry（入口函数）、td_pStackBase/pStackLimit/pStackEnd（栈底/有效栈界/实际栈界）、td_stackSize/td_stackHigh（栈尺寸/历史最高用量）。注意版本差异：VxWorks 7 起 WIND_TCB 为不透明类型，taskLib.h 只提供 VX_WIND_TCB_SIZE 大小宏，字段偏移随版本/SMP 配置变化。定位方法：任务名串在字符串池里（搜 "tIdle"/"tRootTask"），交叉引用回指向它的 TCB；或从上下文切换代码（保存寄存器组到栈、写 td_sp、按 td_priority 挑选任务）反推字段偏移，再沿任务链表回静态区
   - **QNX**：procnto（微内核 + 进程管理器一体）管理线程控制块——线程是调度最小单位，进程只是地址空间容器；线程关键属性——tid（进程内线程号）、优先级（256 级，0 为 idle）、线程名（6.3.2+ 支持）、栈与 TLS 区（含 tid/pid/栈基/errno）（内部布局无官方公开定义，属性经系统调用参数与 /proc 侧信道观察）。定位方法：QNX 固件是 IFS 镜像（startup 头魔数 0x00ff7eeb + "imagefs" 签名），用 dumpifs 解出各系统进程 ELF 再逐个分析（procnto 即内核本体）；应用侧从 `ThreadCreate`/`MsgSend` 等内核调用点定位线程，线程名串交叉引用回线程控制块；动态环境可用 /proc/<pid>/ctl 的 DCMD_PROC_TIDSTATUS 读线程状态做侧信道
   - **INTEGRITY**：分区（partition）是空间+时间隔离单元——空间上每分区独立内存区（MMU 强制），时间上按模块调度表（module schedule）循环分配执行窗口（一轮 = major frame）；分区内任务为 ARINC 653 进程，进程控制块属性含入口、栈尺寸、基优先级、周期/期限。定位方法：全静态配置——启动时一次性分配，无动态内存/无动态任务创建，对象地址固定，boot table 定义资源归属；分区/进程名串在固件里可读，交叉引用回配置表；ARINC 653 APEX 服务名（CREATE_PROCESS/SET_PRIORITY/GET_TIME 等）调用点即内核服务入口
   - 产出任务清单：逐个 TCB 读出任务名/优先级/栈区间/入口地址，每任务一行

4. **任务栈识别**：
   - 每任务 TCB 里有栈区字段：FreeRTOS pxStack/pxEndOfStack、ThreadX tx_thread_stack_start/end、Zephyr stack_info.start/size、RT-Thread stack_addr/stack_size、VxWorks td_pStackBase/pStackLimit/pStackEnd + td_stackSize（默认 0xee 填充，VX_NO_STACK_FILL 选项关闭）、QNX 线程栈界可从 TLS 区（栈基/tid/pid）辅助确认、INTEGRITY 进程栈在分区内存区内（栈尺寸在进程创建属性里）
   - 栈区形态：.bss 中按配置宏对齐的静态数组，或从内存池分配；FreeRTOS 开栈溢出检查时栈内为 0xa5 填充模式，可辅助确认栈范围
   - 按栈归属切分任务边界：栈区间属于该任务（局部变量、嵌套调用链），反编译时用"哪段栈属于哪个任务"划分代码归属；任务切换时保存/恢复的栈指针值直接对应 TCB 的栈顶字段

5. **内核对象（队列/信号量/互斥/定时器）**：
   - 从内核 API 调用点反推：`xQueueSend`/`xQueueReceive`/`xSemaphoreTake`/`xTimerCreate`（FreeRTOS）、`tx_queue_send`/`tx_semaphore_get`/`tx_mutex_put`/`tx_timer_create`（ThreadX）、`k_sem_take`/`k_mutex_lock`/`k_queue_get`/`k_timer_start`（Zephyr）、`rt_sem_take`/`rt_mutex_take`/`rt_mq_recv`（RT-Thread）——调用点第一个参数就是对象指针，沿交叉引用回溯到对象定义处（.bss 静态实例或内存池）
   - 商业 RTOS 内核对象：VxWorks 信号量（semGive/semTake）、消息队列（msgQSend/msgQReceive）、事件（eventSend/eventReceive）、看门狗（wdCreate）——调用点参数即对象 ID，沿交叉引用回溯到静态区定义；QNX 是 channel/connection 模型——MsgReceive 线程建 channel、MsgSend 线程建 connection，同步消息使线程进入 SEND/REPLY/RECEIVE 阻塞态（消息跨地址空间直拷、无中间缓冲），pulse 是 4 字节数据 + 1 字节 code 的非阻塞通知；INTEGRITY 分区间通信是采样端口（sampling port，覆盖写语义）/队列端口（queuing port，排队语义），分区内为信号量/事件/缓冲/黑板，按 ARINC 653 服务名搜索
   - ThreadX 对象头有魔数 ID 可逐个确认（以官方源码为准，勿凭资料记忆）：TX_QUEUE 0x51554555 'QUEU'、TX_SEMAPHORE 0x53454D41 'SEMA'、TX_MUTEX 0x4D555445 'MUTE'、TX_TIMER 0x4154494D 'ATIM'、TX_EVENT_FLAGS 0x4456444E 'DVDE'、TX_BYTE_POOL 0x42595445 'BYTE'、TX_BLOCK_POOL 0x424C4F43 'BLOC'（旧资料中 TIMR/EVEN 写法不实，勿沿用）
   - FreeRTOS 中信号量/互斥是队列（Queue_t）特例（结构同构），定时器为 Timer_t；用 Ghidra 定义结构体后，调用点参数类型传播自动改善反编译
   - 对象用途从语义推断：谁 send 谁 receive、take 之后处理什么，即任务间通信链路

6. **按任务拆分反编译**：
   - 每任务一个入口独立分析：任务创建 API 的 entry 参数 → 函数 → 重命名为 task_<优先级>_<名字>，Ghidra 中逐任务标记入口
   - 任务内阻塞点（延时/等信号量/收队列/等事件）是调度切换点，按阻塞点把任务逻辑切成状态段分析
   - 任务间通信对象（队列/信号量）连接不同任务：先画"任务-对象-任务"关系图，再按图逐个深挖

