<!-- archived from /root/.hermes/skills/security/shellcode-development/SKILL.md on 2026-10-21 -->

---
name: shellcode-development
description: |
  Shellcode 开发全流程：PIC 技术、PEB Walk、API 哈希解析、加载器架构、
  PE-to-Shellcode 转换、注入技术、编码/加密、跨平台（x64/ARM64/macOS）。
  授权红队载荷锻造、反弹 shell 编写、Donut/sRDI 转换、DripLoader 分块注入。
  触发词：shellcode、PEB walk、position-independent code、shellcode loader、
  PE-to-shellcode、Donut、sRDI、NtAllocateVirtualMemory、反弹 shell 汇编。
version: "1.0"
---

> 归档卡：原目录 `/root/.hermes/skills/security/shellcode-development`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/shellcode-development/…')`，不要相对 `references/legacy/` 解析。

# Shellcode 开发 — 红队载荷锻造

> 来源：claude-red `offensive-shellcode` 适配 + 本库 `edr-bypass-re` / `binary-pwn` 补充。
> 与 `edr-bypass-re` 互补：本卡侧重 **编写和打包**，EDR 卡侧重 **绕过检测和注入执行**。

## 开发流程

1. 确定目标平台（x86/x64，Windows/Linux/macOS）
2. 用 PIC 技术编写汇编
3. 提取二进制，控制环境测试
4. 消除坏字节 + 优化体积
5. 编码/加密绕过静态检测
6. 打包加载器 + 选择投递方式

---

## 核心概念

### 执行模式（Allocate-Write-Execute）

避免直接 `PAGE_EXECUTE_READWRITE`——分步操作：

```c
// 1. RW 分配
char *dest = VirtualAlloc(NULL, sz, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
// 2. 写入 shellcode
memcpy(dest, shellcode, sz);
// 3. 改权限为 RX
VirtualProtect(dest, sz, PAGE_EXECUTE_READ, &old);
// 4. 执行
((void(*)())dest)();
```

### PIC（Position-Independent Code）技术

| 方法 | 平台 | 说明 |
|------|------|------|
| Call/Pop | Windows | push 下一条地址，pop 到寄存器 |
| FPU `fstenv` | Windows | 保存指令指针 |
| SEH | Windows x86 | 异常处理器存 EIP |
| GOT / VDSO | Linux | 全局偏移表 / 内核共享对象 |

---

## Windows API 解析（PEB Walk）

定位 `kernel32.dll` 而无需导入表：

1. `gs:[0x60]`（x64）/ `fs:[0x30]`（x86）→ PEB
2. `PEB->Ldr.InMemoryOrderModuleList`：exe → ntdll → kernel32
3. 哈希比较模块名定位 kernel32
4. 解析 EAT（Export Address Table）
5. 找到 `GetProcAddress`，再解析 `LoadLibraryA`
6. 加载 `WS2_32.dll`，解析 Winsock 函数

```asm
; x64 PEB Walk 关键
xor rcx, rcx
mov rax, gs:[rcx + 0x60]    ; RAX = PEB
mov rax, [rax + 0x18]       ; RAX = PEB->Ldr
mov rsi, [rax + 0x20]       ; RSI = InMemoryOrderModuleList
lodsq
xchg rax, rsi
lodsq
mov rbx, [rax + 0x20]       ; RBX = kernel32 base
```

---

## Shellcode 加载器

### 加载器职责

- 环境验证 / keying（沙箱检测）
- Shellcode 解密
- 安全内存分配和注入
- 注入完成后退出

**推荐语言**：Zig（小、无运行时）、Rust（安全）、Nim、Go（注意运行时签名）

### 分配阶段

避免 RWX——两步法：
- `VirtualAllocEx` / `NtAllocateVirtualMemory` 分配 `RW`
- `ZwCreateSection` + `NtMapViewOfSection` 替代方案
- 写入后 `VirtualProtectEx` 改为 `RX`

### 写入阶段

- `WriteProcessMemory` / `NtWriteVirtualMemory`
- 拆分块，随机顺序写入
- 块间加延迟

### 执行阶段

EDR 重点监控——检查线程起始地址是否来自 image-backed 内存：

| 技术 | 说明 |
|------|------|
| `CreateRemoteThread` | 最吵，重度监控 |
| `NtSetContextThread` | 劫持挂起线程 |
| `NtQueueApcThreadEx` | APC 注入 |
| API 跳板 | 覆写函数序言 |
| ThreadlessInject | 无新线程 |

---

## PE-to-Shellcode 转换工具

| 工具 | 用途 |
|------|------|
| [Donut](https://github.com/TheWover/donut) | EXE/DLL → shellcode |
| [sRDI](https://github.com/monoxgas/sRDI) | DLL → PIC shellcode |
| [Pe2shc](https://github.com/hasherezade/pe_to_shellcode) | PE → shellcode |
| [Amber](https://github.com/EgeBalci/amber) | 反射式 PE packer |

**开源加载器**：ScareCrow、NimPackt、NullGate（间接 syscall + 垃圾写序列）、DripLoader（分块 RW + 直接 syscall + JMP 跳板）

---

## Shellcode 存储与隐藏

| 位置 | 风险 | 说明 |
|------|------|------|
| 硬编码 `.text` | 中 | 需重编译，存为 `RW/RO` |
| PE 资源 `RCDATA` | 高 | AV 最常扫描 |
| 证书表 | 低 | 保持签名 PE 有效 |
| 远程托管 | 变 | SharpShooter |

**证书表技术**（推荐）：在证书表中填充 shellcode 字节，更新 PE 头。只后门加载器 DLL。

> **Windows 11 24H2**：AMSI 堆扫描活跃。用 `PAGE_NOACCESS` 分配，原地解密，再改 `PAGE_EXECUTE_READ`。

---

## DripLoader 技术

1. 预留 64KB 块（NO_ACCESS）
2. 在池中分配 4KB RW 块
3. 随机顺序写入 shellcode 块
4. 改权限为 RX
5. 覆写 `ntdll!RtlpWow64CtxFromAmd64` 序言为 JMP 跳板
6. 所有调用走直接 syscall

---

## 跨平台注意事项

### Windows ARM64
- Syscall 用 `SVC 0`，ARM64 表在 `ntdll!KiServiceTableArm64`
- PAC 签署 LR——避免栈跳转或用 `PACIASP` 重签

### Linux 6.9+（eBPF Arena）
- `BPF_MAP_TYPE_ARENA` 映射可持有可执行内存
- 在 arena map 中藏 shellcode 块，通过 `bpf_prog_run_pin_on_cpu` 执行

### macOS（Signed System Volume）
- macOS 12+ 密封系统分区
- 用户空间：launch agents、dylib 劫持
- 内核持久化：创建密封快照，挂载 RW，注入，用 `kmutil` 重签

---

## 与本库其他 Skill 的关系

| 需求 | 走哪张卡 |
|------|----------|
| 编写/打包 shellcode | **本卡** |
| 绕过 EDR/AMSI/ETW 检测 | `edr-bypass-re` |
| Linux 二进制 pwn | `binary-pwn` |
| Windows 提权 | `windows-lpe` |
| 载荷锻造（完整 campaign） | `payload_forge.py` + `redteam-opsec` |
| 内存马 / WebShell | `webshell-stealth-persistence` |
