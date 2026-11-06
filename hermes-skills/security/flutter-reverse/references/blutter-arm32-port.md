# Blutter arm32 移植详细记录(2026-08, QQLink 钱包 armv7)

目标:反编译 armv7 Flutter 应用(QQLink, Dart 3.11.4, android arm, no-compressed-pointers)。
官方 Blutter 只支持 arm64|x64。以下是从零到根因确认的完整记录。

## 环境

- 跳板机 Ubuntu 22.04(x64),gcc-13/g++-13(PPA)
- Blutter 源码:/tmp/blutter(blutter.py + dartvm_fetch_build.py + blutter/ + dartsdk/)
- 输入:/tmp/qq_in/libapp.so(ELF32 ARM,DYN, 26MB),输出:/tmp/qq_out
- 编译命令:`CXX=g++-13 CC=gcc-13 python3 blutter.py --no-analysis /tmp/qq_in /tmp/qq_out`

## 修复链(按顺序)

### 1. extract_dart_info.py
`sed -i "34s/arch = 'arm64'/arch = 'arm' if elf.header.e_machine == 'EM_ARM' else 'arm64'/"`

### 2. dartvm CMakeLists 模板
**关键认知:dartvm_fetch_build.py 每次运行用 `/tmp/blutter/scripts/CMakeLists.txt` 模板重新生成 `dartsdk/v3.11.4/CMakeLists.txt`。直接改 build 目录里的没用——下次运行被覆盖!**
模板加 arm 分支(66-75 行区域)+ MATCHES 加 `|arm`。

### 3. Disassembler_arm.h(322 行)
- ToCapstoneReg/ToDartReg 双向映射
- A32::Register 类引用 dart::Register 类外常量(THR=R10、PP=R5、FP=R11 等是 `const Register xxx = Rxx` 类外定义,非枚举成员——写 SP/PC/FP 而非 SPREG/PCREG/FPREG)
- AsmInstruction(arm32 版,capstone cs_arm_op,内联实现)+ AsmIterator
- 注意:`--no-analysis`(NO_CODE_ANALYSIS 宏)下 DumpCode 只用 `Disassembler::Disasm`(capstone 循环),不需要完整 CodeAnalyzer;只有 Disassembler 系文件引用 AsmInstruction

### 4. Disassembler_arm.cpp
只写 RegisterNames 数据 + 全局 GetCsRegisterName + 构造函数(`cs_open(CS_ARCH_ARM, CS_MODE_ARM + CS_MODE_LITTLE_ENDIAN, &g_cshandle)`)。Disasm/析构在通用 Disassembler.cpp。

### 5. 编译错误逐个修
- `VarValue.h`:无条件 `A64::` → `namespace A64 = A32` 别名
- `Disassembler.h`:`cs_reg`(不存在)→ capstone 架构类型 typedef(cs_arm_reg)
- `DartDumper.cpp`:arm64_reg vs arm_reg 类型 → 宏分支或 uint32_t 显式化
- `Disassembler_arm.h`:ToCloneableDartReg duplicate case(ARM_REG_PC 重复)→ 删
- `cs_mode` cast:`CS_MODE_ARM + CS_MODE_LITTLE_ENDIAN` 是 int,cs_open 第二参要 (cs_mode) cast(注意实际代码是 3 参数版带 &g_cshandle)

### 6. ELF 32 位解析(ElfHelper.cpp)
- dart::elf 结构体用 `#if defined(TARGET_ARCH_IS_32_BIT)` 切换 32/64 布局
- Blutter 本体默认不定义 → 顶部 `#define TARGET_ARCH_ARM 1`(在 include pch.h 之前)
- ei_class 检查无条件 `!= ELFCLASS64` throw → 按 TARGET_ARCH_IS_32_BIT 条件化
- 符号名:dart_api.h 定义 `_kDartVmSnapshotData`(**带下划线**)。readelf 核对:`_kDartVmSnapshotInstructions` value=0x1188000 等
- 32 位 ELF:符号 value=虚拟地址,LOAD 段 vaddr=0 时 value=文件偏移,`elf + value` 直接用

### 7. 致命根因:word 大小不匹配(解决了前面所有 SIGSEGV)
- 现象:ELF 解析成功、dartvm 初始化打印版本后,`DartLoader::Load` 内 SIGSEGV
- gdb:崩在 `dart::Deserializer::GetCodeByIndex`,`mov 0x8(%rax),%rax` rax=0(null 解引用)
- 根因:**dartvm 库/本体在 x64 host 编译,ARCH_IS_64_BIT=1(__x86_64__ 编译器预定义,与 TARGET_ARCH 无关)→ word=8 字节;arm32 snapshot 按 4 字节 word 序列化 → 反序列化错位 → GetCodeByIndex 返回 null**
- arm64 无此问题:arm64 snapshot word=8 与 host 一致
- 解法:`-m32` 编译 dartvm 库 + Blutter 本体(须全套:gcc-13-multilib、32 位 capstone)

## 工具链坑

### paramiko 后台执行
- `exec_command(cmd)` 带 timeout 会因 SSH 断开杀进程 → 编译被掐
- 正确:`(setsid nohup /tmp/script.sh > /tmp/log 2>&1 < /dev/null &)`
- 脚本用 base64 传输:`echo <b64> | base64 -d > /tmp/script.sh && chmod +x`
- 后台脚本用 ps 轮询:`ps aux | grep -c '[b]lutter.py'`

### heredoc 转义
- `<<'EOF'` 里 `${TARGET_ARCH}` 会本地展开 → base64 传
- 远端 python 脚本内 `\r` 字面量 → 语法错误;先 `replace('\r\n','\n')` 再处理

### 编译管理
- blutter.py 只在 `bin/` 二进制不存在时才 rebuild → 改完 C++ 必须 `rm -f bin/blutter_*` 强制重编
- dartvm 库已编译则跳过 fetch_and_build → 改 dartvm 侧(C++/CMake)要删 `packages/libdartvm*.a` + build 目录

### capstone 32 位
- GitHub 直连超时 → pypi 清华镜像 `pip download capstone==4.0.2 --no-binary :all:`
- sdist 无 CMakeLists 但有 Makefile + 完整 C 源码
- `make CAPSTONE_ARCHS="arm arm64 x86 x86_64" LIBARCHS="i386" CFLAGS="-m32"`
- CMakeLists 用 find_library/find_path 指到 /tmp/capstone32,替代 pkg_search_module

## 验证方法

- Python 复刻 ElfHelper 查找逻辑(struct 手解析 ELF32 头/节表),确认 4 个 snapshot 符号及 value——**不用反复编译 C++ 即可验证解析逻辑**
- gdb:`gdb -batch -ex run -ex bt --args ./bin/blutter_* -i libapp.so -o out`
- 成功标志:日志 `Dart version: 3.11.4, Snapshot: <hash>, Target: android arm` + `flags: ... arm android no-compressed-pointers`;outdir 出现 pp.txt/objs.txt/asm/

## 备选路线(若 -m32 仍失败)

- qemu-user + 真 arm32 交叉编译 Blutter(arm-linux-gnueabihf,word=4 原生匹配)
- 换目标:已反编译的 arm64 版本(如 KeepBitPro)先行分析
- IDA/Ghidra 静态反汇编(无对象池标注,粗糙)
