# Next.js App Router 黑盒侦察实战 — Qavlixor 跨境电商案例

2026-08 实战:qavlixor.com(跨境电商商城,USDT 链上支付,Cloudflare 前置)。完整验证了「Next.js App Router 专属打法」的每一层。目标结构:主站 qavlixor.com(buyer)+ admin.qavlixor.com(独立后台)+ seller.qavlixor.com(商家端)+ cdn.qavlixor.com。

## 侦察时间线(每步可复现)

1. **识别 App Router**:响应头 `Vary: rsc, next-router-state-tree` + `Server: cloudflare`;HTML 里 `/_next/static/css/*.css` 三个样式 + `self.__next_f.push` RSC payload。
2. **build ID**:RSC payload `0:{"P":null,"b":"2WNfSv75iF8ZX-a4b5HJv",...}` → 新构建 ID。
3. **拉 chunk**:`grep -oE '/_next/static/chunks/[^"]+\.js'` 从首页/登录页/注册页各拿 chunk 列表 → 下载全部(含 `app/` 页级 chunk)。注意**每页 chunk 不同**——seller/login 页有 `app/seller/login/page-*.js`,buyer 注册页有 `app/register/page-*.js`,各自含自己的 fetch 调用。
4. **API 面**:
   - 通用 chunk:`fetch("/api/chat/unread")`、`"/api/admin/identity"`、`"/api/seller/account"`、`"/api/i18n/extra"`、`"/api/currency/rates"`
   - 动态拼接:`fetch("/api/".concat(v,"/nav-counts"))` → `/api/{seller|admin}/nav-counts` 均 401 存在
   - 页级 chunk 金矿:`app_seller_login_page-*.js` 暴露 `POST /api/auth/login` body `{role:"seller",email,password,remember}` 与登录后跳转逻辑(`next` 参数 + `entry` 字段);`app_seller_register_page-*.js` 暴露 `POST /api/email-verification/send {purpose:"register",email}` + `POST /api/auth/register {role:"seller",email,password,market:"global",emailCode,agree}`
   - i18n 字典 chunk(8873,1.2MB)暴露业务面:USDT 支付、链上转账、交易哈希、GMV 阶梯、提现审核、托管——高价值资金链确认
5. **多构建发现**:某些 404 响应里 build ID 变成 `57MACX2if8m7PYuQ82vem`(旧构建),且旧构建 `/_next/static/57MACX2if8m7PYuQ82vem/_buildManifest.js` 可访问,内含 `__routerFilterStatic:{numItems:168}` → 旧版路由总数 168。首页 `/_next/static/2WNfSv75iF8ZX-a4b5HJv/_buildManifest.js` 反而只有 `/_app` `/_error`(App Router 路由不写在 pages manifest 里)。
6. **API 存在性判定**:GET `/api/auth/login` → 405(存在,POST-only);GET `/api/auth/register` → 405;POST `{}` → 401/400 业务错误。POST 枚举发现 `/api/email-verification/send`(200 可发信)、`/api/sms-verification/send`(400 用途无效)、`/api/uploads`(401 需认证)、`/api/contact`(400 参数校验)。
7. **OTP 锁定阈值**:发一次验证码,连续提交错误码 111111→222222→... 第 6 次(100005)返回 `验证码错误次数过多,请重新获取` → **5 次锁定,6 位数字暴力不可行**。验证码绑定邮箱(用 A 邮箱 code 注册 B 邮箱 → `邮箱验证码不正确`);purpose 枚举仅 `register` 有效;发送接口无限速(可邮箱轰炸)。
8. **子域后台**:nslookup 猜解 `admin/seller/www` 命中;`admin.qavlixor.com/admin` → 307 → `/admin/login?next=/admin`(主域 `/admin` 404);`seller.qavlixor.com/seller` → 307 → `/seller/login`。admin 登录页 `defaultEmail` 为空,但 seller 登录页预填 `<EMAIL-REDACTED>` 测试账号。同一 `/api/auth/login` 用 `role` 参数区分 buyer/seller/admin。

## 复现要点

- 原生 Windows curl 的 `-o /d/渗透/x` 静默失败 → `cd /d/渗透/x && curl -o file` 相对路径
- 服务器会缓存/边缘差异:GET 500 的端点复测可能变 404 —— 以多次一致结果为准
- crt.sh JSON 404 时换 `api.hackertarget.com/hostsearch/?q=` 或 nslookup 猜解

## 结论沉淀

- 验证码类入口:先测锁定阈值、绑定粒度、purpose 枚举、发送限速,4 个测试 30 秒内完成,决定爆破可行性
- 商城类 Next.js 应用:**admin/seller 子域是独立部署**,与主域共享 auth API 但路由/后台页面独立;主域 404 不代表后台不存在
- 双构建(新旧 buildId 并存)= 部署未完全收敛,旧构建常泄露更多路由/旧 API/历史功能
