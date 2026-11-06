# TP 后台鉴权面测绘 + SSO 签名墙（ThinkPHP 多应用自建后台）

案例来源：CF 前置的博彩平台管理后台（ThinkPHP 6.1.4，`/www/wwwroot/game_admin_php/public`，
应用 `/adminapi`、`/channelapi`、`/common`、`/webapi`）。
适用：任何「前端 SPA + PHP 多应用后台 + 外部聚合方 SSO 登录」的自建面板。

## 1. 把 500 条路由全撞一遍，把免登录面收敛成个位数
服务端路由在 PHP 侧（自定义 JSON 路由会回 `{"code":-100,"message":"unknown request"}`），
但**前端 SPA 的调用点就是完整调用面**——直接正则扒：

```python
paths = sorted(set(re.findall(r'"/?(adminapi|channelapi|webapi)/[A-Za-z0-9_/]+', js)))
```

拿到路径表后**用空 body 逐条打一遍**，按响应分三档：

| 响应 | 含义 |
|---|---|
| `410000 请登录` / `401` | 路由存在，鉴权后 |
| `签名无效` / `无效数据` / 业务报错 | **免登录，已进业务逻辑** ← 全部精力放这里 |
| 404 / `unknown request` | 该应用无此路由 |

本案 496 条 → **免登录只有 `login`、`verify`、`groupLogin` 三条**，其余 493 条全要会话。
结论要写死：**接管路径只能从这 3 条上撕，别在 493 条里继续找漏**（那是无效功）。

## 2. 分清「用户名 oracle」和「2FA 情报源」
两条免登录路由的回显差异就是全部情报：

- `POST /adminapi/login {username, pwd(RSA加密)}` —— **用户名枚举 oracle**：
  存在的账号回「账号或密码错误」（错误行号与不存在时不同），不存在的回「无法登录游戏后台!」。
  大小写不敏感（`admin`/`Admin`/`ADMIN` 同判定）。
- `POST /adminapi/verify {username, pwd, code}` —— **2FA 情报源**：
  用户名+口令+动态码全对时回 `{isshow, data, secret}`，**`secret` 就是 Google 2FA 种子**。
  ⇒ 它的作用不是爆破，而是回答「锤到口令后还要不要 TOTP」；`isshow` 决定目标是否已绑 2FA。
- 两侧的用户名集合要交叉比对：login 存在 + verify 存在 = 真账号。

## 3. groupLogin SSO：免登录面里最值钱的一条
前端 GroupLogin 页从 URL 取参，等价于一个**跨站签票登录**：

```
/GroupLogin?data=<loginData>&sn=<loginSn>
  → POST /adminapi/groupLogin {loginData, loginSn}
```

**分水岭：`loginData` 必须是 `base64(JSON)`。**
传明文 JSON 永远回「无效数据」，你会误判成「接口不存在/签名不可破」。

进度判定靠**错误文案 + 异常栈里的 `文件:行号`**：

| 回显 | 走到了哪 |
|---|---|
| `无效数据` / `无效请求` | 解析层没过（结构/base64 错） |
| `签名无效` + `SystemAdminServices.php:<line>` | **已到签名校验**，结构正确，只差 sn 的算法/密钥 |

本案做法：枚举 **24 种 loginData 结构**（字段名组合 `account/username/adminName/channelId/loginTime/nonce/roleId` ×
扁平/嵌套 × 有无签名字段）× **18 个已知密钥**（前端 `httpSignSecret`/`apiKey`/第二把 Key/`pgofficial` 类字面量/品牌名变体）
× **8 种算法**（`md5`/`sha1`/`sha256` 裸值与大写、`hmac-sha256` 截断、拼接顺序两版）= **全 miss**。

**判定结论**：sn 由**外部聚合后台**签发（聚合方生成带票 URL 再跳进来，密钥在对方手里），
本地案卷不可能有。⇒ **如实标为「需外部密钥」缺口，不要回炉重撞**。
同案的另一条签票路由 `accountAdminLogin`（发 admin 票）需要**已有后台会话**才能调用 —— 鸡生蛋，同样标死。

