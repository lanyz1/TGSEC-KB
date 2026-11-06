---
name: acg-faka
description: >-
 异次元 ACG-FAKA 发卡站专项：后台随机路径、USER_SESSION JWT、
 callback handle 枚举、假支付矩阵衔接、共享货上游库存链（gmail168 真经）。
 在用户提到异次元、ACG-FAKA、acg.js、Toka、小马redu、发卡站、橱窗、
 shared_id、共享货、果皮、guopi、code92、上游库存、对接上游时使用。
 打发卡网：假签硬化后先支付栈取钥，再打上游库存；勿只死磕前台 RCE/`sign:true`。
---

# ACG-FAKA 专项

## 真源

| 内容 | 路径 |
|------|------|
| **发卡网分流总卡** | `docs/playbooks/发卡网打法分流手法.md` |
| **gmail168 真经 / 库存上游 Playbook** | `docs/playbooks/ACG共享货上游库存杀伤链.md` |
| 工具包 | `tools/acg-faka/` |
| 探针 | `tools/acg-faka/bin/acg_probe.py` |
| **共享货上游** | `tools/acg-faka/bin/acg_shared_upstream.py` |
| 商户字典样例 | `tools/acg-faka/dicts/shared_merchants.example.json` |
| 会话结构 | `tools/acg-faka/USER_SESSION.md` |
| CF 人机 | `tools/ops/cf_session.py` |
| 假支付 | `pay_matrix.py` + `payment-callback-forgery` |
| **严签后取钥** | `docs/playbooks/支付栈旁站弱口取钥回灌手法.md` |

## 心智（先背）

前台是橱窗。钱：假签 → 支付栈取钥 → 合法签出卡。货：钥也打不通再打**上游库存**。 
ACG 共享货 ≈ gmail168 的 `cookie.store`。 
口诀：`资源宿主 + 共享码 + 历史凭据 = 上游候选`；`钱打不通先取钥，钥打不通再打货`。 
成功口径：**出卡或稳定读上游库存（或 SQL）**，不是前台 RCE。

发现上游五步：①跟资源 ②跟 `shared_id/code` ③历史案卷 ④inventory 对码 ⑤静默扩权。 
档位：L1 API 读库 → L2 Entrance/SQL → L3 主机；复工先选定档，勿三档空扫。

## 强制顺序

1. scope 内 
2. `cf_session capture`（有头过 CF/登录）→ storage 
3. `acg_probe.py --storage …`（后台 + callback） 
4. `pay_matrix.py`（中转异 host 静默扩权）— **严签则停假签空转，下一步取钥，勿死磕 `sign:true`** 
5. **ACG 3.4.x `非法签名`** → **先支付栈取钥**（`支付栈旁站弱口取钥回灌手法.md`，走 `payment-callback-forgery`），再考虑上游 
6. **出现 `shared_id` / cover 异站 / 支付栈也进不去** → **立刻切共享货上游**（Playbook §0–§1） 
7. 会员面用 `session_pipeline` / `cf_session consume` 

损坏的 `USER_SESSION` 禁止手修，见 `USER_SESSION.md`。

## 共享货上游命令

```bash
python3 tools/acg-faka/bin/acg_shared_upstream.py discover \
 --base https://橱窗 --case <案卷> --expand

python3 tools/acg-faka/bin/acg_shared_upstream.py connect \
 --upstream https://上游 --app-id <id> --app-key <key> \
 --base https://橱窗 --case <案卷> --items

python3 tools/acg-faka/bin/acg_shared_upstream.py match \
 --base https://橱窗 --upstream https://上游 \
 --app-id <id> --app-key <key> --case <案卷>
```

产物：`exports/bot-recovery/<案卷>/测绘/acg_shared/` 
签名 / L1–L3 / 踩坑见 Playbook。

## Entrance 探测要点

