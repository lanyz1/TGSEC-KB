# Qavlixor 翻译体系全景图（2026-08-09 盘点定稿）

用户要求"捋一遍现在已有的全部翻译机制"时的完整盘点结论。改翻译相关代码前先读此图定位"哪个机制管什么"，避免重复造机制或漏改入口。

## 一、翻译通道（机器翻译入口清单——各入口独立实现，改一个不等于改全部）

| 入口 | 文件 | 协议 | 用途 |
|---|---|---|---|
| `translateToAllLanguages` | lib/machine-translator.ts | SiliconFlow chat/completions（优先）+ OpenAI /responses 分支 | 发品翻译（buildProductI18n 调用）|
| `makeTranslator` | scripts/i18n-scan-lib.mjs | SiliconFlow chat/completions + response_format json_object | sync-content cron + 批量键翻译脚本 |
| backfill 脚本各自实现 | scripts/backfill-*.mjs | SiliconFlow 优先 | 存量回填 |

- **通道判定**：`SILICONFLOW_API_KEY` 存在即优先（**isSiliconflow 判断不要带 `!TRANSLATE_PROVIDER` 条件**——22.17 事故：.env.local 历史 TRANSLATE_PROVIDER=deepseek 劫持导致 SiliconFlow key 打 deepseek base 全 401）
- SiliconFlow 无并发风控（100 并发实测全过），模型 `deepseek-ai/DeepSeek-V4-Flash` 单请求 ~7-30s（含 6 语言输出）；deepseek 官方 IP 级间歇风控（并发即 401，换 key 无效）

## 二、四层翻译机制（按数据产生时机分层）

```
① 静态 UI 键（预翻译，秒切）
   lib/translations.ts ~800 键 × 7 语言（ui.fix/ui.msg/ui.sel/ui.cn/ui.cn.tier/ui.cn.cat）
   渲染：data-i18n 属性 + getTranslation(lang, key) + currentClientLanguage()
   切语言零延迟（数据预翻译）

② 商品发品即翻（写入时同步翻译，秒级）
   lib/product-i18n.ts buildProductI18n：标题 + 描述(≤300字) + SKU规格名
   → Product.i18nJson（title/detail/skuNames 7 语言）
   → 同步 upsert 入 UiTranslation（scope=dynamic, note="product-live"）
   挂钩：app/api/seller/products/route.ts:134（创建）+ [id]/route.ts（编辑）
   渲染：productTitleI18n() 解析 + DynamicText
   ⚠️ 描述 >300 字发品不翻（524 网关超时）→ backfill 分块补翻

③ 动态内容写入即翻（fire-and-forget，秒级）
   lib/live-dict.ts ensureDynamicTranslated(source) / ensureDynamicTranslatedAll(sources)
   - 非中文跳过（/[\u4e00-\u9fff]/）；inflight Map 并发去重；30 分钟 freshness（用 createdAt，
     UiTranslation 无 updatedAt 字段）；后台不阻塞业务；失败静默 cron 兜底
   - 挂钩 8+ 处：auth/register 昵称、account/profile 改名、messages/[id]/actions、
     orders/[id]/aftersale 售后、admin/products/[id]/review、admin/deposits/[id]、
     appendConversationMessage（消息 body ≤500 字符）、appendBusinessEvent（资金流水 detail）、
     ensureBuyerStoreThread（会话 subject 模板）
   渲染：DynamicText（9 kinds：generic/product-title/store-name/category/status/operation/
         logistics/settlement/note）+ HybridDynamicText（中文段翻译/非中文段原样，流水模板用）

④ 定时 sync（cron 兜底存量/遗漏）
   scripts/sync-content-i18n.mjs — cron 每 2 分钟（2026-08-09 从 10 分钟提速，flock 防重入）
     收集源：售后 reason、消息 body、会话 subject、通知 title/body、保证金 reason/reviewNote、
     提现 reviewNote、商品/店铺 reviewNote、工单 subject/summary、store.name、user.displayName、
     businessEvent.detail、TranslationMiss 队列
     SYNC_CONCURRENCY=20 / SYNC_MAX_NEW=300（手动跑大存量 env SYNC_MAX_NEW=3000）
   scripts/sync-i18n.mjs — 每日 04:47（旧版冗余）
   scripts/backfill-product-translations.mjs — cron 每 10 分钟（商品 i18nJson 补翻）
```

## 三、渲染层

- **LanguageSync**（客户端）：**localStorage 缓存词典秒读**（`qav-dynamic-dict-v1`，~1.5MB 先读缓存注册 + scheduleApply，后台再 fetch `/api/i18n/extra` 增量刷新 + 写缓存——切语言零卡顿）→ data-i18n 翻译 + 漏翻上报 `/api/i18n/report-miss`
- **按需实时翻译兜底（report-miss 路由升级，2026-08-09）**：report-miss POST 除写 TranslationMiss 队列（cron 兜底）外，**同时实时 SiliconFlow 翻译未命中条目入 UiTranslation（单次 MAX_LIVE=8 条防超时）并返回 `{ ok, translations }`**；LanguageSync 的 miss flush fetch 读响应 → `registerDynamicEntries(data.translations)` + `applyDynamicElements(currentLanguage(), true)` 立即重翻——**页面无需刷新/等 cron，任何漏翻秒级补上（最后防线）**
- **DynamicText**：`value` + `kind` → 渲染 data-i18n-dynamic，客户端词典翻译；`as="span|strong"` 透传 props/style
- **HybridDynamicText**：CJK_RUN 正则拆 [中文段|非中文段]——中文段走词典翻译、单号/哈希/数字原样（资金流水/带唯一后缀的模板文案必用，勿整条 DynamicText）
- **data-i18n-raw** = 刻意跳过翻译标记（数据值豁免：语言名/AppleSelect 选项/部分表单值）——用户报"某处还是中文"先 grep 该处有无 data-i18n-raw
- **服务端组件**（非 "use client"）不能用 currentClientLanguage()/getTranslation(currentClientLanguage())——用 data-i18n 静态标记或 DynamicText
- **【坑·data-i18n 属性错位】**：批量脚本把 data-i18n 插到 `>` 外面（`<option value="all"> data-i18n="key"全部字段</option>`）→ 属性失效 SSR 露中文；全库排查 `grep -rn '"> data-i18n=' app/ components/`；批量插属性后必须 grep 校验 `<tag data-i18n=` 位置

