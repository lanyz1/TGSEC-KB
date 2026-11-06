---
name: reverse-engineering
description: >-
  测绘引擎逆向总路由。看不懂该用哪把刀、加壳、还原算法、APK/JS/ELF/Mach-O/固件分诊时使用。
  先认族再开刀。有专链（假支付/盘口/Gateway）时专卡赢。（含 178 张归档子卡索引）
---

# reverse-engineering（测绘引擎总路由）

<!-- MERGED-INDEX:START -->
## 归档子卡（已合并 178 张）

- 索引：`references/index.md`
- 加载：`skill_view(name='reverse-engineering', file_path='references/legacy/<name>.md')`
- 子卡脚本/字典仍在原目录（索引里给了绝对路径），可直接 `read_file` / `terminal`。
- **先按本卡判据决策**；本卡不够时才展开对应子卡，不要一次全读。
<!-- MERGED-INDEX:END -->


目标须在 `config/scope*.json`。本卡**只负责认族和交接**，不代替专卡，不堆工具百科。

## 真源

- 作业手法：`docs/playbooks/测绘引擎逆向作业手法.md`
- 专题分流：`docs/playbooks/逆向专题分流手法.md`
- 缺口与路由表：`docs/playbooks/逆向技能缺口与路由手法.md`
- 路由 JSON：`tools/ops/reverse_routing.json`
- 分诊：`python3 tools/ops/re_sample_triage.py --path <样本>`
- 指路：`python3 tools/ops/reverse_skill_route.py --hint "<任务>"`

## 立刻跑

```bash
# 有文件：认族（不联网）
python3 tools/ops/re_sample_triage.py --path <样本> --case <案>

# 有原话：专卡
python3 tools/ops/reverse_skill_route.py --hint "<用户原话>"
python3 tools/ops/reverse_skill_route.py --self-test
```

PRIMARY 打开后立刻跑那张卡的默认命令。停在本卡读百科 = 没干活。

## 四刀

1. **认族** — 魔数 / 包内文件名 / `go.buildid` / `webpackChunk` / `V1MMWX`
2. **dump-first** — 壳、加密 so、动态 DEX 先落地明文
3. **观察-采样-复现** — 页面证据 → 本地最小脚本，禁止空想补环境
4. **过闸** — 服务端接受，或本地对同一输入复现签名

## 交接（只开一张主卡）

| 认到 | 走 |
|------|----|
| APK 情报 / 密钥 / 后台路径 | `apk-recon` |
| APK 完整反编译 / smali / 重打包 | `apk-reverse` |
| JNI `em5` / OSS STS | `apk-jni-sign-oss-sts` |
| 钱包 `libtcx` / BIP39 | `wallet-core-reverse` |
| 前端签名 / `.map` / JSVMP | `js-reverse` |
| webpack / js-websocket / 国密 clientapi | `spa-protocol-reverse` |
| wxapkg | `wxmini-static-audit` |
| Go / Rust 剥离 | `go-rust-reverse` |
| 无 IDA | `ghidra-reverse` |
| PE / so 深挖（本机有 IDA） | `ida-reverse` |
| PCAP / Protobuf / 私有 TCP | `protocol-reverse` |
| crx / xpi | `browser-extension-reverse` |
| Unity / IL2CPP / 反作弊 / 外挂 | `client-crack-cheat` |
| IPA | `ios-pentest`（内核另开 `ios-research/`） |

同族不并行。`next` 是交接不是第二张一起开。

## 禁止

- 编不存在的脚本（`decode.ps1` / `start.ps1` / `sm_crypto_client.js` 仓库里没有就说没有）
- 编成功率、假 CVE、一键内核 exploit
- 未授权 `--target` 仍 ACT
- 专卡阴性直接写复工结案

## 证据

`测绘/re_triage/sample_triage.json` + 专卡自己的目录。密钥打码。

