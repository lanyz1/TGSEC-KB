---
name: whatsapp-business-profile
description: >-
  测绘引擎·Set up WhatsApp Business profiles for cross-border e-commerce — name, logo/SVG
  concept, bio/description, business category, blue badge verification support.
owned: true
tier: general
pack: survey-skill
---

# whatsapp-business-profile（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/whatsapp-business-profile/`

溯源（仅标记）：`hermes/productivity`

---

# WhatsApp Business Profile Setup

Guide for helping cross-border e-commerce sellers set up their WhatsApp Business profile (企业蓝标/白标). Covers all four key profile elements + account safety best practices.

## Core Workflow

```
intake → name design → logo/avatar concept → bio writing → category selection → verify → deliver
```

### 1. Intake (gather business details first)

Ask the user these questions (one at a time, not all at once):

1. **Business type:** What do you sell? (e.g. 3D printers, clothing, electronics — get specifics)
2. **Your role:** Retailer? Manufacturer? Wholesale supplier? OEM/ODM?
3. **Location:** Where is your business based? (this goes in the bio)
4. **Target market:** Who are your customers? (B2B wholesale? B2C retail?)
5. **Product range:** Do you sell only products, or also consumables/accessories?
6. **Tone preference:** Professional/formal? Marketing/punchy? Bilingual?

### 2. Business Name Design

Guidelines:

- WhatsApp display name should be **15-20 characters max**
- Must be searchable and instantly communicate what you do
- Include location if relevant (e.g. "PrintForge USA")
- Avoid generic names that blend in with competitors

| Style | Example | Best for |
|-------|---------|----------|
| Branded | LayerCraft 3D | Good branding recall |
| Location-tagged | PrintForge USA | Emphasizes local source |
| Wholesale-tagged | Proto3D Supply | B2B/wholesale buyers |
| Adjective+noun | VoxelCraft OEM | Niche positioning |

Always offer 3-5 options with a recommendation. Let the user pick.

### 3. Logo/Avatar Design

WhatsApp Business profile picture should be **400x400px square**.

Best practices:
- **Don't use product photos** — use a clean brand logo or icon
- Dark/industrial backgrounds work well for manufacturing businesses
- Include brand initials in small text on the logo
- SVG concept is preferred — give the user inline SVG they can render or modify

Design approach by business type:
- **Manufacturing/Industrial:** Dark backgrounds (#1a1a2e, #0d1b2a), gold/cyan accent colors, geometric shapes (layer lines, cubes, gears)
- **Retail/Consumer:** Lighter backgrounds, friendly colors, product silhouettes
- **Service:** Clean minimal icons, neutral palette

Provide 2-3 SVG logo concepts as inline SVG code in `<svg>` tags so the user can preview and modify.

### 4. Bio / Business Description

WhatsApp Business bio (description) should be:

- **Short version:** ~150 chars, fits one WhatsApp line
- **Long version:** ~300 chars, more marketing copy
- Include emojis for visual scanning (🇺🇸🔥📩🌎💪)
- Key info to include: location, products/services, factory-direct/wholesale, call to action

**Tone variants:**

| Tone | Characteristics | When to use |
|------|----------------|-------------|
| Professional | "US-based 3D printer manufacturer & supplier..." | B2B, OEM, formal clients |
| Marketing/Punchy | "🔥 US 3D printing source factory!..." | General audience, WhatsApp |
| Bilingual | English + Chinese | Chinese-speaking client base |
| Minimal/Clean | "🇺🇸 US 3D printer & filament source. DM for quotes." | Clean WhatsApp line |

**Key formatting:** Use line breaks and emojis for readability. End with a clear CTA (DM for quotes, WhatsApp for catalog).

**North American manufacturer positioning** (US/Canada factory, overseas orders — trust anchor is location + manufacturing status, not price):

- Lead with "North American Manufacturer" — EU/US B2B buyers pay premium for US-made and trust it over Asia-sourced
- Stack the 3 B2B selling points: `US-Made Quality • Worldwide Shipping • Bulk Orders Welcome`
- Add `ISO Certified` for procurement/enterprise buyers
- Always end with CTA: `DM for price list`
- If clients may be Chinese-speaking too, deliver the bilingual EN+CN layout (each line paired):

```
🏭 NexaCore AI | North American Manufacturer
🏭 北美制造商
🔧 Edge AI Devices • AI Servers • OEM/ODM
🔧 边缘AI设备 • AI服务器 • 定制代工
✅ US-Made Quality | Worldwide Shipping
✅ 美国制造品质 | 全球发货
📦 Bulk Orders Welcome
📦 欢迎批量订购
📩 DM for price list
📩 私信索取报价单
```

Name options worth offering for AI hardware/manufacturing clients: NexaCore AI, TitanChip Tech, CortexWorks, 芯纪元 ChipEra — keep ≤15 chars for WhatsApp searchability.

### 5. Business Category

WhatsApp Business categories relevant to cross-border e-commerce:

| Category Path | Best for |
|---------------|----------|
| Manufacturing → Industrial Equipment & Supplies | Manufacturing, OEM/ODM |
| Shopping & Retail → 3D Printing Service | Retail/consumer 3D printing |
| Shopping & Retail → Electronics | General electronics |
| Business Services → Wholesaler | Wholesale/B2B only |
| Business Services → Import/Export | International trade |

### 6. Blue Badge (企业蓝标) Verification

WhatsApp Business blue badge requirements:
- Verified business with Facebook Business Manager
- Complete business profile (name, icon, description, category, address)
- Facebook Page linked to the account
- Account in good standing (no recent bans/restrictions)
- Verification review takes approximately **24-48 hours**

## User Preferences (this user — LayerCraft 3D)

- Business: US-based 3D printer + filament manufacturer
- Role: Source supplier (源头工厂), OEM/ODM/wholesale
- Tone: Oral marketing (口语营销风), pure English for WhatsApp bio
- Logo: Prefers clean icon with brand initials, dark background, layer/printing motifs
- Wants to use a real/casual American person photo as avatar (not logo required in all cases)

## User Preferences (this user — NexaCore AI, second business)

- Business: **AI hardware manufacturer** (Edge AI devices, AI servers) — North American factory, mainly overseas orders
- Role: Manufacturer, OEM/ODM, bulk B2B
- Tone: Professional English primary; offer bilingual EN+CN paired layout
- Name chosen: NexaCore AI (from offered list: NexaCore AI / TitanChip Tech / CortexWorks / 芯纪元 ChipEra)

## Pitfalls

1. **Name too long.** WhatsApp truncates names over 25 characters in some views. Keep it tight.
2. **Bio too formal.** WhatsApp is a chat app — overly formal bio feels out of place. Emojis and line breaks help.
3. **Wrong category.** Picking the wrong WhatsApp Business category can prevent blue badge approval. Manufacturing ≠ Retail.
4. **Skipping Facebook Page link.** Blue badge (and account stability) is much harder without an associated Facebook Business Page.
5. **Logo has text too small.** WhatsApp profile picture is tiny in chat lists — initials must be bold and readable at 48x48px.

## Related Resources

See `references/whatsapp-account-management-guide.md` for the comprehensive WhatsApp account nurturing and ban appeal guide.
