---
name: re-rtos
description: RTOS 结构分析：FreeRTOS/ThreadX/Zephyr/RT-Thread/VxWorks/QNX/RTEMS/NuttX/eCos/µC-OS/SYS-BIOS/SAFERTOS/CMSIS-RTX5/T-Kernel/TOPPERS/OSE/INTEGRITY/ARINC 653/PikeOS/Deos 运行模型判定、任务表与 TCB…
capabilities: [rtos-analysis]
---

# RTOS 结构分析（FreeRTOS / ThreadX / Zephyr / RT-Thread / VxWorks / QNX / RTEMS / INTEGRITY）

<CORE RULE>
**RTOS 之间的差异不只是"换个 TCB 布局"，而是"驱动/服务在哪个地址空间、什么时候被注册"。**

各内核形态不同（链表任务表 / 编译期设备图 / 全局符号环境 / 用户态 server / 构建期配置），但共性是：**注册模型决定你能看到什么**——一个函数"没有直接交叉引用"，在不同 RTOS 上可能分别意味着"正常（linker 注册）"、"正常（装载时符号解析）"、"正常（用户态 server）"或"真的没被引用"。

所以顺序永远是：**先判这个 RTOS 的运行与注册模型，再谈任务与内核对象。**
</CORE RULE>

<!-- split-index -->

## Section index

- [运行模型差异（不是同义替换）](references/split-01-section.md)
- [失败模式决策表（本技能的主入口）](references/split-02-section.md)
- [何时使用 / 何时不用](references/split-03-section.md)
- [工具准备](references/split-04-section.md)
- [操作步骤](references/split-05-section.md)
- [平台分支（references）](references/split-06-references.md)
- [跨域联合](references/split-07-section.md)
- [常见坑与陷阱](references/split-08-section.md)
