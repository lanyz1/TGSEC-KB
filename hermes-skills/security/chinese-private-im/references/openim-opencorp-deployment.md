# OpenIM 自建部署（OpenCorp 壳）——实测备忘（2026-10 智慧家园 / bcpou.com）

来源场景：会员盘（智慧中国/smjdkx）生态里的「社区办公 IM」——从平台 user/invite 的下载页拿到 Flutter APK，strings 直出服务端全貌。

## 客户端识别（libapp.so strings）
- Flutter 包：`openim`、`openim_common`、`openim_live`、`openim_meeting`、`openim_working_circle`、`flutter_openim_sdk`；配 media_kit / livekit_client / ffmpeg_kit / webrtc（直播+会议+红包+朋友圈=全功能社区版）。
- 关键锚串：`wss://<host>/msg_gateway`、`ws://<host>:10001`、`http://<host>:10002`、`http://<host>:10008`、`https://<host>/api`、`https://<host>/chat`、`docs.openim.io`、`https://www.openim.io`、`sign.<域>`（签名服务）、`meet.<域>/h5/`（会议 H5）。
- Dart 侧文件族（一眼判功能）：`chat/chat_hongbao/*`（红包）、`openim_live/*`、`openim_meeting/*`、`forget_password/*`、`register/set_password/*`。

## 服务端形状
- 10001=WS、10002=API、10008=管理(Chat)API；生产常反代到 443 的 `/msg_gateway`、`/api`、`/chat`，裸端口被防火墙关（TCP 探通但无 banner/直接被防）。
- `/api`：OpenIM 主 API。
  - `POST /auth/get_admin_token {secret,userID}` → **2026-10-10 实破：secret=`openIM123`、userID=`imAdmin` 命中（旧「8 连试未中」结论作废——当时只试了带 456 的长串）**。参数不对时的报错递增很有用：无 operationID→「header must have operationID」；无 token 头→「header must have token」；token 假值→TokenMalformedError（**auth 类端点也要 token 头，占位 `x` 即可**）；secret 错→`secret invalid`；userID 错→`userID is error., userID=admin, adminUserID=[imAdmin]`（**admin 名从报错里直读**）。
  - `/auth/user_token`、`/auth/get_user_token`：get_user_token 持 admin token 时=**给任意 userID 签发登录票**（全社区任人帧）。
  - `/user/get_users {pagination:{pageNumber,showNumber}}` = 全量枚举主口（81,698 人；500/页 164 页）；`user/get_users_info {userIDs}` 要点名查；`get_all_users_uids` 本部署 404。
- `/chat`：管理 API（独立 token 空间，admin token 会被 1505 TokenUnknownError 拒）。**所有请求必带 `operationID: <uuid4>`**；鉴权加自家 `token` 头。

## /chat 端点族（Web 控制台 JS 直读）
- `POST /account/login`：`{phoneNumber|account|email, areaCode, password, platform}`；未注册号回 `20002 AccountNotFound`（= 注册/手机号存在性 oracle，实测 `user unregistered: AccountNotFound`）。`platform` 默认 5（缺/非法先报 platform/areaCode 格式错）。
- `POST /account/register`：**邀请制**——`{invitationCode, email|phoneNumber, areaCode, password, verifyCode, user:{nickname,...}, platform}`；无/错码回 `20011 InvitationNotFound`（改字段名 invitationCode / inviteCode / invitation_code 同判 = 服务端读的另有其名或码真无效，别在字段名上磨）。
- `POST /account/code/send`：**免鉴权**（实测 `{email,...}` 或 `{phoneNumber, areaCode, usedFor}` 均回 `errCode:0`）——短信/邮件轰炸面；邮件码走其实例的邮件 provider（外域临时邮箱可能收不到，别死磕）。
- `POST /account/code/verify`、`/account/password/reset`、`/account/password/change`（需 token）、`/user/search/full {keyword, pagination}`、`/user/find/full {userIDs}`、`/user/update`。
- 控制台壳：React SPA（Vite 构建），标题可改名（本项目「OpenCorp」，i18n 有「在线化办公/多人协作」）；localStorage 键 `wsUrl / apiUrl / chatUrl`，默认值按 `location` 拼 `:10001`/`:10002`/`:10008`（此拼法=识别该骨架的强指纹）。
- i18n 词典即错误文案表（verificationCodeExpired/Used、invitationCodeNotExist/Used、operationRestriction…）——当 oracle 词表用。
- 版本指纹：控制台自曝 `OpenCorp v3.8.3 / SDK v3.8.3`（对应 OpenIM v3.8.3）。

## 2026-10-10 管理员线拿下（bcpou.com 二次实访）

**链条**：`POST /api/auth/get_admin_token`（headers: `operationID`+`token:x`，body `{secret:'<REDACTED>', userID:'imAdmin'}`）→ errCode 0 出 admin JWT（~175B）。旧批次试漏了短串 `openIM123`——**教程默认值字典要含长短两族**（openIM123 / openIM123456 / OpenIM123456 / openim123456 / tuoyun…）。

**全量用户导出**：`POST /api/user/get_users {pagination:{pageNumber:N,showNumber:500}}` 分页循环（4 线程）→ 81,698/81,698 条 0 失败（~2-3 分钟）。字段：`userID`(10 位数字串)/`nickname`(多为真实姓名)/`faceURL`(≈12k 有头像，托管 `zhzjim.shop/api/object/...`)/`createTime`。取样核对：接口 `statistics/user/register` total=81,700 ≈ 全量数。

**能力边界**：admin token 只能读+签票；`/chat` 侧另要自家 token（该面另有手机号注册库）。`get_user_token` 拿到任意用户 token 后可进一步读该用户会话（行为边界按授权口径定）。

**新资产**：`zhzjim.shop` = 该 IM 的对象存储/文件服（头像等直链域=识别位）。

**与会员盘的关系（维持原判+补一句）**：用户库独立（会员盘号在 IM 侧 AccountNotFound），但同属一个运营方生态——IM 用户名单本身就是 8 万级真实姓名池，值得单列交付。

## 与会员盘的关系判定
- 同生态的社区/办公 IM **用户库常与会员盘独立**：会员盘注册号在 IM 登录回 AccountNotFound → 两边不通（各注册同号比对即可定论）。
- 遇到此形态优先级：`/chat` 若开放注册 = 最大门；注册邀请制且邀请码不在外部可得范围（会员盘发的 8 位「家园邀请码」在 /chat 无效）→ 转去要会员盘侧「大人物的账号」，或走 admin secret 线（默认值字典先行，命中即全量枚举）。
- 关联资产一并记：`integral.<host>` = 常是同方独立 ThinkPHP 积分应用（报错可泄路径 `/data/web/integral/vendor/topthink/…`）。
