# 2026-08-09 后段：P1 商品翻译自动化 + backfill 401 根因（#68-#72）

## #68 backfill 401 通道劫持 —— "补了好几次还有 null" 的真凶

**现象**：`/var/log/tiktok-translation-backfill.log` 全是
`API 401: {"message":"Authentication Fails, Your api key: ****aoww is invalid"}`，
backfill 每 10 分钟跑一次但 null 商品永远补不上（成功 0，失败 N）。

**根因链**（backfill-product-translations.mjs 与 machine-translator.ts 的通道判断不一致）：
1. backfill 的 `isSiliconflow = !!SILICONFLOW_API_KEY && !TRANSLATE_PROVIDER`
   —— 服务器 `.env.local` 残留旧配置 `TRANSLATE_PROVIDER=deepseek` → isSiliconflow=false → 走 deepseek 分支
2. backfill 的 `baseUrl = process.env.TRANSLATE_BASE_URL || ...`
   —— 服务器残留 `TRANSLATE_BASE_URL=https://api.deepseek.com`（24字符）→ baseUrl=deepseek
3. 但 `apiKey = <REDACTED> || TRANSLATE_API_KEY`（SiliconFlow 优先 = ...aoww）
   → **SiliconFlow 的 key 发给 deepseek 服务器 → 401 "aoww is invalid"**

**修复**（与 machine-translator.ts 对齐）：
```js
const isSiliconflow = !!process.env.SILICONFLOW_API_KEY; // 去掉 && !TRANSLATE_PROVIDER
const baseUrl = (isSiliconflow ? "https://api.siliconflow.cn/v1" : (process.env.TRANSLATE_BASE_URL || ...)); // isSiliconflow 时硬编码
```

**教训**：全项目多个翻译脚本（machine-translator / i18n-scan-lib / backfill）的通道判断必须一致
（key 存在即优先 + isSiliconflow 时 baseUrl 硬编码，不读 env）。服务器 .env.local 的
`TRANSLATE_PROVIDER=deepseek` / `TRANSLATE_BASE_URL` 残留会劫持所有读 env 的脚本。
排查"cron 慢/翻译不动"先看对应日志的 401/超时，再对脚本通道判断。

## #69 tsx/node 脚本不加载 .env.local —— 误判"key 不存在"

**现象**：`npx tsx` 直跑 lib 函数测试翻译通道 → `process.env.SILICONFLOW_API_KEY` 为 undefined
→ 误报"服务器没配 key"，实际 `.env.local` 里全有（Next.js 运行时才自动加载）。

**修复**：测试脚本手动加载：
```js
import { readFileSync } from "node:fs";
const env = readFileSync(".env.local", "utf-8");
for (const line of env.split("\n")) {
  const m = line.match(/^([A-Z_]+)=(.*)$/);
  if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
}
```
Prisma 直连脚本同理（需要 DATABASE_URL，且 pnpm 结构下 require 路径要走 .pnpm 或 cwd 相对）。

## #70 翻译模型可配 + GLM-5.2 提速

- machine-translator.ts / i18n-scan-lib.mjs / backfill 三处 model 改为
  `isSiliconflow ? (process.env.TRANSLATE_MODEL || "deepseek-ai/DeepSeek-V4-Flash") : ...`
- 服务器 `.env.local` 设 `TRANSLATE_MODEL=zai-org/GLM-5.2`
- 实测：GLM-5.2 单条 11.7s 且 JSON 输出正确；DeepSeek-V4-Flash 20s+
- **注意**：SiliconFlow 40 并发时排队严重（单条被拖到 45s+，出现 abort），并发非越高越好；
  实际吞吐 ~0.9 词/s 可接受（后台 worker 慢慢跑）。小模型（Qwen3.5-9B/27B）JSON 输出不稳（ERR），别选。
- 模型可用列表：`curl -s https://api.siliconflow.cn/v1/models -H "Authorization: Bearer $KEY"`

## #71 P1 商品翻译自动化（POST 秒回 + worker 自动补 null）

- **POST /api/seller/products**：移除同步 `buildProductI18n`（改 `product.i18n = undefined`）→ 保存秒回，
  不再因 SiliconFlow 慢"新建卡灰 20s"。i18n 由 worker 补（≤2 分钟）。
- **sync-content-i18n.mjs（2 分钟 cron）新增"商品 i18nJson=null 补译段"**：
  每轮取 30 个（`orderBy updatedAt asc`），翻译 title+detail(≤300字)+SKU 名 → upsert Product.i18nJson
  + 顺带写 UiTranslation 词典（买家端秒级切换）。失败 catch 静默 → 下轮自动重试（永不落 null）。
  环境变量 NULL_PRODUCT_PER_RUN 可调。
- **PATCH 失败保留旧值**（已有）：`buildProductI18n(...).catch(() => undefined) ?? product.i18n`
- 存量清零验证：`回填完成：成功 2，跳过 6995，失败 0` → 全库 null=0
- cron 配置：sync-content-i18n 2 分钟（flock）/ backfill 10 分钟 / sync-i18n（variant）每天 4:47

## #72 patch 改名陷阱

把 `let added = 0, failed = 0;` 改成 `let done = 0, failed = 0;`（想当然改名）→
后续 187 行仍引用 `added` → `ReferenceError: added is not defined` → cron 每 2 分钟崩溃静默。
**改变量名必须 grep 全部引用**；改完手动跑一次脚本验证（`node scripts/xxx.mjs | tail`），
不能只靠 tsc（.mjs 不查）。

## 用户协作模式（本段确认）

- 用户对反复修不完的问题：**先出方案再决定做不做**（四期方案 → 用户砍掉 P2/P4 只做 P1+P3）
- 判断表类核实：生成醒目 HTML（红框卡片+编号+代码位置）在系统 Chrome 打开逐项核实
  （`D:\跨境商城\会话产物\`），用户逐条给"保持/改"决定
- 定稿后写入 `docs/翻译铁律.md`（一句话原则 + 判断表 + 6 项不翻清单 + 机制保障），
  全项目永久约定，任何 AI 接手都按此执行
- 最终"不翻"仅 6 项：语言切换列表 / 物流追踪号 / 数据行(≥6位数字、@、http) / 货币代码(USDT/US$) /
  链名专有名词(TRC20/PayPal/Wise) / 管理端变更审核（审计原文）
- 裸中文兜底（applyBareChinese）排除列表必须含 `data-i18n-raw` + `.language-switcher`
  （否则语言列表"简体中文"会被误翻——曾真实踩坑）
