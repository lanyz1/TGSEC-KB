# SPA 分包图 + 别名反查 + 编码载荷（实测配方）

来源：@tmqb 提米钱包 / `timi.nimingkj.com`（Vue+Vite SPA + 单端点 `method=<名>` RPC，2026-09-14 授权测试）。
所有接口都走同一个 `/api.html`，方法名在 body 里 → 本文件就是「怎么把方法表和参数表挖干净」。

## 1. 分包图枚举（Vite）

主包 HTML/JS 里找 `__vite__mapDeps`：

```js
const __vite__mapDeps = (i, m = __vite__mapDeps, d = (m.deps || (m.deps = [
  "assets/Pc28Game-Cg5_uPli.js", "assets/red-receive-Dxxxxx.js", ...
]))) => i.map(i => d[i]);
```

做法（脚本，不要内联拼）：
1. 抓线上入口 HTML → 取 `<script type=module src="/vue/index-<hash>.js">` 真名（**别用本地旧包**）。
2. 主包里正则抽全部 `assets/<Name>-<hash>.js` 与 `__vite__mapDeps` 数组。
3. 拼成绝对 URL 全量下载（本例 32 个分包，含 `H5_login`/`red-receive`/`rebate`/`wallet`/`diamond-exchange`/`group-invite`/`Pc28Game`/`withdraw`/`deposit`/`vip-detail`/`PageHeader`…）。
4. 对每个分包跑同一套 grep：`method:"` / `method:'` / `['method']` / `async function` / `=>`。

**产出对比（本案例，就是这条教训的量化证明）：**
- 主包 grep → 45 个方法 → 当时误判「方法表封闭」
- 32 个分包重扫 → **+13 个主包没有的真方法**：
  - `redall(token, redId, readytData, language)` — 空投领取
  - `getrebate` / `receibate(token, lqtype)` — 返水/佣金领取（lqtype 1=返水 2=佣金）
  - `promotion(token, page, pagesize, starttime, endtime, username)` — 下级/推广
  - `myvip` / `mygrouplist` / `mychannel` / `addlink`
  - `bulletinlist` / `carousel` / `tanchuang` / `getcopyright`
- 反向校验：词汇表（11,210 候选）喷服务端 + 前后缀组合（4,521）= **零新增**，这才敢说方法表封闭。

## 2. 压缩别名反查（组件 → 真方法）

压缩包形态：`import{a as sn} from "./index-<hash>.js"`，业务代码调 `sn(...)`；主包里有 `export{ ... as a, ... }` 块。

反查步骤：
1. 分包里拿到调用点与别名（如某组件 import 了两个导出 `Be` / `ct`）。
2. 在主包 `export{...}`（通常是文件末尾的大块）里查 `Be` → 得到内部定义名（如 `Ds` / `Us`）。
3. 包内搜该内部名的定义 `function Ds(...)` / `const Ds = ...`。
4. 函数体里的 `method:"..."` 即真方法，参数名也在同一处。

实测收益：一个「充值奖励」按钮 → 反查出 `getmyplayset(token)`（读档位表，返回 `allsetlist`+`myset`）与
`setmyplayset(token, playsetid)`（写档位）。**没有这一步就会把它当成支付通道写错结论。**

## 3. 编码/映射载荷

提交处理器原文：
```js
const e = k.value.map(s => ({ type: Ce(s.type), group: Ce(s.groupLabel), amount: T.value }));
const o = btoa(unescape(encodeURIComponent(JSON.stringify(e))));
ws(token, gameid, o, issue)          // betpc28(token, gameid, betdata, issue)
```
- `betdata` = **base64(JSON 数组)**；`type`/`group` 过 `Ce()` 拼音映射表（`和→he 值→zhi 龙→long 三→san 四→si 空→kong …`，未命中则原样返回）。
- 实测：原始 JSON → `投注数据格式错误`；base64 → **穿过格式闸**，直接卡 `余额不足`（余额闸），高频时 `操作太频繁`（限速）。
- 结论：校验链 `编码 → issue 期口 → 余额 → 限速`，一次探针全摸完，无需通过任何闸。

## 4. 配置档位零校验（写接口的 ID 面）

- `setmyplayset(playsetid)`：档位列表 `allsetlist=[]`（空）时，喷 `0/1/…/999/9999` **全部回「成功」** → 缺存在性/可见性校验。
- 对照：`walletoperat(supplier, btype)` 有**余额闸**（回「余额异常，请联系管理员！」），`postwithdrawal` 有 `withpassword` 口令闸 —— **同类写接口闸门差异极大，必须逐个实测，不能类推。**

## 5. 活动 ID oracle + 票据透传

- `redall(redId)`：`redId` 默认 `"1"`，`redId=1` 回「空投ID错误!」= **免费存在性 oracle**（真 ID 进下一道闸）。
- 领取路径 `redall(token, redId, readytData={ticket,randstr})`，票据由**腾讯天御**（`ca.turing.captcha.qcloud.com`）在前端产出后**原样透传** → 拿到真 redId 后第一发即「塞假 ticket」，验票与否决定可不可利用。
- 红包/活动页把 `redId` 从 URL 参数（`?id=` / `?redId=` / `startapp`）取，默认兜底 `"1"`。

## 6. 顺手记下的三条判读规则

- `method 参数错误` = 后端**无**此方法（先打假名 `zzz_noexist` 校准形状）；`<x> 参数缺失或无效` = **真**方法。
- 前端有完整调用点（`upflie` + FormData + 加密 `data` 部件）、后端回**与假名逐字相同**的错误 ⇒ **前端超前部署的假攻击面**，立即放弃该路线。
- 云 WAF 对 `.git`/`.env` 回 403 + 1200B「网站防火墙」页（非 404）；判定要看产物特征串，命中防火墙字样一律算 WAF 拦截。
