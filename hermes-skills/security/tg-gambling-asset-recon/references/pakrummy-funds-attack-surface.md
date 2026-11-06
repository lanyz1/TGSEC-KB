# YonoGames 资金面攻击面全图（bdrummy/pakrummy）

## 热更新资源（关键：子模块真实 MsgId 在这里）
- 本地 manifest（APK assets/res/raw-assets/*/xxx.manifest）泄露热更新地址：
  - packageUrl: `http://ifs.fwui238929sh.com/GameX/1.1.7.4/Main`
  - remoteVersionUrl: `http://ifs.fwui238929sh.com/GameX/Main/version.manifest`
  - remoteManifestUrl: `http://ifs.fwui238929sh.com/GameX/Main/project.manifest`
- 下载后 xxtea 解密（密钥 `b32a2160-0c63-41`，不跳 4 字节头，gzip magic → zlib 解压）得新版 project.js/settings.js
- **热更新新版 project.js 含完整资金 MsgId 定义**（比 APK 旧版全）

## 完整资金/游戏 MsgId（从热更新 project.js 挖出）
- 提现：YD_WITHDRAW_GET=130, SAVE=131, DRAW=132, RECORD=133；REQ_WITHDRAWAL=137, RECORD=138；REQ_WITHDRAW_UNFREZE_LIST=540；PULL_WITHDRAW_SUCC=1103
- 转账：REQ_TRANSFER=142, RECORD=140；BONUS_TRANSFER=8011；BONUS_COIN_TRANSFER=419（查询，返回 collect_coin/add_coin/bonus_coin）
- 银行：BANK_SAVE_COIN=102, BANK_TAKE_COIN=103, BANK_TAKE_INGAME=107；REQ_ENTER_SAFE=100
- 红包：REQ_REDPACK=7100, OPEN_REDPACK=7101, REDPACK_RAIN_START=1100, REDPACK_TAIN_CLAIM=666, REDPACK_RECORDS=670, CAME_REDPACK_ALLSCENE=1039
- 邀请：BIND_INVITE_CODE=28, INVITE_CODE=8013, REQ_INVITE_BONUS=367, DETAILS=368, CLAIM=369, ACT_INVITE_GIFT_LIST=83
- 排行：TOTAL_RANK_LIST=56, ALL_RANK_LIST=243, TODAY_RANK_LIST=79, COUNTRY_RANK=354, REQ_RANK_MAIN_VIEW=460, REQ_RANK=242, REQ_RANK_GET_WIN_COIN=247, RANK_THREE_DATA=258
- 游戏下注（rummy）：TABLE_BET_REQ=37（chips=筹码数组，面值由服务器 deskInfo.chips 下发）；GAME_ROOM_LIST=34, GAME_JOINROOM=32, GAME_CREATEROOM=31, GAME_SWITCH_TABLE=52, CHECK_DESK_INFO=502, REGET_DESKINFO=4, ENTER_CASINO=120
- 老虎机：SLOT_START=44（betIndex=预设档位，金额服务器定，不可篡改）
- 破产：GET_BANKRUPTCY_INFO=149, GET_BANKRUPTCY_REWARD=151；新手礼 GET_NEWER_GIFT_REWARDS=665
- 分享现金：REQ_SHARE_CASH_INFO=535, INVITES=536, WITHDRAW=537, 日志=538
- 绑定手机：GET_PHONE_CODE=135, BIND_PHONE=134, CHECK_PHONE_USED=136

## 资金面卡点（客观，服务器端校验）
1. 提现/转账/代理 → spcode 551 invalid_phone（需绑定手机，OTP 服务器校验）；负数金额（coin=-100/-999999/1e9）服务器直接不响应（超时），非客户端校验可绕过
2. 绑定手机 BIND_PHONE=134 验证码校验严格（空/错误 code → spcode 339/553），OTP 无法爆破
3. 下注篡改：chips 面值服务器下发，且 bdrummy 新盘 GAME_ROOM_LIST 返回 rooms:[]（无活跃牌桌），无法进入游戏
4. 排行榜：bdrummy 新盘 datalist 空；pakrummy 成熟盘 ALL_RANK_LIST=243 也返回空（正确入口应是 REQ_RANK_MAIN_VIEW=460/REQ_RANK=242，未验证成功）
5. 支付回调在服务器端，客户端代码挖不到回调 URL

## 真实已确认漏洞（非资金面）
- 登录签名突破：c_ts + x=md5(c_ts+salt) + c_idx + 真实 deviceid（salt 硬编码 getSalt()）
- 分享现金 c=535 + c=538 泄露 40 个真实玩家手机号（+880）
- 游戏广播 NOTIFY_BIG_WIN=100074 泄露玩家真实姓名+赢钱金额（如 Md Majidul Islam 赢 1532.5）

## pakrummy geo-block 绕过
- 198.44.167.83:31023 旋转代理池，30 次轮换约 2 次撞上巴基斯坦出口（pong 200），WebSocket 需循环重试登录（协议1~25次/协议2~4次成功）
- geo-block 白名单极窄：巴基斯坦/香港放行；越南/印尼/泰国/印度/新加坡/缅甸全部 403
