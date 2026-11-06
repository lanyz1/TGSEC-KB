## 2. 移动应用逆向 — Android & iOS

### 2.1 2026年十大移动渗透测试工具

| 类别 | 工具 | 平台 | 主要用途 |
|---|---|---|---|
| 动态运行时分析 | **Frida** | Android & iOS | 运行时插桩、Hook、绕过安全控制 |
| 静态分析和逆向 | **Ghidra** | Android & iOS | 底层二进制分析、固件和库逆向 |
| 静态分析和逆向 | **JADX** | Android | APK反编译为类Java源码 |
| 网络流量分析 | **mitmproxy** | Android & iOS | 交互式HTTP/S/WebSocket拦截 |
| 网络流量分析 | **Wireshark** | Android & iOS | 数据包级网络捕获 |
| 自动化和编排 | **OXO** | Android & iOS | 协调多个移动安全工具 |
| 自动漏洞扫描 | **Nuclei** | Android & iOS | 模板驱动CVE/配置错误扫描 |

### 2.2 Android逆向流程

```bash
# 1. APK解包与反编译
apktool d target.apk -o target_decoded
jadx -d target_jadx target.apk

# 2. 查找敏感信息
grep -rn "api_key\|secret\|password\|token" target_jadx/sources/
grep -rn "http://\|https://" target_jadx/sources/ | grep -v "schemas.android"

# 3. Native库分析
# JNI函数命名: Java_<package>_<ClassName>_<methodName>
# 例: Java_com_target_app_auth_NativeAuth_verifyToken
file lib/arm64-v8a/*.so
# 用Ghidra打开.so文件，搜索Java_前缀函数

# 4. Smali修补（绕过验证）
# 修改Smali代码: 将方法返回值改为true
# 原始: const/4 v0, 0x0  (false)
# 修改: const/4 v0, 0x1  (true)
apktool b target_decoded -o target_patched.apk
# 签名
apksigner sign --ks debug.keystore target_patched.apk
```

### 2.3 Frida运行时插桩

```javascript
// Frida脚本：绕过Root检测
Java.perform(function() {
    var RootBeer = Java.use('com.scottyab.rootbeer.RootBeer');
    RootBeer.isRooted.implementation = function() {
        console.log('[+] RootBeer.isRooted() bypassed');
        return false;
    };
});

// 绕过SSL Pinning
Java.perform(function() {
    var OkHttpClient = Java.use('okhttp3.OkHttpClient');
    OkHttpClient.Builder.implementation = function() {
        console.log('[+] SSL Pinning bypassed');
        return this.certificatePinner(null);
    };
});

// Hook加密函数捕获明文
Java.perform(function() {
    var Cipher = Java.use('javax.crypto.Cipher');
    Cipher.doFinal.overload('[B').implementation = function(input) {
        var result = this.doFinal(input);
        console.log('[+] Cipher.doFinal captured:');
        console.log('  Input: ' + bytesToHex(input));
        console.log('  Output: ' + bytesToHex(result));
        return result;
    };
});
```

### 2.4 Objection一键绕过

```bash
# 启动Objection
objection -g com.target.app explore

# Android绕过
android root disable           # 绕过Root检测
android sslpinning disable     # 绕过SSL Pinning
android keystore list          # 列出KeyStore条目
android hooking list classes   # 列出已加载类
android hooking watch class_method com.target.Auth.verify --dump-args --dump-return

# iOS绕过
ios jailbreak disable          # 绕过越狱检测
ios sslpinning disable         # 绕过SSL Pinning
ios keychain dump              # 导出Keychain
ios hooking watch class_method TargetAuth:verifyToken:
```

### 2.5 iOS逆向

```bash
# 1. 从IPA提取二进制
unzip target.ipa -d target_extracted
cd target_extracted/Payload/Target.app/

# 2. class-dump导出头文件
class-dump -H Target -o Target_headers/

# 3. 查找敏感方法
grep -rn "password\|secret\|token\|auth\|verify" Target_headers/

# 4. Frida Hook Objective-C方法
frida -U -f com.target.app -l hook.js --no-pause
```

```javascript
// iOS Frida脚本：Hook认证方法
ObjC.classes.TargetAuth['- verifyToken:'].implementation = function(token) {
    console.log('[+] verifyToken called with: ' + token);
    return 1; // 强制返回成功
};
```

---

