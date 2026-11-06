## 常见坑与陷阱

- **调度器启动前的代码当任务分析**：现象——把 reset handler 到调度器启动之间的初始化序列当成某个任务的主逻辑，分析半天对不上业务；原因——启动代码（时钟/外设/内存/创建任务）先于调度器执行，不属于任何任务，且与任务入口的调用形态相似；对策——先定位调度器启动调用点（vTaskStartScheduler/osKernelStart/tx_kernel_enter/rt_system_scheduler_start/kernelInit），之前的归为初始化，任务入口一律从创建 API 的 entry 参数取
- **stripped 固件没有任务名**：现象——TCB 里名字字段全空/乱码/全 0；原因——固件 strip 符号且裁剪了字符串表，pcTaskName/tx_thread_name 无内容可读；对策——用栈指针范围（每任务独享栈区间）、优先级值、创建顺序编号区分任务，任务名只当辅助线索
- **链表 vs 静态表结构差异**：现象——按"静态数组任务表"假设在固件里找不到任务列表；原因——各内核组织方式不同：FreeRTOS 是静态链表数组（pxReadyTasksLists 按优先级索引）+ 当前指针 pxCurrentTCB，ThreadX 是全局双向链表 _tx_thread_created_list，Zephyr 是 slist 全线程链 + ready_q 位图队列，RT-Thread 是优先级位图 + 数组链表，VxWorks 任务挂全局任务链表（taskIdListGet 可枚举语义），QNX/INTEGRITY 布局不公开、从创建/服务调用点与句柄表反推；对策——先识别内核再选对应结构（步骤 3），别拿一种内核的布局套另一种
- **新版 RTOS 去字符串/去符号后搜不到特征**：现象——strings 和符号表里什么都没有，内核识别卡住；原因——发布固件常 strip 符号、关断言/关字符串、甚至裁剪版本串；对策——用结构特征兜底：ThreadX 魔数 ID（THRD/QUEU/SEMA…）、FreeRTOS 临界区模式（Cortex-M 上 BASEPRI 保存/恢复的固定序列）、调度入口与上下文切换代码形态、按版本比对 TCB 字段偏移（从任务入口参数如何写入 TCB 反推全结构）
- **idle/低优先级兜底任务当业务任务**：现象——把空转循环任务当成主要业务逻辑深挖；原因——FreeRTOS 自动创建 prvIdleTask（最低优先级 0）、Zephyr 有 idle 线程、VxWorks 有 tIdle 任务，它们只跑钩子/清理/低功耗代码，与业务无关；对策——任务清单按优先级排序，最低优先级、无阻塞的无限循环先排除为兜底任务，业务任务从高优先级和含阻塞点（队列/信号量等待）的任务里找
- **上下文切换/调度代码当普通业务函数**：现象——PendSV/SVC handler 或调度循环被当业务逻辑跟踪，调用关系混乱；原因——RTOS 的上下文切换（保存/恢复寄存器组、切换 pxCurrentTCB/current）与任务代码同属固件，反编译器视为普通函数；对策——识别切换特征（保存全寄存器组、更新当前任务指针、从栈顶恢复 PC/LR）后标记为调度代码不深入，任务逻辑只看创建 API 入口往下的调用树
- **商业 RTOS 结构无公开定义，旧资料偏移不可套用**：现象——按网上 VxWorks 5.x 的 WIND_TCB 偏移在 VxWorks 7 固件里解出乱码；原因——VxWorks 7 起 WIND_TCB 为不透明类型（taskLib.h 只给 VX_WIND_TCB_SIZE）、QNX 线程控制块与 INTEGRITY 进程表布局未公开，且随版本/SMP 配置变化；对策——字段名只当语义线索，偏移一律从上下文切换/创建代码现场反推，用字段读写模式验证
- **任务名字段是字符串指针不是内联数组**：现象——在 TCB 里按 FreeRTOS 习惯找定长名字数组，读到的却是地址值；原因——VxWorks td_name 是 char* 指向字符串池，QNX/INTEGRITY 线程名同理；对策——拿到字段后先判断是地址还是内联数据（交叉引用看是否指向字符串区），固件裁剪字符串后名字字段会失效，改用栈范围/优先级区分任务
- **QNX 固件是 IFS 镜像，不能当裸二进制直接搜**：现象——整块固件里搜不到 procnto 或进程代码；原因——QNX 镜像内文件常 LZO 压缩，字符串与代码都不可见；对策——先按 startup 头（0x00ff7eeb）+ "imagefs" 签名定位镜像，用 dumpifs 解压提取（startup 头字段被改过时加 -z），得到各进程 ELF 再分析
- **INTEGRITY 运行期没有动态创建**：现象——把分区模式切换（SET_PARTITION_MODE 的 COLD_START/WARM_START/NORMAL）或进程启停（START/STOP）当"创建任务"逻辑分析；原因——INTEGRITY 资源启动时静态分配，运行期主要是状态迁移，无动态内存分配；对策——创建类代码只出现在初始化/配置路径，业务逻辑按周期调度（major frame）与 APEX 服务调用组织
