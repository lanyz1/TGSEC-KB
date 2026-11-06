---
name: baowang-platform-access
description: "Use when a 包网/白牌 gambling platform needs live access."
---

# 包网/白牌博彩平台实控接入

适用：uni-app 编译的 H5 博彩前端（chunk 名形如 `pages-<模块>-<页>.<hash>.js`），典型“站群”模式——一个后端挂多站点，靠 `station-id` 区隔。目标是把“只能看前端”推进到“真实会员会话 + 第三方游戏会话”。

## 0. 先定站点号，别先猜参数
主 JS（`static/js/index.<hash>.js`）里搜 `production:{` 取 `siteId`：
```bash
curl -s "$BASE/static/js/index.$HASH.js" -o app.js
grep -oE 'siteId:"[0-9]+"' app.js
```
之后所有请求带 `station-id: <siteId>`，否则返回 `station-id required/forbidden in request header`。

## 0.5 站号/配置面（多数接口免 token，先榨干）
- `GET /api/mem/index/base`（只需 `station-id` 头）→ `stationInfo`：id、stationName、orgId、status、`isOpenLoginCaptcha`、kfLink、vipRoomEnterAmount。非法站返回空/错误。**这是站号枚举器**：1..N 扫一遍就拿到全平台站点表（实测一个“站群”可能只有两三个真站，其余全空）。
- `POST /api/get_open_config?siteid=N` 免鉴权 → `entry`/`bind`/`uploadUrl`/`land`/`tenant`/`name`/`version`。注意它通常忽略 siteid、返回当前租户的全局配置，不能拿来区分站点，但能一次性拿到该租户的入口/绑定/上传/落地域名，逐个探测常有新资产（上传服务、落地裸 IP、入口端口）。
- **注册接口是站号 oracle**：站号校验发生在验证码之前。用假验证码（`captchaToken: bad` + `captcha: 0000`）零成本探测：`站点不存在[N]` = 无此站；其他错误（昵称/推荐人） = 站存在。枚举时每秒 ≤1 个请求，避免触发站点级 429。
- 邀请码错误可区分三类：空 → `仅允许使用邀请码注册`；不存在 → `请输入正确的邀请码`；存在但属于别站 → `推荐人不属于当前站点`。跨站注册必须先拿到目标站自己的码；换 Host 头可能让同一个码在别站通过校验，测试时固定 Host。
- `isOpenLoginCaptcha: 0` 不代表登录真的免验证码（实测仍返回“图形验证码过期”）；以登录接口实际返回为准。

## 1. 密码算法从前端 chunk 取，不要猜
下载登录页 chunk 再搜 `password`：
```bash
curl -s "$BASE/static/js/pages-index-login.$HASH.js" -o login.js
grep -oE '.{80}password.{140}' login.js
```
两种常见形态：
- `password = md5(明文)`
- 开验证码：`password = md5( md5(明文) + captchaToken )`，且 `captchaToken` 放**请求头**，不是 body。
先按第二种实现；登录返回“用户名或密码错误”才说明验证码已过、密码不对。

## 2. 验证码（OCR 直破）
`GET /captcha` 返回 JSON：
```json
{"code":0,"data":{"captchaToken":"<uuid>","content":"data:image/png;base64,..."}}
```
`content` 按逗号切分取 base64，ddddocr 识别（4 位数字，成功率约 80%）。登录请求头三件套：`station-id`、`terminal: 1`、`captchaToken`。`captchaToken` 一次性且短时效，每次登录都要新取。

## 3. 注册自有账号
`POST /api/mem/register`（form-urlencoded）：
- `nickname`：**必须恰好两个汉字**（否则“昵称必填且固定为两个汉字”），重名会提示“昵称[x]已经存在”，换生僻字组合即可
- `username`、`password`（发前端已 md5 的值，别再套一层）
- `invitationCode`：有效码来自推广链接/客服话术/同团伙站点；错误信息能区分“请输入正确的邀请码”
- 可选 `phonenumber`

