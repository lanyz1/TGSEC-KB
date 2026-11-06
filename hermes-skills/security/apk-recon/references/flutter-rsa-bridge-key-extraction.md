# Flutter APK 内嵌 RSA 私钥 + 爱加密加固 + 公开配置仓 — xinbi.com 实战

> 来源：xinbi.com 20 阶段全链渗透报告 P2/P10/P16/P17

## APK 样本矩阵

| 样本 | 来源 | 大小 | 框架 | 加固 |
|------|------|------|------|------|
| SafeX_3.7.1.apk | `sfw.vc/official/app/downurl` | 78.8 MB | Telegram Android 分支 | **爱加密(ijiami)** |
| xpay_v1.6.0_test.apk | S3 dev 桶 | 38.7 MB | **Flutter** + native RSA | 无 |
| xpay_0827_pro.apk | S3 prod 桶 | 38.9 MB | **Flutter** + native RSA | 无 |

## 爱加密加固识别

```
# 特征文件
assets/ijiami.dat
assets/ijm_lib/{armeabi,armeabi-v7a,x86,x86_64,arm64-v8a}/libexec.so
lib/*/libexecmain.so
lib/*/libijm_linker.so
lib/*/libijm-emulator.so     # 反模拟器
lib/*/libijmdetect-drisk.so  # 风险环境检测

# 壳 stub
classes.dex → 13,616 B（极小，仅壳代码）
真实业务代码在加密载荷中
```

→ jadx 无法获取业务代码；需 root + frida-dexdump 脱壳。

## RSA 私钥提取（严重发现）

### 发现位置
`lib/arm64-v8a/libapp.so`（Flutter AOT 编译产物）中**明文 base64 编码的 PKCS#8 私钥**。

### 密钥详情

| 项 | 值 |
|----|-----|
| 类型 | RSAPrivateKey (PKCS#8, 未加密) |
| 长度 | **1024 bit** |
| 公钥指数 e | 65537 |
| 配套公钥 | 同一 APK 另一处内嵌，与私钥完全匹配 |
| 使用框架 | `librsa_bridge.so` = [github.com/jerson/rsa-mobile](https://github.com/jerson/rsa-mobile) |

### 相关算法字符串
```
RSAES-OAEP
RSA_ECB_PKCS1Padding
AES_CBC_PKCS7Padding
aes128/192/256-CBC
IV is required.
XPay will encrypt your information without any verification
```

### 用途判定
- **不是** API 签名密钥（用官方 signData 规则签名 12 组全部验签失败）
- 属于**客户端加密/密钥交换**用途：
  - 配套接口 `POST /common/exchange`（交换秘钥）→ 返回 `{serverAccessKey, serverAccessKeyToken}`
  - 公钥加密敏感字段（KYC、支付密码），私钥解密服务端下发内容
- **客户端同时携带公钥和私钥属严重设计缺陷**

### dev 与 prod 同一把钥
dev APK（xpay_v1.6.0_test）与 prod APK（xpay_0827_pro）**内嵌完全相同的 RSA-1024 私钥**（模数一致）。

## 远程配置仓库泄露

### Bitbucket 公开仓库
```
https://bitbucket.org/xpay2050/xinbipay   (public, 8 commits)
https://bitbucket.org/xpay2050/supay      (public, 4 commits)

作者：
  alen <<EMAIL-REDACTED>>
  xpay <<EMAIL-REDACTED>>
```

### 域名轮换机制
```
APK 内字符串：
  "[domain] fetch domain failed, keep current baseUrl="
  "[domain] no available candidate found, keep current baseUrl="

配置源（APK 内嵌）：
  https://bitbucket.org/xpay2050/xinbipay/raw/main/domain.json
  https://gclg0uvcm.oss-cn-hangzhou.aliyuncs.com/domain.json

内容：加密 blob（AES-CBC + 未知密钥）
  {"data":"kvLN1GYN…O19g"}（96B）
```

→ **供应链风险**：若仓库被接管或密钥被逆向，可向所有客户端下发任意 API 域名。

## App 分发接口未授权

```
GET https://sfw.vc/official/app/downurl → 200
{
  "android": "https://423545.com/download_apk/com.mjsem1.inmehvfa_3.7.1.apk",
  "windows": "https://423545.com/download/SafeW_3.7.8.exe",
  "macos":   "https://423545.com/download/SafeW_3.7.8.dmg",
  "linux":   "https://423545.com/download/SafeW_3.7.8.tar.xz",
  "ios":     "/download/ios.ipa"  // 404
}
```

旧版本残留：`/download/SafeW_3.7.5.exe` → 200（可做版本差异分析）

## 代码签名不一致

| 版本 | Authenticode |
|------|-------------|
| 3.7.5 | ✅ Valid — `Th Technology Co., Limited`（香港 BR#76704717），Sectigo EV |
| 3.7.8 | ❌ **NotSigned** |

→ 新版本反而无签名 = 供应链信任降级

## 多实体归因

| 渠道 | 实体 |
|------|------|
| App Store (iOS) | FUKUDA BOUEKI LLC (日本) / SafeW Technology Co., Ltd. |
| Windows 版权 | SafeW FZ-LLC (阿联酋) |
| Windows 代码签名 | Th Technology Co., Limited (香港 BR#76704717) |
| Android 包名 | com.mjsem1.inmehvfa |
| Bitbucket 仓库 | xpay2050 / alen / xpay |

→ **4 个不同法人实体分发同一产品**，典型实体轮换规避策略。

## 测绘引擎适配

1. Flutter APK 的 `libapp.so` 是 AOT 编译产物，**strings 可直出内嵌密钥**（不需要 Dart 反编译）
2. `librsa_bridge.so` = rsa-mobile 开源库 → 已知接口，可构造调用
3. 爱加密加固特征：`ijiami.dat` + `ijm_lib/` + `libexec*.so` + 极小 classes.dex
4. 远程配置仓库（Bitbucket/OSS）是供应链攻击面 — 查看是否公开、是否可写
5. 同一运营方的多平台安装包要全拉（Android/Windows/macOS/Linux），私钥可能在某个平台明文
6. 版本差异分析：旧版有签名新版无签名 → 分发链可能已被污染
