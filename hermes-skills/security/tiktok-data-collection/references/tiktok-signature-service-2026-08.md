# tiktok-signature 签名服务探索记录（2026-08-19）

## 背景
服务器 Linux 浏览器指纹硬伤（platform 只读/WebGL none/时区覆盖失败）导致 CDP 采集不可行后，
探索"本地生成合法签名 → HTTP 采集"路线。npm `tiktok-signature` v4.3.6 提供纯 node X-Gnarly 算法。

## 资产
- `xgnarly.mjs`（220 行，零依赖）：`encode(queryString, body, userAgent, counters?, options?)` → X-Gnarly 头值
  - fields: 1=65, 3=md5(queryString), 4=md5(body), 5=md5(UA), 6=ts, 9="5.1.3-ZTCA", 10=sdkVersion(默认 "1.0.0.368"), 12/13=请求计数
  - 算法：自定义字母表 base64 + ChaCha20（SIGMA + 12 关键词轮，rounds 由密钥派生）+ 校验和插入位
  - **注意**：`encode` 的 queryString 必须与发送 URL 的查询串完全一致（含编码）
- `javascript/webmssdk_5.1.3.js`（官方 SDK 完整源码，本地注入用）
- `server.mjs`（签名服务）：puppeteer-extra stealth + Safari macOS UA + `ignoreDefaultArgs:["--enable-automation"]` + headless:"new"

## 部署（服务器 /srv/tsig）
```bash
mkdir -p /srv/tsig/javascript
# 上传 server.mjs / xgnarly.mjs / package.json / javascript/webmssdk_*.js
cd /srv/tsig && npm i puppeteer-extra puppeteer-extra-plugin-stealth
# 启动（可选 PROXY_ENABLED + PROXY_HOST=127.0.0.1:8888 走本地桥到用户代理）
(nohup node server.mjs > server.log 2>&1 &)
curl http://127.0.0.1:8080/health   # initMethod: local-sdk, hasAcrawler:true, 捕获 6 cookies
```
- Chromium 路径：getChromePath() 依次找 PUPPETEER_EXECUTABLE_PATH → /usr/bin/chromium → chromium-browser → google-chrome
- 本地 SDK 初始化 = 浏览器打开本地页面注入 webmssdk（**不访问 TikTok 页面，无指纹检测**）→ 签名本地生成

## 实测结论
| 尝试 | 结果 |
|---|---|
| `POST /signature {url}` → 签名 URL（1153 字符） | ✅ 生成成功 |
| 签名 URL + 外部 curl 重放（同 IP） | ❌ **HTTP 400 statusCode 10201**（签名绑定会话，外部重放无效） |
| `POST /fetch {url}`（浏览器内 fetch，服务器直连香港 IP） | ❌ 10201（香港 IP 被风控） |
| 签名服务走用户代理桥（PROXY_ENABLED）后 /fetch | ⚠️ httpStatus:200（过风控）但 **data:null**（响应仍空，未闭环） |

## 关键认知
1. **签名绑定浏览器会话上下文**——/signature 输出的 URL 只对同会话同 IP 有效，外部重放 10201
2. **IP 一致性原则**：签名会话 IP 必须 = 实际请求 IP（tiktok-signature 文档明确 "TikTok rejects with HTTP 200 / 0 bytes" 若不一致）
3. `/fetch` 是唯一可能闭环的端点（浏览器内完成签名+请求+返回），但多代理场景需每账号独立会话/服务实例
4. **secUid 必须用 SSR 实时解析的完整值**（截断版 → 10201 误判）

## 下一步方向（未验证）
- /fetch data:null 的根因排查（可能页面上下文/响应类型）——继续调试或放弃该路线
- 或：客户端（Windows）采集上传服务器（环境指纹真实，本机已验证 79 条成功）——最可靠
