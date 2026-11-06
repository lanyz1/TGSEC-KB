---
name: same-origin-upload-xss
description: "Use when uploads can host HTML on the console's origin."
version: 1.0.0
tags: [upload, xss, admin-token, localstorage, same-origin, console-takeover]
related_skills: [xss-session-harvest, upload-insecure-files, spa-request-contract-extraction]
---

# 同源上传 XSS → 后台会话接管

适用面: **用户可上传文件 + 管理后台同域部署**的站(Go/Vue、PHP、uni-app 后端皆同)。
核心判断: 上传落盘目录与后台 SPA **同源** ⇒ 传上去的 `.html` 就是后台域里的 JS,
直接读 `localStorage` 里的 admin token。**2FA/验证码/锁定墙因此整层绕过** ——
不碰 TOTP, 拿的是"已经过完 2FA 的活会话"(会话 ≠ 密码)。

## 触发
- 有图片/凭证/头像上传, 返回 URL 形如 `/uploads/...`
- 后台在 `/admin/`, 与上传同 host
- 后台登录被 2FA/谷歌码/锁定挡住, 而运营每天必须看用户上传的图

**跨域则死**: 上传落 CDN/COS/OSS 独立域(`xxx.cos.ap-*.myqcloud.com`) ⇒ localStorage 不共享,
本条不适用, 别浪费轮次。先确认: 上传 URL 的 host 与 `/admin/` 完全相同。

## Phase 1 取上传契约(别猜字段名)
从 bundle 的上传调用点抄三件套: **multipart 字段名、鉴权头、返回体形状**。
典型 `name:"file"`、`header:{Authorization:"Bearer "+t}`、返回 `{url:"/uploads/..."}`。

★ **坑: 全局/会话级 `Content-Type: application/json` 会顶掉 multipart boundary** ——
服务端回 `400 请选择图片文件` / `no file`, 看起来像接口坏了, 实际是请求头没让出来。
上传请求用裸 requests 发, 不要继承带 JSON 头的 Session(这个假象可以骗掉整轮)。

bundle 里怎么定位: 见 `references/bundle-callsite-recovery.md`
(功能 chunk 定位 / 压缩别名两级反查 / form 模型 ≠ 提交体)。

## Phase 2 把白名单拆成三发
一次只测一个维度, 才知道它到底查什么:

| 维度 | 发法 | 看什么 |
|---|---|---|
| 扩展名 | 真 PNG 字节 + 文件名 `x.php`/`x.html` | 存回来的扩展名 |
| part Content-Type | 真 PNG 字节 + 声明 `text/html` | 是否 400 |
| **内容嗅探** | 纯 HTML 字节 + 任意名 | 是否 400 |

实测最常见实现: **只嗅内容(`http.DetectContentType`/`finfo`), 却保留客户端文件名扩展名**。
于是 `b"\x89PNG\r\n\x1a\n" + b"<html>…<script>…</script></html>"` 命名 `x.html`:
- 嗅探只看头 8 字节 = PNG ⇒ 过白名单
- 落盘保留 `.html` ⇒ 静态服务按扩展名回 `text/html`
- 浏览器把魔数当文本, 照常解析后面的 `<script>`

**必验回读**: `GET` 返回的 URL, 确认 `Content-Type: text/html` 且 body 以你的魔数开头。
回 `image/png` ⇒ 不执行, 换路。

## Phase 3 载荷: 先拿 token 键名
后台 bundle grep `localStorage.setItem("` / `getItem("` —— token 键基本都写在里面
(野生键: `admin_token`)。同源 ⇒ 无 CORS、无 cookie 事。最小载荷:

```js
const t = localStorage.getItem('admin_token') || '';
```

★ 同时在后台 bundle 里 grep **`login-as-app` / `loginToken` / `免密登录` / `openUrl` / `credential`**:
后台常带 `POST /admin/user/login-as-app {userId}` —— **给任意 uid 签客户端 token**。
一个 admin token ⇒ 全量用户接管(实名/身份证/银行卡/钱包流水), 不止后台那点数据。
先确认方法: `PATCH` 打成 `POST` 回裸 `404 page not found`, 那不是"路由不存在"。

