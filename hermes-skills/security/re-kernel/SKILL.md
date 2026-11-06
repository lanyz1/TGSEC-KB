---
name: re-kernel
description: >
  内核逆向（跨平台）：Windows 驱动（.sys/IRP/SSDT）、Linux 内核模块（.ko/ET_REL/LKM/rootkit）、
  macOS KEXT 与 System Extension/DriverKit、Android GKI/vendor module、seL4（capability 系统）、
  Fuchsia/Zircon（handle 模型 + DFv2 用户态驱动框架）、FreeBSD（linker sets/SYSINIT/KLD）、
  illumos/Solaris（DDI/DKI、dev_ops/cb_ops）、OpenBSD（KARL/autoconf/pledge）、NetBSD（模块按需自动加载）、
  Genode（组件树/session/quota）、MINIX 3（RS 自愈/grants/live update）、Plan 9（命名空间/9P）、
  HelenOS（fibril/DDF）、Redox（scheme）、Haiku（device_node/按需发现）、
  z/OS（TCB·SRB/cross-memory）、IBM i（单一存储层）、OpenVMS（AST）、Unikraft·MirageOS（unikernel）、
  HIC（同特权级 MMU 隔离的驱动模型 / capability / 物理沙箱 / 自描述模块 / 入口页 IPC）。
  触发词：内核、驱动、.sys、.ko、LKM、kext、dext、rootkit、内核模块、IRP、GKI、内核扩展、
  seL4、capability、CSpace、CNode、capDL、CAmkES、MCS、Fuchsia、Zircon、handle、DFv2、driver host、FIDL、
  FreeBSD、KLD、SYSINIT、linker set、illumos、Solaris、DDI、dev_ops、cb_ops、
  OpenBSD、KARL、autoconf、pledge、unveil、NetBSD、kmod、GENODE、session、quota、MINIX、RS、grant、9P、Plan 9、namespace、
  HelenOS、fibril、DDF、Redox、scheme、Haiku、device_node、z/OS、TCB、SRB、cross-memory、IBM i、single-level storage、OpenVMS、AST、$QIO、unikernel、Unikraft、MirageOS。
  English triggers: kernel module, driver reversing, LKM, kext, rootkit, GKI, seL4, capability system, capDL, Fuchsia, Zircon, handle, driver framework, FIDL, FreeBSD, KLD, SYSINIT, linker set, illumos, Solaris, DDI, dev_ops, cb_ops, OpenBSD, KARL, autoconf, pledge, NetBSD, kmod, Genode, session, quota, MINIX, reincarnation server, grant, 9P, Plan 9, namespace, HelenOS, fibril, DDF, Redox, scheme, Haiku, device node, z/OS, TCB, SRB, cross-memory, IBM i, single-level storage, OpenVMS, AST, QIO, unikernel, Unikraft, MirageOS.
capabilities: [kernel-analysis]
---

# 内核逆向（跨平台）

<CORE RULE>
**内核态分析的难点不是"用什么工具反编译"，而是"观察与预期冲突时先怀疑什么"。**
各平台形态不同（PE / ET_REL / Mach-O / 模块集合），但共性是：**构建与加载模型决定你能看到什么**——版本、符号解析方式、结构随机化、签名、加载阶段、缓存集合，都会让"看起来一样"的两份东西实际不同。
所以顺序永远是：**先确认"我在看的这份是不是正在运行/被加载的那份"，再谈逻辑。**
</CORE RULE>

<!-- split-index -->

## Section index

- [平台差异（不是同义替换）](references/split-01-section.md)
- [失败模式决策表（本技能的主入口）](references/split-02-section.md)
- [操作步骤（跨平台通用主线）](references/split-03-section.md)
- [平台分支（references）](references/split-04-references.md)
- [何时使用 / 何时不用](references/split-05-section.md)
- [工具准备（按平台，细节见各分支）](references/split-06-section.md)
- [跨域联合](references/split-07-section.md)
- [常见坑与陷阱（跨平台共性）](references/split-08-section.md)
