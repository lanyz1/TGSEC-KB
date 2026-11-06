## 失败模式决策表（本技能的主入口）

**当反编译结果或运行观察与预期冲突时，按这张表先怀疑、再排除**：

| 症状 | 优先怀疑（按顺序） | 处理方向 |
|---|---|---|
| struct offset 全错 | ① BTF 与目标是否匹配 ② kernel build 是否匹配 ③ **RANDSTRUCT**（`CONFIG_GCC_PLUGIN_RANDSTRUCT`；此类内核带 taint `T`） | 优先级：目标 BTF > exact build debug info > exact seed+config > 动态验证 > 猜 offset（最差） |
| symbol resolution 怪异 | ① **MODVERSIONS**（CRC）② **Android KMI** ③ **livepatch**（`.klp.rela`/`.klp.sym`）④ split BTF | 各按对应分支核对，别当"文件损坏" |
| 文件与运行行为不一致 | ① Linux 运行时 relocation / init-only 段已消失 ② **macOS AuxKC 仍在跑旧版本** ③ Android 实际加载的是另一分区的同名模块 | 记录"磁盘版本 / 运行版本 / boot 时间"，别只看磁盘 |
| 磁盘代码与内存指令不一致 | **先排除合法动态 patching**：alternatives、static keys/jump labels、ftrace、livepatch、paravirt、kprobe（Linux） | 只有"无法解释的修改"才提高 rootkit 嫌疑——大量"像被篡改"其实是内核机制 |
| 内存里找不到某个函数 | ① `__init` 段已释放 ② built-in（本就没有独立 .ko）③ stripped ④ split BTF | 追"**init 留下了什么状态改变**"（callback/hook/改过的指针），而不是找 init 本身 |
| `kallsyms` 全 0 / 地址对不上 vmlinux | ① `kernel.kptr_restrict` ② **KASLR**（kernel text 与 module base 都随机化） | 先看策略与恢复 slide，别判"被 hook"或"不是同一个 kernel" |
| 符号化 offset 一直飘 / 解析成字符串 | ① 漏了 **`__TEXT_EXEC.vmaddr`**（arm64e 的 KEXT panic 基址要加它）② 符号文件与 panic image 的 **UUID/build** 不一致 | 先按段调整基址，再核对 UUID+arch+exact build（KDK），别怀疑反汇编 |
| kext 签名合法但就是加载不了 | 不只是签名：**UAKL / 用户批准 / Reduced Security / AuxKC 重建 + 重启**；x86_64 kext 还撞 `KMErrorDomain 71`（**Rosetta 不翻译 kext**） | 把 architecture / signature / approval / UAKL / boot policy / AuxKC inclusion 分开判断 |
| UserClient 连不上 / `kIOReturnBadArgument` | ① activated/entitlement/Team ID/sandbox ② **dispatch 的 count/size/completion 在 handler 之前就拒** | 按"先授权链、后 ABI、最后 handler"的顺序排，别先猜 selector 逻辑 |
| 模块"消失" | ① built-in（本就没有模块文件）② **rootkit 摘链**（module list unlink）③ macOS Kernel Collection ④ Android 另一分区或另一 boot stage | cross-view 交叉比对，别用单一视图下结论 |
| driver IPC 调不通 | ① selector/ABI ② **entitlement** ③ sandbox ④ Team ID（macOS）⑤ service 根本没 activate ⑥ **dispatch 的 count/size/completion 在 handler 之前就拒**（Windows 的 `kIOReturnBadArgument` 同构情况见 macOS 分支） | 从"能不能连"排到"连上之后怎么调"，而不是直接猜 selector |
| 找不到 IRP handler / `MajorFunction` 为空 | **先判驱动模型**：KMDF（`!drvobj` 指向 Wdf01000.sys 是正常）、NDIS/miniport、minifilter、UMDF | 去找对应的 **callback 注册图**（Evt* / Ndis* / FLT_* / WDF config dataflow），不是"没有 I/O" |
| `IoCallDriver` 已返回但行为没完成 | **completion edge**：`STATUS_PENDING` 不是失败，终态在 `IRP->IoStatus.Status` 与 completion path（`STATUS_MORE_PROCESSING_REQUIRED` 会接管） | CFG 要补 completion 边，否则 cleanup/copy-back/retry 像"没人调用" |
| 老 `.sys` 突然加载不了（签名看着没问题） | ① **2026-04 起 legacy cross-sign 默认不受信**（WHCP 才认；先行评估模式）② HVCI 下 Test Mode 仍要签名 ③ Secure Boot 阻挡 testsigning | 别判"签名损坏"或"API 变了"，先查策略层（见 [[windows-kernel]] §26–28） |
| 看见异常 ELF section | ① 签名尾（附加在 ELF 末尾）② livepatch `.klp.rela` ③ BTF/`.BTF.base` ④ ORC unwind ⑤ 架构/工具链元数据 | 先分类再处理；**不要为了"修好"去 truncate/strip** |
| 相同 CPtr 数值被当作同一对象 | **CPtr 是各 CSpace 的本地地址**，不是全局 ID（seL4） | 先恢复各自 CSpace 映射，按 **kernel object** 对齐 |
| 线程/服务"卡住"或像"配置损坏" | ① MCS：SC 未绑定 / budget 耗尽 / passive server 本就没有 SC ② fault handler 没修复 fault | 按 MCS 语义排查（SC / budget / 捐赠链），**别套 POSIX 死锁** |
| IRQ 只来一次 | 没有 Ack（seL4：未 ack 内核不再送后续中断） | 查 IRQ 处理循环里的 `seL4_IRQHandler_Ack` |
| 相同 handle 数值被当作同一对象 | **handle 数值只在当前进程内有意义**，关闭后还会被重用（Fuchsia/Zircon） | 按各进程的 handle 表恢复到 **kernel object** 对齐；关系图记 **object + handle + rights** 三项 |
| 曾经持有的 handle 现在报 `BAD_HANDLE` | **被 `channel_write` 送走了**（in-transit / transfer），或写入失败被丢弃 | 先查 transfer 语义（含 `ZX_RIGHT_TRANSFER` 是否被移除），**别判 UAF** |
| 明显有驱动间 IPC 但 syscall trace 里没有 channel 调用 | **两个驱动同驻同一个 driver host** → driver runtime 的进程内通道 | 用 driver host 划分验证（同驻时 node symbols 才走进程内），别判"调用被隐藏"（[[zircon-kernel]]） |
| 按 `bus probe()` 找不到驱动绑定 | DFv2 用 **node properties + bind rules 经 driver index 匹配** | 恢复 node → bind rules → driver component → driver host 链，而不是找 probe 回调（[[zircon-kernel]]） |
| 某个 init / 注册函数**没有任何调用者** | **linker set 注册**（FreeBSD `SYSINIT`；Zephyr 见 [[re-rtos/zephyr]]） | 由函数地址回溯到注册结构体与所属 `set_*` 集合，**别标 dead code**（[[freebsd-kernel]]） |
| 一大段连续指针/对象、section 名 `set_*` | 内核自己的**linker set** 集合 | 按注册集合解释，而不是 jump table / 混淆表 |
| 驱动的"支持什么"判断不一致 | `nulldev`（合法 no-op）与 `nodev`（不支持，返回 `ENXIO`）被混同 | 逐字段读 `dev_ops`/`cb_ops` 的占位符语义（[[illumos-kernel]]） |
| 同版本内核**每次启动布局都不同** / 两份二进制逐字节不一致 | **KARL 重链接**（OpenBSD）——不是被 patch、也不是版本不同 | 按符号/语义比较，别做字节比较（[[openbsd-kernel]]） |
| 模块**自己出现/自己消失**，找不到加载者 | 内核**按需自动加载**与自动卸载（NetBSD） | 对齐到触发它的事件与 `.plist` 设置，看时间线而非进程（[[netbsd-kernel]]） |
| 模块加载失败但文件看着正常 | 模块与内核**版本兼容性**（NetBSD） | 先核对 exact kernel version/build，别随手强制加载（[[netbsd-kernel]]） |
| 服务名相同却像连到了不同对象 / capability 数值被当作全局 ID | 名字只在**局部层级**成立、capability 是 **PD 局部命名**（Genode） | 按路由表 + label 链 / 按 session 对齐（[[genode]]） |
| 驱动进程**消失又出现** | **RS 自愈重启**（MINIX 3）——不是持久化 | 对齐 label（稳定）与 endpoint（会变）（[[minix3]]） |
| IPC 里的整数被当作 buffer 指针 | 可能是 **grant ID**（MINIX 3，消息定长 56 字节） | 按 `(endpoint, grant ID, offset, rights)` 还原；`EPERM` 是 grant 无效而非权限不足 |
| 路径相同却访问到不同对象 | **每进程命名空间**（Plan 9） | 恢复 bind/mount 历史与 9P 会话，别按路径断言同一资源（[[plan9]]） |
| 一个 OS thread 内出现大量"线程切换" | **fibril**：用户态协作调度，**内核不知道它**（HelenOS） | 别在内核调度里找证据（[[helenos]]） |
| `read`/`write` 落到的东西不是文件系统 | **scheme 决定含义**（Redox） | 按 scheme 名找 provider；客户端 fd 与 provider 描述符不相等（[[redox]]） |
| boot 时驱动不在、后来才出现 | **按需发现**（Haiku） | 查总线类型规则与按需标志，别判加载失败（[[haiku]]） |
| 执行地址属于另一个地址空间 | **cross-memory / PC 指令**（z/OS） | 区分 home/primary/secondary 与 TCB/SRB，别判劫持（[[zos]]） |
| 例程没有调用者却有行为 | **AST 异步控制流**（OpenVMS） | 补 AST 边；等待"返回后又等待"属正常（[[openvms]]） |
| 对象地址不像 DRAM 指针 | **单一存储层**（IBM i） | 内存与磁盘同一 64 位地址空间，别套 POSIX 文件模型（[[ibmi]]） |
| 找不到 user → syscall → kernel 边界 | **库操作系统 / unikernel** | 先判构建目标；"系统调用"可能只是函数调用（[[unikraft-mirageos]]） |
| 模块自带 UUID/版本/端点/资源/依赖/签名 的自描述元数据 | **先做元数据 triage，再反汇编** | 元数据是第一层证据（[[hic]]） |
| 快路径 IPC 呈"入口页 → 位图测试 → 失败分支 → 跳业务页"、跳转可触发 fault | **正常 IPC 边界**（隔离模式下的换页/验证路径） | 别判混淆 / CFI stub / 坏 CFG（[[hic]]） |
| 同一 capability 结构在不同版本或文档里布局不同 | **先做代际指纹**（per-core 无全局锁 ↔ 受保护全局表） | 别按最新文档直接套结构（[[hic]]） |
| 初始化里大量"看似多余"的 reset / 状态探测 | **sandbox restart / recovery 路径**（驱动重建 ≠ 硬件回到 clean boot） | 别当 boilerplate 删掉（[[hic]]） |