| 形态 | 命中信号 |
|------|----------|
| 核心 AdminEntrance | 响应头 `Refresh` 含 `/admin` +「认证成功」 |
| Entrance 插件 | 「没有使用正确入口」+ Config 路径泄露 |
| 失败 | 勿对**无关**易支付后台广谱喷登录（`@login.lock`）；主站 `submit` 指向的那台支付栈 **要** 短字典 |

## 与假支付分工

- 松散回调 / 中转弱签 → `payment-callback-forgery` 
- 严签 + 支付页跳聚合支付后台 → **先** `payment-callback-forgery` 支付栈取钥（弱口读商户 key → 合法签） 
- 严签 + 支付栈也打不开 + `shared_id` / 发卡默认 → **本 Skill 上游链** 
- 3.4.8 实锤：`POST /user/api/index/query` 对已付单可直接带 `secret`（未付仍不出） 
- zephique/LemPay/TokenPay = 钱；guopi/code92 = 货；勿混打

---

<!-- 补充视角: acg-faka-pentest (兄弟技能库 2026-09-12) -->

---
name: acg-faka-pentest
description: "异次元发卡渗透: 回调伪造免支付+免登录卡密泄露。触发: acg-faka, 异次元发卡"
---

# acg-faka(异次元发卡)系统渗透方法论

基于 shenmika.com(神秘卡寄售平台)实战验证(2026-08,详见 references/shenmika-case.md)。

触发词: acg-faka、异次元发卡、发卡系统、卡密寄售、ACG-SHOP cookie、shenmika、BetterEpa、Tokenpay。

## 指纹识别

- Cookie: `ACG-SHOP` + `server_session_e4df10ce`(PHP session)
- 前端路由:`/user/api/...`、`/user/authentication/...`、`/user/business/...`(商家后台)、`/user/master/...`(分站商品管理)
- 支付插件:`/app/Pay/{handle}/go.php` 结构(旧版插件);BetterEpa=码支付聚合(支付宝/微信),Tokenpay=加密币(俄语收银台)
- 静态资源 `smk.js?v=x.y.z`、`user.js?v=x.y.z` 给版本线索
- 开源仓库:github.com/lizhipay/acg-faka(主程序,3650 文件)

## 版本识别(最关键一步)

线上站点常常是**旧版**,而 GitHub main 是最新版。判断新旧:

| 特征 | 旧版(3.1-3.2) | 新版(3.5+) |
|------|--------------|-----------|
| 支付页 | `/app/Pay/{handle}/go.php` | `/user/pay/order.{tradeNo}.1` 类 |
| 商品回调 URL | `callback.{handle}`(插件名在 URL) | `callback.{tradeNo}`(订单号在 URL) |
| 充值回调 URL | 旧路径 | `/user/api/rechargeNotification/callback.{tradeNo}` |

**回调 URL 差异是最大的坑**:用新版的 `callback.{tradeNo}` 打旧版站点会得到 `Bad request`,误判为"回调不存在",实际是 URL 格式不对。

拉历史源码对比:`GET /repos/lizhipay/acg-faka/commits?path=app/Service/Bind/Order.php` 拿版本 sha,再 `GET /repos/lizhipay/acg-faka/contents/{path}?ref={sha}` 拿旧版文件。raw.githubusercontent 不稳时用 API contents(返回 base64)。

## 回调伪造(核心攻击面,免支付拿卡密)

1. **IP 白名单默认关闭**:`CallbackIpWhitelist::enforce()` 在 config `callback_ip_whitelist` 为空或 `'0'` 时直接 return 放行。大量站点未配置 → 可伪造回调。
2. **响应判读**:
   - `{"code":0,"msg":"sign error"}` = 路由存活 + 白名单未开,只差签名
   - `Bad request` = 路由/版本不匹配(多半是 URL 格式错了)
   - 403 = 白名单已开
3. **验签**:`app/Pay/{handle}/Impl/Signature->verification($map, $payConfig)`,密钥明文存 `pay_config` 表,外部拿不到 → 需插件源码或找插件实现缺陷。
4. 回调成功 → `orderSuccess()` → 卡密发出 / 余额到账 → 免费拿货。
5. 旧版 callback 报文要求:`trade_no`(订单号)、`amount`(金额)、状态字段都在报文里(不在 URL)。

