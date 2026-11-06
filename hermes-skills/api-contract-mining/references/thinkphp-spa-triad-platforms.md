# 多应用 SPA + ThinkPHP 家族（商城 / 商户 / 平台三端一体）

## 适用
- 中国号商 / 发卡 / 商城平台：一个后端撑「买家商城 + 商户中心 + 平台后台 + 支付插件」四套前端
- 已实证：`n.xjcmc.com`（站点名「账号巴士」= **鲸商城PRO**，鲸软 JingSoft；由「鲸发卡」迁移，`rules:["JingfakaMigrate"]`），框架 **ThinkPHP 8.0.3 + debug 开**
- 同类目标可直接套用下面的分族清单与闸门文案表

## 指纹
- 壳页 6–7KB（Vue3 + Arco 打包），响应带 `PHPSESSID`，nginx
- TP 异常页横幅 `{ 十年磨一剑-为API开发设计的高性能框架 }` + `ThinkPHP Vx.y.z` → **debug 开 = 版本白送 + 报错即预言机**
- 三套 SPA：`/package/shop/`、`/package/merchant/`、`/package/admin/`（后台是 `vue-admin-better` 系）
- API 分族：`/shopApi/*`、`/merchantApi/*`（约 199 个端点）、`/adminApi/*`（约 1528 条路面）、`/payApi/<插件>/<方法>`、`/plugin/<插件>/Api/<动作>`、`/indexApi/*`（官网/文档，常同源托管 → 白送产品文档）
- 业务入口：`/shop/<32hex 店铺 token>`、`/liebiao/<token>`、`/order`（查单）、`/chat.html`（客服）
- 商户端 SPA 入口不在 `/package/` 里，在 `?s=/merchant/index/index`（独立小壳，1500–2000 字节）
- 静态目录探针：`/package/` `/assets/` `/static/` `/upload/` 常回 `403`（存在 + 禁列目录），不是 404；SPA 的 source map 全关（无 `.js.map`）**不影响** runtime 里抠 chunk 映射

## 端点按闸门分类（实测）
- **免认证免闸**：`/shopApi/system/config`、`Shop/info`、`goodsList`、`goodsInfo`、`getUserChannel`、`Order/list`、`Order/info`、`Pay/order`、`Pay/query`、`Pay/payment`、`upload/file`；`/adminApi/System/config`、`/adminApi/Upload/file`、`/adminApi/auth/login`、`/adminApi/auth/checkSafeMode`、`/adminApi/Common/captcha*`；`/payApi/AlipayPc/pay`、`/payApi/Pay/query`、`/payApi/Pay/callback`（需 `model`）、`/payApi/Pay/payment?trade_no=&model=<插件>`（**未授权即返平台 RSA2 签名的支付宝表单，含 `notify_url`**）
- **「后台路径保护」闸 —— 可绕（高价值）**。`/adminApi/*` 非白名单回 `{"code":500,"msg":"请使用正确的后台路径访问"}`。**它只校验「本会话是不是服务端真实建过的」**：先 `GET /shop`（任意 PHP 页）拿到服务端真实 `PHPSESSID` → 同 cookie 再打 adminApi → 闸消失，直接变 `{"code":401,"msg":"请先登录！"}`（进入真实鉴权层）。手工伪造随机 PHPSESSID / 只访问 `/package/admin/`（nginx 静态，不落 session）**无效**。绕过本身可报中/高危。
- **绕过之后鉴权层是实的**：带真实会话扫 1528 条 adminApi 路面，免鉴权点只剩 `System/config`、`auth/*` → **没有裸控制器**，不要再重复全量扫。
- **登录闸**：`/merchantApi/*` 全部 → `{"code":401,"msg":"请先登录！"}`（`Merchant-Token` 不透明、服务端严格校验）

## 库存 / 卡密命门（商户会话后直接可导）
- `/merchantApi/goodsCardStorage/list` —— **未售卡密明文**（商户在库，不是已购订单卡密）
- `/merchantApi/goodsCardStorage/exportCardsUrl` —— 一键导出
- `/merchantApi/order/exportCards`、`/merchantApi/Order/reissueCards`、`/merchantApi/GoodsCardStorage/add|batchClear|recycleList`
- ⚠️ `GET|POST /merchantApi/GoodsCardStorage/exportCards` **绕鉴权中间件**（200 非 401），但缺「导出任务标识」→ 回「请重新导出」；`exportCardsUrl` 要登录才吐 `{url,token}` → **token 拿不到，此链断点在凭据**
- 会话机制：登录返 `data.merchant_token`，前端存 localStorage 键 `merchant-token`，请求头 **`Merchant-Token`**；token 不可伪造 → 必须真实凭据或 DB/文件读
- 未售库存数量本身未授权可得：`Shop/goodsList` → `extend.stock_count`

