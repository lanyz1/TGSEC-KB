## 运行模型差异（不是同义替换）

| 平台 | "驱动/服务"在哪 | 注册与发现机制 | 先判什么 |
|---|---|---|---|
| FreeRTOS / ThreadX / RT-Thread | 与内核同镜像；任务 + 内核对象表 | 显式创建 API + 静态对象实例 | 任务表/TCB（本主文档） |
| **Zephyr** | 与内核同镜像，但**设备图在编译期生成** | devicetree + Kconfig + **iterable sections**、`SYS_INIT` | 是否 linker 注册（[[zephyr]]） |
| **VxWorks** | **两种**：DKM 内核态 / RTP 用户态 | DKM 动态加载 + **全局符号环境**；RTP 走标准 ELF/`.so` | 先分 DKM 还是 RTP（[[vxworks]]） |
| **QNX** | **用户态 server**；网络驱动是 io-pkt 内的共享对象 | **pathname 注册** + 消息传递 | 先判形态（[[qnx]]） |
| **RTEMS** | 与内核/应用同处**单一地址空间** | 构建期配置（`confdefs.h`）+ 设备驱动表 + 运行期链接器 | 配置与驱动表（[[rtems]]） |
| **INTEGRITY / ARINC 653 / VxWorks 653 / PikeOS** | **分区**（空间 + 时间 + 资源三域） | 静态配置；分区级 **major frame / partition window** + 分区内调度 | **先对齐分区窗口与分区模式**（[[partitioned-rtos]]） |
| **NuttX** | 与内核同镜像或分离，**取决于构建方式** | 由构建模型决定：FLAT 直接调用 / PROTECTED 走 syscall proxy / KERNEL 走 MMU | **先判 FLAT / PROTECTED / KERNEL**（[[nuttx]]） |
| **eCos** | 与内核同镜像；中断处理分三层 | ISR → DSR → thread，各层同步机制不同 | 判断工作落在哪一层（[[ecos]]） |
| **ThreadX Modules** | 常驻内核 + 可动态装载模块 | **module preamble + request ID 经软件 dispatch** | 先认 module ABI（[[threadx-modules]]） |
| **FreeRTOS（上下文）** | 与内核同镜像；中断上下文特殊 | task API 与 FromISR API 分离 | 先判上下文（[[freertos-context]]） |
| **µC/OS、SYS/BIOS** | 与内核同镜像；**中断参与调度** | ISR 显式通知内核（进入/退出）；分层线程 Hwi > Swi > Task | 调度时机要把中断进出算进去（[[ucos-sysbios]]） |
| **SAFERTOS、CMSIS-RTX5** | 与内核同镜像；**带访问控制与安全等级** | per-task 区域/保护域、API 与对象访问策略、ISR 延迟队列 | 先判"谁能访问什么"（[[safertos-rtx5]]） |
| **T-Kernel、TOPPERS** | 与内核同镜像；**服务调用合法性取决于上下文** | 静态配置生成 task/handler；设备驱动以准任务部分运行 | 先恢复上下文类型与规格家族（[[tkernel-toppers]]） |
| **OSE / OSEck** | 与内核同镜像但**消息可跨节点** | 消息式 IPC + 分布式透明传输层（共享内存/DMA/互连） | 先判消息对端在不在本地（[[ose-oseck]]） |
| **Nucleus** | 与内核同镜像；**MMU/MPU 子系统隔离 + 线性内存映射** | 动态 reload/restart/update 应用与内核模块（不必停机） | "模块被替换但系统继续跑"与"隔离存在但 VA 不像每进程独立"都不是异常 |