## 免登录接口(卡密泄露面,黑盒可直测)

- `POST /user/api/index/query {keywords}`:keywords 为 18 位数字→按 trade_no,否则按 contact 匹配。**已支付(status==1)订单返回 secret 卡密**,无归属校验。限流 30/600s/IP。
- `POST /user/api/index/secret {orderId, password}`:订单未设查单密码(password_status=0)时 password 可空,已支付订单直接返回 secret。限流 40/600s + 8/单号/600s。
- `POST /user/api/order/state {tradeNo}`:无鉴权返回 id/trade_no/amount/status。限流 120/600s。
- **订单号格式**:`Str::generateTradeNo()` = `mt_rand(100,999) . date("ymdHis") . mt_rand(100,999)` = 18 位。已知下单时间到秒时,前后缀枚举空间 900×900=81 万(受限流约束,可试 XFF/多跳板机扩 IP)。
- 拿到任意已支付订单号 → secret 接口直接拖卡密,这是"拿发卡信息"的最短路径。

## 0元免单逻辑

- `valuation()`:金额券(mode==0)`money >= price` 时直接返回 `"0"`(免单);百分比券 money 是 0~1 比例。
- 需已知有效券码(有 owner/commodity 校验,不可枚举)。黑盒常见券码测试:`user/api/index/tradeAmount`(注意参数名:`commodityId/cardId/num/coupon/race`,和 valuation 的 `item_id` 不同)。

## 其他攻击面/Pitfalls

- **后台**:`admin/authentication/login` 常被宝塔防火墙 + openresty 403 双层拦截;API 路径 `admin/api/...` 返回宝塔防火墙页。
- **密码哈希**:`sha1(md5(md5($pass) . md5($salt)))`。
- **会话 JWT**:cookie 是 `base64(JWT)`,HS256 key = `user->password` → 拿到任意用户密码哈希即可伪造其会话(含 admin 系)。
- **上传**:白名单扩展名(图片/zip/woff 等,无 php)+ 随机文件名 → getshell 不可行,别浪费时间。
- **UserSession 拦截器**:API 请求必须带同 host 的 `Referer`,否则返回"当前页面会话失效,请刷新网页.."(这是校验不是 bug)。
- **验证码**:50x24 1-bit PNG,ddddocr 100% 识别,注册/登录/后台登录全可脚本化。
- **CF 前置**:curl 需 `--resolve host:443:CF_IP` 强制 IPv4(IPv6 直连常失败);跳板机/代理场景注意 DNS 污染(子域可能解析到无关 CDN IP)。
- **WAF 对 callback 路径**:部分部署会拦含 `callback.` 的 URL,若全格式 Bad request 而业务接口正常,考虑 WAF 关键词拦截。

## Verification

1. 回调伪造:`callback.{handle}` POST 返回 `sign error` = 可继续;返回 `success` = 免支付成功(卡密/余额到账)。
2. 卡密泄露:`query`/`secret` 用已支付订单号返回 `secret` 字段 = 确认。
3. 0元单:tradeAmount 返回 `amount: "0.00"` = 可免单。

---

<!-- 补充视角: card-shop-pentest (兄弟技能库 2026-09-12) -->

---
name: card-shop-pentest
description: "卡密商城/发卡网/自动发货商城渗透测试。触发: 卡密、发卡网、EMSHOP、ECShop、faka站。"
---

# 卡密商城(发卡网)渗透测试

EMSHOP/ECShop 系自动发货商城(卖卡密/虚拟商品)的渗透方法论,基于 fakainc.shop 实战验证(2026-08, 见 references/fakainc-emshop-session.md)。

触发词: 卡密、发卡网、自动发货、虚拟商品商城、卡商后台、card shop、cdkey shop。

