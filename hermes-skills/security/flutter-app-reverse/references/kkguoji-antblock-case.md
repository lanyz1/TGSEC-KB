# 案例：kkguoji 赌博 App 反封锁体系全解（2026-10）

目标: 赌博白标集团（uulai/U8 等 6 品牌）Flutter App。
路径: 未授权版本接口拿 APK (113MB) → strings 快扫 → blutter 全反编译 → 密钥提取 → 反封锁域表解密。

## 关键提取

- 包名: `package:kkguoji/...`（361 个 Dart 文件路径，一次拿到全功能图谱）
- 反封锁域: `anti-block.{dfklssd,dsklgllas,gfdhg,sldgjsdm}.com/<brand>_base.txt`（brand = uulai/u8/uu6/9u/u69/xyw）
- **AES key: `e0df2f9aa60f4bd70fd05714d5d7cea0`**（UTF-8 32 字符 → AES-256；模式 ECB；`Encrypter::decrypt64`）
  - 解密函数位置示例: `out/asm/kkguoji/services/app_env_config.dart` 中 `AppEnvConfig::aesDecode`
  - 同一 key 同时出现在 Web 端（U8.com 内联 `VITE_ENCRYPT_KEY`）——App/Web 共用密钥很常见
- App 全 API 122 条（含 `/api/agent/*` 代理中心族、`/api/public/register_email`、彩票返佣）

## 反封锁域解密后结构

- 每品牌一组域：活口门户 /「最优线路」调度页 / CF 挑战域 / 公共 DNS 不解析的储备域（占比高，正常）
- 调度链例: `u8.com → teosdf.com → spogiopej.com`；`lotteryac/cp → algkhdghg.com`
- CF WAF 可对同一站做「HTML 放行 / `/api/*` 全 403」双轨规则（IP/地区维度；curl_cffi 指纹无效）

## 客户端加密链（与 Web 端一致）

- 请求: AES-ECB(16位随机key) 加密 body + RSA(JSEncrypt 公钥) 加密 aeskey → `Encry-Key` 头
- 响应: 同 aeskey 反解 base64

## 工具链备忘

- 依赖: cmake ninja-build clang(>=16) python3-pyelftools python3-requests python3-capstone libicu-dev libcapstone-dev
- 运行: `/usr/bin/python3 blutter.py <lib/arm64-v8a> <out>`（venv python 缺 elftools 会报 ModuleNotFoundError）
- 编译 Dart VM 20-40 分钟 → 后台跑 + notify
