# php12comBack / ethp — 假 ETH2 白标矿池农场

Case anchor: firstgo.io / backend.onchains.mobi / back.fengcin.com（案卷 `/root/cases/firstgo.io/`，2026-10）。
栈：nginx + **ThinkPHP 5.0.24** + H+/layui 后台（标题常 `pool`）+ Web3.js 前台。
盘路径：`/www/wwwroot/ethp/`（DEBUG ENV `ROOT_PATH`）。

## 定性

假「Ethereum 2.0 Mining」/质押盘 + **ERC20 USDT approve 收割**。
spender 常为 **EOA**（`eth_getCode` 空，nonce 高，真 `transferFrom`），不是合约。
与 tousphl/defiminer 同属「运营端持 spender」，但白标前端与后台路由不同（见下）。

## 指纹

| 信号 | 读法 |
|---|---|
| FOFA / 源码串 | `php12comBack`、title `pool`、body `ethp` |
| 后台域 | `back.<brand>`、`backend.<brand>`；证书 SAN 一带多十个 back.* |
| TP 版 | 报错页 / 静态资源 `ThinkPHP V5.0.24` |
| 登录 | `POST /login/check_login.html`；字段 **`mobile` + `pass`**（或 `password`） |
| 成功码 | JSON **`code/status == 100000`**（不是 0/200 常见套） |
| 库表 | DEBUG 泄 `system_member`；密码 `enpass()` |
| 业务 API | `reg_user`、`empower_erc`、`get_erc_usdt`（需 `network=erc_usdt`）、`get_coin`、`recharge_p`、`notice` |
| google_reg | **绑谷歌/TOTP**，非开放注册；成功文案易误导 |

## 业务面（常先命中）

1. **邀请码**
   - 公告/`notice`：例 SWGY（firstgo）
   - 前台 HTML 藏码：例 XPpfQ（onchains）
   - **直接试 `ADMIN` / `admin` / admin 系**：窗口期可注册且 **type=2**（高权/已验证态）
   - **运营对抗**：`reg_user` 常被揽 **404**（`.html` 与 pathinfo 都死）→ type=2 会话难重建；历史 type=2 地址可被清回 type=0
2. **`empower_erc` / `empower_erc_*`**：早期任意/随机 tx hash → Verification successful，**type 0→2 无链上校验**；锁面后改 **验 hash** 或统一 `Please register first`
3. **IDOR /裸 address**：用户画像/资产接口常只凭钱包地址
4. **`get_coin`**：吐充值展示地址（ETH/BTC 均可）→ 链上归属/资金流
5. **spender**：前端/Web3 配置抽；必做 `eth_getCode` + 历史 transferFrom（Blockscout/公免 RPC）
6. **多币 get_erc 矩阵（2026-10）**：`token.html` / `join_*` / `stake_*` 挖全族端点
   - 页面：`join_usdt|usdc|uni|wbtc|cro|paypal`、`stake_*` 同族
   - API：`get_erc_<coin>.html`、`empower_erc[_<coin>].html`、`pledge_erc_<coin>.html`、`check_address_erc`、`limit_action`、`mining_income_collection`
   - **`network=` 必须对口**（错 net → `Request error` 或空）：
     | endpoint | network 实测 |
     |---|---|
     | get_erc_usdt | `erc_usdt` |
     | get_erc_usdc | JS 写死 **`erc_usdt`**（不是 erc_usdc！） |
     | get_erc_cro | `erc_cro` |
     | get_erc_paypal | `erc_paypal` |
     | get_erc_uni | `erc_uni` |
     | get_erc_wbtc | `erc_wbtc` |
   - 成功 `code=1` 回 **token 合约地址 + ABI + to_address(spender，未注册常 null)**
   - 标准 ERC20 地址样例（可作指纹，spender 才是收割点）：
     USDT `0xdac1…1ec7` · USDC `0xa0b8…eb48` · UNI `0x1f98…F984` · WBTC `0x2260…C599` · CRO `0xA0b7…450b` · PYUSD/paypal `0x6c3e…A0e8`

