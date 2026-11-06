---
name: qavlixor-marketplace
description: >-
  测绘引擎·维护 Qavlixor 跨境商城 i18n 补键、AppleSelect、prisma dev schema、页面审核。
owned: true
tier: general
pack: survey-skill
---

# qavlixor-marketplace（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-marketplace/`

溯源（仅标记）：`hermes/software-development`

---

# Qavlixor Marketplace 项目维护

跨境商城独立站（买家端根路径 / 卖家端 /seller / 管理端 /admin）。Next.js 15 App Router + TypeScript + Prisma + 全站 i18n（`lib/translations.ts` zh/en 双区 + LanguageSync 客户端词级翻译）。

<!-- split-index -->

## Section index

- [新坑速查 → 详见 refs/（按日期归档）](references/split-01-refs.md)
- [触发条件](references/split-02-section.md)
- [核心流程](references/split-03-section.md)
- [生产部署速查（详见 references/production-deploy.md）](references/split-04-references-production-deploy-md.md)
