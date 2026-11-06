## 二、Android 静态逆向与组件攻击面

### 2.1 APK 解包与基础静态分析
```bash
# 解包与反编译
apktool d app.apk -o output          # 资源+smali反汇编
jadx -d output_src app.apk           # Java反编译（推荐jadx-gui）
unzip -l app.apk                      # 查看结构

# 查看签名/证书
keytool -printcert -jarfile app.apk

# Native库清单
ls lib/arm64-v8a/ lib/armeabi-v7a/   # .so文件 → Ghidra/IDA分析

# 快速敏感信息扫描
grep -rE "(api[_-]?key|secret|password|token|aws_access|AKIA)" output_src --include="*.java" -i
strings lib/arm64-v8a/*.so | grep -iE "api_key|secret|BEGIN RSA|private"
```

### 2.2 AndroidManifest.xml 深度审计
```xml
<!-- 高危配置检查清单 -->
<application
    android:debuggable="true"          <!-- 可调试 → adb调试器直连 -->
    android:allowBackup="true"         <!-- 可备份 → adb backup导出数据 -->
    android:usesCleartextTraffic="true"><!-- 明文HTTP -->
<application android:networkSecurityConfig="@xml/network_security_config">
<!-- 关注: 自定义network_security_config是否放行user证书（测试发现pinning失效点） -->

<!-- 组件导出 -->
<activity android:exported="true">     <!-- 任意App可启动 -->
<service android:exported="true">      <!-- 任意App可绑定/启动 -->
<receiver android:exported="true">     <!-- 任意App可发广播 -->
<provider android:exported="true" android:grantUriPermissions="true">
<!-- 关注: 导出的Provider + grantUriPermissions → URI授权绕过 -->

<!-- 权限滥用 -->
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW"/> <!-- 悬浮窗(钓鱼/Agent攻击) -->
<uses-permission android:name="android.permission.BIND_ACCESSIBILITY_SERVICE"/> <!-- 无障碍(截取输入) -->
```
```bash
# 组件攻击验证
adb shell am start -n com.target/.ExportedActivity --es key "payload"
adb shell am startservice -n com.target/.ExportedService
adb shell am broadcast -a com.target.ACTION --es data "malicious"
adb shell content query --uri content://com.target.provider/data
```

### 2.3 Content Provider 攻击面（重点深化）
Content Provider 是 Android 中常被低估的攻击面，可导致**任意文件读取、SQL注入、越权数据访问**：
```bash
# 枚举导出的Provider
adb shell dumpsys package com.target | grep -A5 "ContentProvider"
# 或反编译后从Manifest提取

# SQL注入（投影/选择参数注入）
adb shell content query --uri content://com.target.provider/users \
  --projection "* FROM users--" 
adb shell content query --uri content://com.target.provider/users \
  --where "1=1 OR 1=1"

# 文件读取（provider实现openFile时）
adb shell content read --uri content://com.target.provider/../../../../etc/hosts
# 路径穿越测试: 尝试 ../ 或 file:// 组合

# grantUriPermission 绕过（授权URI被转发给不可信组件）
adb shell am start -n com.target/.VictimActivity -e "uri" "content://com.target.provider/secret"
```

**Provider 漏洞挖掘要点：** `query()/insert()/update()/delete()/openFile()/call()` 六个入口全测；关注 `openFile` 是否校验文件名（路径穿越）、`call` 方法是否可被外部触发任意函数、返回 CursorWindow 是否过度暴露字段。

### 2.4 插件化与动态加载攻击面
插件化架构（宿主+插件）是国产应用常见形态，引入额外攻击面：
- **动态加载 DEX/APK**：`DexClassLoader/PathClassLoader` 从 `files/`、`/sdcard` 加载外部代码 → 检查加载源是否可被篡改（文件替换→代码执行）
- **双亲委派绕过**：自定义 ClassLoader 破坏委派模型 → 类冲突、恶意类抢先加载
- **插件签名校验缺失**：仅校验宿主角色的插件可被替换 → 植入恶意插件
- **加固场景叠加**：动态加载的 DEX 不在双亲委派链上，FART 等脱壳工具默认不覆盖 → 需用 Frida `Java.enumerateClassLoaders` + `fartwithClassloader`（见第四章）

```bash
# 检测动态加载点
grep -rE "DexClassLoader|PathClassLoader|loadDex" output_src --include="*.java"
# 监控运行时加载
frida -U -f com.target -l - <<'EOF'
Java.perform(function(){
  var DCL = Java.use("dalvik.system.DexClassLoader");
  DCL.$init.overload('java.lang.String','java.lang.String','java.lang.String','java.lang.ClassLoader')
     .implementation = function(path,odex,lib,parent){
       console.log("[DEX] loaded: " + path);
       return this.$init(path,odex,lib,parent);
     };
});
EOF
```

### 2.5 深链（Deep Link）与 Intent 攻击面
- **深链劫持**：自定义 scheme（`myapp://`）无 `android:autoVerify`，恶意 App 注册同名 scheme 抢先接收 → token/回调参数泄露
- **Intent Redirection**：应用将收到的 Intent 原样转发给其他组件，攻击者借应用身份与权限触发恶意行为（2026-04 Microsoft 披露 EngageSDK 漏洞影响 3000 万+ 钱包应用）
- **Intent 注入**：`PendingIntent`、`getParcelableExtra` 反序列化 Intent 不当 → 越权操作
```bash
# 深链触发测试
adb shell am start -W -a android.intent.action.VIEW -d "myapp://auth?token=<REDACTED>"
adb shell am start -W -a android.intent.action.VIEW -d "myapp://payment?amount=9999"
# 未校验来源/参数 → 可能直接处理支付/转账等敏感动作

# 枚举已注册scheme
adb shell dumpsys package com.target | grep -A20 "scheme"
```