例（案例，可变）：
- firstgo spender `0x17075ed9d2fe26aA4924b631c582Ae23a81b5B8a`
- onchains spender `0xaeAEc666a763a5Fa8c660e997E361778C1Dd5D60`

## 后台面

### 登录

```
POST /login/check_login.html
Content-Type: application/x-www-form-urlencoded
X-Requested-With: XMLHttpRequest

mobile=<phone>&pass=<password>[&google_code=NNNNNN]
# 有些变体字段名 password
```

- 成功：响应体含 **100000**（落盘比对，别只看 HTTP 200）
- **pathinfo 备口（2026-10 firstgo 系硬坑）**：运营把 `/login/check_login.html` 揽成 **404** 后，  
  `POST /index.php/login/check_login`（无 `.html`）常仍 **200+JSON**。`.html` 404 **≠** 登录面死；先试 pathinfo 再判锁死。
- 失败文案常「账号密码不匹配」——**不做账号存在性差分**（与 defiminer「验证码不正确=密码已对」不同）
- 短字典 / rockyou 头几千 / 前台泄手机号喷雾：早期 **found 0**；后多白标复现 **`admin`/`123456`**（sydiz/fengcin/yuseain/zhiunip/slydle…）——**仍差有效 TOTP**，见下节差分
- 弱口 10–20 无果即停，转源码/`enpass`/上传/RCE；**已确认密+TOTP 门**则挂 Tor 多 host 喷码，别回头喷密

### 源码泄露（优先于爆破）

1. **缺 `pass` / 异常 password 类型**（数组、超长、特殊字节）在 **DEBUG 开** 的实例上可打出 TP System Error
2. 报错页抽：
   - 绝对路径 `/www/wwwroot/ethp/`
   - `application/admin/.../Login.php` 或 `application/back/...` 片段（后台模块名常是 **back** 不是 admin）
   - 表 **`system_member`**、函数 **`enpass()`**
3. 源码常卡在 `status==2` / 谷歌校验分支之前——**继扫备份** `.php~` `.bak` `.swp` `Login.php.bak`、`enpass` 定义文件、`.env`（本案 ENV 无 DB 密）
4. **DEBUG 关**时 500 常空壳（onchains）——换姐妹域/旧报错 HTML 盘上复用，别死磨同一 500
5. **业务 DEBUG 偶发大页**（`recharge_p`/`num` 异常）：可泄 `Index.php:行号` 栈，但控制器**正文常抠不出**；落盘 ERR_*.html 后续 diff，别当 RCE

### google_reg / TOTP（2026-10 差分纠偏）

- 接口是「已有账号绑谷歌」，不是注册
- 登录页 QR 解出的 TOTP secret **每次刷新可变** = 前端模板，**不当超管突破口**；历史 loot/模板 secret 对 live `admin` **实测无效**
- 与 defiminer「密码对+验证码错」不要混用判读
- **假阳性铁律**：缺 `google_code` 时，**任意密码**都可能回「请输入六位谷歌验证码」  
  → **不能**据此认定密码正确。必须带 `google_code`（错码/随机）再看：  
  - 仍要谷歌码 / 明确「验证码错误」+ 其它信号 → 再怀疑密对  
  - 直接「账号密码不匹配」/笼统 `error` → 密未过或运营收紧
- **运营对抗**：后常统一 `{"code":100001,"msg":"error","data":[]}`，文案差分失效；改靠  
  pathinfo 存活 + 多白标同口令复现 + SESSION 文件命中判定
- **限流**：按**出口 IP**（约 6 分钟级），`X-Forwarded-For` 无效；Tor 换电路 + **多 `back.*` 轮询**同字典（pin_bg2 模式：高频 PIN→日期码→顺序段）
- 全量 1e6 无速率时才值得；有限流就 **多 egress × 多 host × 小字典**，别单 IP 死喷

