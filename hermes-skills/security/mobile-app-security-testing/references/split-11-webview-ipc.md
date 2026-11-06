## 十、WebView 与深链/IPC 攻击面

### 10.1 Android WebView（XSS→RCE 高价值面）
```java
// 高危配置（反编译后在代码中检索）
webView.getSettings().setJavaScriptEnabled(true);      // 开启JS → XSS可达
webView.addJavascriptInterface(new Bridge(), "Android"); // JS桥
// 现代(API17+): 必须@JavascriptInterface注解才暴露 → 审计桥方法是否:
//   - 未校验来源/参数直接执行(如调用支付/发短信)
//   - 接收JSON直接反序列化(无schema校验)
//   - 暴露文件读写/命令执行
webView.getSettings().setAllowFileAccess(true);        // file:// 本地文件读取
webView.getSettings().setAllowFileAccessFromFileURLs(true); // 本地html跨文件访问
webView.setWebViewClient(new WebViewClient() {
    // shouldOverrideUrlLoading 未做scheme白名单 → 协议劫持(intent://, tel://, 自定义scheme)
    // onReceivedSslError 里 proceed() → 证书校验被吞 → MITM
});
```
```bash
# 验证方法
# 1) 找WebView加载入口（搜索loadUrl/setWebChromeClient）
# 2) XSS注入点: 通过深链/JS注入向WebView传参
# 3) 触发桥方法: javascript:AndroidBridge.processPayment('{"amount":0,"to":"attacker"}')
```

### 10.2 iOS WKWebView
```
- evaluateJavaScript / messageHandlers(JS-Native桥) → 桥方法审计同上
- WKURLSchemeHandler 自定义协议处理 → 路径/参数校验
- loadFileURL:allowingReadAccessToURL: 若传NSHomeDirectory() → WebView可读整个App容器
- decidePolicyForNavigationAction 未过滤自定义scheme → 深链注入
- WebView中加载不可信内容(CSP缺失/广告SDK) → JS注入桥调用
```

### 10.3 深链劫持与 Intent Redirection（2025-2026 热点）
```
1. Deep Link劫持(Android): 自定义scheme无autoVerify → 恶意App注册同名scheme抢收
2. Intent Redirection(Android): 
   - 案例: EngageSDK(CVE级,影响3000万+加密钱包) - 转发Intent绕过沙箱窃取私数据
   - 检测: 搜索 startActivity(intent) 且 intent 来自 getIntent()/onActivityResult 未二次校验
   - 攻击: 恶意App构造Intent → 受害App以自身身份权限转发执行
3. iOS URL Scheme/Universal Links:
   - 自定义scheme无校验 → 参数注入(token/action)
   - Universal Links依赖apple-app-site-association文件 → 检查域名授权是否可信
4. 通知/剪贴板钓鱼: Unicode不可见字符(U+200B)构造假域名(ama\u200Bzon.com)诱导深链
```
```bash
# Android深链注入验证
adb shell am start -W -a android.intent.action.VIEW -d "myapp://pay?to=attacker&amount=0"
adb shell am start -W -a android.intent.action.VIEW -d "intent://#Intent;scheme=myapp;..."
# iOS深链（越狱/模拟器）
xcrun simctl openurl booted "myapp://resetpassword?token=HACKED"
```

