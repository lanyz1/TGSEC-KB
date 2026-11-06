<!-- archived from /root/.hermes/skills/security/reverse-engineering-sec/SKILL.md on 2026-10-21 -->

---
name: reverse-engineering-sec
description: "SKILL: 逆向工程 — 专家攻击手册"
---

> 归档卡：原目录 `/root/.hermes/skills/security/reverse-engineering-sec`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/reverse-engineering-sec/…')`，不要相对 `references/legacy/` 解析。

# SKILL: 逆向工程 — 专家攻击手册

> **AI LOAD INSTRUCTION**: 2026年逆向工程全栈技术。覆盖AI辅助逆向(GhidrAssist/GEPETTO/VulChatGPT/Binary Ninja Sidekick/HELIOS)、移动应用逆向(Frida/Objection/JADX)、二进制分析(angr/SysFuSS/Bangr)、固件逆向(SWD/JTAG/SPI嗅探/CH341A)、反混淆(Squanchy/SiMBA++/wasm2c)、WebAssembly逆向(WABT/SeeWasm)、加密协议逆向(CryptoLyzer/CryptoBap/侧信道形式化分析)、硬件逆向(ChipWhisperer/DPA/电压毛刺)。核心CVE：CVE-2026-3142(OpenSSL HollowByte)、CVE-2026-33697(Attested TLS)、CVE-2026-0947(MCP证书链绕过)。



> **🧩 切片技能** — 本 SKILL.md 为索引。详细内容在 `references/`，每份 < 4500 字符（不会被压缩器裁剪）。
> 按需加载: `skill_view(name, file_path="references/章节文件.md")`。多切片章节加载后按文末导航续读。

---

- **00** RELATED ROUTING → `references/chapter-00-related-routing.md`
- **01** AI辅助逆向工程 — 2026核心战场 → `references/chapter-01-ai-2026.md`
- **02** 移动应用逆向 — Android & iOS → `references/chapter-02-android-ios.md`
- **03** 二进制分析与漏洞挖掘 → `references/chapter-03-.md`
- **04** 固件逆向工程 → `references/chapter-04-.md`
- **05** 反混淆与反反调试 → `references/chapter-05-.md`
- **06** WebAssembly逆向 → `references/chapter-06-webassembly.md`
- **07** 加密协议逆向 → `references/chapter-07-.md`
- **08** 硬件逆向 — 侧信道攻击与故障注入 → `references/chapter-08-.md`
- **09** 2026逆向工程技术矩阵 → `references/chapter-09-2026.md`
- **10** 测试检查清单 → `references/chapter-10-.md`
- **11** OLLVM 混淆逆向 — 控制流恢复与MBA化简 → `references/chapter-11-ollvm-mba-01.md` (+2 续篇)
- **12** UPX 脱壳与反脱壳对抗 → `references/chapter-12-upx.md`
- **13** 商业壳逆向 — VMP/Themida/Enigma → `references/chapter-13-vmp-themida-enigma.md`
- **14** 压缩逆向 — gzip/LZMA/Zstd/LZ4 → `references/chapter-14-gzip-lzma-zstd-lz4.md`
- **15** .NET 反混淆与脱壳 — ConfuserEx/Eazfuscator/dnGuard/.NET Reactor → `references/chapter-15-net-confuserex-eazfuscator-dng-01.md` (+1 续篇)
- **16** Java/Android 加固脱壳 — ProGuard/Allatori/360加固/腾讯乐固/爱加密 → `references/chapter-16-java-android-proguard-allatori-01.md` (+1 续篇)
- **17** 反调试技术深度对抗 — PEB/VEH/时序/硬件断点/DBI 检测 → `references/chapter-17-peb-veh-dbi-01.md` (+1 续篇)
- **18** 动态二进制插桩(DBI) — DynamoRIO/Intel PIN/Frida/QBDI → `references/chapter-18-dbi-dynamorio-intel-pin-frida-01.md` (+1 续篇)
- **19** 模拟执行框架 — Qiling/Unicorn/QEMU-user → `references/chapter-19-qiling-unicorn-qemu-user.md`
- **20** 符号执行与污点分析深度应用 — angr/KLEE/Manticore/Triton/QSYM → `references/chapter-20-angr-klee-manticore-triton-qsy-01.md` (+1 续篇)
- **21** 二进制差分与补丁分析 — Diaphora/BinDiff/DarunGrim → `references/chapter-21-diaphora-bindiff-darungrim.md`
- **22** iOS 应用脱壳与逆向 — frida-ios-dump/Clutch/dumpdecrypted → `references/chapter-22-ios-frida-ios-dump-clutch-dump-01.md` (+1 续篇)
- **23** 恶意软件动态分析 — 沙箱对抗/API监控/YARA规则 → `references/chapter-23-api-yara-01.md` (+1 续篇)
- **24** DRM与许可证保护逆向 — keygen/许可证验证patch/硬件指纹 → `references/chapter-24-drm-keygen-patch-01.md` (+1 续篇)
- **25** NEXT ROUTING → `references/chapter-25-next-routing.md`