### C2C 无鉴权（BOLA）— 2026-10 firstgo/fengcin HIT

`reg_user` 被揽 404 后的**主足点**：

| 端点 | 字段 | 结果 |
|---|---|---|
| `/index/c2c/create_order` 或 `/c2c/create_order.html` | `buy_id`/`num`/`type`(+address) | **success**，订单号 `CA0…` |
| `is_pay` / `cancel_order` | 订单标识 | **无鉴权改状态** |
| `order_info` / `order_status` | 订单标识 | 吐银行/手机等 |

- 表：`bus_buy` / `c2c_order` / `legal`（DEBUG/`where` 报错可见）
- TP `where`：`eq` 通、`exp` 被拦
- Chat 常挂 WhatsApp
- **关键**：`order_info`/商户地址（例 `0x4c5BB5…`）常已是 **type=2 用户** → 用该地址打 `empower_erc`（假 hash + 真 `to_address`）、`limit_action`、`recharge_p`，**不需重建 reg_user**

### 上传 / RCE

- `recharge_p`：multipart；**必填 `num`**（缺 → `Invalid num`）；字段 **`image`**（不是 file）；**`coin` 白名单**：`BTC|ETH|XRP|USDC|DOGE|UNI|CRO`（缺/非法常逼源码白名单）
- 会话：
  - 无注册地址 → `Please register first`（文件可进 PHP tmp）
  - **已注册 type=2 地址**（含 C2C 商户） → **`Submitted successfully`**（上传成功）
- 内容检测（`upload_image_us` ~3402–3406）：
  - `stripos` 扫 **`<?`** → 用 **`<script language="php">`** 绕（或其它非 `<?` 短标签）
  - 需合法图片头（PNG/JPEG）过 content 检测；`filesize` 超限回拒（约 10MB）
  - **3407+ `move()`/`getSaveName` 路径常未泄**—先逼 FileException/Unknown column 报错抽行，别假设命名
- 落盘目录线索：`/uploads/YYYYMMDD/` **存在（403 listing）**；`/uploads/report_file/YYYYMMDD/` 报告图**可直读**（命名样式可参）
- **命名规则坑**（已证伪）：非上传原名、非 `md5(文件内容)`、非窄窗 `md5(microtime(true))` 盲爆必中。Tor 大窗口爆极慢且易 timeout—**先挤源码再精爆**
- DEBUG：`num[]` 可炸 `Index.php:3330/3600` 级行号；控制器正文常扣不出—落盘 ERR_*.html 后续 diff
- 旁支：`report_file` / `upload_image_us` 同族口一并探
- TP5 经典 `invokefunction` / `_method=__construct` 在此白标**被路由吞**，别空耗
- `/application/admin/view` 等 **403=路径存在需鉴权**，404=真没；用作路径存在性 oracle
- **上传成功 ≠ getshell**：没 Web 可达路径/解析点不得写「已 RCE」

## 横向与出口

1. **不死磨单域**：证书 SAN + FOFA `php12comBack` → 27+ pool 后台 + ETHP/BitCoin/SEC 变种，至少多 IP 集群
2. FOFA 端口（21/3306/8888 等）**必须 TCP/curl 现场复核**；常只剩 80/443，888 开也常 **纯 403**（无 TLS 面板）
3. 本机 IP 被拉（例 154.x GET 403）→ 跳板 / 姐妹 `back.*` Host / 换 SNI / **Tor:9050**
4. **全站级锁面**：多出口（本机+h107+Tor+WARP+curl_cffi+jina）同时 **GET 403 + POST 405**
   - 判读：**不是**单 IP 黑名单，是整站/WAF 关 POST
   - 动作：换**干净住宅/VPS**；同时离线续：链上、已泄源码、兄弟 IP SSH/:888（本案 207 SSH 短字典未中；217:22 常拒）
   - 锁面可**按出口窗口重开**（h107/Tor 短暂 200）→ 窗口内优先打 **reg_user / check_login pathinfo / get_erc / recharge_p**，别先磨静态
