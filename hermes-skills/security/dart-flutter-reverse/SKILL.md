---
name: dart-flutter-reverse
description: "触发:blutter,dart,libapp.so。Dart AOT逆向含arm32 -m32方案。"
---

# Dart/Flutter AOT 逆向(Blutter)

用 Blutter 解析 Dart AOT 快照(libapp.so),恢复类/方法/地址/对象池/字符串,定位加密链与关键业务函数。经 QQLink armv7 实战验证。

## 触发
- Flutter/Dart 应用逆向(libapp.so / app.so / snapshot)
- 需要方法名、方法地址、对象池字符串(加密算法、API 路径、密钥存储)
- armv7(arm32)snapshot 反编译

## 快速开始(arm64,官方直接支持)
```bash
python3 blutter.py <dir_含libapp.so> <out_dir>
```
输出结构(攻击面价值极高):
- `asm/` — 每个库的 .dart 方法清单:类/方法/**地址**/size(如 `uploadMnemonic // ** addr: 0x1b65734, size: 0x5a8`)
- `objs.txt` — 对象池(加密常量字符串、URL、类名)
- `pp.txt` — 对象池索引(搜 API 路径/闭包)
- `ida_script/` — IDA 符号导入脚本(addNames.py + ida_dart_struct.h)
- `blutter_frida.js` — Frida hook 辅助脚本

## arm32(armv7)支持:核心原理
**根因**:dartvm 库在 x64 host 编译时 ARCH_IS_64_BIT=1(word=8 字节),arm32 snapshot 是 4 字节 word 序列化 → 反序列化全错位 → Deserializer::GetCodeByIndex SIGSEGV(rax=0)。
**解法**:整条工具链(blutter.py 本体 + dartvm 库)用 `-m32`(x86 32 位,word=4)编译,匹配 arm32 snapshot。arm64 能跑是因为 word=8 一致。
完整编译配方 + 崩溃修复链见 `references/blutter-arm32-m32-recipe.md`。

## 关键 pitfall(全部踩过)
1. **CMakeLists 模板**:dartvm_fetch_build.py 每次从 scripts/CMakeLists.txt 模板重新生成 → 必须改模板文件,改生成文件会被覆盖。
2. **Only 64-bit compiler here**:模板里 `CMAKE_SIZEOF_VOID_P=4` 的 FATAL 检查必须删,否则 -m32 配置直接死。
3. **superCid 有符号陷阱**(最隐蔽):DartClass::superCls 临时存 superCid(小整数),post-process 用 `classes[(intptr_t)dartCls->superCls]` 映射。null-super 类(如 Object)会读出垃圾(dart 指针如 0xf3308041),作为有符号 intptr_t 是**负数**,`superCid > 0x100000` 有符号比较拦不住 → 必须 `(uintptr_t)superCid > 0x100000`。
4. **32 位 ObjectPtr 转换**:`(uint64_t)obj.ptr()` 在 32 位下二义性 → 触发 deleted operator bool → 改 `(uint64_t)(intptr_t)obj.ptr()`(64 位也兼容)。
5. **CodeAnalyzer 只有 arm64 版**:完整分析模式(不带 --no-analysis)在 arm32 编译失败(CodeAnalyzer_arm64.cpp 被无条件编入)→ 用 `--no-analysis`(NO_CODE_ANALYSIS)拿方法名/地址/对象池,再对目标函数 objdump/capstone 反汇编。方法地址 → 算 libapp.so 偏移 → 精确反汇编加密链。
6. **capstone 32 位**:GitHub 直连超时 → gitee 镜像秒下;cmake 必须 `-DCMAKE_C_COMPILER=gcc-13 -DCMAKE_CXX_COMPILER=g++-13`(默认 gcc-11 缺 multilib);依赖 libstdc++6:i386 + libicu-dev:i386;include 目录要同时加 `${CAPSTONE_INCLUDE}` 和 `${CAPSTONE_INCLUDE}/capstone`(代码里 `<capstone.h>` 和 `<capstone/arm.h>` 两种写法);链接用 `${CAPSTONE_LIB}` 不是裸 capstone。
7. **pip sdist 不能编 C 库**:capstone 的 sdist Makefile 是 Python 绑定用,缺 pkgconfig.mk/CMakeLists → 必须拿官方 repo(gitee 镜像)。

## 攻击面用法(钱包类 App 模板)
- 对象池字符串直接暴露:加密算法(RSA_ECB_PKCS1Padding/SM4/AES)、API 路径(/v1/common/getConfig)、密钥存储(FlutterEncryptedStorage/SharedPreferences)
- 典型链:getConfig 取服务端 pubKey → 客户端 BIP39 生成助记词 → RSA 加密 → uploadMnemonic 上传。**控制 getConfig 返回自设 pubKey 即能按原加密链注册拿明文助记词**
- blutter_frida.js + 方法地址 → 写 Frida hook 动态验证加密链
- 例:QQLink 钱包攻击面快照见 `references/qqlink-wallet-findings.md`

