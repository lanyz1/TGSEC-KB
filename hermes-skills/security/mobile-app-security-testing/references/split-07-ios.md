## 六、iOS 越狱检测绕过与证书固定绕过

### 6.1 越狱检测原理（识别维度）
```
1. 文件检测: /Applications/Cydia.app、/bin/bash、/etc/ssh/sshd_config、/usr/sbin/sshd、/usr/lib/substrate/
2. 写权限检测: 尝试在沙箱外（/private/ 等）写文件
3. 进程检测: Cydia、Sileo、frida-server等进程
4. 动态库检测: _dyld_image_count、检查已加载dylib是否含substrate/Frida
5. 系统调用: fork()/system() 是否被拦截、ptrace(P_TRACED) 反调试
6. 环境变量: DYLD_INSERT_LIBRARIES
```

### 6.2 越狱检测绕过
```bash
# 方案1: Objection一键
objection -g com.target explore
ios jailbreak disable

# 方案2: Frida定向hook（顽固应用）
```
```javascript
// jailbreak_bypass.js
if (ObjC.available) {
    // 屏蔽文件检测
    var NSFileManager = ObjC.classes.NSFileManager;
    var origExists = NSFileManager["- fileExistsAtPath:"];
    Interceptor.attach(origExists.implementation, {
        onEnter: function(args) {
            var path = ObjC.Object(args[2]).toString();
            this.blocked = /Cydia|substrate|ssh|Sileo|frida/i.test(path);
            if (this.blocked) console.log("[JB] block check: " + path);
        },
        onLeave: function(retval) { if (this.blocked) retval.replace(0); }
    });
    // 屏蔽 _dyld_image 检测
    var dyld = Module.findExportByName(null, "_dyld_image_count");
    Interceptor.attach(dyld, { onLeave: function(ret){ /* 若App遍历镜像名匹配 */ } });
    // 屏蔽 fork/access 等
}
```
```bash
# 方案3: 越狱App安装时使用 RootHide/Dopamine 等"隐身越狱"环境，从根源规避
# 方案4: 结合system-log分析（idevicesyslog）定位崩溃点再定向绕过
idevicesyslog | grep -iE "jailbreak|debug|frida|denied"
```

### 6.3 证书固定（SSL Pinning）绕过
iOS 证书固定实现层：`NSURLSession` delegate（`URLSession:didReceiveChallenge:`）、`SecTrustEvaluateWithError`（底层）、TrustKit 库、Alamofire/AFNetworking。
```bash
# 方案1: Objection一键
ios sslpinning disable

# 方案2: SSLKillSwitch2（Cydia插件,系统级patch,库不可用时的兜底）
# Cydia源: https://julioverne.github.io

# 方案3: Frida自定义hook（三层全覆盖）
```
```javascript
// ios_ssl_bypass.js
if (ObjC.available) {
    // 层1: NSURLSession delegate 挑战处理
    var NSURLSession = ObjC.classes.NSURLSession;
    // 层2: 底层 SecTrustEvaluateWithError
    var secTrust = Module.findExportByName(null, "SecTrustEvaluateWithError");
    if (secTrust) Interceptor.replace(secTrust, new NativeCallback(function(trust, error){
        return 1;   // 恒通过
    }, "int", ["pointer", "pointer"]));
    // 层3: TrustKit
    var TrustKit = ObjC.classes.TrustKit;
    if (TrustKit) { /* hook TrustKit.sharedInstance → 返回空/nil */ }
}
```

### 6.4 非越狱设备测试路径
```
1. 侧载调试版: 用开发者证书重签 + get-task-allow entitlement → 可LLDB调试
2. Frida Gadget: 将frida-gadget.dylib注入Frameworks并配置加载（重签安装）
3. 云端真机: Corellium（虚拟iOS真机，支持越狱/非越狱双模式，A9-A16）
4. 静态先行: 非越狱下优先做静态分析+class-dump+IPA审计，动态部分移步越狱环境
```

