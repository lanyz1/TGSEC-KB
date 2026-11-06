<!-- archived from /root/.hermes/skills/security/go-binary-reverse/SKILL.md on 2026-10-21 -->

---
name: go-binary-reverse
description: "Use when reversing Go binaries: pclntab, envelopes."
version: 1.0.0
tags: [reverse, golang, pclntab, capstone, c2, agent, tauri]
---

> 归档卡：原目录 `/root/.hermes/skills/security/go-binary-reverse`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/go-binary-reverse/…')`，不要相对 `references/legacy/` 解析。

# Go 二进制逆向：符号恢复 + 加密信封 + 客户端密钥矿

适用触发词：`pclntab`、Go 编译的 `.so`（`libclash.so`/`libgojni.so`/mihomo 内核）、
Go 写的 agent/C2/监控客户端、`{"iv":…,"payload":…}` 信封、Tauri 客户端、
符号被 strip 但需要找 `main.getRegisterKey` 这类私有函数、agent 的 AES key。

路线选择：**符号还在二进制里**（Go 不自带 strip 符号表）→ 先解 pclntab，
**不要**一上来就全量 capstone 扫或开 Ghidra 人肉追。

## 1. pclntab 符号恢复（纯 Python 就够）
- 搜 magic `\xf1\xff\xff\xff`（Go 1.16+ `0xFFFFFFF1`）→ `pcHeader{nfunc,nfiles,textStart,funcnameOffset,cuOffset,filetabOffset,pctabOffset,pclnOffset}`。
- **地址基准随构建方式变**：非 PIE Linux ELF ⇒ offset 是相对 **textStart 的 VA**；
  Android `.so`（PIE）⇒ 常是相对 **pcHeader 自身**。两种解释都算一遍，用判据选：
  ① 函数入口前一条指令应为 `ret`；② 函数名前缀应是包路径（`main.*`/`encoding/…`）。
- 解 `_func{entryoff, nameoff}` 表即可全量导出 `符号名 → 地址`（含私有函数）。
  本次由它定位 `main.pkcs7Pad/pkcs7Unpad` ⇒ **直接判定加密模式**（比追 `aes.NewCipher` 快）。
- **`_func` 布局在 Go 1.18~1.20 有 variant/padding**：解析器会「能跑但读出垃圾串」。
  先用 `runtime.main`/`main.main` 自校验，再全量导出；不要拿第一个不报错的版本当定论。
- 反汇编：`pip install capstone`，ARM64 = `CS_ARCH_ARM64`+`CS_MODE_LITTLE_ENDIAN`，x86_64 = `CS_ARCH_X86`+`CS_MODE_64`；
  **只反汇编 entryoff 定位到的那个函数**，别全量扫。

## 2. 加密信封：先定模式，再定密钥来源（顺序反了就烧时间）
- 外层形态：`{"iv":b64,"payload":b64}` ⇒ AES-CBC+PKCS7（iv 每请求随机）；`{"nonce":…,"data":…}` ⇒ GCM。
- **判模式靠 padding 函数**（见上），不靠猜；用客户端自己发的真实报文回测解码成功才叫定对。
- **密钥来源只有两类，先定类**：
  - 常量/环境变量/远端配置 ⇒ 静态可搜（`.rodata`、strings、它的 `/xxxregister.txt` 一类远端配置）——值得搜。
  - **运行时派生 / 堆上指针** ⇒ 静态无解。信号：静态候选全 0 命中 + 函数体内 key 来自参数或堆写入。
    这时写一句「key 运行时派生」就收手，转去打**下发通道**（面板 API/心跳响应）或直读它的 state 文件；
    不要做上千组字典爆（本次 1015 组派生 + 300 万组合全 0 命中，纯浪费）。

## 3. 免逆算法的捷径：去挖它的远端配置与更新链
- 逆向只做到「看出 key/iv 由调用方传入」就停，然后**去下它的远端配置**
  （`/bzyregister.txt`/`/hostdef.txt` 类）→ 一次拿到 key、iv、固定推广 ID、各品牌注册域。
  先看 smali/伪代码里的 URL 常量（`getBzyRegister()` 这类）再动手做数学。
- **PC 端 Tauri 应用**：`strings` 找参数名（`channelId/plat/ver/platver/br/md/selectNodeId`）+ 更新源
  （`raw.githubusercontent.com/<op>/updater/`）⇒ 顺仓库拿**全品牌更新清单**（品牌矩阵/分发域一键铺开），
  并用仓库里的 minisign 公钥确认分发链归属。
- 字段集要**精确**：从 `LoginAtyVM`/`HttpApi.smali` 这类界面类里取全字段名回打，
  别用猜的字段集下「服务端不支持」的结论。

## Pitfalls
- Go 二进制**不要先脱壳/strip 处理**——符号表本来就在。
- `crypto/rand.Reader` 这种符号出现在 key 邻近位置是**诱饵**（本次误判过一轮）。
- 大 `.so`（几十 MB）不要 `strings | 全字典` 生爆：先把候选限定到「长度 16/32 + 可打印 + 出现于相关函数附近」。
- 本地签名/加密猜测失败时，先怀疑**参数不全/编码不同**，再怀疑算法。

## Files
- `references/go-binary-symbol-and-envelope-recovery.md` — 完整实测记录：pclntab 定位表、
  `main.getSS1/getRegisterKey` 导出、agent 信封从 GCM 误判纠正到 CBC+PKCS7、运行时 key 判死、
  Tauri/updater 链挖品牌矩阵（2026-09-26）。