## 远程/自动化排障(跳板机套路)
- paramiko exec_command 读 stdout 会等 EOF 卡住 → `> /dev/null` 重定向 + 不读 stdout + 立即 close
- SSH 断开杀后台 → 必须写脚本文件 + setsid nohup
- 远端 Python 字符串替换:CRLF 文件先 `replace('\r\n','\n')`;heredoc 内 `\\t` 匹配字面反斜杠+t,要用 `\t`(制表符)
- 清缓存:packages 下 .a 在 `packages/lib/`(不是 packages/ 根),路径错会导致旧 64 位库被复用


---

## 外部库增量（2026-10-11 分享包）

## 容器化运行(Windows + Docker Desktop)—— 必读
**★ 核心坑:Docker Desktop 会把宿主的系统代理强制注入每个容器**,覆盖你 `-e http_proxy=` 的空值:
```
http_proxy  = http://host.docker.internal:10808   → 192.168.65.254(VM 网关,那里没有代理)
https_proxy = http://127.0.0.1:10808              → 容器内 localhost(更没有)
```
症状:apt/git/curl 全部 `Unable to connect to host.docker.internal:10808`,而宿主直连一切正常。用 `docker exec c env | grep -i proxy` 确认。
**修法(apt)**:
```bash
printf 'Acquire::http::Proxy "false";\nAcquire::https::Proxy "false";\n' \
  > /etc/apt/apt.conf.d/99noproxy
apt-get -o Acquire::http::Proxy=false -o Acquire::https::Proxy=false update
```
**修法(git/curl/python)**:`unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY` 后再跑;`git config --global http.proxy ''`。
**Debian 镜像坑**:`debian:latest`(=13 trixie)的源在 `/etc/apt/sources.list.d/debian.sources`(deb822 格式),`cat > /etc/apt/sources.list` 写旧格式**不生效** → `apt update` 静默成功但 `Unable to locate package`。先 `cat /etc/apt/sources.list.d/debian.sources` 看清格式,或直接用 Kali 镜像(源在 `/etc/apt/sources.list`)。
**Kali 源提速**:`http.kali.org` 国内极慢(>1 小时没跑完)→ 换 `http://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main contrib non-free non-free-firmware`。

## 附:同批 APK 的 jadx 并行作业(Flutter 包常需与 Kotlin 包对比)
- **jadx `--export-gradle` 会死锁**:实测 3 个进程 74 线程空转、30 秒 CPU 仅 +0.11s、连输出目录都不建。**不要用它**。
- **可靠姿势**:`java -Xmx14g -jar jadx-all.jar -d <out> --no-imports -j 16 <apk>`,日志重定向到文件(别 `| tail`,会缓冲看不到进度)。
- **速度预期**:15 MB 原生 APK = **23,745 类 / 154,418 方法 / 374 万指令**,加载本身就要 5+ 分钟;单个包预留 20-40 分钟。多个包**串行**跑,并行会互相抢 CPU 反而更慢。
- **先测包体**:`find . -name '*.apk' -size -1k` 找 0 字节/残缺下载件,别让 jadx 在坏包上空转(`zip END header not found`)。

10. **★ jadx 必须用 `bin/jadx.bat`（官方 wrapper）,绝不能 `java -jar jadx-*-all.jar`**:直启会在日志打完 `Found 0 classes in disk cache` + `Found new jadx version` 后**死锁**——CPU 归零、74 个线程空转、输出目录都不建,任何参数都救不回来(`-j 1`/`--no-imports`/ASCII 路径/屏蔽代理/JDK21 全无效)。换 `bin/jadx.bat` 同参数立刻跑通(8602 类 → 11,529 个 `.java`)。根因是 wrapper 里的 JVM 模块参数(`--add-opens` 等),不是 JDK 版本。排查手法:测 40 秒 CPU 增量,~0.15s 即死锁而非慢。
11. **apktool 是 jadx 之外最可靠的原生工程路径**:`java -jar apktool.jar d -f --no-debug-info -o <out> <apk>` 直出 `AndroidManifest.xml`(明文)+`res/`(明文 XML)+`smali/`+`kotlin/`+`apktool.yml`,可 `apktool b` 重打包,已在 7900 万行级别的包上验证(8295 smali/1481 res)。jadx 挂了就拿它兜底。

