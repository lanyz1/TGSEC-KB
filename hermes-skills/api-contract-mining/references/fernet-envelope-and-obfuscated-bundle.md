# Fernet 信封 + 混淆单包：从「看不懂的 JS」到全量契约与配置

适用：SPA 首页塞 `window.CONFIG='gAAAAA...'`、接口回 `{"x-data":"gAAAAA..."}`、bundle 被
javascript-obfuscator 混淆（字符串数组 + RC4 + 十六进制索引）。本案为白标博彩平台
（`*.wieuc.com`：`sm-api`/`hm-api`/`gj-api` 前端 + 自建 Plausible 统计台）。

## 1) 混淆单包 → 字符串 dump（Node `vm` 手写 harness）
先试 `npx webcrack bundle.js -o deob`：本案**零产出**（不报错也不写文件），不要在这上面耗时间。
改手写 harness（本技能 `scripts/deob_js_strings.js`）：

1. 从源码文本抽候选 key：正则 `\(\s*0x[0-9a-fA-F]+\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)`
   —— 混淆器把 RC4 的 key 作为第二参写死在每个调用点（实测 48 个候选，形如 `tk4r` `cEZ4` `@N@F`）。
2. `vm.createContext` 造一个假 `window/document/navigator/location`，`runInContext(SRC)`（尾部 IIFE 会报错，
   用 try 吞掉**不影响前面声明的全局函数**）。
3. 顶层 `function l()` = 字符串数组；`function u(i,key)`/`V(i,key)` = RC4 解码器（内部 `i = i - 377`，
   带 `index+salt` 缓存）。在沙箱里 `l()` 拿数组长度，再对每个 key × 每个索引调 `u(i,key)`，
   过滤可打印串去重即得全量明文。
4. 产出里最有价值的往往不是业务串，而是**真应用包路径**（实测 `/static/js/main~43dd7041.<hash>.js`、
   `vendor.crypto-js.<hash>.js`）—— 壳包只是加载器，真契约在那个静态主机上的 `main~*` 里。
   注意：壳包所在域的 `/static/js/*` 常被 SPA catch-all 吃掉（回 HTML 200），必须去**静态/CDN 主机**取。

## 2) 客户端硬编码 Fernet 密钥 → 解一切
Fernet（Python `cryptography`）被 crypto-js 在浏览器里重实现，密钥**明文写在模块导出里**：

```js
86315(e,t,o){o.d(t,["X7",0,"MCGqhW3pJuIffwzTJr2mj-URSanm7XydmUbpZYpenP0=",
                   "o7",0,"NyGRG56A8i5J2JMqh7da83r2MMfgbM7Ppw1aCF8YnAY="])}
34267: decrypt = e => (0,t.F4)(e, i.o7)      // F4 = fernet decrypt
       encrypt = e => (0,t.j1)(e, i.o7)
       encryptQrCode = e => (0,t.j1)(e, "aIuwOVepRY9AwPV4-7-hqiZFgK51XSdU1Moh_CrXIBg=")
```

抄法：全 bundle 正则 `["']([A-Za-z0-9_-]{40,46}=)["']` 收全部 44 字符 base64（实测 3 把：配置/o7、游戏/X7、二维码）。
Python 侧：

```python
from cryptography.fernet import Fernet
Fernet(key.encode()).decrypt(token.encode())   # token 即 window.CONFIG / x-data 的原文
```

- `window.CONFIG`（实测 87KB token）→ 直接吐出站点全配置：`api_url`/`public_url`、`site_id`/`channel_id`、
  多线路 CDN 域、`service_link`(客服)、`business_cooperation`/`traffic_cooperation`(TG 频道)、
  永久域名列表、APK 路径、**第三方 AI 网关 base_url + 每个模板的 `sk_*` api_key**。
- 响应体 `{"x-data":"<fernet>"}` → 解密即明文 JSON（实测广告位/招嫖/所谓「听话水」商品/会员档位全在里面）。
- 逐条响应落盘后再 grep，比在线边看边记快一个量级。

**已实测封死项（别再试）**：客户端请求拦截器里有个调试开关
`force_no_encrypt=567f9c9a-28cf-4096-b540-e428f40a1e74-jh82`（**从包里抠出来的真值**，不是猜的），
带上它服务端**照样回加密体** ⇒ 不要指望它降级成明文。

## 3) 免凭据会话：`/signup/visitor` 类端点
用户/游客注册端点常在**不需要任何凭据**的情况下发 token（实测 `POST /signup/visitor {site_id,channel_id}`
→ `{"data":{"user":{...},"token":"<JWT>"}}`）。拿到它就等于拿到整面认证 API 的测试会话：

- 头形状：`Authorization: Bearer <token>`（+ 游戏面另有 `x-token`/`x-user-id`/`x-user-name`，见拦截器）。
- **只带 `x-user-id`/`x-user-name` 不带 Bearer → `401 需要登录`**：头身份不被信任，别把「头可伪造」写成结论。
- JWT payload 里塞了 id/username/**明文口令**/group/vip 标志（游客号自动生成 5 位数字口令）。
  弱密钥爆破（37 个候选）+ 改 `id` 重签 → 全部 401 ⇒ **签名校验是真的**，直接判死，别再投时间。
- 方法形状：同族端点大量 **POST-only**，`GET` 回 `405 Method Not Allowed`（= **路由存在**），
  `404` 才是没这个路由。逐端点 GET/POST 两轮跑完再画表，别用一轮的 404 下「没这功能」。

## 4) 顺手记：静态主机与兄弟 API
一个域命中后立刻 `crt.sh/?q=%25.<域>&output=json`（**带 `%25`**）+ 常用子域爆破：
实测一次挖出 `gj-api`（另一条线路的 API）、`hm-media`(openresty 媒体仓，`/robots.txt` 可读)、`sh-static`。
子域命名常是「线路前缀 + 角色」（`sm/hm/gj/sh` × `api/static/web`），按这个矩阵去撞。
