## 19. 模拟执行框架 — Qiling/Unicorn/QEMU-user

模拟执行框架通过软件模拟CPU指令集与(可选)操作系统层,在非原生环境运行目标二进制,是跨架构分析、恶意软件沙箱、脱壳的关键基础设施。相比动态调试,模拟执行无调试器痕迹、可精确控制内存与系统调用,适合反检测与自动化场景。

### 19.1 模拟执行框架对比

| 框架 | 底层引擎 | 支持架构 | 系统调用模拟 | 文件系统模拟 | 适用场景 |
|------|----------|----------|--------------|--------------|----------|
| Unicorn | QEMU(精简) | x86/x64/ARM/ARM64/MIPS/PPC/RISC-V | 无(纯CPU) | 无 | shellcode分析/解密例程 |
| Qiling | Unicorn | 同Unicorn | 完整(Linux/Win/macOS) | 完整(rootfs) | 恶意软件沙箱/跨架构/脱壳 |
| QEMU-user | QEMU | 全架构 | 部分(用户态) | 部分(路径映射) | 跨架构调试/fuzzing |
| Manticore | 自研 | x86/x64/EVM | 符号化 | 符号化 | 符号执行/智能合约 |

Unicorn是纯CPU级模拟器,无OS层,适合指令级分析;Qiling在Unicorn之上构建OS模拟层,提供系统调用、文件系统、网络栈模拟;QEMU-user是QEMU的用户态模式,支持gdbstub;Manticore融合符号执行与模拟。

### 19.2 Qiling框架实战

Qiling架构: Qiling = Unicorn(CPU模拟) + OS模拟层(syscall handler + 文件系统 + 注册表 + 网络栈)。支持Windows PE、Linux ELF、macOS Mach-O跨架构执行,内置rootfs提供模拟环境。

运行Windows PE并Hook API:

```python
from qiling import Qiling

# 运行Windows恶意软件
ql = Qiling(["malware.exe"], "/path/to/rootfs")
ql.run()

# Hook Windows API
@ql.hook_api("kernel32.dll!CreateFileW")
def hook_create_file(ql, address, params):
    print(f"CreateFileW: {params['lpFileName']}")
    # 修改参数或返回值
    return 0  # 返回INVALID_HANDLE_VALUE

# Hook注册表操作,模拟持久化
@ql.hook_api("advapi32.dll!RegSetValueExA")
def hook_reg_set(ql, address, params):
    print(f"RegSetValue: {params['lpValueName']} = {params['lpData']}")
```

运行Linux ELF跨架构执行: `ql = Qiling(["arm_binary"], "rootfs/arm_linux", arch="arm")`。Qiling自动识别ELF头并设置正确的架构与模式。运行macOS Mach-O需提供对应rootfs与dyld。Qiling沙箱分析恶意软件: 拦截文件创建/写入、注册表修改、网络连接(C2回连),将行为记录到JSON报告。`ql.os.stats`输出系统调用统计,`ql.fs`可挂载自定义文件系统。Qiling的`on_syscall`钩子可重写任意系统调用语义,实现蜜罐式响应。

### 19.3 Unicorn Engine深度应用

Unicorn提供纯CPU指令级模拟,无OS开销,适合shellcode分析、解密例程还原、漏洞利用开发。

模拟执行shellcode:

```python
from unicorn import *
from unicorn.x86_const import *

# 模拟执行shellcode
mu = Uc(UC_ARCH_X86, UC_MODE_64)
mu.mem_map(0x1000, 0x1000)
mu.mem_write(0x1000, b"\x48\x31\xc0\x48\xff\xc0\x90\x90")  # xor rax,rax; inc rax; nop; nop
mu.reg_write(UC_X86_REG_RSP, 0x1000 + 0x800)

# Hook每条指令
def hook_code(uc, address, size, user_data):
    print(f"Executing: 0x{address:x}, size={size}")

mu.hook_add(UC_HOOK_CODE, hook_code)
mu.emu_start(0x1000, 0x1008)
print(f"RAX = {mu.reg_read(UC_X86_REG_RAX):#x}")
```

模拟执行解密例程: 加载恶意软件中的解密函数shellcode到模拟内存,设置寄存器(密钥指针、密文地址),执行后dump解密结果。结合`UC_HOOK_MEM_READ`/`UC_HOOK_MEM_WRITE`追踪内存访问,定位解密输出缓冲区。Unicorn支持上下文保存/恢复(`context_save`/`context_restore`),可用于分支探索。与angr配合时,Unicorn作为concrete executor执行具体路径,angr处理符号约束,实现混合符号执行(hybrid execution),显著缓解路径爆炸。

### 19.4 QEMU-user模式

QEMU-user模式在用户态翻译执行异架构二进制,无需完整系统镜像,是跨架构fuzzing与调试的标配。

```bash
qemu-arm ./binary                    # 运行ARM二进制
qemu-mips ./binary                   # 运行MIPS二进制
qemu-aarch64 -g 1234 ./binary        # 启动GDB stub等待连接
# GDB连接: target remote :1234
```

GDB stub支持断点、单步、内存读写,配合`gdb-multiarch`调试异架构程序。结合Frida: `frida -U -f qemu-arm -- ./binary`,在QEMU翻译层之上做API hook。QEMU-user的`-strace`输出系统调用日志,`-L`指定sysroot路径映射。2026年QEMU 9.x新特性: RISC-V模拟完善(支持RVV向量扩展)、ARM SME/MPAM支持、TCG插件框架增强(`-plugin`可加载覆盖率/内存分析插件,替代传统DBI)。QEMU-user常用于IoT固件分析,结合FirmAE或firmware-analysis-toolkit运行提取的squashfs根文件系统中的二进制。

### 19.5 模拟执行脱壳应用

模拟执行脱壳利用壳代码在模拟环境中自解密的特性,无需对抗反调试,即可获取原始代码。

```python
# Qiling自动脱壳通用模式
ql = Qiling(["packed.exe"], "rootfs")

# 等待OEP: 监控section hop
def check_oep(ql):
    pc = ql.reg.arch_pc
    # 检测执行从壳代码跳转到原始代码段
    if is_original_code_section(pc):
        ql.mem.dump(pc, original_size, "unpacked.bin")
        ql.emu_stop()

ql.hook_code(check_oep)
ql.run()
```

UPX脱壳: UPX在解压后跳转到OEP,可通过监控`jmp`/`ret`目标地址是否落在原始代码段(.text)判断OEP。ASPack等压缩壳通过异常处理(SEH)转移控制流,需模拟异常分发逻辑。VMProtect/Themida等虚拟化壳需先还原VM handler再提取原始指令,模拟执行可辅助VM dispatcher分析。模拟执行+内存dump = 通用脱壳方案: 记录所有内存写入,在OEP处dump整个可执行段。对比动态调试脱壳,模拟执行更隐蔽(无调试器痕迹、无硬件断点特征、可伪造反调试API返回值),但需处理壳的反模拟检测(如时间戳检查、特定CPUID模拟差异)。Qiling的`ql.os.exit_code`与异常回调可处理壳触发的故意崩溃。

---