## 四、词典（UiTranslation 表，scope=dynamic）

- 生产 ~8800-9300 条；LanguageSync 全量拉取 → 新词条**无需重新构建部署**，页面加载即生效
- 手动补条（代码内静态兜底文案 cron 收不到）：`prisma.uiTranslation.upsert({ where: { source }, update/create: { i18nJson: { 'zh-CN': 原文, en, es, fr, pt, ru, ar }, scope: 'dynamic' } })`——3s 完成无需部署
- **凡"中文模板前缀 + 动态后缀"文案（余额支付：订单XXX）→ 纯中文前缀手动补词典即可全覆盖**

## 五、已知缺口（2026-08-09 盘点 + 收尾更新）

1. **`Product.specs`（产品参数）翻译数据缺失**——用户原始痛点"产品参数部分文字翻译转化不了"的根因：
   - 渲染层已接 ✅（app/products/[id]/page.tsx params_ 渲染走 DynamicText generic/note）
   - 但数据没人喂 ❌：发品 API 只翻 title/detail/skuItems（route.ts:134），sync-content 不收集 specs，backfill 不翻 specs
   - ⚠️ **生产表缺列**：schema.prisma 有 Product.specs/detailBullets（Json?）但生产表没有这些列（raw SQL 42703 column does not exist；Prisma 查询报 library.js 大段错）——schema 与生产 DB 不同步（历史遗留）。**先 raw SQL `SELECT 1 FROM "Product" LIMIT 0` 或 information_schema.columns 验证列存在，再写收集逻辑**；页面走 fallback 不报错所以一直没暴露
   - **【2026-08-09 定稿】specs 仅存在于演示数据（lib/sample-data.ts），生产商品 specs=null 走 fallback 参数 `{类目/发货/库存/SKU}`**——fallback 3 词（类目/发货/SKU）已手动 upsert 词典 7 语言（库存/商家发货原本已有）→ 参数表翻译实际已覆盖；**如未来加真实 specs 字段，先验证生产列存在再写收集**
2. 8 个缺翻译键状态词（商家已拒绝/已删除/已退款/提现冻结/提现打款/订单结算/钱包充值）——按需补（见 SKILL.md 22.9）
3. **存量覆盖实测定稿（2026-08-09）**：title 6997/6997、detail 6956/6997、**SKU 名 ProductVariant.i18nJson 74305/74305 全翻**（别查 `Product.i18nJson->skuNames`——SKU 翻译在变体表）、subtitle 0 数据；TranslationMiss 2553 条已清空（SYNC_MAX_NEW=4000 手动 + cron 2 分钟）
4. **零遗漏验证量化标准**：① SSR 全页复扫 0 残留（剔除 data-i18n 节点；动态内容如店名 SSR 露原文属正常，排除已知项）② TranslationMiss pending=0 ③ 存量数据覆盖表各字段计数——三样全过才算闭环

## 六、"翻译慢"感知的根因分析框架（2026-08-09 用户"为什么翻译这么慢"）

用户感知"翻译慢"≠ SiliconFlow 慢（40 并发翻几百条只要几秒），而是**调度机制慢**：
- 静态 UI 键 / 商品标题 i18nJson：预翻译 → 切语言秒切 ✅
- 动态内容：靠 cron 周期批量翻译 → 新内容最长等一个周期（原 10 分钟 → 已提到 2 分钟）
- 漏翻（TranslationMiss）：LanguageSync 上报 → 等 cron 消化
- 词典生效：extra API 60s 缓存 + 浏览器刷新才拉新词典
- **结论：翻译延迟 = 数据产生时刻到 cron 运行时刻的窗口，不是 API 速度**——秒级需求必须走"写入即翻译"（②③层），cron 只兜底

## 七、生产 crontab 编辑坑（2026-08-09 事故实录）

- **sed 行内替换 crontab 必炸**：`sed 's|*/10 * * * * cd /www/tiktok && flock ...|*/2 ...|'` 中 `*` 在 sed 里当通配 → 匹配错乱 → crontab 变垃圾行（crontab -l 输出全粘连）
- **安全做法**：把**完整 9 条 crontab** 写文件（sftp 上传）→ `crontab /tmp/qav-crontab.txt` → 验证 `crontab -l | grep -c '^\*/'` 计数符合预期
- 服务器 crontab 全貌（2026-08-09）：结算每 10 分钟 / 备份每日 03:15 / 上传清理 04:10 / backfill-product 每 10 分钟 / monitor 每 5 分钟 / sync-i18n 每日 04:47 / **sync-content-i18n 每 2 分钟**（flock 锁 /tmp/tiktok-content-i18n.lock）/ 汇率整点 18 分 / pg-backup 每日 03:17
