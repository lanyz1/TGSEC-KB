# Blutter arm32 -m32 编译配方(经 QQLink armv7 Dart 3.11.4 实战验证)

## 环境
- Ubuntu 22.04,主用跳板机(gcc-13 PPA 已装,默认 gcc-11 缺 multilib)
- 目标:armv7 libapp.so(Dart 3.11.4, AOT, no-compressed-pointers)
- Blutter 源码 /tmp/blutter(blutter.py + dartvm_fetch_build.py + scripts/CMakeLists.txt 模板 + blutter/src)

## 步骤
1. i386 支持:`dpkg --add-architecture i386` + `apt update`
2. 32 位依赖:`libstdc++6:i386 libgcc-s1:i386 libicu-dev:i386`(装完 g++-13 -m32 才可链接;ICU 缺失会 FindICU 失败)
3. patch `dartvm_fetch_build.py`:cmake_dart 加 `-DCMAKE_C_FLAGS=-m32 -DCMAKE_CXX_FLAGS=-m32`
4. patch `blutter.py`:同样加 -m32 flags
5. patch `scripts/CMakeLists.txt` 模板:删 `if(${CMAKE_SIZEOF_VOID_P} STREQUAL 4) message(FATAL_ERROR "Only 64-bit compiler here")`
6. capstone 32 位静态库:
   - GitHub 直连超时 → `https://gitee.com/mirrors/capstone` zip(秒下)
   - `cmake -DCMAKE_C_COMPILER=gcc-13 -DCMAKE_CXX_COMPILER=g++-13 -DCMAKE_C_FLAGS=-m32 -DCAPSTONE_BUILD_STATIC=ON -DCAPSTONE_BUILD_SHARED=OFF -DCMAKE_INSTALL_PREFIX=/tmp/capstone32`
   - 注意:pip sdist 的 Makefile 是 Python 绑定用,缺 pkgconfig.mk/CMakeLists,不能直接编 C 库
7. patch `blutter/CMakeLists.txt`(注意:此文件在 blutter/ 子目录,与模板不同):
   - `set(CAPSTONE32_ROOT /tmp/capstone32)` + `find_library(CAPSTONE_LIB ...)` + `find_path(CAPSTONE_INCLUDE ...)`
   - `include_directories(AFTER ${CAPSTONE_INCLUDE} ${CAPSTONE_INCLUDE}/capstone)` — 两个都要(源码两种 include 写法)
   - `target_link_libraries(${BINNAME} PRIVATE ${DARTLIB} ${CAPSTONE_LIB})` — 必须用变量,裸 capstone 会找系统 64 位 .so
8. 清缓存重编:
   - `.a` 在 `packages/lib/libdartvm*.a`(不是 packages/ 根!路径错 = 旧 64 位库被复用 → find_package 报 64bit)
   - 删 `bin/blutter_*`(本体重编)+ `build/`
9. 运行:`CXX=g++-13 CC=gcc-13 python3 blutter.py --no-analysis <in_dir> <out_dir>`
   - CMake 参数:`-DTARGET_OS=android -DTARGET_ARCH=arm -DCOMPRESSED_PTRS=0`

## 崩溃修复链(每个都是推进,按序)
| 症状 | 根因 | 修复 |
|---|---|---|
| Deserializer::GetCodeByIndex SIGSEGV (rax=0, ecx=0xf3308041 索引) | x64 host word=8 vs arm32 snapshot word=4 序列化错位 | -m32 全链重编 |
| find_package(${DARTLIB}) 报 "64bit" | 旧 64 位 .a 缓存没删 | 删 packages/lib/ 下 .a |
| FindICU 失败 | 无 32 位 ICU | apt libicu-dev:i386 |
| capstone.h 找不到 | include 路径缺 capstone/ 子目录 | 两个 include 目录 |
| DartDumper.cpp:614 ObjectPtr::operator bool deleted | 32 位 (uint64_t) 转换二义性 | `(uint64_t)(intptr_t)obj.ptr()` |
| 链接 "cannot find -lcapstone" | 链接用裸名 | `${CAPSTONE_LIB}` |
| loadFromClassTable SIGSEGV @ `mov (%esi,%ecx,4),%ecx` | superCid 垃圾(有符号负数) | `(uintptr_t)superCid > 0x100000` |
| CodeAnalyzer_arm64.cpp 编译错 | 官方无 arm32 CodeAnalyzer | `--no-analysis` + 对目标地址 objdump |

## 调试技巧
- AddClass 里加 `fprintf(stderr, "[DBG] ... %p super=%p ptr=%p id=%u name=%s", dartCls, dartCls->Parent(), (void*)(uintptr_t)dartCls->Ptr(), ...)` → 直接暴露字段错位与垃圾值。注意 superCls 是 private,用 Parent();Ptr() 转 void* 需经 uintptr_t
- gdb:`bt` + `x/8wx $eax` + `x/s <name_ptr>` 确认崩溃对象;0xf3...41 末位 0x41 = kHeapObjectTag → 是 dart 堆指针不是垃圾
- objdump PIE 偏移:运行地址 - 基址(基址 = 崩溃地址 - 函数内偏移,或 info proc mappings)
- 反汇编对象池里 `cmp $0x100000` 确认防御行是否真的编译进去(优化后 jle = 有符号比较,unsigned 比较会是 jbe)

## 关键源码位置(Blutter + dartvm 3.11.4)
- `runtime/vm/app_snapshot.cc` — GetCodeByIndex 定义处
- `runtime/platform/elf.h` / `blutter/src/ElfHelper.cpp` — 32 位 ELF 需强制 `TARGET_ARCH_IS_32_BIT` + 放宽 ei_class
- `blutter/src/DartClass.cpp` 构造函数 — superCls 临时存 superCid 逻辑(约 45-55 行)
- `blutter/src/DartApp.cpp` loadFromClassTable — post-process `classes[(intptr_t)superCls]`
- `packages/include/dartvm*/vm/tagged_pointer.h` — ObjectPtr 转换操作符(32 位只有 operator int/unsigned int,无 long long)
