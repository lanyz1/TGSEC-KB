---
name: spa-api-discovery
description: "Reveal SPA backend APIs via JS chunks, XHR hooks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [recon, api, javascript, spa, frontend]
    category: security
---

# SPA API Discovery Skill

黑盒渗透 SPA(单页应用)时,不要猜 API 路径——从前端运行时把真实后端接口、请求格式、token 机制挖出来。本技能覆盖 Vue/React 等 SPA 的完整逆向链路:定位 JS → 解压 → 找 API → 抓真实请求 → 复现调用。

## When to Use

- 目标是 Vue3/React SPA,后台 API 路径未知或文档缺失
- curl 复现接口报"参数解析错误/输入值解析错误"等业务错误,怀疑前端对字段做了变换
- 已登录前端但不知道 API 域名/token 头名
- 站点看似有多个 API 域名(迁移/负载均衡),需确认哪个在用

## Prerequisites

- 浏览器工具(browser_navigate / browser_console)
- curl / python(复现请求)

## How to Run

### 1. 定位并下载前端 JS

SPA 的 HTML 里 `<script type="module" src="/static/js/index-XXX.js">` 指向主入口,**主入口往往是加载器,业务代码在 chunk**(HTML 中 `<link rel="modulepreload">` 列出)。

```bash
curl -s --compressed "https://target/static/js/index-XXX.js" -o index.js
# 注意 --compressed!服务器常返回 gzip,不加会得到二进制
zcat file.js > dec.js   # 或 curl -s --compressed 已自动解压
```

### 2. 从 JS 里提取 API 路径与 BASE_URL

```bash
grep -oE '"/api/[^"]{3,80}"' dec.js | sort -u          # 常见绝对路径
grep -oE '(baseURL|BASE_URL)[^,;]{0,80}' dec.js | sort -u  # API 基址
grep -oE 'https?://[a-zA-Z0-9.-]+' dec.js | sort -u    # 全域名(发现迁移/多后端)
```

混淆严重的代码用 `grep -oE '(login|account|password)[^,;]{0,60}'` 找关键字,再回溯上下文。

### 3. 金矿:浏览器 resource timing 看真实请求

在已登录页面的 console 执行——**列出页面实际发出的所有请求**,直接暴露真实 API 域名和路径(尤其 API 迁移后旧域名残留的场景):

```js
performance.getEntriesByType('resource').map(e => e.name).filter(n => /api|yourdomain/.test(n))
```

### 4. Hook XHR/fetch 抓真实请求格式

先 hook 再触发操作(登录/翻页),记录 method/url/body/headers:

```js
window.__reqlog = [];
const oO = XMLHttpRequest.prototype.open, oS = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function(m,u){ this.__m=m; this.__u=u; return oO.apply(this,arguments); };
XMLHttpRequest.prototype.send = function(b){ window.__reqlog.push({m:this.__m,u:this.__u,b:b?String(b).slice(0,500):null}); return oS.apply(this,arguments); };
// 触发登录后:
JSON.stringify(window.__reqlog)
```

### 5. 复现请求——警惕前端字段编码

登录/敏感字段可能被前端变换后发送:

- `unescape(encodeURIComponent(password))` 类编码
- base64、自定义加密、或显示层打码(console 里 password 显示 `"***"` 不一定是加密,可能是工具打码——**用 hook 抓真实 body,别信显示**)
- **curl 直接发明文报"输入值解析错误"而页面登录成功 → 高度怀疑前端字段变换**,需从 JS 还原变换函数

### 6. token 提取

登录成功后 token 通常在 localStorage/sessionStorage。搜索常见 key(`token`、`SOY_token`、`Authorization`、`travelerToken`):

```js
for (let i=0;i<localStorage.length;i++){ const k=localStorage.key(i); console.log(k, localStorage.getItem(k).slice(0,100)); }
```

### 7. ★ 路由表 + token 键名：一条 grep 挖出隐藏后台(2026-10 定型)

**路由表就在 bundle 里**。把每个路由的 `path` 抽出来逐个探活，能拿到**页面上没有任何链接指向的隐藏后台**
（实测：前台无痕，grep 路由表命中一个隐藏的 Admin 登录路由）。同一次 grep 还能拿到后端期望的**令牌键名**——
比登录成功后再去翻 localStorage 快一整轮：

```bash
# 1) 路由表：path 逐个抽（重定向目标 _redirect 常就是隐藏后台入口）
grep -ohE 'path:"/[^"]{2,60}"' chunks/*.js | sort -u | head -50
grep -ohE 'redirect:[^,]{0,60}' chunks/*.js | sort -u
# 2) 鉴权元数据：requiresAuth / role 直接标出哪些路由要登录(=管理面)
grep -ohE 'meta:\{[^}]{0,80}' chunks/*.js | sort -u | head -30
# 3) 令牌键名与后端期望的键（admin_token / admin_token_expires_at 这类）
grep -ohE '(tokenName|authKey|TOKEN_KEY|localStorage\.(get|set)Item)' chunks/*.js | sort -u
```

