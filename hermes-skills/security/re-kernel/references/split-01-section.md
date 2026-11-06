## 平台差异（不是同义替换）

| 平台 | 单元形态 | 加载与签名模型 | 类型信息来源 | 主要观测面 |
|---|---|---|---|---|
| Windows | **先分驱动模型**：WDM / KMDF / UMDF / minifilter / NDIS·miniport；再谈 `.sys`（PE） | SCM 注册 + 驱动签名（WHCP / 测试签名；**2026-04 起 legacy cross-sign 默认不受信**） | PDB（public≠private）、WDK / `ntddk.h` 类型 | WinDbg 内核调试、`!drvobj`/`!process`/`!wdfkd.*`、Volatility |
| Linux | `.ko`（**ET_REL** 可重定位目标） | `insmod`/modprobe + vermagic / symbol CRC / 签名尾 | BTF（含 split BTF 与 `.BTF.base`）、vmlinux、源码 | `/proc/kallsyms`、`/sys/module/*/sections/`、kprobe/ftrace、内存 cross-view |
| macOS | **三套模型**：KEXT（内核态）/ DEXT·DriverKit（**用户态**）/ System Extension（框架） | AuxKC（启动时加载）+ UAKL + Reduced Security / System Extension 激活审批 | 符号、Mach-O、`Info.plist`（IOKitPersonalities） | IORegistry、`kmutil`、dSYM+KDK；dext 走用户态分析与调试 |
| Android | GKI module / vendor module | GKI 签名 + **KMI 符号白名单** | BTF、KMI symbol list、`Module.symvers` | 模块所在分区、`modules.load` 计划 |
| seL4（微内核） | **capability 系统**：对象（TCB/Endpoint/CNode/Frame/Untyped/SC）+ cap 分布 | **无 capability 即无访问权**；对象在构造期由 spec/loader 创建 | capDL spec（`.cdl`）、CAmkES ADL、ELF | capDL snapshot（`seL4_DebugSnapshot`）、`seL4_DebugCapIdentify`、QEMU 仿真 |
| **Fuchsia/Zircon** | **handle 引用内核对象**（数值**进程本地**）+ **用户态驱动 component**（DFv2） | driver manager 维护 node 拓扑、driver index 按 **bind rules** 匹配、driver host 承载实例 | FIDL、组件清单、bind rules | driver manager/driver index 的匹配与拓扑、driver host 进程划分、handle+rights 关系图 |
| **FreeBSD** | `.ko`（KLD，ELF 可重定位） | **linker sets + `SYSINIT`**（`SI_SUB_*` + `SI_ORDER_*` 排序）+ 运行期 kernel linker | 符号、`set_*` 集合、源码 | `__start_set_*`/`__stop_set_*` 边界、加载路径（内建/预加载/`kldload`） |
| **illumos/Solaris** | `.so` 内核模块（DDI/DKI 驱动） | `_init` → `mod_install(&modlinkage)`；`_fini` → `mod_remove` | `modlinkage`→`modldrv`→`dev_ops`→`cb_ops` 静态链 | 逐字段读 `dev_ops`/`cb_ops`（含 `nulldev`/`nodev` 占位语义） |
| **OpenBSD** | 与一般 Unix 同形，但内核**每次 boot 重新随机链接**（KARL）+ autoconf 运行时匹配 | link kit + rc 后台重链接；detach 可等待使用者退出 | 符号（**KARL 后必须按符号而非字节比较**） | link kit/rc 重链接痕迹、autoconf 表、pledge/unveil 状态 |
| **NetBSD** | `.kmod`（ELF，由内核 linker 解析） | **按需自动加载**（含依赖递归）+ 自动卸载；模块与内核版本强约束 | 模块版本报告与内核版本 | 实际模块路径（布局随 `KERNEL_DIR` 变化）、`.plist` 属性 |
| **Genode** | **组件树**：session + capability + quota | parent 中介的路由，名字**逐层重映射** | 组件的 XML 配置与路由表 | capability 的 PD 局部命名、quota 捐赠链、ROM 更新 |
| **MINIX 3** | **用户态服务 + RS 自愈重启** | RS 监控/重启；label 稳定、**endpoint 会变** | 定长消息（56 字节）定义与 grants | 服务 label↔endpoint、grant 校验、live update 阶段 |
| **Plan 9 / 9front** | **每进程命名空间 + 用户态 file server** | bind/mount/union；服务经 `/srv` 发布后挂载 | 9P 的 fid/qid/walk 与消息类型 | 命名空间绑定历史、9P 会话对齐 |
| **HelenOS** | 用户态 server + **fibril**（内核不知道） | 用户态 DDF；devman 按 match id 评分启动驱动 | DDF 结构（`driver_ops_t`） | kernel thread 与 user fibril 的区分 |
| **Redox** | **scheme + 用户态 daemon** | 内核把文件操作转成 SQE/CQE 消息 | SQE/CQE 字段、句柄映射 | scheme 名 → provider；客户端 fd 与 provider 描述符的映射 |
| **Haiku** | kernel module，但分 **driver module / device module** 两层 | Device Manager 的 device_node 树 + **按需发现** | 节点属性与总线类型规则 | `/dev` 路径 ↔ 节点 ↔ 驱动 |
| **IBM z/OS** | **TCB 与 SRB** 两类可调度单位 | cross-memory / PC / AR 模式 | 地址空间三元组（home/primary/secondary） | 当前 primary/secondary/home 与工作单位类型 |
| **IBM i** | 对象式（库即容器对象） | **单一存储层**：内存与磁盘同一 64 位地址空间 | 对象限定名与全局指针 | 对象引用 vs 主存地址 |
| **OpenVMS** | 进程/线程 + **AST 异步控制流** | `$QIO` + 事件标志 + AST | IOSB、AST 参数 | 完成流（IOSB → 标志 → AST） |
| **Unikraft / MirageOS** | **库操作系统 / unikernel**：应用与 OS 库整链 | 构建目标决定一切（native vs binary；unix/hvt/xen…） | 构建配置与 shim | 调用进入"内核"的方式、设备接线来源 |
| **HIC** | **同特权级进程 + MMU 隔离**（Privileged-1 与 Core-0 同物理特权级）；驱动只映射被授权的 MMIO/共享内存 | 自描述模块（UUID/版本/端点/资源/依赖/签名）+ capability 记账；动态加载与滚动更新 | 模块元数据、capability 表 | domain / capability / mapping / device ownership / version / lifecycle 拓扑 |

