---
name: webapp-rebuild-from-recon
description: "重建丢失源码的Web应用: 源码包+架构+API文档。触发: 恢复源码, 源码丢了, 复刻系统, 一模一样。"
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='webapp-rebuild-from-recon', file_path='references/full.md')`

# 从 Recon 逆向重建 Web 应用(源码恢复/复刻)

用户丢失源码时,从线上站点完整逆向重建:前端保真 + 后端行为等价。交付 = 可运行源码包 + 架构分析 + API 文档(用户画像:破解/渗透成功后常要求"一模一样"复刻部署)。

<!-- split-index -->

## Section index

- [When to Use](references/split-01-when-to-use.md)
- [工作流](references/split-02-section.md)
- [环境准备(Windows)](references/split-03-windows.md)
- [Pitfalls(实测)](references/split-04-pitfalls.md)
- [Verification](references/split-05-verification.md)
- [References](references/split-06-references.md)
- [外部库增量（2026-10-11 分享包）](references/split-07-2026-10-11.md)
- [Pitfalls](references/split-08-pitfalls.md)
- [前端工程重建（只有 dist 时：反编译回 `.vue` 工程）](references/split-09-dist-vue.md)
- [交付形态（重建工程的最后一公里）](references/split-10-section.md)
- [老版本功能/UI 装回新代码树：对齐口径与覆盖计数](references/split-11-ui.md)
