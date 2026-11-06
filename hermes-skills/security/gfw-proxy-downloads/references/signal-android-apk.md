# Signal 安卓官方 APK（2026-08 实测）

## 关键事实

- 官网 APK 页：https://signal.org/android/apk/ （页面底部 "Danger zone" 区）
- 推荐路径仍是 Google Play（`org.thoughtcrime.securesms`），但国内同样要代理
- **signal.org 在国内被墙**：直连 `HTTP:000`，必须走本机代理（10808）
- 页面按钮由 mustache.js 模板渲染，数据来自 `https://updates.signal.org/android/latest.json`

## latest.json 结构（官方版本/哈希/直链的唯二来源之一）

```json
{
  "versionCode": 173701,
  "versionName": "8.23.3",
  "sha256sum": "de0b92239854a36111eb7a3dcd982ab42663f491ff5ebbce9402542df1e793e4",
  "url": "https://updates.signal.org/android/Signal-Android-website-prod-universal-release-8.23.3.apk",
  "uploadTimestamp": 1787156397737
}
```

- URL 规律：`https://updates.signal.org/android/Signal-Android-website-prod-universal-release-{versionName}.apk`
- **旧文件名 `signal-website-universal-release-{v}.apk` 已 404**，别用
- universal 版兼容 arm64/arm32/x86 全架构，要求 Android 6.0+
- 大小 ≈ 115.8 MB（121,416,446 字节），Content-Type: `application/vnd.android.package-archive`

## 官网给出的校验信息

- 4096-bit 签名证书 SHA-256 指纹（apksigner 校验用）：
  `4B:E4:F6:CD:5B:E8:44:08:3E:90:02:79:DC:82:2A:F6 5A:54:7F:EC:C2:6A:BA:7F:F1:F5:20:3A:45:51:8C:D8`
- 校验命令：`apksigner verify -v --print-certs --min-sdk-version 24`

## 完整下载命令（本机实测，走代理）

```bash
# 1. 拿最新版本信息
curl -sL -x http://127.0.0.1:10808 -A "Mozilla/5.0" "https://updates.signal.org/android/latest.json"

# 2. 下载到桌面（带进度条，115MB 走代理约 5 分钟）
cd "$USERPROFILE/Desktop"
curl -# -L -x http://127.0.0.1:10808 -A "Mozilla/5.0" \
  -o "Signal-Android-8.23.3-official.apk" \
  "https://updates.signal.org/android/Signal-Android-website-prod-universal-release-8.23.3.apk" \
  --max-time 500

# 3. 校验：结果须与 latest.json 的 sha256sum 逐字符一致
sha256sum Signal-Android-8.23.3-official.apk
```

## 手机端提醒

手机装 Signal 后，注册/同步也要连 Signal 服务器——国内手机需同时挂代理，否则装上了也用不了。
