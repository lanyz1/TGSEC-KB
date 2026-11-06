---
name: ios-real-rce-payloads
description: >-
  iOS 真机 RCE / infoleak 载荷验证。只认可复现日志，不认概念链。
  触发：iOS 真实 RCE、exploit payload、WebKit 到内核组合、aks_oob.log、
  CONFIRMED_KASLR、真机侧载复测。
  应用面走 ios-pentest；内核判定走 ios-kernel-exploitation。
---

# iOS 真机 RCE / 载荷验证

## 本仓探针

```bash
python3 tools/ops/ios_surface_probe.py lab --path <日志> --case <案>
```

L2=build 或 AKS 痕迹。证据进案卷 `测绘/`。

「真实」= 授权机上跑出原件日志。没有 log 就是 `NOT_RUN`。

先读：`docs/playbooks/iOS内核与RCE研究手法.md`  
应用面复测：`docs/playbooks/iOS渗透测试/部署与复测.md`

```bash
python3 ios-research/tools/aks-oob/bin/aks_oob_lab.py doctor
python3 ios-research/tools/aks-oob/bin/aks_oob_lab.py classify --log <aks_oob.log> --build 23G71
```

## 和内核卡的分工

| 卡 | 负责 |
|----|------|
| `ios-kernel-exploitation` | 原语、版本、AKS 研究档、分流 |
| 本卡 | **载荷是否在真机成立**：侧载、点 Run、classify、落证据 |
| `ios-webkit-hunt` | WebContent / JSC 面，未接到内核不要写「已 RCE 到 root」 |
| `ios-pentest` | App 沙箱、Keychain、流量 |

## 验证步骤

1. `doctor`：xcodebuild + iphoneos SDK + 真机。有 blocker 就停。  
2. `build --team --udid` 侧载。  
3. 真机点 Run，取出 `aks_oob.log`。  
4. `classify`。阳性才进 `测绘/findings.md`。  
5. 资产面另走 `ios_crypto_loot.py scan --path <导出>`，与内核不要混报。

## 链怎么写（诚实）

```
WebKit/JSC 原语（若有）→ 沙盒仍在 → 内核 infoleak（65343 到 slide/kptr）
  → 还不等于任意内核 R/W，更不等于钱包已拖走
```

后半段（任意写、越狱、持久化）以 `ios-research/docs/` 当前笔记为准；缺 PoC 就写 coverage「未测」，不要补假脚本名。

## 证据

`exports/bot-recovery/<案>/测绘/ios/65343/`

- `aks_oob.log` 原件  
- `classify.json`（verdict / kptr_count / note）  
- 构建号（23G71 / 23G83）

转账、改密码、清数据：先问。

## 真源

- 手法：`docs/playbooks/iOS内核与RCE研究手法.md`
- 工具：`python3 ios-research/tools/aks-oob/bin/aks_oob_lab.py classify --help`
- 分流：`python3 tools/ops/hypothesis_route.py --signal 65343`
- 研究：`ios-research/docs/真实RCE载荷技术集成.md`（当笔记，不以文中未落地脚本为准）

## Exploit Chain 代码库（2026-09-16 整合）

完整利用链代码已整合到 `ios-research/exploit-chains/`：
- **Stage1-3**（Coruna 三段链）：覆盖 iOS 13–17.2.1 的完整 WebKit→SBX→Kernel 路径
- **Client CVE Exploits**：CVE-2025-43529, 43520, 24201, 14174, 31200 独立 exploit
- **Kernel Priv（iOS 26）**：`kernel_priv_26.js` PPL v2 绕过
- **Beacon C2**：AES-GCM beacon + Shell/Screen 客户端
- **Build Profiles**（14 套）：`ios-research/profiles/` 覆盖 iOS 15.3–26.3
- **Payloads**：`ios-research/payloads/` bootstrap.dylib + manifest

索引：`ios-research/exploit-chains/README.md`
