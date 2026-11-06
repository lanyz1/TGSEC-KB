---
name: apk-implant-cheat-reverse
description: "游戏APK内置外挂逆向:so替换植入/假SDK/隐藏dex/卡密授权so。"
---

# 游戏内置外挂逆向 · so 替换式植入取证

授权本地样本专用。「内置外挂」结论必须落到证据，不许靠 strings 猜。
触发词：内置外挂、so替换植入、假SDK、导出符号伪装(AceProvideJavaVmV1)、隐藏dex、
键鼠映射外挂、自瞄、卡密授权so、OLLVM、il2cpp外挂、重打包植入。

## 结论分档

| 档 | 成立 |
|----|------|
| 认到 | 有第三方 so/dex，导出名可疑 |
| 实锤 | ① mtime 时间线：植入文件独立于游戏构建时间、与重签名同分钟 ② 真身鉴别：so 内只剩外挂源文件名、零原 SDK 特征 ③ 加载链：manifest/smali 原本就 `loadLibrary(该so名)`，外挂借此自动跑 |
| 完整 | 功能全谱（字节码+JNI 注册表）+ 卡密授权链双还原 |

## 五步

```text
① 包级指纹  apktool d / unzip → manifest、lib/、dex 数、META-INF 签名条目
② 时间线    lib/*.so、classes*.dex、META-INF 逐条 mtime 排序 → 后塞者差数月
③ 真身鉴别  strings 源文件名残留 + 导出表（假 ACE / 假 SDK 同名替换）
④ 隐藏载荷  so 内扫 dex\n035 magic → 按 header size 切片 → jadx/javap
⑤ 功能还原  导出函数表 + JNI 注册表 + .data 配置键 → 功能全谱；卡密链单独还原
```

```bash
python3 scripts/apk_implant_probe.py apk --path target.apk --analyze-so
python3 scripts/apk_implant_probe.py so  --path libztgame.so --dump-dex out/
```

## 三件套判据（横向可换）

1. **本体 so**：替换原 SDK 同名 so 但保留其标准导出名（`AceProvideJavaVmV1`=冒充腾讯 ACE）。真身靠内部字符串（`KeyMouseMapper.java`/`ImGui.java`）+ 导入画像：`dlopen/dlsym/dl_iterate_phdr` 找 il2cpp 基址、`mprotect/memcpy` inline hook、`sigaction/fork/waitpid/getppid` 反调试、`getauxval` 取 linker 基址。
2. **授权 so**：独立卡密模块，导出 `*InitCardKey/Login/CheckLogin/QueryStatus/Begin|CompleteKeyExchange` 一族；内含手工 ELF 解析（`e_phoff` 校验、`symbol not found`）= linker 绕过/符号劫持。
3. **隐藏 dex**：不落 APK，运行时由 so 释放；其类清单即功能清单。

## OLLVM + 可执行 .bss

别硬刚反编译：**字符串/导出/导入/配置键**四样即可定性。真身函数可在 `JNI_OnLoad` 运行时解密到可执行 `.bss`，静态不可见 → Frida attach 后 dump。

## 强制

1. 只有 strings 不算实锤；时间线 + 加载链才闭环。隐藏 dex 必须真提出（offset+size+类清单）。
2. **导入画像只是线索不是结论**：正常库（VPN/加解密/MMKV）天然带 `fork/waitpid/dlopen/mprotect`；必须与「时间线 + 导出名替换 + 内嵌 dex」合判。
3. **时间线可能被归一化**（apktool/AS 打包会把 zip 时间戳写死成 1981-01-01，实测 v2rayNG）→ 改用签名块证书/`.comment`/AndroidIdent note/内嵌 dex 存在性作替代证据，见 references。
4. 只做样本逆向取证，不做他人局对抗；native 静态还原不了就明说边界+给动态补齐路径，不许编造 C 源码。

## 关联与真源

上级 `client-crack-cheat` ｜ 解包重打包 `apk-reverse` ｜ 卡密家族 `net-license-crack` ｜ 运行时 `android-app-runtime-analysis` ｜ 壳 `vm-and-bytecode-reverse`
细节：`references/so-implant-forensics.md`、`cheat-mechanics.md`、`cardkey-so-protocol.md`、`case-ztgame-keymouse.md`；探针 `scripts/apk_implant_probe.py`
