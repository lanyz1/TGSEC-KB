<!-- archived from /root/.hermes/skills/security/qavlixor-i18n-complete/SKILL.md on 2026-10-21 -->

---
name: qavlixor-i18n-complete
description: >-
  测绘引擎·用 when qavlixor 任务收尾需把所有新增内容纳入 6 语言翻译体系。扫描新中文文案→结构化→补键→验证。
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/qavlixor-i18n-complete`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/qavlixor-i18n-complete/…')`，不要相对 `references/legacy/` 解析。

# qavlixor-i18n-complete（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-i18n-complete/`

溯源（仅标记）：`hermes/software-development`

---

# qavlixor 翻译完整性(6 语言自动补齐)

## 触发条件
每次 qavlixor 任务完成后,检查所有**新增/修改的中文文案**是否进入翻译体系(用户铁律 2026-08-14:每完成任务自动纳入翻译)。

## 检查清单(任务收尾必跑)

1. **扫描新增中文**:
   ```bash
   cd "/d/跨境商城/qavlixor-marketplace"
   git diff HEAD~1 --stat   # 本次改动的文件
   grep -rn "[\u4e00-\u9fa5]" <改动的组件/页面>  # 找新增中文
   ```
   重点位置:按钮/标题/提示(前端组件)、空态文案、表格列头、服务端返回的 message。

2. **服务端铁律**:服务端**禁止直接返回中文串**(返回结构化数据:null/时间/状态码),中文文案一律前端翻译键渲染。发现服务端中文 → 改结构化 + 前端 data-i18n。

3. **补翻译键**:
   - 内置键文件:`lib/translations.ts`(按语言区:es/fr/pt/ru/zh/en 六个区块)
   - 每键必须 **6 语言齐全**:zh/en/es/fr/pt/ru
   - 插入后验证:`grep -c '"键名"' lib/translations.ts` 必须 = 6
   - 管理端键前缀 `admin.` / `ui.sel.`;卖家端 `seller.`;按钮用 data-i18n 属性 + 中文兜底文本

4. **前端挂键**:按钮/文本加 `data-i18n="键名"`,兜底中文保留(SSR/未翻译时显示)。

5. **生产 UiTranslation 表**:新增键需 upsert 生产表(scope=console, 覆盖模型名=i18nJson)。

6. **通知模板体系(2026-08-14 新增,独立于 translations.ts)**:`lib/notification-templates.ts` 是通知内容多语言字典(16+ 模板 × 6 语言 × 角色/参数分支)。**新增/修改任何 notify() 调用或模板键时**:
   - 通知正文用**已有模板键**(复用 order_paid/shipment_updated 等,参数进 metadataJson)
   - 若需新模板键:在 NOTIFICATION_TEMPLATES 里写满 6 语言(zh/en/es/fr/pt/ru),排除 conversation_message(消息本体)/contact_*(客服主题)
   - 渲染回退:未知模板/参数缺失自动回退库中原文,存量兼容

7. **验证**:6 语言插入后 grep -c 每键=6 → tsc → commit → 部署 → 生产 SSR 验证。

## 坑
- 锚点必须全局唯一(grep -c 每键=6 是最硬验证)
- 服务端中文串是漏翻重灾区(etaAt 事件、message 字段)
- 改完 translations.ts 用 execute_code 按语言区行号插入,别手写六遍
