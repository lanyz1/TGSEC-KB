### 22.1 iOS应用保护机制

iOS 应用逆向的第一道关卡是 Apple 的 FairPlay DRM。FairPlay 是 Apple 应用于 App Store 分发应用的 DRM 系统,对应用的 Mach-O 主二进制中的 `__TEXT` 段进行加密,加密密钥与设备 Apple ID 账户绑定,只有授权设备才能解密执行。加密层级为:**FairPlay 加密层 → Mach-O 加载层 → 代码执行层**,内核在 `exec_mach_imgact` 阶段调用 `cape->crproc` 完成 FairPlay 解密后才会跳转入口。

**脱壳原理**基于一个根本事实:解密后的代码必须以明文形式驻留在内存中才能被 CPU 执行,因此在运行时从进程内存中 dump 出 `__TEXT` 段即可获得解密后的二进制。具体做法是定位 Mach-O header,读取 `LC_ENCRYPTION_INFO` / `LC_ENCRYPTION_INFO_64` load command 获取加密段的文件偏移与大小,从内存中读取解密后的数据,再回填到原始 Mach-O 文件对应位置,即可生成脱壳后的 IPA。

2026 年 iOS 18/19 新增了**代码签名完整性检查**:内核在 page-in 时校验每个代码页的 SHA-256 哈希(硬编码在 `fairplay` 模块),单纯修改磁盘上的二进制会触发签名失败;此外 `AMFI` 引入了运行时 `proc_jailbreak` 标志检测,对越狱环境做了更严格的限制。这意味着传统脱壳工具必须适配新的内存布局与签名校验路径。

### 22.2 脱壳工具与方法

| 工具 | 原理 | 需要越狱 | 2026状态 |
|------|------|----------|----------|
| frida-ios-dump | Frida hook + 内存 dump | 是 | 活跃,主流首选 |
| Clutch | 直接调用 fairplay 解密接口 | 是 | 维护缓慢 |
| dumpdecrypted | 注入 dylib,dump 解密后 Mach-O | 是 | 老牌但仍可用 |
| FlexDecrypt | 通过 Frida 从内存提取 | 是 | 基本停更 |
| Azul | 基于 KFD 漏洞的免越狱脱壳 | 否 | 2026 新兴 |
| CrackerXI | 在线脱壳服务(需上传 IPA) | 否 | 服务可用 |

### 22.3 frida-ios-dump实战

frida-ios-dump 是当前最主流的脱壳工具,基于 Frida 运行时插桩,工作流清晰、自动化程度高。

```bash
# 1. 安装frida-ios-dump
pip3 install frida-tools
git clone https://github.com/AloneMonkey/frida-ios-dump

# 2. 列出已安装应用
python3 dump.py -l
# 输出: [pid] [bundle_id] [name]

# 3. 脱壳指定应用
python3 dump.py com.example.app
# 自动完成: 解密 → dump → 生成IPA

# 原理:
# a. Frida attach到目标进程
# b. 调用dlopen/dlsym定位Mach-O header
# c. 读取LC_ENCRYPTION_INFO获取加密段
# d. 调用mprotect修改权限, 读取解密后的内存
# e. 重建Mach-O: 用解密数据替换加密段
# f. 打包为IPA
```

脱壳流程的关键点:frida-server 必须以 root 运行在越狱设备上,且设备的 frida-server 版本要与主机 frida-tools 匹配(2026 年推荐 frida 17.x)。dump 时应用必须处于运行状态(已通过 FairPlay 解密),`dump.py -l` 列出的 `[pid]` 为 0 表示应用未启动,需先手动启动应用再执行 dump。生成的 IPA 可直接用 `class-dump-z`、`Hopper`、`Ghidra` 进行后续静态分析。

### 22.4 dumpdecrypted实战

```bash
# 1. 编译dumpdecrypted.dylib
git clone https://github.com/stefanesser/dumpdecrypted
cd dumpdecrypted && make

# 2. 设置DYLD_INSERT_LIBRARIES注入
# 在目标应用启动时注入:
cp dumpdecrypted.dylib /Library/MobileSubstrate/DynamicLibraries/

# 3. 启动应用, dylib自动dump
# 输出: /var/mobile/Documents/com.example.app.decrypted

# 原理: 
# - 在dylib构造函数中hook dlopen
# - 检测主二进制加载完成
# - 通过LC_ENCRYPTION_INFO确定加密段
# - 读取解密后的内存并写入文件
```

dumpdecrypted 的优势是不依赖 Frida,纯 dylib 注入方式更隐蔽,适合 Frida 被应用检测的场景;劣势是必须通过 `DYLD_INSERT_LIBRARIES` 或 MobileSubstrate 加载,iOS 9 之后系统对 `DYLD_INSERT_LIBRARIES` 有限制(受 `CS_HARD`、`CS_KILL`、`get-task-allow` 影响),实际多用 MobileSubstrate/Tweak 形式注入。

### 22.5 iOS逆向分析工具链

- **class-dump-z**:从 Mach-O 提取 Objective-C 类信息(类名、方法、属性、ivar),生成头文件,是 ObjC 应用逆向的第一步。
- **Hopper Disassembler**:macOS 原生反汇编器,反编译质量高,对 ARM64 支持优秀,适合交互式分析。
- **Ghidra + iRET**:Ghidra 开源免费且支持 iOS 二进制,iRET(iOS Reverse Engineering Toolkit)集成常用脚本。
- **objection**:基于 Frida 的运行时插桩框架,提供高层 iOS 探查 API。

```bash
# objection iOS分析
objection -g "com.example.app" explore

# 转储Keychain
ios keychain dump

# 监控方法调用
ios hooking watch class_method

# 绕过越狱检测
ios jailbreak disable
```

objection 还支持 `ios cookies get`、`ios nsuserdefaults get`、`ios pasteboard monitor` 等命令,覆盖了 iOS 应用数据存储探查的绝大多数场景。

### 22.6 iOS反逆向对抗(2026)

应用层反逆向日益严格,主要检测手段与绕过方法如下:
- **Jailbreak detection**:检查文件路径 `/Cydia`、`/Applications/Cydia.app`、`/private/var/lib/apt`、`/usr/sbin/sshd`;检查能否写入 `/private/`;`fork()` 测试(沙箱内 fork 失败)。绕过:Liberty Lite/Bypass、A-Bypass、Choicy(tweak 选择器,选择性加载 tweak)。
- **Frida detection**:扫描进程列表查找 `frida-server`;扫描默认端口 27042(D-Bus);检测 `frida-agent` 在内存中的特征字符串;检测 `gum-js-loop` 线程。绕过:修改 frida-server 名称、改用 `frida-gadget` 静态嵌入、使用 `objection` 的 anti-anti-frida 模式。
- **Code signing verification**:`SecCodeCheckValidity` 自校验签名,检测重签名;`dtfabric` 校验 entitlement。绕过:Hook `SecCodeCheckValidity` 强制返回 0。
- **Symlink-based jailbreak detection**:`lstat` 检查 `/Applications`、`/Library/Ringtones` 是否为符号链接(越狱后常为 symlink)。绕过:Hook `lstat` 返回正常值。
- **2026 越狱生态**:RootHide jailbreak(隐藏 root,反检测强)与 Dopamine(公开 root,功能全)并存;KFD-based 内核漏洞(iOS 16-17)成为免越狱利用新方向,Azul 脱壳工具即基于 KFD。



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-22-ios-frida-ios-dump-clutch-dump-02.md")`