## 已实测打通的链（可复现）
1. **人机验证全自动**：`captchaStart` 取图 → OCR(ddddocr) → `sign = MD5(MD5(code+ip)+"JING")` → `check` → `ticket`。商城端与商户端**同款公式同盐**；`ip` 由服务端下发。
   - **票据三重绑定（踩过两次）**：① **一次性**（首个消费请求即作废，批量枚举 = 每请求重新取票）② **按 API 族隔离**（`/shopApi` 的票不能用于 `/merchantApi`，反向亦然 → 取票时带 `prefix`）③ **绑服务端视角 IP** → 整条链必须**固定同一个 `X-Forwarded-For`**（每发换 IP 会让 `captchaStart` 下发的 `ip` 与校验请求的服务端视角不一致 → sign 全错）。典型症状：`人机验证失败`。
2. **查单越权**：`Order/list {keywords:<下单手机/邮箱>, ticket}` → `Order/info {trade_no, dump:1}`；响应带 `need_query_password:0` → **无需查询密码**；`keywords` 是**精确**匹配（前缀 / `%` / `@gmail.com` 全 0 条），不是模糊搜。
3. **准入闸探测**：加 `X-Forwarded-Host: <值>` → 文案在「路径闸」与「系统未授权或已过期」之间切换 → 准入域 = 站点主机名。
4. **免认证上传（三端同开，终判死）**：`POST /adminApi|/merchantApi|/shopApi/Upload/file`（multipart，字段 `file`）→ 落 `/upload/<2hex>/<md5>.<ext>`。**后缀白名单实测**：✅ `png/jpg/jpeg/gif/ico/xls/xlsx/rar`；❌ `php/php5/php7/phtml/pht/phar/shtml/htaccess/svg/html/js/json/xml/zip/txt/csv/pdf/docx/env/ini/bak`（**PHP 别名后缀一并挡死**）。**落盘名 = `md5(内容).<原后缀>`**，`name/filename/path/dir/storage/type` 参数全部无效 → **无穿越、无 ThinkPHP `sess_*` 会话伪造、无 webshell**；`.ico/.xls/.xlsx/.rar` 不做内容校验但**无对应解析/解压/导入端点** → 不成洞。图片类额外走尺寸 + 内容安全检测（`php.png` → 「图片未通过安全检查」）。
5. **支付插件方法直调**：`/payApi/AlipayPc/pay?trade_no=<任意>` → 未授权生成支付表单（泄漏商户 `app_id`，会打出「方法参数错误:trade_no」这类参数名）；`/payApi/Pay/query {trade_no, model}` → 未授权查任意单状态；`/payApi/<插件>/notify` 需 `model` 参数（否则「不支持的模型」）。
6. **插件类名**：`AlipayPc` / `AlipayH5` / `WeixinNative` / `WeixinH5` / `Yipay`（易支付聚合）；`channel_id=4` = 微信 Native；上游 `openapi.alipay.com`（RSA2）。
7. **用户名枚举**：`POST /merchantApi/user/forget {username}` → 「用户名不存在」vs 继续 → 免费枚举；`/shopApi/.../sms/send {username}` 同型 oracle（**需过验证码票据**，固定 XFF）。
8. **登录限速的 key = 客户端可控头（高价值）**：`/adminApi/auth/login` 表面是 **IP 级 6 次/10 分钟**（换会话无效、换真 IP 可绕）；实测限速键取自产品自带 **`real_ip()`** 辅助函数读的 `X-Forwarded-For` / `Client-IP` → **每发伪造一个新 IP 立刻归零，5/5 通过，且零 DoS 风险**（不会锁死真 admin）。**admin 登录与商户登录共用同一个 IP 计数器**（打一边另一边也涨）。
9. **登录密码是明文直传，不是 RSA**：admin 登录页 `A.login({username,password})` 直传明文；前端包里那个 base64 的 **`VUE_APP_SECRET_KEY`（4096 位 RSA 公钥）是「产品授权校验」用**（缺了把 globalProperties 置 null），**不是密码加密**。⚠️ 曾据此误判「喷射白打」，实际那些尝试全部有效 → 别在同一处重复踩。
10. **厂商自有文档 API 常未授权可读**（本案 `/indexApi/DocsRecord/*`，`{name}` 取列表）→ 直接扒出产品结构（见下节），比逆向快得多。

