---
name: flutter-app-reverse
description: "Use when reversing Flutter apps via libapp.so/blutter."
version: 1.0.0
tags: [reverse, flutter, dart, blutter, mobile, apk]
---

# Flutter App 逆向（libapp.so / blutter 全反编译）

来源: 2026-10 赌博白标矩阵实战（kkguoji/快快国际 App）——从 APK 拿到全部硬编码密钥与反封锁体系。

## 0. 识别与快分

Flutter App 特征（unzip -l 一眼）：
```
lib/arm64-v8a/{libapp.so, libflutter.so}
lib/armeabi-v7a/{libapp.so, libflutter.so}
assets/flutter_assets/...   (+ AssetManifest.json)
```
- `libapp.so` = Dart AOT 代码 + **字符串常量**（URL/路径/密钥候选都在里面）；`classes.dex` 只是壳。
- iOS 侧 `Payload/Runner.app/Frameworks/App.framework/App` = iOS AOT，**blutter 不支持**（仅 Android libapp.so arm64）→ strings 能捞多少算多少。

## 1. strings 快扫（先做，5 分钟出第一批金）

对 `lib_arm64-v8a_libapp.so` 做字符串提取，重点 regex：
- `https?://...`（基建域名、anti-block/反封锁域）
- `package:<pkg>/...` 之类 **App 自己的 Dart 文件路径**（一次拿到完整功能图谱：api/、pages/、services/、crypto_helper 直接暴露）
- `/api/...` 路径串；`[0-9a-fA-F]{32,}` 密钥候选（注意大量是 EC 曲线常量噪声，`04…` 开头排除）
- `Key("...")` / `decrypt64` / `AES` 邻近上下文（用 keywords 开窗 ±800B 抽周围字符串）
- **自建 IM（OpenIM 系）识别**：`package:openim*` / `openim_common` / `flutter_openim_sdk` 包路径 + `/msg_gateway`、`:10001`/`:10002`/`:10008`、`openim.io` 文档串 → 目标是自建 OpenIM 服务端（Web 控制台可换壳名，如「OpenCorp」）→ 打 `/api`(用户API)、`/chat`(管理API，需 `operationID: <uuid4>` 头)、wss `/msg_gateway`；细节走 `chinese-private-im`。

## 2. blutter 全反编译（拿到 Dart 伪代码）

环境（Ubuntu 24.04 实测；**必须用 /usr/bin/python3**，venv python 没有 elftools/capstone）：
```bash
apt-get install -y cmake ninja-build clang python3-pyelftools python3-requests python3-capstone libicu-dev libcapstone-dev
# clang>=16 / gcc>=13 必需（Ubuntu 24.04 的 clang18 可用）
git clone --depth 1 https://github.com/worawit/blutter.git /root/blutter
# 从 APK 解出整个 lib/arm64-v8a 目录：
unzip -o -j app.apk "lib/arm64-v8a/*" -d lib/arm64-v8a
/usr/bin/python3 /root/blutter/blutter.py lib/arm64-v8a /root/blutter/out
```
- 自动识别 Dart 版本 → 下载对应 Dart 源码 → 编译 Dart VM：**20-40 分钟**，放后台 + notify。
- 产物：`out/asm/<package>/.../*.dart`（逐文件 Dart 伪 disassembly，注释里带 pp 引用）；`out/pp.txt`（对象池全量常量）；`out/objs.txt`、`blutter_frida.js`、`ida_script/`。

## 3. 定位敏感逻辑（实测路径）

1. `grep -n "findAvailableDomain\|aesDecode\|decrypt" out/asm/<pkg>/services/*.dart`
2. 读该函数附近的 asm：常量就在注释里出现 —— 例：
   ```
   r16 = "e0df2f9aa60f4bd70fd05714d5d7cea0"   // Key() 的参数
   bl  #... Encrypter::decrypt64
   ```
   → 即 **AES key = UTF-8 的 32 位十六进制串**（AES-256），数据=base64 密文（`decrypt64`）。
3. 请求加密链：`services/http_service/http_interceptors.dart`；环境/域名：`services/app_env_config.dart`；常量：`common/crypto_helper.dart`。
4. 全量 API 路径：grep `out/asm/**/*.dart` 里引号路径串 + 交叉 `common/api/*.dart`（比 Web 端 JS 全）。

## 4. 解密“App 启动拉取的加密列表”的通用解

反封锁/配置域表常是：`GET https://anti-block.<x>.com/<brand>_base.txt` → base64 密文。
试解矩阵（`scripts/decrypt_b64_candidates.py`）：
- key 形态：utf8(32字符hex串) / hex-decode(16B) × 模式 ECB / CBC(iv=0) / CBC(iv=key[:16])
- 命中判据：明文出现 `http` 或 `.com/.cn/.net` 等域名字符。

## 5. Pitfalls

- **headed browser/playwright 需 xvfb-run**（无 X 直接 TargetClosedError）。
- venv python 缺 elftools/capstone → 一律 `/usr/bin/python3`；apt 的 python3-capstone 4.x 与 blutter 兼容。
- `strings` 对 iOS AOT 常一无所获；Android libapp.so 才是主战场。
- 密钥可能是**代码构造**（拼接/派生）而非明文——pp.txt 里搜不到就去 asm 里读构造函数；先试简单形态（utils 里的 Key(常量)）。
- 大量 32-64 位 hex = EC 曲线表噪声，别全试。
- 冷启动 App 的部分域名（储备域）公共 DNS 不解析——常态，不是 extract 出错。
- **APK 获取坑**：分发包链接可能伪装成 `.html` 但直接回 ZIP 二进制（`file`/PK magic 先验，别被扩展名骗）；curl 限时截断 → `BadZipFile`，用 `curl -C -` 续传并核对 final size（实测 88MB 截断 → 续传至 238MB 完整）。

## Support files
- `references/kkguoji-antblock-case.md` — 完整案例（反封锁解密→40 域→门户链）。
- `scripts/decrypt_b64_candidates.py` — base64+AES 多形态试解器。
