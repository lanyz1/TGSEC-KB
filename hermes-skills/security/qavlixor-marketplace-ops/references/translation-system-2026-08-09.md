# Qavlixor 翻译体系全景与切语言机制（2026-08-09 实测固化）

用户核心诉求（verbatim）："不管原文字是中文英文还是别的语言，全部可以切换语言，翻译体系里不要有遗漏"、
"切语言一步到位，不要卡顿"。

## 一、翻译机制层次（从快到慢）

| 层 | 机制 | 生效时机 |
|---|---|---|
| 1 | **静态键** `lib/translations.ts`（~800+ 键 × 7 语言）+ `data-i18n` 属性 | LanguageSync 客户端实时替换（切语言即时）|
| 2 | **商品 i18nJson**（title 6997/6997、detail 6956、SKU 名存 ProductVariant.i18nJson 74305/74305）| 切语言即时（DynamicText product-title kind）|
| 3 | **动态词典 UiTranslation**（~9300+ 条，source→7 语言 map）| 客户端词典命中即时；未命中走层 4 |
| 4 | **report-miss 实时兜底** `app/api/i18n/report-miss/route.ts`：未命中+含字母 → SiliconFlow 实时翻译入词典 → 返回 translations 给客户端立即生效（单次 ≤8 条，IP 限 10 次/分）| 首次 ~1-2s，之后秒级 |
| 5 | **写入即翻** `lib/live-dict.ts` ensureDynamicTranslated：发品/消息/售后/昵称/注册/审核备注 8+ 处 API 挂后台 fire-and-forget 翻译（30 分钟去重）| 内容写入后秒级入词典 |
| 6 | **sync-content cron** `scripts/sync-content-i18n.mjs`（2 分钟，40 并发，flock 防重入）| 兜底所有动态源 + TranslationMiss 队列 |
| 7 | **词典缓存** localStorage `qav-dynamic-dict-v1`（~1.5MB 秒读，后台增量刷新）| 首屏零等待 |

**渲染组件**：DynamicText（9 种 kind：generic/product-title/store-name/category/status/operation/logistics/settlement/note）+ LanguageSync（data-i18n/data-i18n-placeholder/data-i18n-aria-label/data-i18n-title/data-i18n-dynamic + 货币换算）。

## 二、⚠️ getTranslation SSR 固化坑（本次用户三次反馈的根因）

**getTranslation(currentClientLanguage(), key) 在服务端组件里是 SSR 固化的**——页面加载时算好语言写进 HTML。
切换语言后 LanguageSync 只处理 `data-i18n` 元素，SSR 固化文本**不更新 → 必须手动刷新**才变。
用户实测症状："切中文时只有确认收货（客户端组件）变中文，其他按钮要二次刷新"。

**修复三件套**：
1. **服务端组件的按钮/标签 getTranslation → `data-i18n` 属性**（客户端 LanguageSync 实时翻译，切语言即时）
2. **客户端组件用 getTranslation**（如 ConfirmReceiptButton）→ 加 `qavlixor-language-change` 事件监听 forceUpdate：
   ```tsx
   const [, setLangTick] = useState(0);
   useEffect(() => {
     const handler = () => setLangTick(v => v + 1);
     window.addEventListener("qavlixor-language-change", handler);
     return () => window.removeEventListener("qavlixor-language-change", handler);
   }, []);
   ```
3. **LanguageSync 兜底**（根治全站）：handleLanguageChange / handleStorage 里 scheduleApply 后自动 `router.refresh()`（防抖 400ms）——SSR 固化文本自动重新渲染，用户一步到位无需手动刷新。

**判断准则**：文字要切语言即时生效 → 用 data-i18n（客户端）；组件内动态文本（saving 状态等）→ getTranslation + 语言监听。

## 三、售后列表 actor 中文标签坑

`lib/aftersale-reason.ts` 的 `parseHistoryEntry` 解析出的 `entry.actor` 是**中文标签**（"商家"/"平台"/"买家"，来自 ACTOR_LABELS 写入），**不是英文码**。
判断"买家补充过材料"必须写 `h.actor === "买家"`——写 `=== "buyer"` 永不匹配（本次实际踩坑，用户反馈"没改动"）。

## 四、翻译键插入纪律（本次 2 次踩坑）

1. **键号可能被占用**：插入新键前先 `grep '"ui.sel.321"'` 确认号段空闲——本次 ui.sel.321 已被"取消失败"占用，误插导致每语言 2 个重复键（JS 后者覆盖前者）。清理：删误插行 + 换号段（ui.cn.94）。
2. **7 语言块插入定位**：translations.ts 每语言块顺序一致，用**该语言特有的锚点值**（如 en 的 `"ui.sel.320": "Confirm Receipt"`、ar 的带前导空格 `" تأكيد الاستلام"`）定位，往回找上一键插入；键值里带前导空格（ar）会破坏字符串匹配。
3. **zh 插键后其他 6 语言都要插**——验证 `re.findall(r'"key"', s)` == 7。

## 五、批量翻译并发规范（用户点名）

- **SiliconFlow 100 并发实测全过**；批量翻译一律 **40 并发池**（sync 脚本标准配置）
- **禁止手写串行 for-await 循环**（73 店名串行跑了 10+ 分钟被用户批评）——写并发池或复用 sync 脚本
- 临时脚本 `process.env.SILICONFLOW_API_KEY` 为空（node 直接跑不加载 .env）——需硬编码 fallback key 或 loadEnvFiles

## 六、部署包自我包含事故（连续 3 次解压 EOF）

`qav-deploy.tar` / `qav-deploy.tar.gz` 被 `git add -A` 误跟踪 → `git archive` 把包**打进包里**（25MB 包含 25MB gz）→ 服务器 `tar xzf` 解压时**覆盖正在读取的 gz 文件** → `gzip: stdin: unexpected end of file`。
**修复**：`git rm --cached qav-deploy.tar qav-deploy.tar.gz` + .gitignore 加两行 → 重新打包 3.6MB 正常。
**教训**：git archive 前检查 `git ls-files | grep qav-deploy` 为空；部署包永远不 commit。

## 七、物流 lastEvent JSON 乱码（17TRACK）

`lib/logistics-provider.ts` parse17Track 的 lastEvent 兜底 `JSON.stringify(payload).slice(0,260)` 把 17TRACK 失败响应整段塞进 lastEvent（rejected 时 readNestedText 读不到 error.message）→ 总后台显示原始 JSON"乱码"。
**修复**：rejected 时读 `error.message` 作可读文案，兜底 "17TRACK 暂未查询到物流轨迹"。存量 22 条已清理。

## 八、售后证据 CDN 白名单过滤

上传走对象存储（`https://cdn.qavlixor.com/...`），但证据白名单（安全扫描 L3）只认 `/api/upload-files/` 和 `/uploads/` → CDN URL 全被过滤 → evidenceJson 存空 → 卖家端看不到证据。
**修复**：两处白名单正则加 `|^https:\/\/cdn\.qavlixor\.com\/`（app/api/orders/[id]/aftersale/route.ts + app/api/aftersales/[id]/evidence/route.ts）。外链（evil.com/IP）仍拒绝。

## 九、test-orders 时间限制（2026-08-09 用户拍板）

完全放开：任意历史/未来时间均可批量生成（统计/售后顺应数据）。仅保留：结束>开始（顺序）+ 格式有效校验。
前端时间输入可选（不填不传），datetime-local 无默认值。
