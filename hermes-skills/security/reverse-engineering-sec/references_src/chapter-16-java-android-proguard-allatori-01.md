### 16.1 Java 字节码混淆技术

Java 字节码与 Android DEX 同样富含元数据,反编译极易还原源码,混淆与加固成为标配:

- **ProGuard**:Oracle 系开源混淆器,提供 shrink(压缩)、optimization(优化)、obfuscation(重命名为 `a`/`b`/`c`)、preverification(预校验 StackMapTable)。不加密字符串、不做控制流混淆,是最基础的保护层。
- **Allatori**:商业混淆器,增加字符串加密(XOR)、控制流混淆(假分支)、水印(类名/字段名嵌入版权)。解密器特征明显(静态方法 + int 参数)。
- **Zelix KlassMaster (ZKM)**:业界最强 Java 混淆器,支持控制流扁平化(方法体转 switch 状态机)、字符串加密(多重 XOR + 变换)、引用混淆(改变类继承结构),使 CFR/Procyon 反编译输出大量 `goto`。

| 混淆器 | 重命名 | 控制流 | 字符串加密 | 水印 | 成本 |
|--------|--------|--------|-----------|------|------|
| **ProGuard** | 强 | 否 | 否 | 否 | 免费 |
| **Allatori** | 强 | 弱 | XOR | 是 | 商业 |
| **Zelix KlassMaster** | 强 | 强(扁平化) | 多重 | 是 | 商业 |
| **DashO** | 强 | 中 | AES | 是 | 商业 |

### 16.2 国产 Android 加固壳全景(2026)

国产加固占据国内 90% 以上市场,技术从 DEX 整体加密发展到函数抽取、VMP 虚拟化:

| 加固壳 | 厂商 | 特征文件 | 核心技术 | 脱壳难度 | 主流脱壳工具 |
|--------|------|---------|---------|----------|------------|
| **360加固** | 奇虎 | `libjiagu.so` | DEX 整体加密 + 函数抽取 | 中 | BlackDex、FART、Youpk |
| **腾讯乐固** | 腾讯 | `libshell.so` | DEX 函数抽取(指令抽取) | 中 | BlackDex、FartAttack |
| **爱加密** | 爱加密 | `libijmdata.so` | DEX 加密 + SO VMP | 中高 | BlackDex、frida-dexdump |
| **百度加固** | 百度 | `libbaiduprotect.so` | DEX 加密 + 反调试 | 中 | BlackDex、FART |
| **阿里聚安全** | 阿里 | `libsgmainso-6.0.x.so` | DEX 加密 + SO 加固 | 中高 | Youpk、frida-dexdump |
| **梆梆安全/Bangcle** | 梆梆 | `libsecexe.so` | DEX 整体加密 + **VMP 虚拟化** | 高 | Youpk、定制 ROM |
| **娜迦/Nagain** | 娜迦 | `libnagain.so` | DEX 加密 + SO 壳 | 中 | BlackDex、FART |

技术分类:**DEX 整体加密**(360/百度/阿里)将 classes.dex 加密存储于 SO 或 assets,运行时解密到内存;**DEX 函数抽取**(腾讯乐固早期)保留 DEX 结构但抽取每个方法的指令体,运行时在 `dvmDexFileOpenPartial` 前还原;**VMP 虚拟化**(梆梆)将关键 Java 方法体替换为 native 解释器调用,Java 层仅留 native 桩。

### 16.3 DEX 脱壳核心技术

**内存 dump 脱壳法**是最通用的方案:DEX 无论怎么加密,最终必须在内存中以明文交给 ART/Dalvik 加载,在 DexFile 构造后从内存 dump 即可。

**Frida DEX dump** 扫描内存中的 DEX magic(`dex\n035\0`)定位并 dump:

```javascript
// frida DexDump 通用脱壳脚本核心(基于 frida-dexdump)
Java.perform(function() {
    var dexFiles = [];
    var dexMagic = '64 65 78 0a 30 33 35 00'; // "dex\n035\0"
    // 遍历所有可读内存区域,搜索 DEX magic
    Process.enumerateRanges('r--').forEach(function(range) {
        try {
            Memory.scanSync(range.base, range.size, dexMagic)
                .forEach(function(match) {
                    // 读取 DEX header 中 file_size(偏移 0x20, 4 字节)
                    var dexSize = match.address.add(0x20).readUInt();
                    if (dexSize > 0 && dexSize < 100 * 1024 * 1024) {
                        var dexData = match.address.readByteArray(dexSize);
                        dexFiles.push({addr: match.address, size: dexSize, data: dexData});
                        console.log('[+] DEX at ' + match.address + ' size=' + dexSize);
                    }
                });
        } catch (e) { /* ignore unreadable */ }
    });
    dexFiles.forEach(function(d, i) {  // 写入文件
        var f = new File('/data/data/' + pkg + '/dump_' + i + '.dex', 'wb');
        f.write(d.data); f.close();
    });
});
```

```bash
frida-dexdump -U -f com.target.app -o ./dump_dir   # 一键脱壳,输出 dump_dir/*.dex
```

- **BlackDex**:免 Root 脱壳工具,通过自身作为独立进程注入目标(利用 `app_process` 重打包),在 ART 加载 DEX 后 dump,适用于无 Root 设备。
- **FART**:基于定制 AOSP ROM,在 `art/method.cc` 的 `Execute` 入口主动调用所有类方法(强制触发指令还原),再 dump 内存中的 DEX。对函数抽取型壳(腾讯乐固)效果极好。
- **Youpk**:基于 Unikboot 的定制 ROM,在 ART 层 hook `DexFile::OpenMemory`,在 DEX 加载且指令还原后 dump,并修复 DEX header 中的 checksum/signature。

### 16.4 VMP 壳对抗

**梆梆 VMP** 将 Java 方法体替换为 native 解释器调用:原 `access_flags` 中 `ACC_NATIVE` 被置位,实际逻辑由 `libsecexe.so` 中的虚拟机执行自定义指令集。

**识别 VMP 化方法**:方法声明非 native 但方法体仅含 native 桩或空指令(`0x0140`);反编译后方法体为单条 `invoke-static` 调用某 native 函数;SO 中存在大段 switch-case 解释器(VM dispatch loop)。

**半自动还原**:Hook native 解释器 `interpret` 入口,记录每条虚拟指令执行前后 ART 虚拟寄存器(vreg)与 PC 变化,建立 `vopcode -> bytecode` 映射表,将解释器 trace 重构为 DEX 指令序列:

```javascript
// Hook 梆梆 VM 解释器入口,trace 虚拟指令
Interceptor.attach(Module.findExportByName('libsecexe.so', 'vm_interpret'), {
    onEnter: function(args) {
        this.pc = args[1].toInt32();  // 虚拟 PC
        console.log('[VM] pc=' + this.pc);
    },
    onLeave: function(retval) { /* 记录 PC 序列,离线分析 */ }
});
```



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-16-java-android-proguard-allatori-02.md")`