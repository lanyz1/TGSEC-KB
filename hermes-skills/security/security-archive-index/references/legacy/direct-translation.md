<!-- archived from /root/.hermes/skills/security/direct-translation/SKILL.md on 2026-10-21 -->

---
name: direct-translation
description: >-
  测绘引擎·Bilingual translation (Chinese <-> English) for users who want ONLY the translation
  output — no explanations, no disclaimers, no commentary mixed in.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/direct-translation`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/direct-translation/…')`，不要相对 `references/legacy/` 解析。

# direct-translation（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/direct-translation/`

溯源（仅标记）：`hermes/productivity`

---

# 直接翻译 — Direct Chinese↔English Translation

## 核心规则 (Core Rule)

**When the user asks for translation, output ONLY the translated text.**

No preamble. No explanation. No ethical disclaimer. No commentary. No "here's your translation". No context about why you're translating it. No warnings. No back-and-forth questions.

Just the translated text, directly, in the requested language.

## 触发识别 (Trigger Recognition)

| User says | What they want |
|-----------|----------------|
| "帮我翻译成英文" | Only the English translation |
| "帮我翻译成中文" | Only the Chinese translation |
| "直接翻译成英文发给我" | Only English, no extras |
| "把这句话翻译成英文" | Only the English of the quoted text |
| "Translate this to Chinese" | Only Chinese of the provided text |

## 输出格式 (Output Format)

- One message = one translation. Nothing else.
- If user gives multiple sentences, translate all of them.
- Preserve the original tone (formal/casual/technical).
- Do NOT quote the original text back unless asked.
- Do NOT add translation notes like "literally means X".

## 反例 (Anti-patterns)

❌ "Sure! Here's the translation: [translated text]"
❌ "I'd be happy to help. The English translation is: [text]"
❌ "[translated text]\n\nBy the way, if you need more help..."
❌ "This translates to: [text]"

✅ "[translated text only]"

## 用户语境 (User Context)

This user is a Chinese native speaker who is:
- Impatient with unnecessary text
- Knows what they want
- Wants concise, direct output
- Does NOT want the AI to assume intent or add safety commentary to translation tasks

If the translation request is part of a larger conversation (e.g., user says "帮我翻译成英文" after providing Chinese), just translate. Do NOT analyze, critique, or respond to the content being translated. The translation IS the response.
