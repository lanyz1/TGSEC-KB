# gofile 2026 `wt` 签名器离线复现（实测 2026-10-17）

## 场景
用户给了 `https://gofile.io/d/<contentId>` 分享，API 直拉报 401 / `error-notPremium`。目标：不靠浏览器把内容列表拉下来。

## 契约（从 SPA 源码逆出，不是猜的）
`https://gofile.io/js/services/contents.js`：
```js
const wt = await generateWT(token);           // token = 账号(游客)token，不是 contentId！
apiFetch(`/contents/${contentId}?${query}`, {
  token,
  headers: { 'X-Website-Token': wt, 'X-BL': navigator.language || '' },
});
```
- `generateWT` 在 `/js/core/wt.js`（薄壳）→ 真身 `/js/wt.obf.js`（obfuscator.io，密钥烤死，服务端轮换，前端产物 ≤6h 保鲜）。
- 算法骨架：SHA256(时间桶 14400s + navigator.userAgent + language + 内容ID/账号token)——**以混淆文件实际实现为准**，本行仅备忘。

## 步骤
1. `POST https://api.gofile.io/accounts`（空 body）→ 游客 token（32 字符）。
2. 拉最新 `/js/wt.obf.js` → Node vm 里 shim 环境执行 → `generateWT(token)`。
3. 请求带：`Authorization: Bearer <token>` + `X-Website-Token: <wt>` + `X-BL: en-US` + `Origin/Referer: https://gofile.io`。
4. 403 → 401 → `status:ok`：错误码逐层退位即签名对齐。

```js
import fs from 'fs'; import vm from 'vm'; import { webcrypto } from 'crypto';
const code = fs.readFileSync('/tmp/gf_wt.js', 'utf8');
const ctx = vm.createContext({
  navigator: { userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36', language: 'en-US' },
  window: {}, self: {}, atob, btoa, TextEncoder, TextDecoder, console,
  crypto: { subtle: webcrypto.subtle, getRandomValues: (a) => webcrypto.getRandomValues(a) },
});
vm.runInContext(code, ctx);
console.log(Object.keys(ctx));            // 定位导出符号名
const wt = ctx.generateWT(accountToken);  // 注意：签账号 token
```

## 分享 gate 状态解码（拿到 `status:ok` 之后才是真问题）
- `{canAccess:false, public:false}` → **notPublic：分享未开 Public**，内容锁在用户侧；让他去 gofile 打开 Public 或换托管，我们这边无解。
- `password: true` → 密码保护；有 `expire` 字段 → 过期。
- `status:ok` 只代表接口通，不代表能下载。

## 直链死路（别再浪费轮次）
- `/download/<cid>` → 404；`/download/web/<cid>` → 301 自我循环。
- `/download/web/<cid>/<假名>` → 302 路由到真实 store 节点 → 200 却回 SPA 外壳：**服务端校验文件名**，不知真名无法盲下。
- 老 v1 `/getContent?contentId=` → 已下线。

## 未验证
本次分享 `public:false`，止步于 metadata；「列 children → 取 link → 真实字节下载」未实测。