12. **★★ 绕开 Blutter 的 `git clone dartsdk`（GFW 破坏 git 智能 HTTP 分帧的通用解法）**:
    GFW 下 `git clone https://github.com/...` 必报 `fatal: expected flush after ref listing`（git 协议的 chunked 分帧被破坏），但**普通文件下载完全正常**。所以不要跟 git 死磕，改用 tarball 直供源码：
    ```bash
    # ① 取源码（codeload 单次 GET，不走 git 协议）
    curl -sL -o dartsdk.tar.gz https://codeload.github.com/dart-lang/sdk/tar.gz/refs/tags/3.12.2
    tar -xzf dartsdk.tar.gz          # 顶层目录名 sdk-<ver>
    # ② 把 Blutter 要的三个目录放进它期望的位置
    DST=<blutter>/dartsdk/v<ver>
    cp -r sdk-<ver>/{runtime,tools} $DST/ && mkdir -p $DST/third_party
    cp -r sdk-<ver>/third_party/double-conversion $DST/third_party/
    ```
    **③ 关键洞察——`runtime/vm/version.cc` 是「本地生成」的产物，不是仓库文件**:
    `dartvm_fetch_build.py:checkout_dart()` 的逻辑是
    `if clonedir 存在 且 version.cc 不存在 → rmtree(clonedir)` 然后 `git clone --sparse` → 再跑 `tools/make_version.py` **生成** version.cc。
    ⇒ 只要**预先自己生成 version.cc，整个 clone 分支被无条件跳过**（`if not os.path.exists(clonedir)` 为假），Blutter 直接进 cmake 阶段。
    **④ version.cc 里的 `SNAPSHOT_HASH` 必须用目标 APK 的真值**（错了 Dart VM 拒绝加载快照）。先用 Blutter 自带的纯 Python 解析器取（不需要 git）：
    ```bash
    python3 -c "import sys;sys.path.insert(0,'<blutter>');\
    from extract_dart_info import extract_dart_info;\
    print(extract_dart_info('libapp.so','libflutter.so'))"
    # → ('3.12.2', 'ace654289f5abc240509fc941453ebc5', [...flags...], 'arm64','android')
    ```
    **⑤ Blutter 自带的 `scripts/dartvm_make_version.py` 会调 `git rev-parse`/`git log`** → 造一个最小 git 桩放 `/usr/local/bin/git`：
    ```sh
    #!/bin/sh
    case "$1" in
      rev-parse) echo "<10位hash>" ;;
      log)       echo "Tue Jun 9 16:11:00 2026 +0800" ;;
      *)         exit 0 ;;
    esac
    ```
    然后 `python3 scripts/dartvm_make_version.py $DST <snapshot_hash>` → 生成带真 hash 的 version.cc。
    **⑥ 绝不能删 `$DST`** —— 一删 Blutter 就回去走 git clone。做完先 `cp version.cc version.cc.bak`。
    **⑦ 别忘依赖**:Blutter 的 cmake 要 `find_package(ICU)`，缺了报 `Failed to find all ICU components (missing: ICU_INCLUDE_DIR ICU_LIBRARY uc)` → `apt-get install -y libicu-dev liblzma-dev pkg-config`。

13. **★ `docker exec` 剥离代理必须用 `-e` 显式传空值，`export -n` 是假动作**:
    `export -n http_proxy` **只去掉 export 标志、变量还在**，apt/curl 照样读到 → 仍然 `connecting to 127.0.0.1:10808` 失败。
    正确写法：`docker exec -e http_proxy= -e https_proxy= -e HTTP_PROXY= -e HTTPS_PROXY= -e NO_PROXY='*' <c> bash -c 'unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY; apt-get install ...'`。
    只写 `/etc/apt/apt.conf.d/99noproxy` **不够**（覆盖不了环境变量路径）。

14. **★★ 跳板池是 GitHub 的高速出口（12–14 MB/s），比容器快 ~4000 倍**:
    容器内 `github.com` ≈ 3 KB/s、宿主代理 200 但 body 0 B/s，而**阿里云跳板机实测 12–14 MB/s**（`8.133.234.161` 13.4 MB/s / `120.76.176.155` 12.9 / `116.62.103.69` 12.2 / `47.108.106.137` 11.6 / `101.200.225.184` 11.5）。
    **注意**：同批测试里 `1.1.1.1:443` 全 DEAD，容易被误判成「整池国外出站已死」——**实际上只是 Cloudflare DNS 被 GFW 拦，GitHub/codeload 完全可用**。别凭 1.1.1.1 下结论。
    **套路**：`paramiko` 连跳板机 → 远端 `curl` 拉大文件 → `sftp get` 回本机（回传实测 27 MB/s）。36.5 MB 的 Dart SDK tarball 全程 4.2 秒。
    取件/回传脚本模板见 `references/blutter-gfw-bypass.md`。
