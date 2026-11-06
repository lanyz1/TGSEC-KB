# 03 敏感信息存储 + 输入侧信道

源：Android APP渗透测试方法大全 §4 / §5（附实测细节）

---

## 3.1 数据文件存储六查

**前置纪律：先把 App 完全退出再取数据**（部分客户端会在退出时清除临时文件与缓存，不退出会误报）。

### ① 私有目录与文件权限
```bash
adb shell                                  # 需 root 或 run-as
ls -laR /data/data/<pkg>/ | head -100
```
判据：
- 正常文件：`-rw-rw----`（用户+组可读写，other 为空）
- 正常目录：`drwxrwx--x`（比文件多一个 x，用于遍历）
- 若 other 位有 r/w（如 `-rw-rw-rw-`）⇒ 代码用了 `MODE_WORLD_READABLE` / `MODE_WORLD_WRITEABLE` ⇒ 其他应用可读/改写 → 高危
- Android 7+ 已禁用这两个 MODE，但**旧版本机/低 targetSdk 仍能触发**；同时注意 `/sdcard`、`/data/local/tmp`、`/data/data/<pkg>/files` 是否被 chmod 放开

### ② SharedPreferences
```bash
adb shell cat /data/data/<pkg>/shared_prefs/*.xml
```
找：明文密码、token、手机号、身份证、设备指纹、本地保存的登录凭据（自动登录常存这里）。

### ③ SQLite
```bash
adb shell ls -l /data/data/<pkg>/databases/
adb pull /data/data/<pkg>/databases/x.db .
sqlite3 x.db '.tables' ; sqlite3 x.db 'select * from <table> limit 20;'
```
**用 WebView 的 App 必有**：`databases/webview.db`、`databases/webviewCache.db`
- `webview.db` 存 **表单密码明文**（由 `setSavePassword` 控制）与 remembered 表单
- `webviewCache.db` 存 Cookie 与页面缓存

### ④ APK 包内的敏感信息
```bash
apktool d -s app.apk -o res_only
strings -n 5 classes.dex | grep -iE 'key|secret|token|passw|http://|https://' | sort -u
strings -n 5 app.apk | grep -iE 'admin|test|api' | sort -u
```
常见：硬编码对接密钥、后台管理路径、测试/预发环境域名、第三方服务 AK/SK、推送/AI 服务 token。API 18 之前 WebView 还在 `/data/data/<pkg>/app_webview/Local Storage/` 存本地存储，同样按私密数据对待。
硬编码密钥拿到即伪造请求 → 接 `mobile-hardcoded-key-decrypt` / `apk-recon`。

### ⑤ 其他文件存储：缓存与外部存储
```bash
adb shell ls -laR /sdcard/Android/data/<pkg>/ 
adb shell ls -laR /sdcard/<AppName>/          # 很多应用自建同名目录
adb shell ls -la /data/data/<pkg>/cache /files /app_webview
```
**不知道落盘在哪时用 strace 反推**：
```bash
adb shell su -c 'strace -f -ff -e trace=file -o /sdcard/st.<pid> -p <pid>'
# 或启动时挂：strace -f -e trace=open,write,rename -o /sdcard/st.txt <app's cmdline>
```
`open/read/write` 参数与返回值会把真实路径全部暴露。

### ⑥ 加密是否真加密
- `base64` 编码冒充加密（base64 不是加密）
- 硬编码密钥的 AES/DES ⇒ 可解密，等同明文
- MD5/SHA1 单次散列也按不安全算（碰撞 + 查表）
- 算法本身的安全性另走 `11. 弱加密审查`

### 附件：现代等价（无 root）
```bash
# run-as（仅 debuggable）
adb shell run-as <pkg> sh -c 'cat shared_prefs/*.xml'
adb exec-out run-as <pkg> tar -c files shared_prefs databases > pull.tar
# frida（需 root / 重新打包注入 gadget）
frida -U -f <pkg> -l dump_storage.js
# objection
objection -g <pkg> explore -c 'env; ls; sqlite connect <db>'
# 自动化：MobSF 直接输出存储类问题清单
docker run -it --rm -p 8000:8000 opensecurity/mobile-security-framework-mobsf:latest
```

### logcat 日志
```bash
adb logcat -v time | grep -iE 'passw|pwd|token|session|card|idcard|phone|IMEI|IMEI|secret'
adb logcat -d > all.log; grep -inE 'passw|pwd|token|session|cookie' all.log
```
判据：密码/卡号/token/身份证 在 logcat 明文打印 → 中~高危（任何 App 读日志或设备取证即得）。

---

## 3.2 密码软键盘安全性（输入侧信道）

| 项 | 实测做法 | 判据与坑 |
|---|---|---|
| 键盘劫持 | ① 装 `ns_keylogger.apk` 类 IME（或自己写一个 `InputMethodService`）② 设置里把默认输入法切到它 ③ 目标 App 输入框长按空格→选该输入法 ④ `adb logcat` 看击键 | 能拿到**完整明文击键** = 高。若 App 用**系统输入法**则已被记录；用自带加密键盘则拿不到（降级）。需社交工程诱导安装，但银行类 App 常不拦截 |
| 随机布局软键盘 | 反编译看键位生成逻辑；实操：反复进出输入页面，截图比对键位 | 不随机 = 中；**页面载入时随机一次**（非每次点击输入框重随机）也算可预测（一次窥屏即失效）；仅使用系统键盘 = 高 |
| 屏幕录像 / 视觉回显 | ```bash
while true; do adb shell screencap -p /sdcard/$(date +%s).png; adb pull ...; done```；或 `/system/bin/fbtool -d /sdcard/screen.bmp`（需 root） | 输入时有**视觉回显**（按键高亮/气泡）→ 连拍即还原密码。无防截屏时**即使随机布局+无回显也会被截** |
| FLAG_SECURE 防截屏 | grep 密码/支付 Window 的加载处：`getWindow().setFlags(LayoutParams.FLAG_SECURE, ...)` | 未设置 = 高。**兼容性坑**：实测同版本 App 在不同机型结论相反（N/中兴可截图，ASUS TF300T 被阻止）——不要拿单机结果当全局结论 |
| 系统底层击键记录 | `getevent -p` 找带 `KEY_*` capability 的 device → 输密码时 `getevent /dev/input/eventN` | 能读到键盘码 = 高（需 root）。**新系统多已不向该节点输出事件**，拿不到击键不等于安全，只能记「未验证」 |

反向模拟输入（验证你能否重建用户操作）：
```bash
getevent -p /dev/input/event0                 # 看设备类型与支持事件
sendevent /dev/input/event0 1 2 1             # type=EV_KEY code=2(KEY_1) value=1
sendevent /dev/input/event0 0 0 0             # SYN_REPORT
sendevent /dev/input/event0 1 2 0             # 抬起
```

### 三件套的最优组合（写加固建议时用）
1. 自带**每次点击均重新随机**布局的加密软键盘（含数字键盘）
2. 密码/支付窗口开启 `FLAG_SECURE`
3. 输入框无视觉回显 + 禁止第三方输入法（`setInputType` 配 `IME_FLAG_NO_PERSONALIZED_LEARNING` 仅为缓解，真正阻断需自绘键盘）
