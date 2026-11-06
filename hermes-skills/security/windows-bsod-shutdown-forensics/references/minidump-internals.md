# Kernel small memory dump (minidump) 结构与手工解析

已实测于 Windows 11 24H2/25H2 x64（`C:\Windows\Minidump\*.dmp`，默认小内存转储 ~5MB）。
全部字段都是小端。

## 文件整体
```
[ DUMP_HEADER64 ] 固定 0x2000 字节（x64 小转储；x86 为 0x1000）
[ TRIAGE_DUMP64 ]  紧随其后
[ 各段数据 ]       驱动列表、字符串池、调用栈、未加载驱动、上下文/异常记录…
```

## DUMP_HEADER64（相对文件起点，绝对值）
| 偏移 | 类型 | 含义 |
|---|---|---|
| 0x00 | u32 | DumpType，**4 = 小内存转储(minidump)** |
| 0x38 | u32 | **BugCheckCode** |
| 0x40 / 0x48 / 0x50 / 0x58 | u64×4 | BugCheckParameter1..4 |

## TRIAGE_DUMP64（相对 TRIAGE 起点）
| 偏移 | 类型 | 含义 |
|---|---|---|
| 0x00 | u32 | ServicePackBuild |
| 0x04 | u32 | SizeOfDump（≠ 文件长度） |
| 0x08 | u32 | ValidOffset |
| 0x0C | u32 | ContextOffset |
| 0x10 | u32 | ExceptionOffset（异常记录） |
| 0x14 | u32 | MmOffset |
| 0x18 | u32 | **UnloadedDriversOffset**（该处有已卸载驱动的 ASCII 名） |
| 0x1C | u32 | PrcbOffset |
| 0x20 | u32 | ProcessOffset |
| 0x24 | u32 | ThreadOffset |
| 0x28 | u32 | **CallStackOffset** |
| 0x2C | u32 | **SizeOfCallStack**（u64 数组，逐项即可疑返回地址） |
| 0x30 | u32 | **DriverListOffset** |
| 0x34 | u32 | **DriverCount** |
| 0x38 | u32 | **StringPoolOffset** |
| 0x3C | u32 | **StringPoolSize** |
| 0x40 | u32 | BrokenDriverOffset |
| 0x44 | u32 | TriageOptions |

实测取值（可直接作健全性参照）：DriverListOffset=0x13378 / DriverCount=245 / StringPoolOffset=0x1bd48 / StringPoolSize=0x23c8 / CallStackOffset=0xffa8 / SizeOfCallStack=0x2538，TRIAGE 起始 0x2000，文件 5,037,883 字节。

## DUMP_DRIVER_ENTRY
- **stride 实测 0x90**（Win11 24H2/25H2 x64）；其它 build 见过 0x78 / 0x60 —— 解析失败时按此顺序换。
- 字段：
  | 偏移 | 类型 | 含义 |
  |---|---|---|
  | +0x00 | u32 | **NameOffset**：指向字符串池的文件偏移（个别 build 可能是相对 TRIAGE 的偏移，两种都试） |
  | +0x08 / +0x10 | u64 | 池内指针（非镜像地址，别当成 base） |
  | +0x18 | u64 | 入口点（可选，落在自身区间内） |
  | +0x38 | u64 | **DllBase**（页对齐） |
  | +0x48 | u32 | **SizeOfImage** |
  | +0x80 / +0x88 | u32 | CheckSum / TimeDateStamp（部分 build） |
- 列表顺序 ≈ 加载顺序，**第一项是 ntoskrnl.exe**，其后 hal.dll、kdcom.dll、symcryptk.exe… 可用来对表验偏移是否正确。
- 区间映射：`DllBase <= addr < DllBase + SizeOfImage`。命中多个时按条目顺序取第一个即可（正常无重叠）。

## 字符串池（StringPool）
重复结构：`u32 字符数` + `UTF-16LE 字符串` + 补齐到 **8 字节边界**；遇到 0 长度就跳过 4 字节继续（池里有非字符串片段）。
名字顺序与驱动列表一一对应（第 1 个 = all `ntoskrnl.exe`，第 2 个 = `hal.dll`…）。

## 自检清单（解析对不对）
1. `len(mods) == DriverCount`；
2. 名字全部解析出来（不是 `<off 0x…>`）；
3. 每个 `base` 落在 `0xffff000000000000` 以上的内核区且页对齐；
4. BugCheckParameter 中的指令地址落在其中一个模块区间内（本次 `ntoskrnl.exe+0x3e6265`）。
任一条不成立 → stride 或 NameOffset/基址字段偏移不对，换候选重试。

## 归因经验
- `0x1E KMODE_EXCEPTION_NOT_HANDLED` + `0xC0000005`：出错指令常落在 ntoskrnl，但**调用栈里第三方驱动的帧数**才是指认依据（实测反作弊驱动 15 帧 vs ntoskrnl 49 帧）。
- 栈里出现大量同一驱动的连续帧 = 该驱动的调用链是崩溃现场。
- 只有地址没有符号也能下结论；要函数名再上 WinDbg + 符号服务器。