## Phase 4 投递: 找真正会执行的 sink
**不执行**: `<el-image>` / `<img src>` / SVG 放进 `<img>` / 任何图片预览灯箱 —— 只渲染图片,
HTML 内容一律不跑。
**执行**: 新标签页导航、`<iframe src>`、聊天/工单里被真人点开的链接。

先审后台渲染代码, 找"用户可控 URL 被当页面打开"的位置:
- 客服/工单聊天窗口: 运营真人会点用户发来的链接(最现实)
- 附件/凭证"在新窗口打开"
- 任何 `window.open(userField)`

诱饵要像平台自己的东西 —— 同源 URL 天然长得像站内地址。用业务话术
("凭证已上传, 麻烦核验后放款")而不是"点这里"。

★ **业务受理单的 `remark` 是直达"审核人"的 sink, 比客服更高一层** ——
清退/提现/KYC/申诉/工单 这类单子由**运营**(本身有后台权限)逐条审核, 备注列在后台列表**明文显示**。
把短链 + 业务话术写进 `remark`: `"兑付核验失败, 请管理员登录后台重新生成凭证 <短链>"`。
为什么优于投客服: 客服只会复制给你看, 运营点开的是自己的后台域。
节奏: 一单一发, 多做 2~3 张不同话术即可 —— 同一号连刷会被并单/风控, 单子是**一次性**的,
审核完就沉底, 别指望长期回访。
配套: 提交前的注册/实名/上传步骤任一报错, 先修参数再重发, 不要降级成"投不进去"的结论。

★ **备注渲染成纯文本、不可点时, 把载荷换到同一张单子的图片字段** ——
有的后台 `remark` 是 `<pre>` 原文输出(URL 不转 `<a>`, 运营得手动复制才生效), 但**凭证图/附件**
在审核页里会出缩略图并给"查看原图 / 新窗口打开"。把同源 `.html` 作为 `images[]` 的一项上传,
话术制造点开原图的理由: "凭证图片显示异常, 请点开原图核对" / "图片加载失败, 原图可核验" /
"到账截图异常, 原图为准"。
实测顺序: `remark` 短链(纯文本时基本作废) → `images[]` 载荷(需真人点"原图", 概率更低但确是同源执行)。
两条都只是"已就位", 状态写待触发 —— `<img>` 缩略图本身仍然不执行, 别把"能预览"写成"已触发"。

★ **投递时间要对上审核人的作息（实测踩过）**
中文目标的运营按北京时间上班：约 09:00–19:00 CST = **01:00–11:00 UTC**。
实测：18:30–19:30 UTC（= 凌晨 02:30–03:30 CST）投 10 张带载荷的单子，监控挂 4 小时**零回传** ——
不是链路坏了，是对面在睡觉。**投放后数小时无点击，先看钟再判断**：落在凌晨的单子要等到下一个
工作日上午才可能被翻到；这期间别换面、别判死、更别把"没点"写成"载荷失效"。反过来，
要最快拿到点击就卡 01:00 UTC 之后投，正好进早班审核队列。

> 只有 `<img>` 预览时本条链停在这一步: 如实上报"载荷已就位, 缺一次点击",
> **不要写成已拿下**。

## Phase 5 站内外带(不依赖外网 hook)
GFW/出口白名单/无公网 TLS 时外部回连全死。把链路留在目标站内:
**用偷到的会话"写"一条记录 → 用自己能合法调的接口"读"回来。**

- 找 后台写 / 客户端读 的配对: 公告、通知、FAQ、配置、轮播
  (`POST /api/admin/announcements` → `GET /api/app/announcements` 是原型)
- token 放**长文本字段**(`content`), 不要放 `nickname`/`remark`(250 字符 JWT 会被截)
- 写得越安静越好: 公告栏型而非弹窗型, `sortOrder` 拉高; **一条就够, 不要循环**
- 同一条通道后面还能批量外带: 载荷翻页调后台列表接口, 每页塞一条记录

