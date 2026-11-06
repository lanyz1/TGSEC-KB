## 十、移动端资产（小程序/App）

### 10.1 小程序发现
```bash
# 入口：微信搜索公司名（全部小程序列表）、公众号关联小程序
# 资产查询平台：爱企查/天眼查关联小程序、七麦数据/点点
# 每个小程序 = 一组完整 API 面（往往比 Web 端更少防护）
```

### 10.2 小程序抓包与反编译
```bash
# 抓包（PC 微信 + Proxifier 转发到 Burp；或模拟器 + 抓包工具）
# 低版本微信/Android 7 模拟器可绕过证书校验；高版本需系统证书挂载
openssl x509 -in cacert.der -out cacert.pem
# 将证书放入模拟器 /system/etc/security/cacerts/ 并 chmod 644

# 获取小程序包（本地缓存）
# Windows: C:\Users\<user>\AppData\Roaming\Tencent\xwechat\radium\Applet\packages
# Mac: ~/Library/Containers/com.tencent.xinWeChat/Data/.wxapplet/packages/

# 反编译（主包+分包）
node wuWxapkg.js __APP__.wxapkg        # wxappUnpacker 主包
unveilr "小程序目录"                    # 自动处理分包，输出源码

# 源码分析重点
# - app.js / config.js：AK/SK、云环境ID、API 域名
# - request 封装：BaseURL、加密签名逻辑（sign 参数生成）
# - 分包路径：未授权模块、隐藏功能页
# - WXSS 注释：测试账号、开发信息
```

### 10.3 小程序专属风险点
```
- 云函数未授权调用（wx.cloud.callFunction 任意函数）
- API 越权：JWT 签名不校验/算法混淆（alg:none）
- 敏感参数明文传输（路由 URL 带 token/用户ID）
- 内网地址直连：小程序后端常部署在办公网，请求头 X-Forwarded-For 伪造
- 加密算法逆向：硬编码密钥提取 → 重放/构造合法请求
```

### 10.4 APK 分析（Android App）
```bash
# 获取：小蓝本 / 点点 / Apple Store / 七麦数据 / 应用市场

# 静态分析
jadx -d output app.apk                      # 反编译为 Java 源码
apktool d app.apk                           # 资源与 smali
# AppInfoScanner / ApkAnalyser / bytecode-viewer
# 提取：URL/域名、AK/SK、证书文件、SQLite 数据库、硬编码凭据

# 字符串全量提取
strings -n 8 app.apk | grep -iE "http|api|key|secret|token"

# 脱壳（加固应用）
# BlackDex / fdex2 / 反射大师 / 微脱壳
# 绕过抓包：JustTrustMe++ / HttpCanary / 小黄鸟 / Frida SSL Pinning 绕过

# iOS：爱思助手提取 IPA → class-dump / Hopper 分析（方法论同上）
```

### 10.5 移动端与 Web 资产联动
```
1. 从 App/小程序提取的 API 域名/内网 IP 合并进攻击面清单
2. 移动端接口往往绕过 WAF/CDN（直连源站）→ 真实 IP 溯源捷径
3. 移动端参数构造（版本号/设备指纹）可能绕过 Web 端风控
4. 云端配套（OSS/COS/云函数）与 Web 端共享存储 → 横向
```

