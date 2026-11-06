# 「花」系 / pc28gj.cc 生态档案（2026-10 实测）

## 资产面
- **主站 pc28gj.cc/app** =「Canada 28 挂机」TWA：TG 自动投注台（绑定+initData 双门）。bot @PC28GJbot（数字 id 8709090627，即匿名 cookie 前缀 `pc28_web_<botid>` 的来源）。
- **pro.pc28gj.cc**「PC28 Pro」：独立账密（开放注册）；/api/admin/* 403；CSRF 全站、批量赋值被过滤、DELETE/verify 按用户作用域（A/B 对测）→ 用户级基本无洞。
- **qf.pc28gj.cc**「QF 控制台」：TG 群发/采集/账号库管理（bot @HHQFbot；菜单 34 项：拆包/合并/格式互转/筛活/克隆资料/改2FA/手机号转协议号/文件转API≤5000…）。initData 登录；admin 回调（admin_panel/hb_menu）**静默丢弃**；user_id/tg_id 注入无效；上传文件名 sanitized（`../` 剥掉）；下载 token=22位 base64url（16B 随机、可复用、篡改 404、需 auth）。
- **yijian.pc28gj.cc**（旧棋室）+ **wuzi-20261006.pc28gj.cc**（新构建，FastAPI）：`/openapi.json` 全开（78 路由，含 /api/admin/* 全集）；`POST /api/session {"initData"}` → token；admin 全 403；娱乐城=签到 +50000 USDT/日（游戏钱包）；rooms code=8位数字、replay token=32 字符。
- **api.pc28gj.cc**：短链服务（`链接无效或已过期`；POST 405）。
- 全族 Cloudflare 后（`via: 1.1 Caddy`）；16 个历史 IP 全为停放/无关机 → 疑 CF Tunnel。

## 运营者与 bot 生态
- 「花」@hua49（t.me 预览署名：TG号/代开会员/僵尸粉）；频道 @hua49x；交流群 @GJJLQUN；客服 @okhhh；
- 号铺 **@HHPFbot「花花API」**；群发器 @HHQFbot；棋牌 @WZVSbot（wuzi 前端）；挂机 @PC28GJbot。

## 号铺库存（@HHPFbot 菜单实测，≈75万+）
6-12月 275,476 / 1-2年 236,391 / 2-5月 72,099 / 3-4年 65,570 / 二手老号 26,306 / 5年+ 22,592 / 欧美 27,910 / 亚洲 15,950 / 非洲 14,592 / 双向Spam 10,887 / 7年+主号 2,148 / VIP盲盒 727 / 靓号4A 35。购买=余额扣款→自动发 S+J ZIP；商户申请=人工审核。

## 支付链
- USDT：TRON 地址 + 服务端 TronScan 验链（「我已转账」按钮 → 查链；实测回显 `TronScan HTTP 401`=其集成故障）。
- OKPAY：`t.me/OkayPayBot?start=shop_deposit--<hash>`（bot 内屏显示商户/金额/订单号；内部钱包转账，需余额+4位PIN）。
- KkPay：`t.me/kkpay?start=merchant_deposit--<hash>`（主站/Pro 会员订单）。
- 金额一律服务端定价（篡改被忽略）；订单号 `R<yyyymmddhhmmss><rand>`；回调端点未暴露。

## 主站绑定链 / 挂机门
- `POST /web/session` → link_code(15位/600s/可复取) → bot `/start web_CODE` → cookie `linked:true`(30d)。写接口绑定即可（无 initData）。
- 挂机引擎 start 有会员门（`请先购买会员`）；提现需收款信息；admin/action 需 role（`无管理员权限`）。

## 已测负结果（勿重复）
- 各系统 admin 面 403 或静默丢弃；QF 无跨租户；wuzi SQLi 被输入校验拦、profile 只认真实 id；pro 作用域正确；主站 `?user_id=` 被忽略。
- /api/replays/{token}/export 等未测（token 随机不可猜）。

## 资源
- 测试号 Hazel（8621525517，+57…，2FA 8899）：客户提供；已绑主站 + 办 QF/wuzi 会话（initData/token 在 loot/initdata/）。
- 免费拿号的三条路：支付链伪造 / 运营者后台凭据 / 服务端 RCE——均未破，属持续目标。

## 钱包 bot 族（OkPay/KkPay 双胞胎，2026-10 实测）
- **@OkayPayBot「OkPay」**菜单：充值/提币/转账/收钱/红包/闪兑/余额宝/话费·星星·会员/商户/官方交易群/OK游戏中心(@ok28)；**@kkpay「KkPay」**同款 + 匿名信用卡、添加到群组、自由承兑群(OTC)。两者与主站/号铺/棋室互链 → 同一家族。
- 关键实测：零余额点「✅ 确认支付」→ `操作失败，余额不足`（**校验真实，非信任式**）；USDT 充值=共享 TRC20 地址（可重复充值，**按发送方地址归账**——无 memo/tag）；商户创建入口「➕ 创建商户」被 4 位支付 PIN 拦截（旧卡主 PIN 未知——不爆破）；个人中心/收钱=选付款人式发票流程。
- 未测余项（供下轮，非已验证漏洞）：红包/闪兑的负数与重复领取、商户回调测试模式、PIN 重置链（SMS/客服/TG 确认）、钱包与号铺/主站的订单状态机对撞。

## 补充负结果（勿重复）
- QF 教程页（代理 IP 教程等）纯文本无外链；畸形/空/深嵌套 zip 不吐栈（错误处理干净）；QF 「手机号转协议号/文件转API/交付安全化」=对自有上传文件操作，无中央号库接口。
- wuzi：rooms 全流程可用（创建/聊天/close 需体）；`share/prepare` → `{id, t.me/wzvsbot?start=<8位房码>}`；game id 全局存在但**他人局 403 正确拒**（games/1/replay）；sticker-pack 名无穿越（编码路径 nginx 归一化）。
- OkPay「设置确认」类按钮点击后回显服务端原始集成错误（`TronScan HTTP 401`）——付款确认链的健康状态可直接观测。
