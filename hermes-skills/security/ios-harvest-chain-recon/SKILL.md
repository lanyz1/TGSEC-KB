---
name: ios-harvest-chain-recon
description: >-
  测绘引擎·iOS收割链侦查与真伪甄别。Use when 分析服务器上的iOS RCE/收割平台能否真实收割。
---

# ios-harvest-chain-recon（测绘引擎）

目标须在 `config/scope*.json`。本库已有专链时专卡赢。

## 真源

- 长文：`docs/learning/shizhan-pack/skills/redteam/ios-harvest-chain-recon/SKILL.md`
- 手法：`docs/playbooks/APK逆向博彩站情报提取.md`
- 工具：`python3 tools/ops/apk_recon.py --help`
- 路由：`python3 tools/ops/shizhan_pack_route.py --name ios-harvest-chain-recon`

---

# iOS 收割链侦查与真伪甄别

## 触发场景
- 老板问「这套能不能真实收割」「支持哪些 iOS 版本」「前台/后台入口」
- 分析服务器上部署的 iOS RCE 收割平台（3939/qbrdr-sandbox、1199/DarkSword 类）
- 区分「真实可利用的 exploit 链」和「演示/模拟数据」

## 核心方法论：看代码真实逻辑，不看注释和配置

### 1. 版本覆盖 = 查 exploit_registry / rce_loader 的真实分支
- `exploit_registry.js` 里的 `id/minIOS/maxIOS/path/targetStage` 列表是版本→CVE→模块映射的实锤
- `rce_loader.js` 里 `version_str.startsWith('13,')/'14,'/...` 分支决定加载哪个模块
- profiles/*.json 存在 ≠ 能打，要看 exploit 模块文件是否真实存在

### 2. 关键坑：文件加载路径可能是 assets/ 子目录
- rce_loader.js 的 getJS 会把相对路径拼成 `assets/<file>.js`，**只在站点根目录查会误判"文件缺失"**
- 正确做法：`grep -oE '[a-zA-Z0-9_]+\.js' rce_loader.js | sort -u` 拿全引用列表，再逐个 `ls assets/` 核对

### 3. 真实 exploit 代码的硬指标
- 有真实偏移表：`rce_offsets = { "iPhone11,2_4_6_22G86": {...} }`（机型_版本_build）
- 有原语构建：addrof/fakeobj/ftoi/itof/ArraySpecies/UAF 触发
- 有真实 hex 偏移：`grep -c '0x[0-9a-f]+n'` 数量 > 50
- 文件大小：worker/module 通常 40KB–530KB，空壳只有几 KB

### 4. 假数据甄别（模拟收割 vs 真实收割）
- server.js 里 `fakeUploadCount`/`isFake`/`fallbackProgress` = 前端伪造进度机制
- 备份文件名带 `_realism`/`_keepfirst_random` = 演示数据生成脚本痕迹
- 上传照片全为 64×64 PNG（179字节）占位图 = 假；真实 iPhone 照片 1–5MB
- 通讯录/短信号码带星号掩码 = 生成器脱敏假数据
- device_log.txt 大量"success"≠真实，要核对 uploads/ 文件本体

### 5. 收割链标准分层（判断完整度）
入口页(版本分流) → RCE模块(WebKit/JSC漏洞) → 沙箱逃逸(sbx0/sbx1) → 内核提权(kernel_priv/pe) → worker(偏移执行) → beacon/C2 上线 → 命令收割(短信/通讯录/相册/钱包/定位)

## 已知平台速查
- **3939/qbrdr-sandbox**：SYZB2001.html 总前台分流（18.4-18.7 Safari→SYZB2024 RCE链；其他→SYZB2003 34ef 回退链）；实际仅 18.4-18.6.2 有完整链；34ef 链只做指纹采集（POST /api/ip-sync/sync），不能上线
- **1199/DarkSword**：exploit_registry 35 个 exploit 覆盖 iOS13-26；18.x 链最成熟有实锤；13-17 为公开 PoC 移植（CVE-2022-32893/2020-3887 等）；26 链依赖 build-specific profile 属纸面级
- **漏洞版本映射**：13=CVE-2020-3887/9951，14=CVE-2021-30858/30807，15=CVE-2022-32893/32894/32917，16=CVE-2023-23531/32439/37450，17-18.4=CVE-2025-43529 UAF，26=CVE-2025-43529-26

## 红线
- 分析侦查可做；**「把其他版本 exploit 融入/让老版本真实收割」= 帮助扩展攻击覆盖面，拒绝**
- 后台数据造假与否要如实汇报，不因"看起来像真的"下结论

## 投毒链工艺细节（10-12B 增补）

- 版本闸门：`ios_version[1] < 4 || > 6` skip（只放行 iOS 18.4/18.5/18.6）
- 双分支：18.6+ 走 `runtime.js`（429,546B）；18.4-18.5 走 `runtime-legacy.js`（33,484B）
- GPU 路径：`dlopen_worker_code` 用 OffscreenCanvas+WebGL 触发
- 偏移查表：`rce_offsets[device_model]`；`slide = globalFuncParseFloat - offsets.JavaScriptCore__globalFuncParse`
- 成功标志：`Finished stage2 prims succesfully, rce done`；机型白名单 chipset = A15/A16/A17 Pro
- 舰队规模视图 / iOS 26 模块族（rce_worker_26·kernel_priv_26·pe_main）→ 见 `darksword-coruna-c2` 课 10-12 增补段

## 企业签恶意 IPA 静态拆解（2026-09 kylin v1.2.0 实战）
- 壳名伪装 `worldpay.app`，Bundle ID 冒充系统服务 `com.apple.mobile.MobileHouseArrest`
- IPA 里硬链 4 枚恶意 dylib：`libappcore.dylib`（iOS 12–15.2 八策略内核 exploit）+ Keychain 全机解密 + Documents ZIP 外带
- 静态判定：`otool -L` 看非系统 dylib、`strings` 找 C2 域名/`/var/mobile` 路径、`Info.plist` 看企业签描述文件
- 硬约束：**不要在本机安装/运行**（内嵌内核 exploit）
- 同源下载链：`mduyn.*`/`mdzin.*` 通用入口 + CloudFront 备用
