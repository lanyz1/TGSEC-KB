# 01 客户端程序保护 + 弱加密审查

源：Android APP渗透测试方法大全 §2.1-2.6 / §6.13（人行式客户端安全评估口径）

---

## 1.1 数字签名检测

判定客户端是否用**自有证书**发布：

```bash
jarsigner -verify -verbose -certs app.apk | head -40
keytool -printcert -jarfile app.apk
```

判据：
- `CN=Android Debug, O=Android, C=US` → **debug 证书**（未正式发布）
- 证书属于第三方/外包方 → 非客户自有，资产归属不清
- `validity` 已过期 / 自签且无 CA → 记录但不单列高危（Android 本身不要求 CA 签）

**签名机制要点（写报告时的原理段）**：Android 不要求权威 CA 签名；数字证书作用有二：①判断 apk 签名后是否被篡改 ②识别作者。升级时只有新包与旧包证书相同，系统才认为是同一程序并覆盖安装，否则要求改包名。

---

## 1.2 反编译检测

```bash
apktool d -f -o src app.apk            # 资源 + smali
unzip -o app.apk -d raw                 # 原始结构
jadx -d java_out app.apk                # 直接出 Java（现代首选）
strings -n 6 app.apk | sort -u | head -200
```

判据：若不经任何破壳即能获得**可读的业务 Java 代码**，且无混淆（类名/方法名有意义、字符串明文），判为「客户端易被反编译」。
加固/壳/混淆的存在本身就是缓解措施，但**不构成"安全"**——先按 `apk-reverse` 判壳，能脱则继续。

---

## 1.3 应用完整性自校验（高价值，最容易被漏）

**测试法（改一个不影响功能但显眼的资源）**：

```bash
apktool d -f -o src app.apk
# 改 src/res/drawable*/logo*.png（换成另一张图）或改 res/values/strings.xml 里的可见文案
apktool b src -o repacked.apk
keytool -genkey -v -keystore test.keystore -alias t -keyalg RSA -validity 3650 \
  -storepass 123456 -keypass 123456 -dname "CN=t"
jarsigner -keystore test.keystore -storepass 123456 repacked.apk t
jarsigner -digestalg SHA1 -sigalg MD5withRSA -keystore test.keystore -storepass 123456 repacked.apk t
zipalign -v 4 repacked.apk final.apk      # 可选
adb uninstall <pkg> && adb install final.apk
```

判据：**改了还能正常运行 = 无完整性校验 = 高风险**（攻击者可植入木马/改逻辑后重签分发）。

**代码侧**：找是否有对自身签名的校验（`PackageManager.getPackageInfo(..., GET_SIGNATURES)`、`getSignature()` 比对）或对 so/dex/assets 的 Hash 校验。搜 `getPackageInfo`、`signatures`、`MessageDigest` 在启动路径上的调用。

**坑**：
- 重打包后不签名无法安装（报未签名）
- 证书不同不能覆盖安装，先 `adb uninstall`
- apktool 打包报 `NOT A PNG file` → 把非 png 扩展名改回或转成 png
- 资源编译失败 → 补 framework：`apktool if framework-res.apk -t tag0` 后 `apktool d -t tag0`

---

## 1.4 debug 模式

```bash
adb shell run-as <pkg> id                # 成功输出 uid → debuggable=true
adb shell dumpsys package <pkg> | grep -i -E 'flags|debuggable'
aapt dump xmltree app.apk AndroidManifest.xml | grep -i debug
```

判据：debuggable=true → 可 `adb jdwp` + jdb/Android Studio 附加到进程，下断点改内存、读存储（配 `run-as` 可读写私有目录）。

**坑**：`run-as` 在包名层数 < 3 时报 `Package is unknown`（工具 bug，非权限问题）。

---

## 1.5 应用数据可备份（allowBackup）

```bash
# manifest 未显式 android:allowBackup="false" ⇒ 默认 true
adb backup -noapk -f backup.ab <pkg>
# 解包 backup.ab（zlib+tar）为 abe 格式后再转 tar
java -jar abe.jar unpack backup.ab backup.tar
```

判据：能备份出私有目录明文（token/账号/缓存）→ 无 root 即可取敏感数据，视为高风险。仅需设备端确认（备份时手机需确认手势解锁），也属未授权访问面。

---

## 1.6 应用权限测试

```bash
python manitree.py -f AndroidManifest.xml      # 权限树
# 或直接 grep
```

判据：申请权限 **> 业务需要** 即存在隐患。典型过度：读短信/通讯录/位置/相机 出现在无对应功能的 App 上；`READ_PHONE_STATE` 拿 IMEI 做设备指纹（合规问题）。
`<uses-permission android:name="..."/>` 与自定义 `<permission android:protectionLevel>` 都要看：protectionLevel=dangerous/normal 的自定义权限等于开放给别人用。

---

## 1.7 弱加密审查（§6.13，代码清单）

反编译后逐个 grep：

```java
// ① 弱算法：DES（56bit）
SecretKeySpec key = new SecretKeySpec(rawKeyData, "DES");
Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");

// ② RSA 无 Padding
Cipher.getInstance("RSA/NONE/NoPadding");

// ③ 无安全 IV：硬编码常量 / 全零
byte[] iv = { 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00 };
IvParameterSpec ips = new IvParameterSpec(iv);

// ④ 不安全模式：ECB
Cipher.getInstance("AES/ECB/PKCS7Padding", "BC");

// ⑤ 不安全密钥长度：RSA 512
KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
keyGen.initialize(512);

// ⑥ 硬编码密钥/常量密钥（最常见）
String KEY = "1234567890123456";  String IV = "0102030405060408";
```

grep 关键词：`SecretKeySpec|Cipher.getInstance|IvParameterSpec|initialize(|ECB|NoPadding|"DES"|Base64`。

判据汇总：DES/RC4/ECB/无 Padding/固定或全零 IV/RSA<2048/密钥硬编码/MD5·SHA1 直接存密码 —— 任一项命中即记为「加密实现不安全」。**base64 不是加密**。

---

## 1.8 报告口径（重要）

> **所有需要对客户端程序/设备进行操作后，才能解除的保密性或完整性措施，不算作风险。**

即：需要 root / hook / 反编译 / 改包才能突破的防护，属「加固建议」而非「漏洞」。判风险时以**攻击者在无特权、无物理接触**条件下能否达成为准。
