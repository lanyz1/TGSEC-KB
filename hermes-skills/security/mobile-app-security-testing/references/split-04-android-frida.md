## 三、Android 动态分析：Frida 全面对抗与检测绕过

### 3.1 Frida 基础与常用 Hook 矩阵
```bash
# 环境搭建（客户端-服务端版本必须一致）
pip install frida-tools
adb push frida-server-<ver>-android-arm64 /data/local/tmp/frida-server
adb shell "chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &"
frida-ps -U                     # 验证连接

# 两种启动模式
frida -U -f com.target -l hook.js          # spawn模式(冷启动,先于app代码执行)
frida -U -n com.target -l hook.js          # attach模式(热附加)
```

**核心 Hook 脚本模板（加密函数监控）：**
```javascript
// hook.js: 密码学函数全景监控
Java.perform(function() {
    // Cipher算法监控
    var Cipher = Java.use("javax.crypto.Cipher");
    Cipher.getInstance.overload("java.lang.String").implementation = function(algo) {
        console.log("[Cipher] algo=" + algo);
        return this.getInstance(algo);
    };
    Cipher.doFinal.overload("[B").implementation = function(input) {
        console.log("[Cipher] doFinal in=" + hexdump(input));
        var ret = this.doFinal(input);
        console.log("[Cipher] doFinal out=" + hexdump(ret));
        return ret;
    };
    // AES密钥/IV抓取
    var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
    SecretKeySpec.$init.overload("[B","java.lang.String").implementation = function(key, algo) {
        console.log("[AES-KEY] " + algo + " key=" + bytesToHex(key));
        return this.$init(key, algo);
    };
    // Base64日志
    var B64 = Java.use("android.util.Base64");
    B64.encodeToString.overload("[B","int").implementation = function(input, flags) {
        console.log("[B64] " + Java.use("java.lang.String").$new(input));
        return this.encodeToString(input, flags);
    };
});

function bytesToHex(bytes) { var h=""; for(var i=0;i<bytes.length;i++){h+=("0"+(bytes[i]&0xff).toString(16)).slice(-2);} return h; }
function hexdump(b) { var s=""; for(var i=0;i<b.length;i++){s+=("0"+(b[i]&0xff).toString(16)).slice(-2);} return s; }
```

**Objection（免root/快速评估）：**
```
objection -g com.target explore
android sslpinning disable
android root disable
android keystore list
android hooking list activities
```

### 3.2 Frida 特征检测手段（知己知彼）
现代加固/金融 App 普遍内置 Frida 检测，识别以下特征：

| 检测维度 | 检测原理 | 绕过方法 |
|---------|---------|---------|
| 文件扫描 | 扫描 `/data/local/tmp/` 等目录下 `frida-server` 文件名 | 重命名+迁移目录 |
| 进程扫描 | `ps -A` 匹配 `frida-server/frida-helper` 等进程名 | 重命名 |
| 端口检测 | `netstat` 检测 27042/27043 监听 | `-l` 指定随机端口 + adb forward |
| D-Bus 协议 | 遍历端口发 D-Bus 握手，匹配 `REJECT` 响应 | HLuda 魔改版/改通信协议 |
| 内存特征 | 扫描进程内存 `frida:rpc`、`gum-js-loop` 字符串 | HLuda（二进制改名） |
| `/proc/self/maps` | 检测 frida-agent 注入的匿名可执行段 | 注入方式改造（Zygisk Gadget） |
| ptrace 自占坑 | 启动早期 `ptrace(PTRACE_TRACEME)` 阻止附加 | spawn 模式 + hook ptrace 返回0 |
| 时序/线程检测 | Native 层监控线程周期性验证 | 定位并 patch pthread_create |

### 3.3 Frida 反检测实战绕过
```bash
# 方案1: 自定义端口 + USB转发（避开27042扫描）
adb shell "/data/local/tmp/fs -l 0.0.0.0:8888 &"
adb forward tcp:8888 tcp:8888
frida -H 127.0.0.1:8888 -f com.target -l hook.js
```
```javascript
// 方案2: hook ptrace 绕过TRACEME（spawn模式必做）
// 目标App在自己代码执行前调用ptrace(TRACEME)，Frida先进场后将其静默
var ptrace = Module.findExportByName("libc.so", "ptrace");
Interceptor.replace(ptrace, new NativeCallback(function(request, pid, addr, data) {
    console.log("[ptrace] blocked request=" + request);
    return 0;   // 假装成功，实际不执行 → App检测不到被附加
}, "long", ["int", "int", "pointer", "pointer"]));
```
```javascript
// 方案3: hook文件/进程/字符串检测（通用对抗）
Java.perform(function(){
    // 屏蔽 frida 关键字文件探测
    var File = Java.use("java.io.File");
    File.exists.implementation = function(){
        var p = this.getAbsolutePath();
        if (/frida|\.fs|agent/i.test(p)) { console.log("[BYPASS] File.exists: "+p); return false; }
        return this.exists();
    };
    // 屏蔽 Runtime.exec 中的 frida 探测命令
    var Rt = Java.use("java.lang.Runtime");
    Rt.exec.overload("[Ljava.lang.String;").implementation = function(cmd){
        if (cmd.join(" ").match(/frida|netstat|ps -A|/i)) { console.log("[BYPASS] exec: "+cmd); return null; }
        return this.exec(cmd);
    };
    // Native层: hook strstr/fopen 过滤frida特征（配合Interceptor）
});
```
```bash
# 方案4: Zygisk Frida Gadget（系统级注入，最难检测，2025实战主流）
# Magisk + LSPosed + Zygisk Frida Gadget模块(sucsand)，app无感知注入
# 方案5: HLuda（魔改版Frida，全量特征改名，对抗深度检测）
```

