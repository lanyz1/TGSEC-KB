# 移动端 App 安全测试手册（Android/iOS）

> SRC 目标常带 App/小程序。App 是接口地图 + API 钥匙库（硬编码密钥/调试接口/隐藏域）。**先静态拆解、再动态 Hook、最后打 API**——App 挖洞的效率核心在"把 App 变成接口清单"。

## 一、APK 静态分析（最快拿到接口地图）

### 1. 拆解
```bash
apktool d app.apk                # 资源+smali+Manifest
jadx -d out app.apk              # 反编译为 Java（主用）
unzip -l app.apk | grep -E '\.(js|so|json)$'
```

### 2. 接口/密钥提取（重点）
| 搜什么 | 找什么 |
|--------|--------|
| `https://`、`http://` | 全部 API 域名与路径（接口地图） |
| `apiKey`/`secret`/`token`/`password`/`accessKey` | 硬编码密钥/ID |
| `SharedPreferences`/`getSharedPreferences` | 本地存储键（token 存哪） |
| `BASE_URL`/`BuildConfig` | 测试/生产环境地址（测试环境常有漏洞） |
| `Encrypt`/`AES`/`RSA`/`MD5` | 加密算法与密钥（抓包解密用） |
| `WebView`/`loadUrl`/`addJavascriptInterface` | WebView 面 |
| `.so` 内的字符串 | `strings lib/*.so` 找签名密钥/协议 |

### 3. AndroidManifest 危险配置审计
- `android:debuggable="true"`（生产开了 = 可调试提权）
- `android:allowBackup="true"`（可备份拖数据）
- `exported=true` 的 Activity/Service/Provider（无权限启动 → intent 劫持/敏感操作）
- `usesCleartextTraffic="true"`（明文流量 → 中间人）
- exported provider（FileProvider 配置错误 → 任意文件读）
- deep link scheme（可被其他 App 唤起/劫持）

### 4. 常见漏洞代码模式（jadx 搜索）
```java
// WebView 无限制 + 任意 URL
webView.getSettings().setJavaScriptEnabled(true);
webView.loadUrl(getIntent().getStringExtra("url"));   // XSS/intent 劫持

// addJavascriptInterface（API<17 或没配 @JavascriptInterface）
webView.addJavascriptInterface(obj,"android");        // 任意 JS → 文件读/RCE 面

// 明文存储
Log.d("token", token);                                 // 日志泄露
getSharedPreferences("x", MODE_PRIVATE).putString("pwd", pwd);  // 密码明文存
```

## 二、动态分析（Frida 核心）

```bash
# 环境：模拟器/真机 + adb + frida
frida -U -f com.target.app -l hook.js     # 启动时注入

# 常用 Hook
# 1. 抓 HTTP 层（绕过 Cert Pinning / 解密）
#    objection -g com.target.app explore
#    → android sslpinning disable
# 2. Hook 函数看入参出参（IDA/算法/签名参数）
Java.perform(function(){
  var cls = Java.use("com.target.ApiClient");
  cls.encrypt.overload('java.lang.String').implementation = function(s){
    console.log("encrypt(" + s + ")");
    return this.encrypt(s);
  };
});
```

- **Burp 抓包**：模拟器设代理 + 装 CA；遇到证书固定（pinning）→ Frida/objection 关闭
- **抓 API**：所有请求记录 → 整理成接口清单（打 API 用）
- 无 Root 场景：Frida Gadget 注入（重打包）或 Magisk 模块

## 三、网络层测试

- 接口清单出来后按 SRC Web 流程打（越权/注入/逻辑，见 `打野短表`）
- App 特有面：**深链（deep link）参数注入**、WebView 混合面、OAuth 回调劫持（`intent://`）、SDK 内嵌第三方登录回调
- **签名参数**：App 请求常带签名（时间戳+参数+盐 hash）——逆向找到盐后在 Burp 重放/改包可用

## 四、本地存储审计

| 位置 | 内容 | 风险 |
|------|------|------|
| `/data/data/<pkg>/shared_prefs/` | token/账户信息 | 明文或弱加密存储 |
| `/data/data/<pkg>/databases/` | SQLite 业务数据 | 敏感数据落盘 |
| 外部存储/备份 | `adb backup` 可拖出 | allowBackup=true 时 |

Root 环境读取；证据：能读到 token/密码 → 对应本地存储漏洞报告（中危起，看内容敏度）

## 五、iOS (IPA) 要点

```bash
# 静态：class-dump / MachOView / strings
unzip -l app.ipa; class-dump -H Payload/App.app/App
# 动态：frida-ios-dump / cycript / objection
# 绕过 SSL pinning：objection ios sslpinning disable
# 检查：Keychain 存储、UserDefaults、Info.plist 配置、ATS 明文例外
```

## 六、小程序/快应用

- 小程序包：`wxapkg` 解包（unpack 工具）→ JS 里有接口+密钥
- 云开发：云函数未授权调用、数据库权限（`db.collection(...).get()` 未加权限）
- WebView/内嵌 H5：全栈 Web 手法直接套

## 七、报告要点
- App 挖到的洞按 Web 定级标准（`report-format.md`）；硬编码密钥过**认钥闸**
- 复现步骤写清：逆向步骤 → 找到的点 → 利用过程（截图）
- 修复建议：混淆加固、证书固定、密钥服务端下发、最小权限 exported