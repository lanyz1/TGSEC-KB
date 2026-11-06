## 跨域联合

- [[re-fw-extract]]：镜像提取与格式识别前置（binwalk 解包、magic 扫描、字节序判断、偏移切分）
- [[re-fw-emulate]]：需要动态验证（跑任务、触发调度、观察切换时序）时仿真目标固件
- [[re-automotive]]：QNX 车机中控场景联动（车载系统侧固件/进程分析，与 CAN/ECU 侧互补）
- [[re-binary-core]]：RTOS 应用深层反编译底座（[[re-ghidra]] 定义结构体，或按环境选 [[re-radare2]]）
- 发现恶意逻辑 → [[re-malware]]；任务与服务器通信 → [[re-protocol]]
- 本技能可被 [[re-firmware]] 网关的 MCU 固件深挖路径调用

