# 小木子(Commonxmz / xiaomuzhi)系棋牌平台档案

国产 PHP 棋牌/博彩商业系统,同一套代码多实例(品牌 × 前端站/大厅站/WS 服分离)。

## 指纹

- 模板目录 `commonxmz67/`(`fiesc/` 游戏 + `files/` 大厅两套);页面 `<base href="http://<bucket>.oss-*.aliyuncs.com">` 指向公共读 OSS 静态桶
- 代码根 `/www/wwwroot/xiaomuzhi_front/application/{controllers,models,views}`,模型入口 `application/models/db_models.php`
- 自带 WAF `application/third_party/phpcode_shield.php`;日志路径常为 `/mnt/log/dealer/dealer2/shield_<date>.log`(目录不存在 → 每次告警回显绝对路径)
- 未登录时任意路径都渲染登录页(`<title>XX大厅</title>` + 内联 `var t = '<站点令牌>'`);登录页里 `apiUrl = http://<ip>:8281/userapi/`,常与当前主机不同
- `/site/index`、`/app/` 返回「XX大厅聊天室」页,泄露 `phpWxIp/phpWxPort/phpWxUrl`、微信 appId、`wxConfig` 签名
- 客户端入口形如 `bbull21_1.html?i=<房间号>&t=<毫秒时间戳>`;`js/config.js` 里 `BaseUrl = http://<ip>:9903`,旧地址常以注释留档
- 静态 404 页「404，您请求的文件不存在!」= 未登录时的假响应;CodeIgniter 风格 `Database Error` 页 = db_debug 开着

## 资产分层

| 角色 | 典型 | 说明 |
|---|---|---|
| 前端/游戏站 | `:9903` | `xiaomuzhi_front`,承接 /home1 /api /site /userapi /qr /chat /app |
| 大厅/用户中心 | `:8281` | 同一代码库另一实例,nginx 按源 IP/路径白名单(云厂商段常 403) |
| Workerman WS | `:20010`(常在另一台机器) | HTTP 访问回 `Sec-WebSocket-Key not found` |
| MySQL | 连接来源是另一台主机(`user()` 回显) | 3306 不对外 |
| 静态资源 | OSS/COS 公共读桶(禁列举) | `vu2-xb-<brand>-0`、`<brand>-<appid>.cos-website.<region>`、`ufo006`(renhai 通用模板) |

## 接口面

- `POST /userapi/{loginPwd,loginSms,getLoginSms,getRegSms,regSms,setPassword,logout}`,全部带站点令牌 `t`
  - `loginPwd {phone=<用户名或手机号>,password,t}` → `{account_id,wwid,code,tk}`
  - `loginSms {phone,code,password}` = 短信登录**兼改密码** → 配合明文验证码 = 任意账号接管
  - `getLoginSms` 对已注册/未注册返回不同文案 = 账号枚举 oracle
  - `getRegSms` 无频控(60s 只是前端计时);`regSms` 提交注册需真实验证码
- `GET /site/lg?wwid=&t=&return_url=<host>/` = 前端自动登录,换 PHPSESSID + 477KB 用户中心页
- `GET /home1/index`(资料/session/ws_ip/tk/tt)、`GET /home1/room?i=<room>_`(room_status、balance_scoreboard 含真实玩家与分数、`socket=ws://…/gamebdn?session=…`)
- `GET /api/getgamelist?wid=`、`/api.php`(回 wx_url/ws_ip/ws_port)、`/clubapi/join`、`/qr/index?url=`(任意文字转二维码,缺 url 时报错回显路径)
- `POST /site/upload {avatar=<任意字符串>, token=<登录返回 code/tk>}` → 把 avatar 原样拼 CDN 前缀写库(headimgurl),无扩展名/内容校验 → 存储型 XSS 或服务端取图 SSRF 载体
- hall.js 里的 `/f/*`、`/account/*` 是另一版客户端残留,当前实例常 404,别恋战

## 关键数据表

| 表 | 价值 |
|---|---|
| `wechat_account` | 会员主表: account_id/open_id/union_id/nickname/phone/username/password(md5)/salt/balance/vip_level/saler_level/user_code |
| `sms_detail` | mobile + **identifying_code 明文** + type + invaild_time + session → 直接读验证码 |
| `dealer_account` | 代理: account + passwd + **clear_pwd 明文** |
| `manage_member` | account_id ↔ manager_id ↔ user_code(代理/管理层关系,可推超管链) |
| `account_login_log` | 全量登录 IP 日志 |
| `config` | Platfrom_Name/qx_aes_key/qx_token/qx_wx_*/WebSocket_<各游戏> |
| `ws_list` | 游戏服 ip:port |
| 其余 | bull_room/room_game_result/room_scoreboard、payment_*/withdraw_order、union_*/dist_*/guild_*、shop_skin* |

## 实战要点

- 注入入口: `POST /userapi/getRegSms` 的 `phone`(SQL: `select create_time from sms_detail where mobile="$phone" and is_delete=0 order by sms_id desc`)
- DB 账号常只给 `PROCESS,REPLICATION SLAVE,REPLICATION CLIENT`(**无 FILE**)→ load_file/outfile 全废,shell 须另找面
- 管理后台通常不在已暴露的 IP 上(`/manage` `/dealer` `/admin` `/system` 全 404 或「Directory access is forbidden」);`game_domain`/`fa_domain`/`io_url` 里的域名大量 NXDOMAIN,是历史残留
- 微信链路用 EasyWeChat,`/chat/` 会抛 `errcode 40164`(IP 白名单未配)并顺带回显配置线索
- WS 载荷 AES key 常以反转字符串硬编码在 hall.js(`"…".split("").reverse().join("")`)
- 测试期间写入的业务字段(如 headimgurl)测完改回原值:用同一个 upload 接口传空串即可
- 收尾分级: SQLi 读权限 + 管理身份业务会话 ≠ 控制权,报告里分开写
