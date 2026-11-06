# 2026-08-10：混合翻译扫描方法论 + 服务器脚本模式 + 键只插 zh 区坑

## 1. ★ 翻译键只插了 zh 区 → 切语言不翻（新 bug 模式）

案例：`seller.funds.wallet.availableNote2`（"与提现处一致，可直接申请提现"）只在 translations.ts zh 区有值（其他 6 语言区缺失）→ 切英文 getTranslation 返回 undefined → data-i18n 不替换 → 永远中文。同文件 `availableNote` 键同样只有 zh 区（含 `{num(...)}` 变量占位，翻译时原样保留）。

- **排查法**：`grep -n '"键名"' lib/translations.ts` 数出现次数——正常应 ≥6（es/fr/pt/ru/zh/en），只出现 1 次 = 只插了 zh 区。
- **插键法**：按语言区锚点定位——各语言区的值不同（如 funds 键 es="Centro de fondos" / fr="Centre des fonds" / pt="Central de fundos" / ru="Центр средств" / zh="资金中心" / en="Funds Center"），用 `grep '"键名"'` 列出全部行看值 → 在每个语言区的对应行后插入该语言值。
- ⚠️ ar 区历史缺失：`translations.ts` 只有 6 个语言区（es/fr/pt/ru/zh/en），**没有 ar 区**（ar 侧栏等键全部缺失，历史遗留）——插键时 ar 无法插入，接受与现状一致（ar 界面这些键显示中文/fallback）。

## 2. 服务器 node 脚本执行模式（踩坑修正）

- **静态 `import { PrismaClient } from '@prisma/client'` 在服务器 node 直跑报 `ERR_AMBIGUOUS_MODULE_SYNTAX`**（@prisma/client 双模式入口与 node ESM 冲突）→ 改用**动态 import**：`const { PrismaClient } = await import('@prisma/client')`。写 `.mjs` 文件用 `node` 跑（不要 tsx）。
- **模型属性名**：UiTranslation 的 client 属性是 `p.uiTranslation`（不是 uITranslation！大写 I 会 undefined）。
- **字段**：`source`（@unique，不是 sourceText）、`scope`（默认 "console"，词典预置用 "dynamic"）、`i18nJson`（7 语言对象含 zh-CN 键）。
- **查询**：`findUnique({ where: { source: '...' } })`（source 是唯一键）。
- **SellerDeposit 无 amount 字段**（只有 paidAmount/requiredAmount）。

## 3. 批量词典预置脚本（GLM ×7 语言，可 nohup 后台）

```js
// 服务器 /www/tiktok 下 _q.mjs，node 后台跑：
// cd /www/tiktok && nohup node _q.mjs > /tmp/q.log 2>&1 & （paramiko exec 会因管道卡 30s 超时——属正常，重连 ps 验证 PID）
// 词表分批 5 词/批，prompt 要求返回 JSON 数组 [{src,en,es,fr,pt,ru,ar}]，temperature 0.1
// 入库：existing ? update : create({ source, scope:'dynamic', i18nJson })
// 43 词约 2-3 分钟（GLM 每批 ~15s）
```

- 翻译通道：SiliconFlow `https://api.siliconflow.cn/v1/chat/completions`，model 读 `TRANSLATE_MODEL`（env），key 读 `SILICONFLOW_API_KEY`。
- 词表来源：子代理静态扫描清单（见下）。

## 4. 混合翻译运行时扫描法（治标排查链）

拆段翻译混合根因：2-4 字短词词典 miss → LanguageSync 拆段 → 拼接残留（"已同意退还"→"已Agree退还"；"已缴足应缴额"→"Paid in fullAmount Due额"）。治标=整句词典预置（命中优先于拆段）。

**排查三层**：
1. **浏览器运行时扫描**（最准）：切英文（localStorage + dispatchEvent）等 12s 兜底翻译后，TreeWalker 扫文本节点，正则 `/[\u4e00-\u9fff]/.test(t) && /[A-Za-z]/.test(t) && !/\d{6,}/.test(t)` 收集"中文+拉丁混合"文本 → 逐条预置。
2. **子代理静态扫描**：grep 无 data-i18n 的 JSX 硬编码中文，按风险分级——T0 拼接前缀词（已/待/未/共/第/剩 开头）拆段必混，最高优先；T1 2-4 字按钮/状态词；T2 5-6 字组合词。产出 `文件:行号:原文` 清单。
3. **代码层高频词**：`grep -rhoE ">[一-鿿]{1,5}<" app/ components/ --include="*.tsx" | sort | uniq -c`——注意大部分是 data-i18n fallback（会替换，非问题），重点找拼接型。

**本批已预置 T0+ 词**（63 词）：已退款/待接/已选/剩余/待审核/已通过/已禁用/加余额/已缴净额/未缴差额/未完结订单/商家处理中/同意退款/拒绝退款/强制退款/已上架/已下架/已删除/待支付/未付款/待揽收/运输中/已签收/已确认到账/已确认收货/待人工打款/待财务确认/拆单/打款/驳回/导出/开启/重试/结算/取消/删除/加载中/已完成/运费/优惠/订单/金额/异常/全部/手续费/已驳回/草稿/确认取消订单/应付总额/应付金额/商品金额/申请金额/预计打款/单据金额/冻结余额/真实订单/审核清单/当前关联工单/直营店清单/生成校验订单/处理提现/商家已退款/平台强制退款 + 退款原因/同样/处理记录/问题描述/证据材料/已转回余额/正常/已同意/退还/余额划转保证金/占用可提现/申请退还后释放/保证金/同意退款/已介入处理。

## 5. 语言切换器图标

`LanguageSwitcher.tsx` 的 `.language-switcher-globe` 原为文字"文"（英文界面突兀）→ 改 🌐 emoji。

## 6. 脏数据处理（售后 reason 记录）

QA 测试在售后 reason 里留了"同样/看/cnm/7/1"等回复文本 → 批量替换为规范文案（"同意退款"/"已介入处理"），正则 `/\n[0-9]{1,3}$/` 清尾部数字。处理记录文本（"退款原因：质量问题\n同意退款"）会同时展示在买/卖家端售后详情，清理后两端受益。