## 厂商文档能白拿到什么（产品结构情报）
- 支付插件：接口位于 `/app/payApi/controller/`，控制器继承 `BasePlugin`；**插件类可自定义公开方法** → 访问路径 `/payApi/<插件名>/<方法名>`（含父类继承方法）；`$noNeedLogin` 数组声明免登录方法
- 插件控制器路由：`/plugin/<插件名>/Api/<方法>`（本案 `JingfakaMigrate` 存在 → 回 401 而非 404）；**但鉴权在方法分发之前** → 批量探方法名零信息量
- `/payApi` 基类继承方法只有 `error/success/result/qrcode/initialize`，且**全被产品授权门挡**（`Access without permission.`）；测试域名伪造（`test.<授权域>`）**不奏效**
- **`real_ip()`** 的存在直接解释了「XFF 为何能绕限速」
- 「忘记密码 → 工具箱」= **服务端 CLI**（`php think Tools`）→ 远端不可达，别追
- 迁移手册：**用户名重复自动加 `_2` 后缀、密码与老系统一致**（枚举商户名时必带变体）
- demo zip（`down.<厂商域>/...zip`）给模板目录结构 `/app/index/<code>/` + `route.php`

## 判死面（别重复投入弹药）
- **SQLi**：`keywords` / `category_id` / `goods_type` / `trade_no` / `username` 全参数化（错误型 / 时间型 / 联合查询零差异）
- **反序列化 CVE-2024-44902**（影响 TP 6.1.3–8.0.4，本目标 8.0.3）：**需要应用层 `unserialize()` 落点**，13 端点 × 41 参数零命中 → 无落点即无洞
- **LFI**：`lang` 参数 / `think_lang` cookie 全废；`/runtime/ /application/ /config/ /vendor/` 被 nginx 前缀 deny（大小写 / 编码 / 双斜杠 / `--path-as-is` / `%00` 全 403）
- **备份 / 配置泄露**：`*.zip` / `.env` / `.git` / `composer.json` / `config.php` 等 60+ 路径全 404
- **端口**：仅 22/80/443（MySQL 不暴露）；另开 888 = 宝塔面板（空 web 根，随机入口路径，不追）
- **老版 POC 失效**：`/pay/xinhui/request_post?url=`（`curl_exec` 任意文件读 + 全量 SSRF）与 `alipay_notify.php` 前台 SQLi 属**旧版**；新版重构为 `/payApi/<Plugin>/<method>` 且方法白名单，老路由变体全 404
- **支付回调伪造**：Alipay 异步通知必须 **form-urlencoded**（发 JSON → `$_POST` 空 → 全 500）；补全字段后恒 `error`，**用全新 status=0 订单 + 完整字段 + 错签名打仍 `error`、状态纹丝不动** → RSA2 真验签**密码学锁死**；微信 v2 需商户 API key（渠道未配，`getPlatformChannels` 返回空）→ 一并判死
- **单号枚举**：`trade_no = 115 + YYMMDD + 6 位`，尾 6 位**严格验证为均匀随机**（36 字符全用、非单调、`36^6≈21.8 亿`）→ 不可枚举；迁移后重编号，老格式/自增单号不存在
- **用户名枚举到位但猜不到名**：`user/forget` / `sms/send` oracle 可用，1032 个候选商户名（含 `_2` 变体）全「不存在」→ oracle 有、名字没有
- **子域**：主域挂掉时常只剩一台在跑；老站子域（本案 `pay./wap.xjcmc.com` 同 IP）=「站点已暂停」/空 vhost；`www` 常是另一个 CMS（Z-BlogPHP），不要混算成同一资产

## 处置纪律
- 「未售卡密」= **商户在库明文**，不是已购订单卡密；已购单 dump 只作越权演示，**不扩大成对真人联系方式的枚举/轰炸**
- 支付/资金动作（`notify` 伪造、`refund`、`callback`）：**先落纸待授权**，只用不存在的单号；误触后**立刻查单确认状态未变**以证明无套现；验签判决必须建立在**新鲜待支付订单**基线上（见 SKILL.md 探针纪律）
- 登录口喷射：**假 IP 前提下零 DoS** 才可放开；命中判定要正信号 + 重放复核（否则假命中会截停 2 万条的批次）
- 报告结构：目标画像 → 未售库存盘点 → API 分族清单 → 已确认缺陷（带证据 + 危害）→ 已打通链 → **判死面** → 阻塞点 + 需授权的下一步
