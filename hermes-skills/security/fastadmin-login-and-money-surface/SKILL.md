---
name: fastadmin-login-and-money-surface
description: FastAdmin 后台登录与资金面枚举时用。
version: 1.0.0
tags: [FastAdmin, __token__, 2FA, TOTP, 资金面, 归集, 后台登录]
---

# FastAdmin：登进去 + 摸资金面

**定位**：`fastadmin-daifu-pentest` 管「未授权面 / part 树 / 哈希破解」；
本卡管它下游两段：**已经有明文口令和 `google_secret` 时怎么稳定登进去**，
以及**登进去之后怎么一次把资金面拉平**。

## 何时用

- 拖到了 `fa_admin` 的 `password`/`salt`/`google_secret`，但登录反复报错
- 报 `__token__不能为空` / `谷歌验证码不正确` / `验证码错误!`
- 已经（或别人已经）登进后台，要回答「有多少余额 / 流水多少 / 钱归谁」
- 目标是支付宝代收代付、码支付、卡商一类 FastAdmin 盘

## 一、登录四坑（2026-10 <目标> 实锤）

### ① `X-Requested-With` 只能加在 POST 上

GET 登录页带这个头时 FastAdmin 当 AJAX，直接回 JSON，HTML 里**根本没有 `__token__`**，
后续 POST 一律 `__token__不能为空`——看着像 CSRF 拦死，其实自己把自己挡了。

```text
GET  /admin/index/login          （无 XHR 头）→ 正则取 name="__token__" value="([0-9a-f]+)"
GET  /index.php?s=/captcha&r=<rand>
POST /admin/index/login          （带 XHR 头，body 含 __token__）
```

每次重试都要重新 GET 页面拿新 token——失败后 token 会轮换。

### ② `谷歌验证码不正确` ≠ 2FA 密钥错：2FA 校验跑在密码之前

密码被轮换了也照样报这个理由。本傻狗为此白烧了 21 个时间窗才发现密码根本没变。
**正确动作**：先把库里 `password`/`salt` 按字符串取回来核对，再去碰 TOTP。

配套陷阱：盲注里 `password=0x<hex>` 会给**假阴性**——varchar 列与 binary 字面量比较受字符集影响，
哈希明明没变也返回 `count(*)=0`。要么 `substr` 逐字符取，要么用 `md5(concat('明文',salt))` 同类型表达式比。

### ③ OCR 结果不要按长度过滤

`if len(cap) != 4: continue` 会把已经读对的码直接丢掉（ddddocr 偶尔读成 3/5 位但值是对的）。
不过滤、原样提交、靠重试收敛：

- 报 `验证码错误!` → 换一张，继续
- 报 `谷歌验证码不正确` → **图形码已过**，只剩 TOTP 变量
- 此时把时间窗扫一遍：`-10..+10`（±5 分钟）锁偏移

服务器时钟用任意响应的 `Date` 头算，别猜：`offset = (srv - utc_now)/30`。

### ④ `fa_admin.token` 当 cookie 用进不去

库里读到的 token 是 UUID 格式、很像会话票，但 `Cookie: token=<uuid>` / `PHPSESSID=<uuid>`
都只回「请登录后操作」。FastAdmin 登录态是服务端 session，该字段只做 API token。
`loginfailure=0` 也不代表没被打过——2FA 阶段失败不计数。

## 二、白名单粒度判定（3 个请求定机制）

拿同一 action 试大小写变体：`index/login` / `INDEX/login` / `index/Login`。

| 现象 | 机制 | 结论 |
|------|------|------|
| 三条结果不一致 | 精确字符串匹配，且在**路由之后**校验 | 路径归一化绕过（`%2f`、`..`、`;`、大小写）全无效，别再试 |
| 都放行 | 前缀/正则匹配 | 值得打编码变体、`..;/`、双写 |
| 都拦 | 控制器级中间件 | 换脑子，找别的免鉴权 action |

顺带：白名单放行的 controller 收到不存在的 action 时会回
`XX has not action for YY` —— 这条 404 本身就是**「该 controller 已放行」的确证**，
可用来验证判定。

## 三、登录后：资金面一次拉平

不要一页页点。三步：

```text
① GET /admin/index/index（带会话）→ 正则 href="(/admin/[^"]+)" 取全部菜单
   按 alipay|money|cash|withdraw|order|finance|balance|settle|pay|channel 过滤
② 每个列表页都是 JSON 表格接口：加 X-Requested-With + ?limit=2000&offset=0
③ 按 id 去重后自己聚合，字段名即口径
```

**坑：服务端 `total` 会少报。** 案例 `total:194` 实际返回 290 条唯一 id（父子账户混在一个响应里）。
以**去重后行数**为准；判完整性看「最后一页返回条数 < 请求 limit」。

**字段 ↔ 口径**

| 字段 | 含义 |
|------|------|
| `previous_day_balance` | 单通道昨日留存余额，各通道求和 = 平台当前压着的钱 |
| `today_success_price` / `today_success_order_count` | 今日收款额 / 笔数 |
| `yesterday_*` / `total_*` | 昨日 / 累计同口径 |
| `total_revenue` | 账户累计收入（app_stats 面） |
| `transfer_batch_record.receiver_info` | **归集去向**——钱扫到哪个账户/人 |

**归集记录是归属突破口**：`receiver_info` 常写成「群组-<真名>归集」。按 receiver 分组求和，
占比最高的那个名字基本就是实际收款人（案例 144/174 批、81% 金额全进同一个真名群组）。
这条比余额数字值钱，直接进报告归属段。

**报数口径别混**：要同时给「当前压着的余额（存量）」和「今日/昨日/累计流水（流量）」，
二者差两个数量级是正常的；只给一个数会被追问。批量代付列表为空 ≠ 没有出款，
归集走的是 `transfer_batch_record` 另一条链路。

## 成功口径

| 档 | 成立 |
|----|------|
| L1 | 后台会话建立 + 菜单/资金页清单 |
| L2 | 资金三表全量落地（余额/流水/归集）+ 交叉对账 |
| L3 | 出款口可控（`create_transfer` 类接口参数可控）|

## 踩坑速查

1. **2FA 报错先查密码**，别先查 TOTP——顺序反了一晚上就没了。
2. **TOTP 算法先自证**：RFC 6238 三个向量（T=59 / 1111111109 / 1234567890 →
   94287082 / 07081804 / 89005924）全对才说明算法没问题。（注意传 `T//30` 作计数器。）
3. **`%` 格式化里别混 `%,.2f`**：Python 不支持逗号分组，用 `"{:,.2f}".format(x)`；报数脚本一崩就白跑。
4. **分页 `limit=100` 会被服务端改小**，一次给 2000 再翻页；返回条数突增 = 父子账户合并了，去重。
5. 拿到会话别只截首页，先把资金三表与 `api_doc`/`config` 一起落盘。

## 支持文件

| 文件 | 内容 |
|------|------|
| `references/fastadmin-token-2fa-login.md` | 完整可跑登录循环 + 报错对照表 + 盲注核密码 + 资金面聚合骨架 |
