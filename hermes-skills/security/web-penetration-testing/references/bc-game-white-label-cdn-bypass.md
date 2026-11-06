# BC.GAME 白标赌场 + CDN 拦截下的浏览器渗透技法

> 来源:queen-casino.com(BQUEEN.GAME = BC.GAME 加密货币赌场白标)渗透 2026-08
> 核心价值:①CloudFront IP 级拦截下 curl 全 403 → 浏览器工具是唯一通路;②browser_console 在 Windows 的 cmd 表达式陷阱;③用 performance API 提取前端真实 API 面(比静态 grep 可靠)。

## 1. 白标识别(3 秒确认)

- 页面/JS 出现 `/bc_debug`、`/bcd/rule`、`/50tilt50`、`/events/bc-lottery`、`/api/game/support/...`、`collect.ccsccorp.com`(神策埋点) → **BC.GAME 白标**(sptpub.com 域名体系:api-k-{id}.sptpub.com 是核心 API、start9.sptpub.com 静态、files-immutable 存储)。
- 前端 JS 变量 `license`(localStorage.system) 存白标名(如 "queen")。
- 品牌数字 ID 在 API 调用里:`/api/v2/auth/brand/2666724129364905992/settings`。

## 2. CloudFront IP 级拦截 → 浏览器工具绕过

- **症状**:curl 直连/代理/带 UA/带 Origin/Referer 全部 `403 Request blocked`(919B CloudFront 错误页);`--resolve` 到边缘 IP 也一样。
- **根因**:CloudFront geo/ASN 限制(数据中心 IP 被拦)。**不是 UA/header 问题**。
- **绕过**:browser_navigate 打开站点(真实浏览器环境,CF 放行)→ 页面加载成功 → 前端调 API 成功。
- 源站发现(DNS 直连时):`api.sptpub.com` 解析到非 CF IP 时逐个端口探测;但**响应头 `Server: CloudFront` + 301 到 https 说明仍是 CF 边缘**,别当源站。
- S3 托管识别:`x-amz-id-2`/`x-amz-request-id` 响应头 + `/assets/*.js` 直接返回 `<Error><Code>AccessDenied</Code>` XML → 静态资源在 S3 bucket 且策略配置错误(信息泄露)。

## 3. browser_console 在 Windows 的 cmd 表达式陷阱(重要!)

Hermes 的 browser_console 在 Windows 上把表达式经 cmd 执行,**以下字符会触发 "not recognized as command" / "Command failed"**:
- `|`(管道)、`&`、`>`、`<`、`%`、反引号、`.join('|')` 等
- 复杂 Promise 链 + 箭头函数(`fetch().then(r=>...)`)不稳定,偶发失败

**可靠写法**:
```js
// 同步 XHR + var 循环,零 cmd 特殊字符
var x=new XMLHttpRequest();x.open('GET','/path',false);x.send();x.status+' '+x.responseText.slice(0,400)
// 批量枚举端点
var p=['/a','/b'];var r='';for(var i=0;i<p.length;i++){var x=new XMLHttpRequest();try{x.open('POST',p[i],false);x.setRequestHeader('Content-Type','application/json');x.send('{}');r+=p[i]+' '+x.status+' '+x.responseText.slice(0,80)+'\n';}catch(e){r+=p[i]+' ERR\n';}}r
// 读 localStorage(无特殊字符版本)
var r='';for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);r+=k+'='+localStorage.getItem(k).slice(0,80)+'\n';}r.slice(0,1200)
```
- `JSON.stringify(localStorage).slice(...)` 这类纯表达式能过;`.map(e=>e.name).filter(...)` 这类箭头函数+管道会挂。

## 4. 前端真实 API 面提取(比静态 grep 强)

- **performance API**:`performance.getEntriesByType('resource').map(e=>e.name)` 拿到页面已发出的全部请求 → 直接暴露**真实可用的 API 端点**(比在 600KB 压缩 JS 里 grep 快且准)。
- **重点:API 可能同域**!queen-casino.com 前端调的是 `https://queen-casino.com/api/...`(同域 Spring Boot),而 `api-k-*.sptpub.com` 反而是受 CF 保护的另一个服务。先看 performance 再判断。
- localStorage/sessionStorage 常泄露:`app_run_device_id`(设备 UUID,API 认证关键)、`system`(license/币种配置)、`wallet`、`account`(游客态 userId=0)。
- **XHR hook 捕获认证头**(等用户触发注册/登录,拿到 1:1 请求头):
```js
window._hdrs=[];var _set=XMLHttpRequest.prototype.setRequestHeader;XMLHttpRequest.prototype.setRequestHeader=function(k,v){if(!this._h){this._h={}}this._h[k]=v;return _set.apply(this,arguments)};var _open=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u){this._u=u;return _open.apply(this,arguments)};var _send=XMLHttpRequest.prototype.send;XMLHttpRequest.prototype.send=function(b){window._hdrs.push(this._u+' :: '+JSON.stringify(this._h||{}));return _send.apply(this,arguments)};'hooked'
```

## 5. Spring Boot 后端识别与端点探测

- 错误格式 `{"timestamp":...,"status":401,"error":"Unauthorized","path":"/auth/register"}` = Spring Boot(网关/过滤器 401)。
- **401 全端点 vs 404 区分**:401 = 路由存在但全局认证过滤器拦截(所有 /api/auth/* 都是 401 → 这些端点存在,只差认证头);404 JSON `{"code":1901,"msg":"Oops, coco is gone!"}` = 应用层自定义 404(路径不存在);404 nginx HTML = 网关层不存在。
- 开放端点示例(游客可访问):`/api/account/get/`、`/api/user/amount/`(多币种余额)、`/api/account/device/isRegistered`、`/api/game/support/*`、`/api/payment/deposit/history/`、`/api/payment/withdraw/history/`。
- 高额榜单/最近中奖接口(`/api/game/support/home/v2/high-rollers/`、`/v3/recent-big-wins/`)泄露玩家昵称+金额 = 隐私信息泄露,可作报告素材。
- SPA catch-all 干扰:`/actuator`、`/swagger` 等返回 200 + HTML(index.html)= 前端路由捕获,**不是真实后端端点**;真实后端在 `/api/` 前缀下,探测要带 /api/。

## 6. 陷阱

- 别被 `/assets/*.js` 的 S3 AccessDenied 误导(S3 配置错误 ≠ 站点全挂;浏览器能拿到内容,curl 拿不到 → 用浏览器/console 读 JS)。
- 白标平台注册/登录接口(`/api/auth/register`)全局 401,需要先拿到设备 token/游客 token——优先走页面 UI 真实注册流程(XHR hook 抓 header),不要硬猜 header 名。
- 事件收集/埋点域名(collect.ccsccorp.com)不是业务 API,忽略。
