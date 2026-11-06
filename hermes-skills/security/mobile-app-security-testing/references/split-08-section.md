## 七、移动端抓包与流量分析

### 7.1 代理环境搭建
```bash
# 1. Burp监听 0.0.0.0:8080（生成CA证书）
# 2. 手机导入CA证书
# Android:
adb push cacert.der /sdcard/
adb shell "settings put global http_proxy <PC-IP>:8080"
# Android 7+ 用户证书默认不被信任 → 处理:
#   a) 目标targetSdk<=23 直接有效
#   b) App使用networkSecurityConfig信任user证书(debug构建常见)
#   c) 将证书导入系统分区(需root): adb shell "mount -o rw,remount /system && cp ..."
# iOS:
# 设置→通用→VPN与设备管理→安装描述文件→证书信任设置→启用完全信任
# 无代理工具: iproxy 2222 22 && ssh -L 8080:localhost:8080 root@localhost
```
```bash
# 7.2 绕过SSL Pinning后抓包（结合第三章/第六章脚本）
objection -g com.target explore
android sslpinning disable     # Android
ios sslpinning disable         # iOS

# 若Objection失效 → 自写Frida脚本 hook:
# Android: TrustManagerImpl.verifyChain / X509TrustManager.checkServerTrusted / OkHttp CertificatePinner.check / WebView onReceivedSslError
# iOS: SecTrustEvaluateWithError / NSURLSession didReceiveChallenge / TrustKit
```

### 7.3 mTLS（双向认证）绕过
金融/高安全应用常做客户端证书双向认证，抓包需先绕过：
```
1. 逆向提取客户端证书: jadx/class-dump搜索 .p12/.pfx/bks 资源，strings搜索"BEGIN PRIVATE KEY"
2. 从Keychain/Keystore提取: objection android keystore list / ios keychain dump
3. 若证书内嵌代码: hook加载点拿到证书字节 + 密码（hook SecretKeySpec/KeyStore.getKey）
4. 在Burp配置客户端证书: Project Options→TLS→Client Certificates→Add
5. 也可hook SSLContext.init 强制使用自签客户端证书
```

### 7.4 非 HTTP 流量分析（深化）
```
1. TLS加密的私有协议: 
   - 获取TLS会话密钥 → Wireshark解密(SSLKEYLOGFILE / frida hook SSL_CTX_set_verify等)  
   - 或 Frida SSL dump: r0capture / frida-ssl-pinning-dump 直接输出明文
2. protobuf/gRPC: protoc --decode_raw 盲解字段；Ghidra分析序列化函数定位字段含义
3. WebSocket/长连接: Burp WebSocket支持 / mitmproxy -w 流量
4. DNS隧道/自定义DNS: DNSLog外带检测、Wireshark过滤 dns
5. 加密字段逆向思路: hook 加密函数(input/output) → 找到算法与密钥 → 脱机复现解密
```
```bash
# r0capture（Frida通用抓包,直接输出SSL明文到文件）
frida -U -f com.target -l r0capture.py -o pcap.txt --no-pause
# mitmproxy
pip install mitmproxy && mitmweb --listen-port 8080
```