判读纪律：

- **抽出的路由必须逐个 HTTP 探活**（`curl -o /dev/null -w '%{http_code}'`）——否则只是「代码里有」而已；
  200/302 是活路由；404 仍可能是 catch-all 吞掉（见 Pitfalls）。
- **隐藏后台的登录接口常与前台共用同一后端前缀**（如 `/adminApi/auth/*` 之于 `/shopApi/*`）——
  拿到路由名就等于拿到**命名空间**，顺着抽该名字空间下的 chunk 即可拿到完整后台 API 契约。
- **令牌键名直接告诉你后端认哪个头**（`tokenName:"admin-token"` ↔ localStorage 的 `admin_token`）：
  爆破/登录取票一次到位，不用再靠试 `Authorization`/`token` 猜一轮。

## Next.js (App Router) 专属打法

Next.js 前端结构完全不同:没有单一 `index-XXX.js`,路由页按 `app/<route>/page-*.js` 分片。**API 契约全在页面级 chunk 里**,比 Vue SPA 更好挖。

### 识别

- 响应头含 `Vary: rsc, next-router-state-tree` + HTML 里有 `/_next/static/css/*.css` → App Router
- HTML 尾部 `self.__next_f.push([1,"0:{...\"b\":\"<buildId>\"...}])` → build ID

### 1. 拉全量 chunk

```bash
grep -oE '/_next/static/chunks/[^"]+\.js' <page.html> | sort -u   # 每页 chunk 列表
# 逐一下载到 chunks/,app/ 前缀的页级 chunk 必须下(业务逻辑在那)
```

### 2. 挖 API(三层)

- 通用 chunk(数字命名 8873/9030 等):`grep -ohE 'fetch\("[^"]*"' chunks/*.js | sort -u` → 静态 API 路径
- 动态拼接:`grep -ohE '"/api/"\.concat\([^)]*\)'` → 前缀+后缀组合(如 `/api/{role}/nav-counts`)
- **页级 chunk 金矿**:`app/seller/login/page-*.js` 里有完整 fetch 调用与请求体,直接还原接口契约(字段名/role/market/agree)
- i18n 大字典 chunk(如 8873)可确认业务能力面(支付/提现/售后/风控关键词)

### 3. 多构建探测(重点!)

不同路径可能由**不同 build 的实例**响应——RSC payload 里 `"b":"<buildId>"` 不同即多部署(旧版常暴露更多路由/旧 API,且旧版 `_buildManifest.js` 常仍可访问):

```bash
for p in /api/xxx /yyy; do curl -s "$T$p" | grep -oE '"b":"[^"]{8,20}"' | head -1; done
curl -s "$T/_next/static/<oldBuildId>/_buildManifest.js"   # 含 __routerFilterStatic.numItems=路由总数
```

### 4. API 存在性判定(Next.js 特性)

- GET 返回 **405** = 路由处理器存在,仅接受 POST(再 POST 确认)
- **405 只说明「路由存在、方法不对」,不说明「鉴权缺失」** —— 不要读成「鉴权后置可分绕」。
  从前端 JS 抽全契约后按正确方法重测:同一批端点 GET 回 405、换 POST 后全回 **401**,结论就是**鉴权有效**;
  只有换对了方法仍不返回 401 的端点才是未鉴权候选面
- GET 返回 **500** = 处理器存在但 GET 异常——**必须复测**,500 可能是瞬态/边缘节点伪影,再测可能变 404
- GET 返回 404 页面(带站点壳) = 路径不存在(被 catch-all 吞掉)
- 401/400 带中文业务错误 = 存在且需认证/参数
- **用「400 字段校验 vs 401」判未鉴权面**:protobuf / gRPC-Gateway 校验的后端只要空 body 一发就吐
  `field "x" is not set`,逐字段喂回去即可枚举完整请求契约(必填字段名/类型,省掉猜参数的一轮);
  而**回字段级 400 而不回 401 = 请求已穿过鉴权中间件**(走到了参数绑定)⇒ 这批端点就是未鉴权面

### 5. 验证码(OTP)锁定阈值测试(爆破前必做)

邮箱/短信验证码类接口,先探锁定策略再决定是否爆破:

```bash
# 发送一次验证码后连续提交错误码:
for i in 111111 222222 333333 444444 555555 666666; do
  curl -s -X POST "$T/api/auth/register" -H 'Content-Type: application/json' \
    -d "{\"email\":\"<EMAIL-REDACTED>\",\"emailCode\":\"$i\",...}"
done
# 出现"错误次数过多,请重新获取"= 有锁定(本案例 5 次),6位数字暴力不可行,转注册提权/账号接管思路
```

