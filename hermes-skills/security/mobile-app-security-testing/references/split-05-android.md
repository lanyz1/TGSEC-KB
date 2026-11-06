## 四、Android 加固脱壳全解析

### 4.1 加固壳识别
```bash
# 方法1: 查看Application类/入口
jadx-gui app.apk | grep "android:name=\".*Application\""   # 若指向壳类（如com.secneo.apkwrapper.ApplicationWrapper）
# 方法2: 查看assets/lib中的壳特征
unzip -l app.apk | grep -iE "secneo|ijiami|bangcle|qqpim|libprotect|libshell|libDexHelper"
# 方法3: 运行观察
adb logcat | grep -iE "decrypt|unpack|shell|protect"

# 常见壳特征速查
# 腾讯乐固: libshella-*.so / libshellx-*.so / assets/tosversion
# 360加固: libjiagu.so / libjiagu_64.so / assets/jiagu
# 梆梆加固: libSecShell.so / libDexHelper.so
# 爱加密: libexec.so / libexecmain.so / ijiami.dat
# 网易易盾: libnesec.so
# DexProtector: 自定义so + 强完整性校验
```

### 4.2 脱壳方法论（按强度递进）
```bash
# 方案1: 内存Dump（最通用，frida-dexdump）
pip install frida-dexdump
frida-dexdump -U -f com.target -o dump/    # dump运行内存中所有dex

# 方案2: FART主动调用脱壳（Android源码级,需要定制ROM）
# FART在DexFile中新增dumpMethodCode等方法，对加固后的类主动调用实现"函数级脱壳"
# 配合Frida增强: 枚举所有ClassLoader → 对动态加载的dex逐个调用fartwithClassloader
frida -H 127.0.0.1:1234 -F -l fart_all_classloaders.js
# 注: 局部变量的ClassLoader会被GC/不可枚举 → 需在创建点立即dump

# 方案3: BlackDex / DexExtractor（Xposed模块，拖拽式脱壳）
# 方案4: 定制ROM + frida脱壳机（对VMP壳前的多代dex整体处理）
```

**fart_all_classloaders.js（Frida 增强 FART 处理动态加载 dex）：**
```javascript
Java.perform(function () {
    var ActivityThread = Java.use("android.app.ActivityThread");
    Java.enumerateClassLoaders({
        onMatch: function (loader) {
            try {
                if (loader.toString().includes("BootClassLoader")) return;
                console.log("[*] fartwithClassloader -> " + loader);
                ActivityThread.fartwithClassloader(loader);
            } catch (e) { console.log("[-] " + e); }
        },
        onComplete: function () { console.log("[*] done"); }
    });
});
```

### 4.3 加固对抗（壳的反脱壳防御与破解）
2025 年主流壳已内置**反 Frida/反 FART/完整性校验**三重防御，实战流程：
```
1. 反调试识别: logcat观察崩溃时机 → 确认检测线程来源
2. 定位检测so: hook android_dlopen_ext观察哪个so被加载
3. 阻断检测线程: hook pthread_create，对来自壳so(pthread_create caller在libexec.so内)的线程创建直接返回0
4. 绕过完整性校验: 定位xxHash/SHA256/HMAC校验点 → "等式化替换"（让校验恒通过）
5. 匿名段转储: 从JNI_OnLoad→函数指针→匿名可执行段，结合/proc/self/maps dump未导出代码
6. 修复: IDA补区段、引android_arm64类型库，梳理RegisterNatives动态注册链
```
```javascript
// 核心对抗脚本: 阻断壳so创建检测线程 + 屏蔽dlopen路径暴露
var dlopen_ext = Module.findExportByName(null, "android_dlopen_ext");
if (dlopen_ext) Interceptor.attach(dlopen_ext, {
    onEnter: function(args){ console.log("[dlopen] " + args[0].readCString()); }
});

// 关键: 壳so（如libexec.so）创建的检测线程，直接拦截pthread_create
var pt = Module.findExportByName(null, "pthread_create");
var orig = new NativeFunction(pt, "int", ["pointer","pointer","pointer","pointer"]);
Interceptor.replace(pt, new NativeCallback(function(a,b,c,d){
    var caller = Process.findModuleByAddress(this.returnAddress);
    var mods = ["libexec.so","libexecmain.so","libprotect.so"];
    if (caller && mods.indexOf(caller.name) >= 0) {
        console.log("[BYPASS] block pthread_create from " + caller.name);
        return 0;   // 丢弃检测线程
    }
    return orig(a,b,c,d);
}, "int", ["pointer","pointer","pointer","pointer"]));
```

### 4.4 VMP / so 加固 / 反混淆
- **VMP（虚拟化保护）**：核心逻辑转译为自定义字节码 → 静态无解，需**内存 dump + Unidbg 模拟执行**（`com.github.zhkl0228:unidbg` 可在 PC 端模拟 ARM so 逐步 trace）
- **so 加固（UPX/自定义加密）**：`upx -d` 解压；自定义壳需 `init_array` 解密点分析
- **字符串加密/控制流平坦化**：Ghidra 插件（DeFlat）、`frida-dexdump` 后的代码修复
- **检测"是否已脱壳"的壳**：完整性校验（对 DEX/SO 做 hash/HMAC）→ 用 4.3 的等式化替换；对"内存段基址校验" → 复制干净 text 段并用干净副本地址过检

