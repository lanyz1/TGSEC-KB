# pakrummy/bdrummy WebSocket 登录协议（完整打穿版）

## 关键突破：登录签名（之前 209 的根因）
之前一直卡 `spcode 209 auth fail`，根因是**登录消息缺少三个 send() 附加字段**：
1. `c_ts` = 毫秒时间戳（`int(time.time()*1000)`）
2. `x` = `md5(str(c_ts) + "hero888")`（**仅 LOGIN c=1 时加**，LOGIN_USERID c=2 不加）
3. `c_idx` = 客户端消息索引（从 0 递增）

盐值 `getSalt() = "hero888"`（写死在 project.js）。

## 209 → 218 → 成功的演进
- 缺签名 → `spcode 209 param_nil`（参数空）
- 加了签名但 deviceid 用顺序假 ID（`a1b2c3d4e5f6a7b8`）→ `spcode 218 "Unsupported device!"`
- deviceid 用真实随机格式 Android ID（如 `9774d56d682e549c`）→ **登录成功**

**教训：deviceid 必须是随机 16 位 hex（真实 Android ID 格式），顺序值会被判定为模拟器/假设备。**

## 完整两段式登录流程
### 协议1 LOGIN (c=1) 登录服务器
- WebSocket: `wss://<loginServerAddress>/ws`（bdrummy 无 geo-block，pakrummy 有 CloudFront geo-block 需亚洲代理）
- 消息（msgpack，24字段）：c=1,user=Guest+随机,passwd=同user,app=17,av=versionName,bundleid=真实包名,v=resVersion(默认"1.0.0.0"),t=1(Guest),accessToken="",platform="Android",phone="Brand_Model(版本)",code="",token=时间戳_随机,bwss=1,LoginExData=1,language=2,dlan="en",client_uuid=deviceid,deviceid=AndroidID,dinfo='{"gid":"GSFID","sid":"","oper":""}',c_ts=毫秒,x=md5(c_ts+"hero888"),c_idx=0
- 请求头：`[2B大端len][2B CRC-16][4B大端ts秒][msgpack]`；CRC-16 poly 0x70B1 init 0xFFFF 只算前 min(len,128) 字节
- 响应头：固定 ASCII `"00000000"`(8字节) + msgpack body
- 成功返回：`{uid, subid, net, token, server, code:200}`

### 协议2 LOGIN_USERID (c=2) node 服务器
- WebSocket: `wss://<net>/ws`（协议1返回的 net，如 ga.fcwjosk830sj.com）
- 消息：c=2,uid,openid="",server,subid,token,deviceid,appver=versionName,app=17,bundleid,v,resVersion,kouuid="",av=versionName,fmcToken="",c_ts=毫秒,c_idx=1
- 成功返回：**完整 playerInfo（含余额 coin/dcoin/bankcoin/cashbonus/diamond/ticket/rp/pts）+ 推广码 code + invit_uid + kyc 状态**

## 关键结论
- **appId=17（YonoGames），不是 19**；cAppid=2(pakrummy YonoRummy)/501(bdrummy BDRUMMY)
- **bwss=1**（loginServerAddress 不含":"端口时 isUserWSS()=true）
- **language 是数字 id**（EN=2）
- getDInfo: appId 17/19 都是 YDApp → dinfo 含 gid/sid/oper；gid=GSF ID(hex)，sid/oper 恒空
- getDeviceId=Android ID；getSimOperator/getSimacardid 恒空
- 包名/版本：pakrummy `com.rummy.pak.games`/1.1.4，bdrummy `com.bdl.rummy.games`/1.0.2，代理端 yonorummyagent
- xxtea 密钥 `b32a2160-0c63-41` 全矩阵通用（pakrummy/bdrummy/spinharta/agent 均同密钥）

## 资金 MsgId
LOGIN=1、LOGIN_USERID=2、SYNC_COIN=29、DRAW=132、TRANSFER=142、PURCHASE_GOODS_LIST=51、BIG_CHARGE_ORDER=90、BANK_SAVE_COIN=102、BANK_TAKE_COIN=103

## 支付反馈 URL 拼接（项目内）
`getPayFeedbackUrl() + "#/list?d=" + cAppid + "&uid=" + uid`
