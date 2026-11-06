## 13. 商业壳逆向 — VMP/Themida/Enigma

### 13.1 壳识别与难度分级

```bash
# Detect It Easy (DIE) — 当前最主流壳识别工具
# GitHub 10,200+ stars, 支持400+ packers
diec -a packed.exe

# 输出示例:
# VMProtect 3.x
# Themida 2.x
# Enigma Protector
# ASPack 2.x
# MPRESS
# NSPack
# PECompact
```

| 壳 | 难度 | 脱壳技术 | 自动化可行性 |
|----|------|----------|--------------|
| **UPX** | 简单 | `upx -d` 或 OEP+dump | 完全自动化 |
| **MPRESS** | 容易 | OEP+dump+IAT修复 | CAPE自动化 |
| **ASPack** | 中等 | 模拟+dump(Unipacker内置) | Unipacker自动化 |
| **Themida** | 困难 | VM分析+dump，LZSS算法识别 | 部分(模拟启发式) |
| **VMProtect** | 专家级 | VM字节码分析 | 困难(64位需Qiling超时dump) |
| **Enigma** | 困难 | 迭代脱壳(常与.NET混淆层叠) | 部分 |

### 13.2 VMProtect 3.6逆向

```
VMProtect 3.6 (2026)核心机制:
  ├── 完整代码虚拟化: 原始代码→自定义VM字节码
  ├── 滚动密钥寄存器(VKEY): 每条操作码用唯一密钥解密
  │   └── handler1用EDI中的密钥解密opcode1
  │       → 密钥经唯一变异 → handler2解密opcode2 → ...
  ├── 纯静态分析无法解密操作码流(必须动态执行)
  └── 64位: 需Qiling+Windows rootfs超时dump

VMP脱壳策略:
  32位:
  ├── Unipacker(Unicorn模拟) + section hop/W+X启发式dump
  └── 工具: Oreans UnVirtualizer(稳定性差但可完整还原)
  
  64位:
  ├── Qiling + Windows rootfs
  ├── ql.run(timeout=...) → 从基址dump SizeOfImage
  └── IAT未修复 → 需Scylla后续处理

  学术方法:
  └── DevMP: 虚拟指令提取(ACM 2026)
      ├── 自动提取VM handler语义
      ├── 重建原始控制流
      └── 适用于商业代码虚拟化混淆器
```

### 13.3 Themida逆向

```python
# Themida脱壳三步法
"""
Themida核心机制:
  - LZSS压缩 + 控制流平坦化(CFF)
  - 中央dispatcher替换自然控制结构
  - 状态变量选择下一个执行块

脱壳步骤:
  1. DIE确认壳 → 010 Editor查看EP数据 → 确定加密数据
  2. x64dbg断在EP → 反汇编解压代码 → 识别LZSS算法
     - LZSS特征: 滑动窗口+look-ahead buffer
     - 搜索LZSS解压循环模式
  3. 跟踪到OEP → dump + IAT修复(Scylla)

关键: 不运行程序直接解Themida加密代码段
  - 定位LZSS解压例程
  - 离线执行解压(无需在调试器中运行完整壳)
  - 适用于: 已知LZSS算法参数的情况
"""
```

### 13.4 多层壳迭代脱壳

```python
# 多层壳脱壳流水线(2026: anpa1200/Unpacker)
# pip install 1200km-unpacker

# 一条命令完成 detect → unpack → validate
# unpacker /path/to/sample.exe -o ./unpacked --timeout 180

# 典型三层壳结构:
# 商业crypter(MaaS) → 中间loader → 内部packer → 最终payload

# 脱壳器调度策略:
unpacker_dispatch = {
    'UPX': 'native_unpack',        # upx -d, 无模拟
    'ASPack': 'unipacker',          # Unicorn模拟从EP运行
    'Themida_32': 'unipacker',      # 模拟+启发式dump
    'VMProtect_32': 'unipacker',    # 模拟+启发式dump  
    'VMProtect_64': 'qiling',       # Qiling+rootfs, 超时dump
    'MPRESS': 'stub',               # 检测但未实现
    'Enigma': 'manual',             # 手动x64dbg+de4dot
    'unknown': 'qiling_generic',    # 通用Qiling模拟
}

# orcastor/unpack (Go库) — 多层递归脱壳
# unpack unpack -depth 10 packed.exe
# 自动检测每一层壳类型，逐层脱壳
# 支持层叠: ASPack → UPX，从外向内逐层剥离
```

### 13.5 反调试与反虚拟机对抗

```python
# 2026壳的反DBI(动态二进制插桩)检测

# 1. Frida检测绕过
# 壳检测: 内存扫描frida-agent.so、/data/local/tmp文件、库完整性校验
# 绕过:
Interceptor.attach(Module.findExportByName(null, 'fopen'), {
    onLeave: function(retval) {
        // 隐藏/proc/self/maps中的frida相关条目
    }
});

# 2. 反虚拟机检测绕过
anti_vm_checks = {
    '注册表': 'HKLM\\SOFTWARE\\VMware等hypervisor键',
    '虚拟驱动': 'vmhgfs.sys, VBoxGuest.sys文件存在性',
    '集成进程': 'vmtoolsd.exe, VBoxService.exe进程存在',
    'CPUID': '返回hypervisor名称到EBX/ECX/EDX',
    'I/O端口': 'VMware通信通道I/O端口0x5658',
}

# 模拟器(Unicorn/Qiling)不暴露真实hypervisor特征
# → 可绕过CPUID检测
# → 但复杂系统交互模拟不完整

# 3. 2026新兴对抗技术
emerging_anti_analysis = {
    '滚动XOR/AES-128-CTR字符串混淆': '字符串动态解密，静态不可见',
    '加盐SHA-1 API解析': '不使用标准IAT，哈希动态解析API',
    'Local Hollowing + AES': '自注入hollowing，永不写盘(RedSun技术)',
    'AMSI Ghosting': '绕过AMSI检测机制',
}
```

### 13.6 内存转储与IAT重建

```
脱壳后内存转储工具链:

  ┌──────────────────────────────────────────────────────┐
  │                    脱壳后处理                          │
  ├───────────────┬──────────────────────────────────────┤
  │   内存Dump     │  IAT重建                              │
  ├───────────────┼──────────────────────────────────────┤
  │ Scylla        │ Scylla (标准)                        │
  │ OllyDumpEx    │  - IAT Autosearch                    │
  │ PE-sieve      │  - Get Imports                       │
  │ hollows_hunter│  - Fix Dump → _SCY文件               │
  │ revdump       │ revdump (对齐dump+IAT重建)           │
  │               │ ImpREC (异常计数法)                   │
  └───────────────┴──────────────────────────────────────┘

验证脱壳成功:
  1. Ghidra/IDA中正确识别函数和字符串
  2. 熵值降低(如ASPack案例: 6.25→2.38, 文件33KB→176KB)
  3. 沙箱执行验证行为一致性
  4. 比较动态API调用与重建IAT导入
```

---

