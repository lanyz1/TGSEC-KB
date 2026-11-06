# Next.js + WASM 签名器离线复现（zm1s8x / 开云 ky 案例全记录）

案例：`/root/cases/drfmud7h5b2n`（绸固案下游）。目标 `https://www.zm1s8x.vip:6508`（开云体育 H5；内部前缀 `ky`；siteId 4002）。2026-10 实测全程，签名算法完整离线化（无需浏览器）。

## 0. 目标解剖
- 活站 = Next.js App（SSR HTML 带 `__NEXT_DATA__`），非 Vite/Nuxt。
- 真后端：`_app` bundle 里 axios `baseURL: https://production-microservices.yk8s.in`（浏览器走同源相对路径）。
- 头族：`x-api-client:h5` / `x-api-xxx`（签名）/ `x-api-version:1.0.0` / `x-api-site:4002` / `x-api-type:h5` / `x-api-token` / `x-api-uuid`；登录带 `x-api-finger`。
- 频道（sign 输入白名单）：`/site/api` `/act/api` `/game/api` `/fd/api` `/agent/api`；env：`prod/dev/release`。
- `/sact/api` 不在白名单 → 见 §6。
- localStorage 前缀 `y-h5-main:ky:prod:*`；userCode 格式 `y_4002_<uid>`。

## 1. chunk 全量挖掘
1. 首页 grep `/_next/static/chunks/*.js` → 22 个入口 chunk。
2. runtime（`webpack-*.js`）里解析**全映射**（懒加载包含在内，共 50）：正则 `(\d+)===e\?"([^"]+)"` → `chunkmap.json`。
3. 按映射下载全部 chunk + 发现 wasm：`static/wasm/5bd33e776bcea985.wasm`。
- 签名器在懒加载 chunk 2284（`2284.d7d5979f4b177dd4.js`）+ wasm；只抓首页那批会漏。
- glue：模块 922284 内 `n.e(2284).then(n.bind(n,922284))`；`sign(u,c,d,_,l)` 直调 wasm 导出。

## 2. 签名输入定位（_app @~1350900 头组装模块）
```js
async function z(t){
  t.t0 = await TC( (path.match(/\/\w+\/\w+/i)||[]).shift() || "" ); // ← URL 前两段当频道
  r = {"X-API-CLIENT":"h5", "X-API-XXX":t.t0, "X-API-VERSION":..., "X-API-SITE":..., "X-API-TYPE":...};
  if (tok = token()) r["X-API-TOKEN"] = (0,M.a)(tok);   // token 变换
  r["X-API-UUID"] = (0,B.lv)();
}
```
`TC` = 动态 import chunk 2284 → `sign(path, "prod")`；失败回退读 localStorage 缓存（AES-CBC 解 path→sign 映射，键 `uuidToBase64`）。

## 3. Node 直跑 wasm（关键细节）
- imports 仅 4 个：`__wbg_now_*`→Date.now、`__wbg_random_*`→Math.random、`__wbg_floor_*`→Math.floor、`__wbindgen_throw`。
- 调用约定：`sign(sp, p1,len1, p2,len2)`，返回值写回栈槽：`Int32Array[sp/4]`=ptr、`[sp/4+1]`=len；结尾 `__wbindgen_free` + `add_to_stack_pointer(16)`；开头 `add_to_stack_pointer(-16)`。
- 每次输出不同（掺 now/random）。
- **trap 诊断**：`unreachable` 且 0 个 import 被调用 = 输入没进计算逻辑（被输入校验拒绝）。合法输入=精确频道串+env；非法值别调参，换值。
- 模板：`templates/wasm_bindgen_sign_runner.js`（本次 glue 移植版）。

## 4. 校验强度矩阵（实网实测）
- 64×0 垃圾签名 → `6003 非法请求`
- 去掉签名头 → `6003`
- 数小时前旧签名 → ✅ 通过（可重放，时窗以小时计）
- 现造新签名 → ✅ 基线
- fresh `/site/api` 签名打 `/act/api` → ✅
- fresh `/site/api` 签名打 `/game/api` → ✅（另测某旧 `/site` 值打 game 被拒 → 有细微差异，跨频道**逐端点实测**别外推）
- fresh `/act` 签名打 `/game/api` → ❌ 6003
结论：校验存在但宽松——无逐请求绑定、无短时窗、跨频道大多放行 →「一个 fresh 签名≈多频道通行证；旧值可重放数小时」写报告。

## 5. 密钥/变换台账
- `x-api-token` 变换（模块 455363）：`t=Base64(Hex.parse(token))` → AES-CBC 解（key=iv=`g1kD3G46J2j9c3S8`）→ 明文 len≥60 用明文，否则原 token。
- localStorage token AES-CBC：key=`N2841A3412APCD6F` iv=`AUCDTF12H41P34Y2`。
- 签名缓存 AES-CBC：key=`ZFRYCMdFYGf0i5HgO0oWvFV0terUABU0` iv=`CbE3P3t1lY34Ns8F`。
- sec 密钥端点轮换：`/site/api/v1/sec/<rot>`（nByhoeAyA4 / Hf6dtBdmHx / UJHG7plmGp）、`/act/api/v1/Hf6dtBdmHx`、`/page/fd/api/v1/Hf6dtBdmHxV1`。

## 6. `/sact` 频道的 'undefined' 彩蛋
`sact` 不在可签名列表 → JS 里签名抛错 → 浏览器把头填成**字面字符串** `"undefined"`，服务端**照收**。复刻：签名失败降级 `'undefined'`；实测返回 6008（=校验已过，缺业务参）。

## 7. 离线客户端（案卷工具）
- `signloop.js`：常驻 Node，stdin 逐行 `channel [env]` → stdout 签名。
- `ky_api.py`：`KyApi(token,uuid,base)`；`headers(path)` 按频道现签（失败降级 undefined）；`get/post`。
- 已打通：`member/info`（id=521742345, inviteCode=22963235）、preInfo、banner、`game/appList`、`/site/api/v1/user/member/jwt`（352 字符 JWT，iss=zy-jp-pd-pro-go-frontendapi31）。
- 工作细节：空 body POST 显式 `Content-Length: 0`（否则 411）；UA 用 iPhone Safari；token/密钥落盘 `analysis/secrets/`（显示层会脱敏）。

## 8. 续打清单
- 端点：`analysis/nextjs/endpoints_all.txt`（122 个；动态拼接的再挖）。
- 待打：IDOR 矩阵；redEnvelope(6005)/sact signGift(6008)/agent pilgrimage(6601) 挖入参；充值链 `newTypesV10`+`eBPAYDirectCharge`（`analysis/ky_member_ui.json`）；提现链。
