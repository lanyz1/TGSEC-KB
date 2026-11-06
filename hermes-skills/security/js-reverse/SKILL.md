---
name: js-reverse
description: >-
  测绘引擎前端 JS 逆向。签名链路、SourceMap、webpack 加密模块、JSVMP/WASM/Worker。
  盘口 webpackChunk / js-websocket / 国密走 spa-protocol-reverse。
  二进制/APK/so 不要用本卡。
---

# js-reverse（测绘引擎）

目标须在 `config/scope*.json`。本卡绑定**仓库里真有的工具**，不绑定不存在的 MCP 前缀，不引用空的 `references/`。

盘口 webpackChunk / js-websocket / 国密 → `spa-protocol-reverse`。  
`sk_encrypt` → `encrypted-api-spa`。仅 MD5/VITE → `gambling-api-crypto-reversal`。  
微信小程序目录 → `wxmini-static-audit`。

## 真源

- 手法：`docs/playbooks/JS逆向与前端签名手法.md`
- 作业层：`docs/playbooks/测绘引擎逆向作业手法.md` §3
- 专题表：`docs/playbooks/逆向专题分流手法.md` §2
- 工具：`python3 tools/ops/js_secret_hunter.py doctor`
- 分诊：`python3 tools/ops/re_sample_triage.py --path <bundle.js>`

## 立刻跑

```bash
python3 tools/ops/js_secret_hunter.py doctor
python3 tools/ops/js_secret_hunter.py hunt --base https://授权站 --case <案>
# 已有 bundle
python3 tools/ops/js_secret_hunter.py file --path app.js --case <案>
```

产物：`测绘/js_secrets/js_secrets.json`。  
L1：score≥60 的 aes/salt/jwt，或 sourcemap 非空。有密钥立刻接协议/假支付。

## 五步（观察优先）

1. **Observe** — 目标请求 URL、initiator、可疑脚本。抓页用 `scrapling` / 浏览器，不要先猜环境。
2. **Capture** — 最小采样：请求体、签名字段、调用顺序。能 hook 入参就不要先下断。
3. **Hunt** — 跑 `js_secret_hunter`（会跟 `.map`）。不要手写第三套正则。
4. **Rebuild** — 本地 Node 复现必须有页面证据。一次一个最小补丁。
5. **Verify** — `verify` 或业务探针只读重放；服务端接受才算过闸。

JSVMP：先找 dispatcher，禁止盲补环境。  
WASM：先导入表/桥，再反编译。  
Worker：先看 `postMessage` 契约。

## 本库钉死的坑

webpack 第三参才是 require，返回值不是：

```js
window.__req = null;
window["webpackChunk"].push([["se-temp"], {}, function (r) { window.__req = r; }]);
```

国密复现用 Node `sm-crypto`，不用 Python `gmssl`。  
报错差异当 oracle，比读压缩 JS 快。

## 没有的东西不要找

- 仓库没有 `js-reverse/references/*.md`
- 仓库没有 `bootstrap-reverse.ps1`
- 当前 Cursor 会话没有 `js-reverse_*` MCP 时，用 `js_secret_hunter` + 浏览器，不要假装工具在

## 交接

| 发现 | 切 |
|------|----|
| `js-websocket` / `/clientapi` / SM2 | `spa-protocol-reverse` |
| 支付 notify/sign | `payment-callback-forgery` |
| APK 同 salt | `apk-recon` |
| 自定义 TCP/PCAP | `protocol-reverse` |

## 前端加载器双层混淆取证（2026-10 PC28 投毒）
- 外层 `eval(atob(...))` + 内层 `\xNN` 字面量，逐层落 SHA-256
- 恶意片段 HTML 内联 6 份（按字节偏移）+ 每个 JS 头部前置 3 份（偏移 0/880/1760）、业务代码约 2640 起 → 按「同片段重复数+偏移」判构建后批量污染
- UA 黑名单 `/Windows|Macintosh|X11|Android 6.0|Android 5.0/` 取反才执行 → 桌面分析机与 Googlebot 双双被排除
- 坑：Vite 内容哈希文件名未变 = 注入在打包命名之后，不能据此认定源码仓库被改