完整 Dujiao-Next(Go 发卡)+ TokenPay(ASP.NET 支付中心)渗透链见 `references/dujiao-next-tokenpay-chain.md`(2026-08 实测:CF WAF 绕过、用户态接口全景、支付回调伪造测试、TokenPay ApiToken 默认值验证、admin 路径隐藏识别)。

## 攻击面清单(按优先级)

1. **后台弱口令** — `/admin/sign.php`(EMSHOP 后台)
   - **CSRF 密钥可伪造**:未配置 `auth.secret` 时,密钥降级为 `base64_encode('em_admin_csrf')` → 攻击者可自签任意 token(线上已复现)
   - **限流 session 级**:LoginThrottle 存 `$_SESSION` → 每次换新 PHPSESSID 即重置(8次错误零锁定)
   - **无验证码** → 爆破链路:伪造CSRF + 新session = 每轮1请求,无限速
   - 安全入口:配置了 `admin_entry_key` 时需 `?s=xxx`,未配置可直接访问
2. **订单查询泄露** — `/user/find_order.php`
   - **orderno 模式**:仅凭订单号 + 算术验证码(`refresh_captcha` 直接返回算式,可脚本化自动解)返回完整订单 + guest_token + `delivery_content`(卡密字段)
   - **token 模式**:凭 guest_token 列出该客人的全部订单(最多10条)
   - 限流 10次/分/IP;`RateLimit::clientIp()` 取 `CF-Connecting-IP` 优先 → **XFF 伪造无效**(CF 会覆盖)
3. **API 接口** — `?c=api&act=xxx`
   - 签名: `md5(ksort(params除sign/sign_type/c/a/act,跳过空值) + SECRET)`,SIGN_TTL=600s
   - 注册用户可在用户中心「API对接」生成自己的 appid+secret(可合法自建凭证)
   - `query_order` 归属校验只查 merchant_id/owner_id(不查 user_id)→ 同域(主站 owner_id=0)可查任意订单号
4. **支付/订单逻辑**(常见封死点)
   - 0元订单自动 `payFreeOrder()` 标记已付 → 但数量<=0钳制为1、优惠券 percent>=100 返回0折扣、余额支付需余额>0
   - 支付回调 `/notify` 验签正常(epay 需网关商户密钥,难伪造)
5. **虚拟卡插件** — `?plugin=virtual_card&action=export_order_cards&order_id=N` 前台导出卡密txt(需订单归属/session白名单;线上可能404未启用)

## 方法论

1. **指纹识别**:首页 HTML 找 `EMSHOP_URLS`/`/?c=` 路由 → EMSHOP;GitHub 找源码(`tuikr123/emshop`, `ihehe1996/emshop`)
2. **有源码 → 克隆审计**(353 PHP 文件,可3路子代理并行:①鉴权/登录 ②订单/卡密 ③上传/插件)
3. **后台路径 + 敏感文件探测**:admin 301→sign.php;install/ 302 正常;`backup.zip`/`config.php` 200 多为回落HTML假阳性(需验内容)
4. **注册测试账号** → 拿 API 凭证 + 体验购买流程(创建待付款订单拿真实订单号,不付款)
5. **用户名枚举**:注册接口"该账号已被注册"差异响应(注意自己探测时注册成功的账号会变成"已占用")
6. **爆破**:伪造CSRF + 新PHPSESSID,每轮1请求(比 GET-token+POST 快一倍)
7. **卡密链**:orderno 查询(10次/分) → 拿 guest_token → token 模式列单 → delivery_content 拿卡密

## Pitfalls

