# 05 进程保护 + 通信安全 + 第三方 SDK

源：Android APP渗透测试方法大全 §8 / §9 / §10 / 附录一

---

## 5.1 进程保护

### ① 内存访问与修改
```bash
# 传统：MemSpector / CheatEngine / DDMS 搜索字符串/数值
# 关键内存段：/dev/ashmem/dalvik-heap  （用户名/密码常在这）
# 现代：frida
frida -U -f <pkg> -l memscan.js
```
```javascript
// memscan.js：在 Java 堆上搜明文密码
Java.perform(function () {
  var S = Java.use('java.lang.String');
  // 或直接对 Native 内存：
  var ranges = Process.enumerateRanges('rw-');
  ranges.forEach(function (r) {
    try {
      Memory.scanSync(r.base, r.size, '70 61 73 73 77 6f 72 64') // "password"
        .forEach(function (m) { console.log('HIT', m.address, r.base); });
    } catch (e) {}
  });
});
```
判据：内存中能搜到**明文密码/卡号** = 高。多数工具走 **ptrace**，客户端可用 ptrace 自保护（检测 `TracerPid`）对抗 —— 但属加固建议不属漏洞。

### ② 动态注入
- 检查 `LD_PRELOAD` 是否可被利用：预加载任意 so 劫持（如劫持 `ls` 的 `__libc_init` 验证）
- 工具：`ddi`（github.com/crmulliner/ddi）；hook 框架见 `android-root`
- 现代：frida-server 注入 / `objection`

### ③ 本地端口开放检测（高价值）
```bash
busybox netstat -tuanp | grep -Ei 'listen|udp'
lsof | grep -i sock                                            # 看 socket 归属
```
风险模型（写报告用）：App 用 `PF_UNIX / PF_INET / PF_NETLINK` 做本地 IPC 或远程通信，这些 socket 是**本地/远程攻击面**；特别是 `PF_INET`（TCP/UDP），原本是 Linux 开放网络服务的做法，**因缺乏对调用者身份 / 本地 uid / permission 的细粒度检查**，实现不当时可**突破 Android 沙箱，以被攻击应用的权限执行命令**。历史上多次出现利用 socket 做 DoS / root 提权 / RCE 的案例。

### ④ 外部动态加载 DEX
```bash
grep -rn 'DexClassLoader(' src/
```
风险：Android 4.1 之前系统允许 App 把动态加载的 DEX 放在**其他应用可读写目录**（如 `/sdcard`），因此：加载的 DEX 可被恶意应用替换/注入；若对已加载 DEX **无完整性校验**，应用实际执行的是恶意代码。
风险位置：`public DexClassLoader(String dexPath, String optimizedDirectory, String libraryPath, ClassLoader parent)`；核对 `dexPath` 是否落在外部可写目录，以及有无 Hash 校验。

### ⑤ so 库函数接口
尝试用其他程序调用该 App 的 so 导出函数 —— 能轻易被其他应用调用 = 风险（应校验调用方 / 不导出敏感函数）。

---

## 5.2 通信安全（抓包三条路径 + 八个检查点）

### 先判类型（决定路能否走通）
| 情形 | 方案 |
|---|---|
| HTTP(S) + 认系统代理 | 电脑开 Burp/Fiddler 允许远程连接 → 手机/模拟器设代理指向电脑出口 IP。模拟器：设置→无线和网络→移动网络→APN→设代理；Genymotion：WLAN 长按→修改网络→代理手动；真机：`netsh wlan` 开承载网络后手机连电脑 WiFi |
| HTTP(S) 但不认系统代理 | ① root 设备装 **ProxyDroid**（ixatbles 透明代理） ② 不能 root：安卓虚拟机跑在 Windows 虚拟机里，再挂 Proxifier 到物理机代理 |
| 非 HTTP（TCP/UDP 私有协议） | WPE 附加进程仅适合请求-响应式；委托-回调式/复杂协议用 `tcpdump` 抓 pcap + Wireshark 分析；协议简单自行仿制，复杂则反编译摘出通信代码或重实现 |

```bash
# 模拟器启动即带代理：
emulator -avd <name> -http-proxy 127.0.0.1:8080
# Burp 需在 Proxy→Options→Request handling 勾 Support invisible proxying
# 抓包：
adb shell tcpdump -w /sdcard/traffic.pcap -i any -s 0 -p
# 实时直通 Wireshark：
adb shell "tcpdump -s 0 -w - | nc -l -p 4444"
adb forward tcp:4444 tcp:4444
nc localhost 4444 | wireshark -k -S -i -
```

### 非标准端口 HTTP 的透明代理（ProxyDroid 只吃 80/443/5228）
```bash
adb shell su -c 'iptables -t nat -A OUTPUT -p tcp --dport <PORT> -m tcp -j REDIRECT --to-ports 8123'
adb shell su -c 'iptables -t nat -A OUTPUT -p tcp --dport <PORT> -j DNAT --to-destination 127.0.0.1:8123'
# https 换 8124；多端口各来一条；模拟器默认无 iptables（需重编内核）
```