### 3.4 Root 检测与绕过
**检测手段：** `su` 二进制路径探测、`Runtime.exec("su")`、Magisk 包名（`com.topjohnwu.magisk`）探测、`test-keys` 构建标志、`/system` 挂载 rw、SELinux 状态、Play Integrity API（替代 SafetyNet 的硬件级认证）、`ro.debuggable` 属性。

**绕过组合拳：**
```
1. 设备侧: Magisk DenyList（对目标App隐藏root，推荐）+ MagiskHide Props Config（还原build属性）
2. Hook侧: 见3.3通用对抗脚本（File.exists/Runtime.exec/getPackageInfo）
3. API侧:  hook Play Integrity API回调 / 使用Play Integrity API测试工具伪造认证结果
4. 签名侧: 检测test-keys → 使用官方签名ROM或hook Build.TAGS
```
```javascript
// Play Integrity/SafetyNet 常见绕过点
Java.perform(function(){
    // 业务层自定义isRooted
    Java.enumerateLoadedClasses({onMatch:function(c){
        if (/root|integrity|safetynet/i.test(c)) console.log("[CLS] "+c);
    },onComplete:function(){}});
    // 常用: 找业务自实现的检测类，直接改返回值为false
});
```

### 3.5 模拟器检测与对抗
**检测维度：** `ro.kernel.qemu=1`、Build 属性（`sdk/goldfish/ranchu`）、QEMU 特征文件（`/dev/socket/qemud`、`libc_malloc_debug_qemu.so`）、传感器缺失（加速度计/陀螺仪无数据）、TelephonyManager 返回空（IMEI/IMSI）、CPU 指令特征（x86 vs arm64）。

**绕过矩阵：**

| 检测类型 | 绕过方法 |
|---------|---------|
| Build 属性 | 修改 `build.prop`（`ro.product.model=SM-G960F`）；Magisk 模块替换；hook `Build` 类 |
| QEMU 特征 | `ro.kernel.qemu=0`；删除/重命名特征文件；hook 文件访问 API |
| 传感器 | 启用虚拟传感器（Android Studio AVD）；hook `SensorManager` 伪造数据 |
| IMEI/设备ID | 模拟器设置自定义 IMEI；hook `TelephonyManager.getDeviceId()`；hook RIL |
| CPU 特征 | 使用 ARM 镜像（`arm64-v8a` 镜像而非 x86）从根源消除大部分特征 |
| 调试痕迹 | 关闭 `ro.debuggable`、移除 `adb` 默认开着的端口转发 |

```bash
# 检测当前环境是否被App标记（观察崩溃/功能隐藏）
adb logcat | grep -iE "emulator|qemu|root|jailbreak|integrity"
```

### 3.6 Native 层动态调试
```bash
# 方案A: IDA/Ghidra 远程调试（配合脱壳后的so）
adb push android_server /data/local/tmp/   # IDA的android_server
adb shell "chmod 755 /data/local/tmp/android_server && /data/local/tmp/android_server &"
adb forward tcp:23946 tcp:23946
# IDA → Debugger → Attach → Remote ARM Linux/Android Debugger → localhost:23946

# 方案B: lldb-server 调试
adb push lldb-server /data/local/tmp/
adb shell "/data/local/tmp/lldb-server platform --server --listen unix-abstract:///tmp/lldb &"

# 方案C: Frida Native Hook（常用）
frida -U -f com.target -l native_hook.js
```
```javascript
// native_hook.js: hook native导出函数与inline
// hook 导出
var func = Module.findExportByName("libnative.so", "native_check_sign");
if (func) {
    Interceptor.attach(func, {
        onEnter: function(args){ console.log("[native] check_sign called"); },
        onLeave: function(ret){ console.log("[native] check_sign ret=" + ret); ret.replace(0); }
    });
}
// hook 未导出函数: 先读IDA中偏移，base+offset 计算绝对地址
// var target = Module.findBaseAddress("libnative.so").add(0x12345);
```

