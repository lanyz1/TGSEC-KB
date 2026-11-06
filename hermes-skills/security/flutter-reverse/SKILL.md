---
name: flutter-reverse
description: "Flutter/Blutter 逆向 libapp.so, 含 arm32 支持补丁。"
---

# Flutter 应用逆向(Blutter)

用 Blutter 反编译 Flutter 应用的 libapp.so(Dart AOT snapshot),提取方法名→地址映射、对象池、反汇编、Frida 脚本。官方只支持 arm64/x64;**arm32(armv7)需要打补丁**——补丁链与根因见下文,详细移植记录见 `references/blutter-arm32-port.md`。

## 工作流程(已验证,arm64 路径稳定)

1. **输入准备**:APK 解包拿 `lib/armeabi-v7a/libapp.so` + `libflutter.so`(可选)。放同一输入目录。
2. **运行**:`CXX=g++-13 CC=gcc-13 python3 blutter.py --no-analysis <in_dir> <out_dir>`
   - `--no-analysis` 跳过 CodeAnalyzer,只输出方法名/地址/对象池——多数任务够用,且避免 AsmInstruction 全量移植
3. **流程链**:`blutter.py` → `extract_dart_info.py`(pyelftools 读 ELF 头拿 dart 版本/架构/flags)→ `dartvm_fetch_build.py`(cmake 编译 dartvm 静态库到 packages/)→ 本体 cmake(链接 dartvm + capstone)→ 二进制 `-i libapp.so -o outdir`
4. **产物**:`pp.txt`(对象池)、`objs.txt`(对象)、`asm/`(反汇编)、`ida_script/`、`blutter_frida.js`(Frida 脚本,可直接 hook)
5. **关键参数**:`-DTARGET_OS=android -DTARGET_ARCH=arm/arm64 -DCOMPRESSED_PTRS=0/1`(从 extract 的 flags 自动推断)

## arm32 支持补丁链(核心成果)

官方 Blutter 只支持 arm64|x64。arm32 需要 6 处修改(全部在跳板机 /tmp/blutter 下):

1. **`extract_dart_info.py`**:`arch = 'arm' if elf.header.e_machine == 'EM_ARM' else 'arm64'`
2. **dartvm CMakeLists 模板**(`/tmp/blutter/scripts/CMakeLists.txt`,**不是** build 目录里的!dartvm_fetch_build.py 每次运行用模板重新生成)→ 加 `TARGET_ARCH=arm` 分支 + `if (NOT "${TARGET_ARCH}" MATCHES "^(arm64|x64|arm)$")`
3. **`blutter/src/Disassembler_arm.h/cpp`**:移植 arm64 版。arm32 Dart 寄存器映射(AOT):R5=PP(对象池)、R10=THR(线程)、R11=FP、R7=DISPATCH_TABLE、R12=TMP、R13=SP、R14=LR、R15=PC。类外常量 `const Register THR = R10` 等不是枚举成员,引用写 SP 而非 SPREG
4. **`VarValue.h`**:无条件用 A64 → `namespace A64 = A32` 别名
5. **`blutter/CMakeLists.txt` defines**:加 `TARGET_ARCH_ARM=1`(本体编译宏)
6. **`ElfHelper.cpp`**:顶部 `#define TARGET_ARCH_ARM 1`(在 include 前,强制 elf.h 32 位结构布局)+ ei_class 检查按架构条件化

编译时遇到类型错(cs_mode cast、cs_reg typedef、duplicate case)逐个修,都是小问题。

## ⚠️ 致命根因:word 大小匹配(最重要)

**dartvm 库/本体在 x64 host 上编译,`ARCH_IS_64_BIT=1`(由编译器预定义宏 `__x86_64__` 决定,不是 TARGET_ARCH)→ word=intptr_t=8 字节。arm32 snapshot 是 4 字节 word 序列化 → 反序列化错位 → `Deserializer::GetCodeByIndex` 返回 null → SIGSEGV(`mov 0x8(%rax),%rax` rax=0)。**

- arm64 能直接跑:arm64 snapshot word=8 与 x64 host 一致
- **arm32 必须 `-m32` 编译 dartvm 库 + Blutter 本体(x86 32 位,word=4)才匹配**:
  - 装 `gcc-13-multilib g++-13-multilib`(Ubuntu 22.04,验证可用)
  - dartvm_fetch_build.py / blutter.py 的 cmake 调用加 `-DCMAKE_C_FLAGS=-m32 -DCMAKE_CXX_FLAGS=-m32`
  - capstone 需 32 位静态库(见下)
- 诊断手法:gdb `bt` 看栈(崩在 DartApp 构造→DartLoader::Load→Deserializer),`info registers` 看 rax=0 即 null 解引用

## capstone 32 位库(arm32 需要)

GitHub 直连常超时(跳板机环境)。**最快:pypi 清华镜像下载 sdist**:
```
pip download capstone==4.0.2 --no-binary :all: -i https://pypi.tuna.tsinghua.edu.cn/simple
```
sdist **没有 CMakeLists 但有完整 C 源码 + Makefile**:
```
make -j4 CAPSTONE_ARCHS="arm arm64 x86 x86_64" LIBARCHS="i386" CFLAGS="-m32"
make install PREFIX=/tmp/capstone32 ...
```
然后 blutter CMakeLists 用 `find_library(... PATHS /tmp/capstone32/lib NO_DEFAULT_PATH)` + `find_path(... include)` 替代 pkg_search_module。

## 操作坑(paramiko / 远端)

- **paramiko exec_command 会因 SSH 断开杀后台进程** → 用 `(setsid nohup script.sh > log 2>&1 < /dev/null &)`,且先 base64 把脚本写到远端再执行,避免引号嵌套
- heredoc 中 `${TARGET_ARCH}` 被本地 shell 展开 → 用 base64 传脚本
- 远端 Python 脚本的 `\r` 转义问题 → 先 `open(p,'rb').read().decode().replace('\r\n','\n')` 统一行尾再 replace
- 每次改完 C++ 源码,删掉 `bin/blutter_dartvm*` 二进制强制重编(blutter.py 只在文件不存在/版本不匹配时 rebuild)
- 32 位 ELF 的符号 value 是虚拟地址,LOAD 段 vaddr=0 时 value=文件偏移,`elf + value` 直接可用;`readelf -sW | grep kDart` 快速核对 4 个 snapshot 符号

## 验证要点

- snapshot 解析成功的标志:日志打印 `Dart version: x.y.z, Snapshot: <hash>, Target: android arm` + `flags: ... arm android no-compressed-pointers`
- 4 个符号缺一不可:`_kDartVmSnapshotData` / `_kDartVmSnapshotInstructions` / `_kDartIsolateSnapshotData` / `_kDartIsolateSnapshotInstructions`(dart_api.h 定义**带下划线前缀**)
- 出产物前先确认 outdir 非空(pp.txt 等)

## 状态说明

arm32 补丁链:ELF 解析/符号查找已 Python 复刻验证通过,word 大小根因已确认,-m32 方案已实施;dartvm -m32 全量重编 30-60 分钟,最终出产物待验证。若仍崩,优先查:snapshot 版本与 dartvm 库版本不匹配、COMPRESSED_PTRS 推断错误。