- **CMS 未知路由回落 200**:sitemap.xml/config.php/backup.zip 等全部返回首页HTML(约34KB)→ 判断文件存在必须验内容(HTTP头/文件头),不能只看状态码
- **时间差枚举用户名不可靠**:CF + TLS 握手 ~2s 延迟,phpass 校验差异(~50-100ms)被噪声淹没
- **子域名泛解析**:所有子域解析到 CF IP → 子域枚举找源站无效;找源站试 CT日志(crt.sh)/被动DNS/SPF
- **订单号格式**:`YmdHis + 6位随机`(10^6/秒)→ 纯枚举不可行(即使 API 无限流)
- **API 参数在 query 里要参与签名**(act/appid/timestamp/sign 除外),用 Python urllib 时注意 HTTPSHandler(context=) 注入,不能直接传 context 给 opener.open()
- **找源码是最高效路径**:源码审计比黑盒探测快得多,3 个子代理并行审计 353 文件约 10 分钟出完整报告

## 修复建议(交付给靶场方)

1. Csrf::getCookieSecret() 安装时生成随机 secret
2. LoginThrottle 改 IP+账号维度
3. find_order.php 输出剥离 delivery_content
4. RateLimit::clientIp 受信代理白名单
5. 后台启用 admin_entry_key

## 同类发卡系统对照与批量采集(2026-08 实战)

### 多系统对照

| 系统 | 技术栈 | 核心漏洞 | 防御特点 |
|------|--------|----------|----------|
| **ZCard** | Laravel 13 + Sanctum | 卡密导出越权/订单查询泄露/mock-pay | 路由中间件缺失是主因 |
| **EMSHOP** | ThinkPHP(PHP) | CSRF 默认密钥可伪造/限流 session 级可绕 | `?c=` 控制器路由 |
| **独角数卡 Dujiao-Next** | Go + Gin(新版) | 设计较安全,卡密全在 admin 组 | Guest 凭证 `Authorization: Guest base64url("email\npassword")`,SQL 层 GuestScoped 校验 |
| **TokenPay 支付中心** | ASP.NET Core(SQLite) | 默认 ApiToken 若未改可伪造回调/订单 | `MD5(排序参数+ApiToken)` 验签 |
| **彩虹易支付** | PHP 5.x(常 EOL) | 历史 SQLi(admin/download.php batch UNION)/前台 0.5day | **sec_defend JS 混淆 + RSA 加密密码 + 图形验证码 + 失败锁定** |

### 彩虹易支付专项

- 指纹:Apache + `X-Powered-By: PHP/5.6.40`(EOL)、`security_session_verify` cookie、`/user/test.php`
- 防御链:①sec_defend JS 混淆 cookie(防机器人)②密码 RSA 加密(`openssl_private_decrypt`)③图形验证码(session 绑定,`strtolower($code) != $_SESSION['vc_code']`)④失败锁定(`@login.lock`)
- 验证码 OCR:rapidocr-onnxruntime + Pillow 预处理(灰度→放大3倍→二值化),4位字母数字部分可识别
- 历史 SQLi 位置:`admin/download.php?act=settle&batch=1' UNION SELECT ...`(需登录)

### 批量采集方法论(找同类模板站)

1. **测绘引擎选择**(2026-08 实测):Censys/Fofa/Shodan 要账号;无住宅代理下 Google/Bing/DDG/Startpage 全反爬(别硬试);URLScan.io API 可调但无中文索引;免费可行 = GitHub README/合作伙伴页找官方自营店(demo.dujiao-next.com、niub.me)
2. **主动测绘 C 段**:从已知**直连 IP**(非 CDN)扩展,扫同 /24 的 80/443 指纹匹配;CF IP(104.21.x/172.67.x)共享不能扫兄弟站;v2ray TUN 开启时端口扫描全 OPEN(假象),用 Python socket connect 验证
3. **本地 CDP Chrome 复用登录态**:`chrome.exe --remote-debugging-port=9227 --remote-allow-origins=* --user-data-dir="...\Profile N"`(必须加 `--remote-allow-origins=*`,否则 WebSocket 403);/json/list 拿 ws URL,websocket-client 发 Page.navigate + Runtime.evaluate
4. **展示系统**:SQLite 入库 + `python -m http.server` 静态页(列表/搜索/系统筛选/PHP EOL 标记)
