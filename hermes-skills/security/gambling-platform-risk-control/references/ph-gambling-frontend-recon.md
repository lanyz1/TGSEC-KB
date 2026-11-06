# 菲律宾博彩平台前端 Recon 实战(m9600 / MM99 案例)

会话沉淀:2026-08 渗透 m9600.com(MM99 品牌,菲律宾在线赌场/老虎机聚合)的完整 recon 链。

## 目标画像(m9600.com = MM99)

- **类型**:菲律宾(PHP 货币 ₱、Asia/Manila 时区、英文界面)在线赌场,聚合厂商老虎机
- **品牌**:MM99,协议名 `protocolName: m9`
- **技术栈**:Nuxt 3 SPA + Cloudflare + PHP 7.4.19 后端
- **关键域名**(从 SSR payload 提取):
  - API 后端: `https://t.pg-nmgas.com`(403 需 Referer)
  - WebSocket: `wss://wsm9.spiritapis.com/net`(游戏实时协议)
  - 资源 CDN: `https://downm9.sp-slots1.com/source/public`
  - 官网: `https://mm99.game`
- **镜像站矩阵**:OneSignal config 泄露 **30+ 镜像域名**(m9001~m9005、m9ph.club/click/love/xyz、m19990、m99000、freshnew66、new88life、vegas98lucky 等)— 博彩站用多域名防封,同一套前端/后端

## 游戏厂商类型 ID 映射(比缩写列表更精确)

从 `config.js` 的 tabs 配置提取:`type` 字段 = 厂商 ID:
| ID | 厂商 | ID | 厂商 |
|---|---|---|---|
| 1 | PG Soft | 16 | FC(福彩) |
| 2 | Jili(Tada) | 17 | CQ9 |
| 4 | Spirit | 18 | JDB |
| 12 | PP(Pragmatic) | 19 | WG(W Game) |
| 15 | Hacksaw | 20 | SPADE |
| 21 | G759 | 22 | POPOK |

- 游戏 ID(如 7423、1401、2084)是厂商内游戏编码,前端 `sortList` 控制展示顺序
- `price`/`growLevel`/`replace` 字段存在 = 该厂商支持 RTP 档位替换配置(呼应 rtp_level 传参)

## API 签名机制(硬编码密钥)

```
POST /api/* 需签名:
  key = "7f6e5d4c3b2a1f0e9d8c7b6a"(硬编码在前端 main.js)
  params 按 key 排序 → "k1=v1&k2=v2"(encodeURIComponent)
  data = str(Date.now()) + sorted_params
  signature = HMAC-SHA256(key, data).hexdigest()
  headers: x-timestamp=..., x-signature=...
```

- 签名函数 `signedPost`,key 在 JS 里明文可提取;Chunk 内导出名经压缩(如 `Q_` = HmacSHA256 包装)需从 export 语句反查
- **部分 GET 接口无签名直接可调**(缺 Referer 会 403):`/api/withdraw_info`、`/api/customer_info?dataid=`、`/api/get_push_config`、`/api/cpfservice_info`、`/api/visitor?dataid=`
- `/api/customer_info` 泄露客服/Telegram 渠道配置(`qesdeegs.icu`、`t.me/M91GAME` 等)

## Nuxt 3 配置提取要点

- SSR payload:`window.__NUXT__.config.public` 含 `gameURL`、`wsURL`、`assetsURL`、`env`、`apiBase`
- `env=production` 时 API base = `window.location.origin`(不是 /dev-api);`development` 才用 `apiBase`
- Build 信息泄露:Jenkins 路径 `/var/lib/jenkins/workspace/prod-all@2/locales/en`、buildTime/buildDate
- 硬编码第三方 token:ipinfo `0344c19ebbcbfa`、gtag `G-1YHQNJ2S7G`、gtm `GTM-KRG75XNP`

## Pitfalls

- 博彩站前端无头浏览器常被反自动化跳 `about:blank`,改用 curl + 静态 JS 分析更稳
- **但业务协议(WS)要交互时 curl 不够用**:有头 Chrome(非 headless)+ CDP +
  `Page.addScriptToEvaluateOnNewDocument` 预注入可绕过反自动化(有头反检测弱于
  headless);页面加载后前端可能已自动建立 WS 连接(`getSendBufferSize()==16376`),
  复用已有连接直接发命令即可。完整 CDP 驱动方案见
  `white-label-casino-pentest` skill「二进制 WebSocket 协议平台」节
- 全路径 200 是 SPA 兜底假象(备份文件 .sql/.zip 探测全 200 实为 index.html),必须看 body 内容
- `/api/*` 403 分两种:Cloudflare 层(Server: cloudflare)vs 应用层(X-Powered-By: PHP/7.4.19)— 应用层 403 通常是缺 Referer/Origin/签名
- 游戏大厅页面资源与 API 不同域(sp-slots1.com CDN),提取 API 要在 main.js/chunks 里找,不在 HTML