### 八个检查点
1. **通信加密**：代理能否解密？tcpdump 看是否真 TLS。把客户端内所有 URL 的 `https` 改 `http`，看是否报连接错误；无 HTTPS 且无应用层加密 = 高
2. **证书有效性**：① 代理替换证书是否报错（能代理 = 未校验） ② 改 DNS 把主页指到 `https://mail.qq.com/` 看是否提示域名不符 ③ 代码 grep `java.net.ssl.HttpsURLConnection.setDefaultHostnameVerifier()` → 找 `HostnameVerifier.verify()`，恒返回 true = 无校验
3. **Certificate Pinning**：换成代理证书就断网 ⇒ 预存了服务端公钥/Hash/整证书。若客户端无完整性校验 → 反编译改其内置证书为代理证书（证书常放 `res/raw/mystore`，BKS 格式）；工其其：Android SSL Trust Killer / Android-ssl-bypass
4. **SSL 版本/套件**：`openssl s_client -connect host:443`；< TLS1.0 或 RC4/DES 算不安全
5. **关键字段加密**：密码/收款人信息是否明文提交；无代理可用时反编译读提交代码
6. **完整性校验**：代理改参重放看服务端是否拒绝；反编译找 MD5/SHA 校验函数并定位它校的是哪些参（无签名 → 可任意重放/篡改）
7. **客户端更新安全性**：代理抓更新包 → 把服务端返回的更新 URL 换成恶意链接 → 看客户端是否直接打开下载安装；再把下载的 apk 换掉，看是否照样安装。无签名/IP校验 = 高
8. **短信重放**：重放短信验证码请求包 → 可轰炸 = 中

### 手动装根证书（老系统路径）
```bash
adb pull /system/etc/security/cacerts.bks        # Android < 4.0
# Portecle 打开 bks（口令直接 OK）→ Import Trusted Certificate → 导入 Burp 证书
adb shell su -c 'mount -o remount,rw /system'
adb push cacerts.bks /system/etc/security/ && adb reboot
# Android 4.0+：设讧→安全→从 SD 卡安装（证书落 /data/misc/keystore|keychain）
# 现代（Android 7+ 不信任用户证书）：Magisk 模块 AlwaysTrustUserCerts，或重打包把 pin 证书/Network Security Config 改掉
```

### 加密协议仿制（从硬编码密钥到解密成功）
典型链路：点登录按钮 → 找到 Listener → 密码 Base64 后走异步 → 异步子程序调 `HttpWebService.login()` → 里面调加密封装 → **算法/IV/Key 以常量字符串硬编码**。
```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
key = b'1234567890123456'; iv = b'0102030405060408'      # 从代码里拷出来的
c = AES.new(key, AES.MODE_CBC, iv)
print(unpad(c.decrypt(bytes.fromhex(cipher_hex)), 16))
```
注：通信过程有加密/签名时，通常必须回到客户端代码做传统逆向；**实现足够复杂时可认为安全**（写报告时如实标注"未能解密"）。

---

## 5.3 安全增强测试

### ① 第三方 SDK：WormHole 虫洞（百度 SDK）
```bash
grep -rn '40310\|6259\|7777\|127.0.0.1' src/            # 定位 SDK 与本地端口
adb shell netstat -an | grep -E '40310|6259|7777'
adb forward tcp:40310 tcp:40310
```
存在性验证请求（返回数据即漏洞成立）：
```
http://127.0.0.1:40310/getcuid?secret=0&mcmdf=inapp_&callback=test_deviceid_callback
http://127.0.0.1:6259/getcuid?secret=0&mcmdf=inapp_&callback=test_deviceid_callback
http://127.0.0.1:7777/getcuid?callback=test_deviceid_callback
http://127.0.0.1:40310/getapplist?secret=<REDACTED>
```
危害：该本地端口**无调用者身份验证**且监听 `0.0.0.0` 时，同一局域网/网页 JS 借浏览器可达 → 远程读设备信息/静默装包。同类本地 HTTP 服务（NanoHTTPD）走 `webview-deeplink-bridge`。

### ② 二维码识别测试
扫描畸形二维码图 → monitor/logcat 看崩溃。样本：`http://static.wooyun.org//drops/20151201/201512011130233308817.jpg`。崩 = 风险（二维码解析未做异常处理）。

### ③ 开放网络服务（ServerSocket 无鉴权）
```java
// 风险代码形态：收到指令直接执行，对 socket 与内容零校验
serverSocket = new ServerSocket(SERVER_PORT);
while (mainThreadFlag) { Socket client = serverSocket.accept(); ... }
// 且
msg = readCMDFromSocket(in);
if ("exec" == msg) { /* execute command without any check */ }
```
判据：未对接收到的 socket（调用者身份）和内容（指令合法性）做任何校验 → 高风险（沙箱逃逸级：可越过 Android 沙箱以该应用权限执行命令）。

### ④ 运行其它可执行程序
```java
Runtime.getRuntime().exec(new String[]{"/system/bin/ls","-l"},
                          new String[]{"a=1","b=2"});
Runtime.getRuntime().load("/data/data/com.x/lib/libtest.so");
Runtime.getRuntime().loadLibrary("test");
```
grep `Runtime.getRuntime().exec|.load\(|.loadLibrary` → 若执行路径/参数可控或来自第三方库，存在被滥用的风险。

### ⑤ 数据完整性校验（重放测试两段）
```
第一段：
1. 部署代理，启动 app 正常操作
2. 看提交字段里有无**较长的加密 header / POST·GET 参数**（潜在签名）
3. 在 app 上改变提交数据，重新提交，看这些参数值有无变化
4. 改包重放，看能否正常返回
5. 正常返回 ⇒ 未做完整性校验
第二段（代码确认）：
1. 反编译 → 2. 分析特定动作（如 login）→ 3. 看是否有单独的 MD5/SHA 校验函数
4. 有则看它校的是哪些参 → 5. 用代理 payload 处理重放验证
```
