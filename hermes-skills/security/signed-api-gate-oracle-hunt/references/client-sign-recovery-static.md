# 客户端签名静态还原(App 侧 sign/HMAC 无法伪造时)

适用:目标 API 强制 `sign`/`signature`/`nonce`,密钥在 App 里;你**手上有 APK(或 dex/.so)**。目标 = 在**本地离线**算出合法签名,零目标流量。

## 0. 决策:静态优先,别先搭运行时
| 先做什么 | 判据 |
|---|---|
| **静态反汇编**(本节) | `.so` 里 `Java_*` 符号明文导出 —— 加固壳通常只保护 dex,`.so` 符号与 `.rodata` 常量照样可读 |
| Frida / 模拟器 | 符号被 strip、密钥运行时派生(白盒/密钥分片)、或算法在 Java 层被动态解密 |
模拟器+Frida 是**小时级**且常卡 `emulator-5554 offline`;静态是**分钟级**。**先跑第 1 步再决定。**

## 1. APK 拆解
```bash
unzip -o app.apk -d nwjx                       # 取 lib/<abi>/*.so、classes*.dex、META-INF/*.RSA
for d in nwjx/classes*.dex; do jadx -d dexsrc_$d --no-res -j 4 "$d"; done   # 全量反编译
```
- 有的样本 `classes.dex` 是**多 dex 拼接 blob**:按魔数 `dex\n035\x00` 的偏移切分(边界=下一个魔数),再逐段反编译。本样本 5 dex,真代码在 `classes2/3/4`。
- 包名从 `AndroidManifest.xml` 取:AXML 字符串是 **UTF-16** ⇒ `strings -e l`(`strings -a` 只吐乱码)。

## 2. .so 静态挖密钥
```bash
readelf -sW libnwdNativeLib.so | grep -i 'Java_\|getUqsz\|getXjut'   # 导出符号 + 内部校验函数
aarch64-linux-gnu-objdump -d --start-address=0x8b44 --stop-address=0x9488 <so>   # 反汇编密钥函数
python3 -c "d=open('<so>','rb').read(); print(d[0x24d80:0x24e30].hex())"        # .rodata VA==偏移
```
识别要点:
- **返回值路径**:`NewStringUTF` = JNIEnv 函数表 **offset 1336 / index 167**;其前的 `adrp x1,#page` + `add x1,x1,#off` 给出串的 `.rodata` 地址。
- **拼接顺序**:多个 6 字符短串按 `append` 调用顺序拼;间隔常为 7 字节(串尾 `\x00` + 对齐)。
- **多环境密钥**:常见 PRO / 非 PRO 两个函数(如 `getQfHJvIYo` / `getExUAnRTH`),**两个都要挖,实测才知道目标用哪个**。
- **防重打包陷阱**:函数可能先 `getUqsz()`(读实际签名)与 `getXjut()`(期望值)比对,不等则返回**空串** ⇒ **改包重签后必须同步改掉期望值**,否则永远拿空串。

## 3. 第二盐 = APK 签名证书 RSA 模数
两种取法:
```bash
# ① 从 APK 签名块(多数 APK 直接有)
unzip -o app.apk 'META-INF/*.RSA' -d sig && openssl pkcs7 -inform DER -in sig/*.RSA -print_certs -noout
# ② 从 .so/.rodata 里藏的整份 X.509 DER 的 hex 串(本项目实际形态:0x24820 起)
#    DER 里 30 82 01 0a 02 82 01 01 00 <256B 模数> ; 或直接 python + bytes.fromhex 后走 ASN.1
```
- **Java 侧 `BigInteger.toHexString()` 会丢掉首字节 `0x00`** ⇒ 模数 hex 用**不含前导 00** 的 512 位(小写);从 DER 的 INTEGER 直接 dump 会多带一个前导 `00`,记得 `[2:]`。
- 同一段 `.rodata` 里常还有:自定义字母表(如 `+xX0123456789abcdef0123456789ABCDEF`)、16B 辅助常量 —— 一起记下来,可能是第三段盐。

## 4. Java 侧找签名函数(jadx)
- **Retrofit 注解名被压成单字母**:`@GET→@f`、`@POST→@o`、`@Headers→@k`、`@QueryMap→@u`、`@Body→@y`。`grep '@GET('` 恒空。
```bash
grep -rhno '@f("/[^"]*"\|@o("/[^"]*"' --include=*.java dexsrc*/sources/ | sed 's/.*("//;s/")//' | sort -u   # 全量接口路径
```
- 常用类名族:`*SignUtil`、`*DynamicsSignKeyUtil`、`ParamUtils`、`SignParamInterceptor`、`RetrofitUrlManager`(消费 `Domain-Name` 头做动态域名)、`getAppRunUrl()/getWebHost()`(宿主表)。
- 参数组装器(`ParamUtils.b(map, isNwd)`)会**注入固定字段再 put("sign")** ⇒ 这些固定字段**必须同时参与签名且发给服务端**;请求里已带 `sign` 时客户端会跳过签名(⇒ 可自填)。

## 5. 公式形态与重建
```
sign = md5( md5( 按 key 字典序拼接的所有非空参数值 + 密钥源 ) + 证书模数hex )   # 只拼 value,不拼 key
密钥源 = SP 里的登录后 signKey ?? 空则回退 native 密钥
```
- **盐在哪一层必须逐字对**:native/SP 密钥常在内层、APK 证书模数在外层;**写反 = 全错**。反编译能确认就别猜。
- 服务端只用你发来的参数重算 ⇒ 设备的真实 OS 版本/渠道/mid **不重要**,自造一组自洽值 + 正确签名即可(未登录态可用)。
- 一键重建(Python):`md5(md5("".join(str(p[k]) for k in sorted(p)) + key).hexdigest() + cert_mod)`。

## 6. 验证(不许跳)
- **A/B 对照**:同一路径发「无 sign / 错 sign / 正确 sign」三发,响应必须出现**形态变化**(如 `未获得签名` → `token不存在`)。
- **没在活 handler 上做过 A/B 就不要声称签名可用**;只拿到密钥+公式 = 「半成品」,还差一个**路由该族的活宿主**。
- 宿主活没活的判据:Spring Boot `404` 体带**实时时间戳** = 宿主活、路径不对;**405** = 方法不对(改 POST);**Apache 式 HTML 404** = 前面还有 httpd 按 vhost 分发 ⇒ 同 IP 多 vhost,换 Host 头重打。
