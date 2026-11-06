## 五、iOS 深度逆向：Mach-O / LLDB / Objective-C Runtime

### 5.1 IPA 静态分析
```bash
# IPA解包（本质是zip）
unzip app.ipa -d output
# 结构: Payload/MyApp.app/{MyApp(二进制), Info.plist, embedded.mobileprovision, Frameworks/}

# Mach-O分析
otool -l Payload/MyApp.app/MyApp | grep -A4 LC_ENCRYPTION_INFO   # 是否App Store加密
otool -l Payload/MyApp.app/MyApp | grep -E "LC_SEGMENT_64|__TEXT|__DATA"  # 段信息
otool -L Payload/MyApp.app/MyApp                                   # 依赖动态库
nm -gU Payload/MyApp.app/MyApp                                     # 导出符号

# ObjC类导出
class-dump Payload/MyApp.app/MyApp > classes.h                     # 全类/方法/属性
# Swift: swift demangle / swift-class-dump / 直接Hopper/IDA/Ghidra

# Info.plist审计
/usr/libexec/PlistBuddy -c Print Payload/MyApp.app/Info.plist
# 关注: URL Schemes / App Transport Security(NSAllowsArbitraryLoads) / 权限描述 / 第三方SDK(如Apple Intelligence接入)

# 证书与权限
security cms -D -i Payload/MyApp.app/embedded.mobileprovision        # 查看entitlements
# 关注: keychain-access-groups(越权访问他人Keychain) / get-task-allow(可调试) / aps-environment
```

### 5.2 Objective-C Runtime 与 Method Swizzling
Objective-C 的运行时特性（动态消息分发）使其天生适合 Hook，也天然暴露攻击面：
```bash
# 运行时类/方法枚举
class-dump MyApp > classes.h          # 离线
# 在线枚举（已运行进程）
frida-ps -Ua
frida -U -n MyApp -l enum.js
```
```javascript
// enum.js: 枚举全部类/方法 + 追踪objc_msgSend
// 方案A: Frida ObjC API
if (ObjC.available) {
    for (var clsName in ObjC.classes) {
        var cls = ObjC.classes[clsName];
        if (/Login|Auth|Token|Key|Crypto|Network/i.test(clsName)) {
            console.log("[*] " + clsName);
            var methods = cls.$ownMethods;
            methods.forEach(function(m){ if (/secret|token|key|password|auth/i.test(m)) console.log("    " + m); });
        }
    }
}
// 方案B: hook objc_msgSend 全量消息追踪（性能开销大,定向用）
// var objc_msgSend = Module.findExportByName(null, "objc_msgSend");
// Interceptor.attach(objc_msgSend, { onEnter: function(args){
//     var sel = new ObjC.Object(args[1]).toString();
//     if (/token|key|decrypt/i.test(sel)) console.log("[msgSend] " + sel);
// }});

// 方案C: 直接hook指定方法（含参数读取）
var LoginVC = ObjC.classes.LoginViewController;
if (LoginVC) {
    Interceptor.attach(LoginVC['- storeCredentials:password:'<REDACTED>, {
        onEnter: function(args){
            var pwd = new ObjC.Object(args[3]);
            console.log("[*] password = " + pwd.toString());
        }
    });
}
```

**Method Swizzling（运行时方法交换）：**
```objc
// 传统tweak方式（Theos/Logos）: %hook + %orig
%hook NSURLSession
- (void)dataTaskWithRequest:(NSURLRequest *)request completionHandler:(id)handler {
    %orig;  // 执行原逻辑
}
%end
// 攻击面: 若App对第三方SDK的方法依赖swizzle做安全校验（如hook UITextField取明文），
// 攻击者同样可swizzle安全相关方法使其失效
```

### 5.3 LLDB 动态调试
```bash
# 越狱设备: 远程附加
# 1. 设备上启动debugserver（/Developer/usr/bin/debugserver，需codesign重签+get-task-allow）
debugserver 0.0.0.0:1234 -a MyApp
# 2. 电脑端转发并连接
iproxy 1234 1234 &
lldb
(lldb) process connect connect://localhost:1234

# 常用调试指令
(lldb) image list                      # 已加载镜像
(lldb) image lookup -n "-[LoginVC login:]"   # 按方法名查地址
(lldb) breakpoint set --selector login: # 按selector下断点
(lldb) po $r0                          # 打印第1参数(ObjC self)
(lldb) po (char*)$r1                   # 打印selector
(lldb) memory read --size 8 --count 16 0x100000000   # 读内存
(lldb) image dump symtab MyApp         # 导出符号表
(lldb) expression -l objc -O -- [UIApplication sharedApplication]  # 执行ObjC表达式
```
**LLDB 攻防要点：** 反调试（`ptrace`/`sysctl P_TRACED` 检测）→ hook `ptrace` 返回0；`get-task-allow` 缺失则无法调试（重签名处理）。

### 5.4 加密、签名与重打包
```bash
# App Store分发版: 二进制LC_ENCRYPTION_INFO加密 → 需解密（越狱环境dump解密后的内存镜像再修复）
# 或使用砸壳工具（frida-ios-dump / dumpdecrypted）
pip install frida-ios-dump
dump.py com.target.app    # 自动砸壳+导出

# 重签名（篡改后安装）
codesign -f -s "证书" --entitlements ent.plist Payload/MyApp.app/MyApp
# 注意: 重签名后Provisioning Profile的device名单/entitlements必须匹配
```