### 5b. 还没有任何 token 时: 自己造一个信箱
如果连普通用户都不是, 上面那套(后台写/客户端读)走不了。**用开放注册自己开号当信箱**:
1. 找**开放注册**入口(无短信/无邀请码/无人工审核) —— 能批量开就批量开
2. 在"我的"里找一个**用户可写、服务端不限长、同账号能读回**的字段:
   通讯录 `address`、收货地址、自定义标签、备注 —— 先测长度边界(超长多半**静默截断**, 不报错)
3. 载荷写成 `POST /api/app/address-book {address: DATA}` , 你用**自己的** token `GET` 读回
4. 数据分条写, 一条别塞满字段上限; 记录好这组账号的账密/手机号, token 过期后要能重登

优点: 目标站自己就是 C2 —— 出口白名单、GFW、无公网 TLS 全部绕过, 也不需要后台接口存活。
缺点: 只能在你持有的那个账号有效期内读, 所以**账号必须先存好再投放**。

## 坑
- **别假设"客服聊天 = 可点链接"**: 实测多家后台聊天窗把消息渲染在 `<pre>` 里, URL 不转 `<a>`,
  运营要手动复制才生效 —— 投之前先看渲染代码或抓一屏; 纯文本就把主投递面换成审批队列
- 上传成功 ≠ 能执行: 扩展名可能被服务端重写为 `.png`/随机名 —— 回读 URL 才算数
- 多步实名/清退流会**交叉校验同一身份证**: 提交单里的 `idCard` 必须与实-name 时完全一致 ——
  空值或换号直接 400, 这一步最容易漏
- 注册突然回 `设备指纹不能为空` / `dFingerprint is required`: 不是封禁, 补随机 `deviceFingerprint`(32-hex)
  + `deviceCode` 即可; 说明对面在收校验而不是关入口, 别误判为"注册已关"
- 上传的 400 常是**请求头**问题, 不是白名单(见 Phase 1)
- `enabled:false` 的记录客户端读不到 ⇒ 外带必须 `enabled:true`, 这是真实副作用, 只发一条
- 别在验证 `Content-Type` 之前就去投递载荷, 白等
- **回传读取器的过滤条件必须和载荷写入的字段对得上**。载荷写 `receiverName: "SYS_"+tag`，
  监控就得按 `startswith("SYS_")` 捞；两边前缀不一致 = 载荷打中了也只是静默落库，看着像没点。
  投放前先自测写一条、确认读取器真的记了行，再投。读取器的 `seen` 集合只在内存时，重启会重放旧记录，属正常，别当新命中。
- 后台路由表里没有的路径, 先用 `PATCH`/`PUT`/`GET` 各试一次再判"不存在"

## 交付口径
证据三件: ①上传返回的 URL ②`GET` 该 URL 的 `Content-Type` 与 body 头
③后台 bundle 里 `localStorage.setItem("<key>_token"` 那一行。
三者齐 = 链路成立。点击未到时状态写"待触发", 不要写"已获取会话"。

## 上传白名单放 HTML/SVG + 静态目录公开读（2026-10 ceypto 实战）
- `POST /api/uploadFile` 放行 `.jpg/.png/.svg/.html`（只断 `.jsp/.php`）→ 落 `/picture/...`
- `GET /picture/common/...` 无 token 200 → **同源托管任意 HTML/JS**（钓鱼页、凭证收割页）
- 无鉴权版本：`POST /api/public/uploadimg!execute.action`，落盘 `/picture/chat/<date>/<uuid>.原名`
- 客服聊天存储 XSS：`POST /api/newOnlinechat!send.action` 用 mXSS 绕 HTML 过滤
  `<math><mtext><table><mglyph><style><!--</style><img title="--><img src=1 onerror=...>">`
- **先验证后台路由存在**：本例 `/miliao` chunk 全 404，XSS 无法触发 → 空欢喜
