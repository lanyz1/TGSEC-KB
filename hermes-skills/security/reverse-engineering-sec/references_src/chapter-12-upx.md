## 12. UPX 脱壳与反脱壳对抗

> **2026 UPX 5.x新特性**：`memfd_create`支持SELinux Enforcing模式、`--unmap-all-pages`避免依赖`/proc/self/exe`、两步解压缩、RISC-V 64位支持(5.1.0)。攻击者通过修改UPX头部规避`upx -d`，需要多层脱壳策略。

### 12.1 标准UPX脱壳

```bash
# 标准UPX脱壳(格式公开可逆)
upx -d packed_binary.exe -o unpacked.exe

# UPX使用NRV2B/NRV2D/NRV2E或LZMA算法
# 压缩数据存储在UPX0/UPX1节中，解压器算法固定

# 批量脱壳
for f in samples/*.exe; do
    upx -d "$f" -o "${f%.exe}_unpacked.exe" 2>/dev/null
done

# ELF UPX脱壳
upx -d packed_elf -o unpacked_elf
```

### 12.2 修改UPX检测与修复

```
攻击者常见UPX头部篡改手法:
  1. 清空/修改AddressOfEntryPoint → 设为0，破坏静态分析
  2. 修改节名 → UPX0/UPX1重命名为随机字符串
  3. 修改UPX!魔术标记 → upx -d报错"file is modified/hacked/currupt"
  4. 修改校验和与版本字段 → 标准upx -d拒绝解压

检测修改UPX的方法:
  ┌─────────────────────────────────────────────────────┐
  │ 1. DIE(Detect It Easy)扫描                          │
  │    diec -a sample.exe                               │
  │    输出: UPX / 未知(被修改)                          │
  │                                                     │
  │ 2. 熵分析(pescanner.py)                             │
  │    节熵 >7.0 → 压缩/加密                            │
  │    原生x86代码熵值: 5.5-6.5                         │
  │                                                     │
  │ 3. UPX!标记计数验证                                 │
  │    PE/ELF要求 ≥ 2个UPX!标记(对应UPX0/UPX1)          │
  │   少于2个 → 被篡改                                  │
  │                                                     │
  │ 4. 节名模式检查                                      │
  │    搜索UPX0/UPX1或变体(如UPX., .UPX, 随机6字符)    │
  └─────────────────────────────────────────────────────┘

修复被修改UPX的步骤:
  1. 用010 Editor打开，定位UPX!标记位置
  2. 恢复被篡改的UPX!标记(搜索0x55505821)
  3. 恢复节名为UPX0/UPX1
  4. 恢复AddressOfEntryPoint到UPX1节内
  5. 再次执行 upx -d
```

### 12.3 动态脱壳 — OEP定位与内存转储

```python
# UPX动态脱壳: 当upx -d失败时的递进策略
# 工具: x64dbg + Scylla

"""
动态脱壳流程:
  1. x64dbg加载样本(不要运行)
  2. 在VirtualAlloc/VirtualProtect上下断点
     → UPX stub分配内存解压时会调用这些API
  3. 运行到断点后，在.text节下内存执行断点(hardware breakpoint on execution)
  4. 继续运行，当执行跳转到解压后代码时即到达OEP
  5. 用Scylla/OllyDumpEx dump内存
  6. Scylla重建IAT:
     a. IAT Autosearch → 自动搜索IAT位置
     b. Get Imports → 获取导入表
     c. Fix Dump → 指向dump文件，生成_SCY后缀修复文件
"""

# 模拟执行脱壳(Unipacker — 基于Unicorn)
# pip install unipacker
from unipacker.api import UnipackerAPI

# 自动脱壳: 模拟执行→检测解压完成→dump内存
api = UnipackerAPI("packed.exe")
api.unpack()  # 自动检测section hop或W+X转移
# Unipacker dump触发条件:
# 1. Section hop: 执行跳转到运行时写入的不同节
# 2. Write+Execute: 运行时写入区域变为可执行且执行进入
# 3. 壳特定逻辑(ASPack内置)

# Qiling脱壳(支持64位，Unipacker不支持PE32+)
from qiling import Qiling

ql = Qiling(["packed.exe"], rootfs="x8664_windows")
ql.run(timeout=180)  # 超时后从基址dump
# 从镜像基址dump SizeOfImage大小内存
# 注意: IAT未修复，需后续Scylla处理
```

### 12.4 UPX 5.x新特性对抗

```
UPX 5.x关键对抗机制:

1. memfd_create + SELinux兼容 (5.0.0):
   ├── 解压不写临时文件到磁盘，使用匿名内存文件
   ├── 基于文件系统监控的脱壳沙箱看不到中间产物
   └── 对抗: 内存dump(进程内存中直接提取)

2. --unmap-all-pages:
   ├── 完全避免读取/proc/self/exe
   └── 对抗: 监控/proc/self/mem或使用ptrace附加

3. 两步解压缩:
   ├── 解压流程拆分，per-PT_LOAD段独立处理
   └── 对抗: 更耐心的OEP等待+多次内存断点

4. RISC-V 64位支持 (5.1.0):
   ├── 新增linux/riscv64格式
   └── 对抗: 使用QEMU user-mode模拟RISC-V环境

5. MIPS r3000共享库 (5.1.1):
   └── 对抗: QEMU MIPS模拟环境
```

---