附加测试:验证码是否绑定邮箱(用 A 邮箱 code 注册 B 邮箱)、purpose 枚举(`register`/`login`/`forgot` 哪些有效)、发送接口是否限速(无限速 = 可做邮箱轰炸 DoS)。

### 6. 子域名后台发现

市场/商城类应用常拆 buyer/seller/admin 子域,且共用同一 `/api/auth/login` 只差 `role` 参数:

```bash
for sub in admin api seller buy shop m www app portal dashboard console manage backend panel; do
  nslookup "$sub.$DOMAIN" 2>/dev/null | grep Address
done
# 命中后:admin.$DOMAIN/admin → 307 → /admin/login?next= 即独立后台(主域 /admin 反而 404)
# 测试 role 提权: {"role":"admin","email":...,"password":...} 打同一 login 端点
```

## Pitfalls

- **JS 是 gzip**:curl 不带 `--compressed` 得到二进制,file 命令显示 "gzip compressed data",先解压再 grep
- **主 JS 是加载器**:业务接口几乎都在 chunk 里,别只查主文件
- **跨域 Failed to fetch ≠ 请求没到**:浏览器 CORS 拦截可能发生在响应读取阶段,服务端已处理请求;用 curl 绕过 CORS,但注意字段格式
- **API 迁移**:旧域名可能仍响应但报业务错误(`ROUTE_NOT_FOUND`/`输入值解析错误`),resource timing 里的新域名才是活的
- **字段打码 vs 编码**:console 里看到 `"password":"***"` 时,先确认是工具打码还是前端真的替换了值——hook send 的原始 body 是唯一可靠来源
- **同一个 `/api` 同域路径返回 SPA HTML**:说明该路径没有反代,API 在别的域;同域 `/api` 命中 SPA fallback 是常见陷阱
- **登录/注册的完整载荷要从页面与它的 JS 里枚举,不能只按猜的字段名试** —— HTML 隐藏域(`captchaId` 之类)+
  `captcha.js` / `sign.js` 这类模块就是前置闸门;带验证码或签名的接口,请求在**密码比对之前**就被拦下,
  所以字典全 NO HIT 是**无效测试,不是负结论**。发布负结论前必须发一发真实请求并打印完整响应体,
  按文案分类(「验证码错误」≠「密码错误」)
- **原生 Windows curl 不认 MSYS 绝对路径**:`curl -o /d/渗透/x` 静默失败(No such file),`cd` 后用相对文件名或 `C:/` 风格路径
- **crt.sh JSON 查询不稳定**:`crt.sh/?q=%25.domain&output=json` 常 404(2026-08 实测),换 `api.hackertarget.com/hostsearch/?q=` 或直接子域猜解(nslookup 循环)

- **生成式 client 里的方法名不是路由**:`{path:"/api/<ns>/<Method>",method:"POST"}` —— 只抽 `"/api/Xxx"` 会拿到一堆方法名, 直接打全 404;要按 `path:"...",method:"..."` **成对提取**, 才得到带名字空间(`/api/buckets/*`、`/api/users/*`)的真实路由表。路径未知时每个路径 GET+POST 各打一发, 否则 405 会被误读成不存在(详见 `references/frontend-api-map-vs-swagger-delta.md` §5)。批量探测前先自证:候选数要打印并与提取到的路由总数对照(过滤依赖正则捕获时, 空集会被读成「零候选」的干净负结论), 命中判定排除 401/404/405 并打印状态码直方图 —— 否则 405/401 会被误标成未授权命中

## References

- `references/umi-platform-api-recon.md` — UMI 企业智脑实战案例:API 迁移发现(qyapi→znapi)、登录密码编码、token 提取全流程
- `references/nextjs-app-router-recon.md` — Qavlixor 跨境电商实战:Next.js App Router 双构建发现、页级 chunk 挖 API 契约、OTP 5 次锁定、admin/seller 子域后台
- `scripts/extract_route_table.py` — 从 bundle 提取 (path, method) 路由表 + 只读未授权探测(带 401/405/404/400 语义分桶, 破坏性路径自动跳过)
- `references/js-host-fragment-and-namespace-mining.md` — CDN 死路时从 JS 字符串片段挖活宿主(`indexOf("https://<前缀-)"` + `location.origin` 端口分支), 按**多前缀**抽契约(不只抽 `^/api/`), 用 `POST {}` 零成本探第二套命名空间的未鉴权面

## Verification

- 能从 resource timing / XHR hook 拿到至少一个真实 API 请求(method+url+body)
- curl 复现该请求得到与页面一致的业务响应(而非"解析错误")
- 定位到 token 存储位置与传递头名