> 通用判据：**签名所需的密钥/私钥在不在你已拿到的资产里？**
> 不在 = 这条路对你永久关闭，写进报告当「外部依赖」，把火力移到别的免登录面。

## 4. 拿到任意会话后的第一锤：解绑 2FA，再改管理员口令
这套后台自带一批 google 解绑 / 口令重置路由，**全在鉴权后**——这就是「弱口令 → 彻底接管」的缺失环：

```
/adminapi/system/userUnbindgoogle
/adminapi/vlogger/vloggerUnBindGoogle
/adminapi/agent/unbindgoogle          /adminapi/channel/unbindgoogle
/adminapi/vlogger/requireGoogleVerify
/adminapi/player/innnerAccountPwd     # 内户（内部账号）口令重置
```

⇒ 报告里要把这条**链环**画出来：
`弱口令命中任意低权账号 → 解绑管理员 2FA → 重置/接管管理员口令 → 完整后台`。
大多数复核者只看「喷口令未中」，链环图才说明为什么口令是唯一但值得打的闸。

## 5. 姊妹品牌 SPA = 免费密钥/资产矿
同平台常有多个品牌站共用后端。扒它们的 bundle 就能扩张资产池与口令候选池：

- **两代前端路径都要抓**：老版 `/home/js/app.<hash>.js`、新版 `/static/js/app.<hash>.js`（本案两代共存，各自泄不同密钥）。
- 从 bundle 抠五类东西：① `httpSignSecret`/`apiKey`/`GameApiKey` 等明文密钥；
  ② `wss://server.*` 游戏/长连集群；③ `https://*.s3.<region>.amazonaws.com` 桶（本案白拿 `gulu3`/`company-fj`/`milagresbet`，跨 `sa-east-1`/`ap-east-1`）；
  ④ **开发域**：`devserver.*`、`devmail.*`、`codeverify.*`；⑤ 第三方聚合方域名（回到 §3 说明密钥归属）。
- 用途：**新密钥同时是「签名候选」和「口令候选」**（开发者跨品牌复用密钥极常见）；
  **开发服/开发邮件比生产软**（邮件服务器 = 密码重置信拦截）。
- 姊妹品牌的 admin 子域**不一定解析**（本案 `admin.<新品牌>` 全 NXDOMAIN）—— 别据此判定「新品牌没有后台」，
  它们仍共用老品牌的管理入口。

## 6. 租户闸门（`WHERE [channel_url] = '<Origin 头>'`）的收敛标准
中间件拿请求头当租户键查库、查不到就空指针 500（顺带把源码+DSN 打回来）。两步收尾：

1. **绑定 vs 拼接**：把 `'` 塞进合法 URL 打。回「无记录」= **参数化绑定，注入死**；回 SQL 语法错误才是拼接。
   注意 `FILTER_VALIDATE_URL` 会先挡裸引号 —— 别把「格式校验拦截」误读成「绑定」。
2. **猜键值本身**：池子 = 品牌 × 前缀(`channel`/`admin`/`agent`/`www`/`m`/空) × TLD(`.com`/`.bet`/`.site`/`.top`/`.net`/`.vip`)
   × 路径后缀。本案先 1152 个不中，扩到 **2632 个仍全不中** ⇒ 记录用的是不可猜域，**标死**。

> 闸门类目标的时间盒规则：**候选池扩过一轮（×2 以上）仍零命中 = 标死**，
> 把结论写成「该键不可猜，需其他入口」，不要第三次回炉。

## 陷阱
- **别拿单条路由的 500 推断整站**：本案 `getPackageInfo` 回 200、`login` 回 500（`miss app@` 与 404 也有区别）。
  中间件按路由分支，逐条判定。
- **验证码没校验不等于能撞库成功**：本案后台登录图形验证码错码也照样进到「账号或密码错误」，
  但那是**枚举**面；爆破面依然受账号锁定/风控限速约束，别把「验证码不校验」写成「可无限爆破」。
- **`(Origin: 任意值)` 稳定 500 = 情报源，不是拒绝**：先榨 DSN/`$_SERVER`/SQL，再谈修不修。
- **搜索源被限速时不要停线**：grep.app 回 429 就转「本地 SPA 全量抠路由 + 官方 GitHub 搜索 API」，
  这两条都不需要 key。
