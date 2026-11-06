# pakrummy.com WebSocket 登录协议逆向（Cocos Creator 博彩盘）

## 消息格式（客户端→服务器）
`[2B 大端长度][2B CRC-16][4B 大端时间戳(秒)][msgpack body]`
- 长度=msgpack body 字节数；CRC-16 多项式 0x70B1(28849) 初始 0xFFFF，只算前 min(len,128) 字节
- 头部 `struct.pack('>HHI', length, checksum, int(time.time()))`
- body `msgpack.packb(dict)`（Python msgpack 与 msgpack-lite 的 fixstr/map16 二进制兼容，已验证）

## 服务器响应格式（不对称！）
`[8B ASCII "00000000"][msgpack body]` — 响应头部是固定 ASCII 零（非二进制），body 仍是 msgpack。解析跳过前 8 字节再 msgpack.unpackb。

## 登录消息字段（MsgId.LOGIN=1，游客）
```python
{
  "c":1, "user":"Guest"+随机4位, "passwd":同user, "app":17或19,
  "v":"1.1.7.1",  # resVersion 资源版本，从 assets manifest 的 "version" 字段取！非硬编码
  "t":1,  # LoginType.Guest=1 PHONE=9 PHONE_REGIS=8
  "accessToken":"", "platform":"Web", "phone":"Web_Android",
  "code":"", "token":时间戳_随机, "bwss":1, "LoginExData":1,
  "language":"en", "dlan":"en", "client_uuid":时间戳+随机,
  "bundleid":"com.rummy.pak.games",  # 从 AndroidManifest package 取
  "deviceid":"a1b2c3d4e5f6a7b8",  # 16位十六进制 Android ID
  "dinfo":'{"gid":"","sid":"","oper":""}',  # appId∈{17,19} 时 isYDApp=true 必须含三键
}
```

## 关键坑（易错点）
1. appId∈{17 YonoGames, 19 RummyVIP} 时 `isYDApp()=true`，dinfo 必须 `{"gid":"","sid":"","oper":""}` 而非 "{}"
2. `v`(resVersion) 从 APK assets 里 manifest 的 "version" 字段取（如 1.1.7.1），不是 AndroidManifest versionName(1.1.4)
3. autoTravellerLogin 真实调用 `reqLogin(user,passwd,Guest,"",loginAction=1,token)` — accessToken 是空串，token 才是时间戳_随机
4. 服务器响应头部 ASCII "00000000"，与客户端二进制头部不对称，别按二进制解析响应头部

## 登录成功判定
`{"c":1,"code":200,"spcode":0,...}` 成功；spcode 非 0 走错误。`209=param_nil` `210=illegal_parameter` `211=invalid_token`。成功返回 uid/net/server/subid/token，客户端再发 LOGIN_USERID(c=2) 连 node 服。

## geo-block 绕过
CloudFront Geo Restriction 只放巴基斯坦。免费巴基斯坦 http 代理（proxyscrape country=pk）：`http://111.119.162.248:10934`、`http://110.39.15.206:8082`（HTTP ping 通但 WebSocket 握手不稳需多试）。"动态住宅池" 198.44.167.83:31023 实为全球随机轮换无巴基斯坦，勿依赖。

## 短信注册端点（公开无需 session）
`GET https://service.cwvi65sop.com/sms/dosend?phone=PK号码&channel=0&otptype=6`（注册 otptype=6 登录 otptype=1）；`{"code":0}` 成功 `{"code":10027}` Send Failed（需有效手机号）。

## 逆向链（APK → 明文 JS）
1. APK 解压取 `assets/src/project.jsc`（xxtea 加密）
2. 从 `lib/arm64-v8a/libcocos2djs.so` 用 r2/objdump 恢复 xxtea 密钥（`jsb_set_xxtea_key`）
3. Python 实现 xxtea（所有算术 `& 0xffffffff` 掩码，JS uint32 溢出语义）解密
4. 解密结果是 gzip(magic 1f8b08)，用 zlib 解压（非 gzip 模块，CRC 破坏但 payload 完整）
5. 得到 browserify 打包明文 JS，grep 挖域名/端点/密钥/协议