5. 免费 SOCKS/HTTP 代理池对此类目标多废；别烧额度
6. **撞名旁支**（勿当主线 shell）：
   - `ethp.net` 等写易 CMS / 低权会话+静态上传 ≠ 矿盘 ethp
   - 同 IP 清空后的 **Z-Blog 默认站**（CVE 主题马常被 WAF；登录「非法访问」= CSRF）→ pivot 旁支，不替代 `back.*`
7. 白标品牌扩例（同 217 栈或同 php12comBack）：fengcin / sydiz / yuseain / zhiunip / slydle / riverjiang / tangdynasty / sortegg / ohiruneol / onchains / firstgo…

## 交付分栏（必做）

| 栏 | 例 |
|---|---|
| 业务 F* | 邀请码、假 hash→type=2、IDOR、get_coin、spender EOA |
| 后台 | 登录面/源码片段/表名 — **会话 HIT?是/否** |
| 锁面 | 哪些出口 403/405；是否全站级 |
| 未拿 | admin session / enpass 定义 / SSH / DB |

**禁止**把业务 HIT 写成「后台已拿下」；用户会直接回击「没有拿到后台停下来干什么」。

## 与 tousphl/金砖类差异

| | tousphl/defiminer | php12comBack/ethp |
|---|---|---|
| 登录字段 | name/username + password + google | **mobile + pass** |
| 成功码 | 跳转/会话 cookie | **100000** |
| TOTP | 真 GA，「验证码不正确=密对」 | google_reg 绑定；页面 QR 常假 |
| 鱼表 | fish + kill API | system_member；前台钱包用户主 |
| 密码 | bcrypt 日志可泄 | **enpass()**（定义常未全泄） |

## Pitfalls

- 内联 python 多层引号/中文 bytes/`http()` 盖住 `http.client`/f-string → **脚本落盘再 tee**；长跑 **background+notify**，前台 420s/SIGTERM 会杀 pin 喷
- 业务 REPORT 完了就问「继续吗」=触用户逆鲞；没后台/root/shell 就继续换面
- 888 AMH/FTP FOFA 命中不要当真面，先 socket
- 同机判定只认 A 记录 IP 或首页 JS 真连栈；FAQ/友情链/第三方 IM 不算关联
- **缺 google_code 的「请输入谷歌码」≠ 密码正确**（任意密同文案）
- **`.html` 登录 404 ≠ 登录死**——先打 `/index.php/login/check_login`
- **reg_user 404**：先打 **C2C BOLA + 商户 type=2 地址**，再 TOTP/源码/旁 IP；别空转 empower
- **`/index/register.html` 页在 ≠ 接口活**——`reg_user` 可被 nginx 真 404
- get_erc_usdc 的 network 跟 JS 走（常是 `erc_usdt`），别想当然 `erc_usdc`
- 管理 API 未登录统一要会话；扫一圈 401/请登录 后别当「未授权金矿」误报
- **不带 `X-Requested-With`** 时业务口常回 SPA 壳/窗体 HTML—别当成功
- **喷密把登录页 HTML 当 SUCCESS**—必须严格 JSON（有 `code`/`msg` 字段）分类器
- **`admin/123456` 窗口会失效**（改密后带历史 TOTP 也「账号密码不匹配」）—oracle 死后停 PIN 喷，转 C2C/上传/`enpass`
- **60.205.149.117 / ethp.net**：撞名 Windows 调试/写易，**不是** `/www/wwwroot/ethp/` 矿盘主线
- Tor 微秒级 md5(microtime) 盲爆易 timeout/SIGTERM—先挤 `move` 源码，再用 PHP 精确浮点串格式精爆