## 4. 限流绕行（最常见的卡点）
先判限流维度，再决定绕法，否则会白烧几十次请求：
- **入口/IP 级**：主域登录 429 时不要等，换同一后端的其他入口域名/端口（`xh.<domain>:4041/4042`、源站 IP + Host）。判定同后端：同一 `station-id` 下 `/api/mem/index/base` 返回相同 `stationName`。
- **站点级全局**：注册/登录返回 `当前接口请求过于频繁`，且换入口、换 XFF、换 `terminal`、换 Tor 出口全部还是 429 → 配额按站点全局计（测试站阈值极低）。此时换 IP 无用，只能降速（实测约 100 次/窗口就触发）或等窗口过期。批量枚举前先估算请求数。

## 5. API 面一次性拉全
从主 JS 的 `__uniConfig["async"]` 取 `pages-*: <hash>` 映射，批量下载后：
```bash
grep -roE '"/api/[a-zA-Z0-9_/{}.-]{2,70}"' chunks/ | sed 's/.*://' | sort -u
```
比字典盲爆快一个数量级，还能拿到带 `{}` 的路径模板。

## 6. 拿到会话后优先验证这几条
- `GET /api/mem/getInfo`（**不带 station-id**，否则 forbidden）→ memberId、username、手机号、regIp、`pid`/`ancestors`（代理树）
- `GET /api/mem/index/others` → 房间列表与在线人数（真实运营规模）
- `GET /api/cr/LaunchGame` → `memToken` + 免密 URL：`FT_index.php?...uid=<table><memberId><suffix>`；浏览器打开即真实下注界面，cookie 形如 `login_<memberId>`。uid 带签名，改一位即 `table id error`
- 站点配置 `kfLink` 指向客服系统；`/api/chat/visitor/chatStart` 无鉴权发 `userId/sessionId`，`getAdminCard` 泄露客服 adminId
- `GET /api/mem/agg?preferTimestamp=true&limit=50&roomId=<id>&lotteryType=<lt>&acc=1&cp=1&rp=1&st=1&my=1&rc=1&rule=1` → `rc` 实时聊天/下注流（playerId/nickName/msgBody/msgType/headImg），`rp` 开奖记录，`cp` 当期，`acc` 账户；`limit=999999` 实测可用
- `GET /api/mem/recent_chatmessage?roomId=<id>&limit=50` → 最近聊天（含客服/机器人播报，常带玩家余额）；`hide`/`msgType`/`limit>50` 参数被忽略
- 实时通道（SockJS/STOMP）另见 `sockjs-stomp-pentest` 技能

## 7. 客服系统（同团伙常独立部署）
- 前端 `umi.js` 搜 `enc.Utf8.parse` 得 AES key/iv；消息字段 `msgContentSe` 用 AES-128-CBC/Pkcs7 解（key=iv 很常见）
- `tenantId` 从 `channelInfo` 取
- 上传接口只放行图片且服务端会转码，**做不了 webshell**
- `/api/v1/**` 是管理端，任何路径都先回 `token 无效`，不能靠状态码判断路由是否存在

## 死路清单（实测，别重复烧时间）
- 管理后台 URI 含 `admin` → CDN/Tengine 直接 403；`%61dmin`、双重编码、大小写、`..;/` 全 403
- 带 `;` 的路径（`/api/adm;in/login`）能过 nginx，但被 Spring Security 统一 401——**这是默认拒绝，不是绕过**
- SQL 关键字（`and/or/sleep/union/benchmark`、`/*!50000and*/`）在 query 与 JSON body 均 403；且多数参数是 Integer 强类型（`2'` 直接报“参数类型不匹配”），先判类型再谈注入
- 上传扩展名可控 ≠ 可执行：先确认落地是对象存储/CloudFront（静态）还是应用服务器
- `/upload` 返回 200 但恒 `文件为空`：前置 Tengine/openresty 会剥离 multipart body（非 multipart 直接 401/403）；chunked、80+ 字段名、换 Content-Type 全部无效 → 上传面直接判死，别反复试字段名
- 改 `station-id` 跨站 → 被 token 绑定挡回（“请求方法不存在”）
- SSH 密码认证开放 ≠ 弱口令：curated+top100k 约 49 万次 0 命中；放后台跑，别阻塞主攻

## 报告口径
- 区分“接口可达 / 有权限 / 已生效”，200 不等于成功
- 会员级实控要写可复现命令与关键字段，敏感值脱敏
