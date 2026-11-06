# 案例：白标 IM「轻序协同 / 即联达」QXXT（企业号租户平台）

实战记录，配合 SKILL.md 的通用方法阅读。产物在 `D:\渗透\qxxt_2026\`。

## 目标形态
- 白标 IM SaaS，厂商 TG `@imim`（又名 `@kaiban`），旗下即联达/轻序协同/飞象，按"企业号"卖租户。
- 客户端：Flutter（Dart 包名 `package:fchat/...`）+ Go `libgojni.so`（gomobile 桥接类 `mxl.Mxl`）。
- 包名混淆：`com.umlghsqog.kdtf.ksusqrh`；App 显示名即产品名（`frida-ps` 里直接看到 `QXXT`）。

## 主机是运行时按企业号下发的（静态分析必然空手）
App 与二进制里**没有任何底座域**（`jldgjno2.cc` / `i7517.cn` / `5roxr.cn` / `jldcdn.cc` 全搜不到，
ASCII 与 UTF-16 都试过）。只有跑起来读 `GoLog` 才有：
```
GoLog: hosts ["global-779.jldgjno2.cc","jldfz2-779.i7517.cn","jldfz2-779.5roxr.cn"]
GoLog: 线路Base检测: global-779.jldgjno2.cc   使用线路: global-779.jldgjno2.cc
```
命名规律 `{线路}-{企业号}.{底座域}`；**不同企业号的线路集合不同**（333 是
`jldfz2-333.5roxr.cn` + `jldfz2-333.i7517.cn`，没有 `global-` 线）。
网关是腾讯 EdgeOne（`*.eo.dnse4.com`），租户 API 子域可直连，PC/图片域对 CN 出口 403。

## 免登录态注入（实测有效）
`shared_prefs/FlutterSharedPreferences.xml`：
```xml
<map>
  <boolean name="flutter.isConfirmUseApp" value="true" />
  <string name="flutter.enterprise">779</string>
  <string name="flutter.username"><PHONE-REDACTED></string>
  <string name="flutter.uuid">ddfd8a2a-767b-5818-b8f3-e59f9566bb02</string>
  <string name="flutter.token">11qn4ed18pidlggqoai8delaaocisbo1</string>
</map>
```
`chown 10110:10110`（uid 从 `ps -A -o PID,USER,NAME` 取）→ `am start` → 直接进主界面并开始发帧
（`send 2 20 1 seq=0` / `send 10 20 {"time":null,"uids":null} 1 seq=1`）。
**只有 enterprise 没有 token 会卡白屏/启动图**。

## 协议：`mxl.Mxl.send(cmd, body, "1")` → 服务端 JSON
命令空间 1–300 **全部存在**（用 `{}` 探测，返回 `{"emsg":...,"code":...}` 即命令在、参数缺）。
实测语义（779 自己的账号）：

| cmd | 语义 | 返回值特征 |
|---|---|---|
| 2 | 本人账号信息 | `uid/loginname/phone/invitecode/nick/avatar/status/permission{...}` 权限矩阵 |
| 10 | 会话列表 | `list[]` 含 `mseq/hseq/seq/unread/last{msg,uid,nick}`、群 id 为负数、`tops[]` 置顶成员 uid |
| 11 | 对象详情（用户/群） | 传 `{"id":<uid或群id>}`；群含 `hseq`=消息总数 |
| 14 | **全局搜索（用户枚举）** | 字段名是 `query`；只按**昵称/群名**模糊匹配，手机号/uid 搜不到 |
| 16 | GIF 库 | 泄露 OSS 桶域名 |
| 21 | OSS 签名 | 返回 `{"url":"u:<base64密文>"}` |
| 28 | 余额 | `{"balance":0}` |
| 1003 | 联系人 | `{"list":[...]}` |
| 3/4/6/7 | 提现记录/提现/转账金额类 | 参数校验可枚举 |
| 26 | 与密码加密相关 | 空体报"密码加密错误" |

Dart 侧 `core/base/http/v2/*_req`（登录/注册/改密/OSS签名/版本/配置）与
`core/base/websocket/req/{user,group,friend,message,session,batch}/*` 是**字段名反推表**。

## 静态侧的两个收获
- `libapp.so` 里硬编码 **4096-bit RSA 私钥**（PKCS#1，多行 base64，起点 `MIIJKAIBA...`）→ 已转 PEM；
  二进制里**没有**对应公钥（说明 Dart 用运行时导出/传入）。
- GoLog 里出现 `RSA.Encrypt: public key missing` → 客户端加密用的公钥是**运行时注入**的，
  这解释了为什么 HTTP 层怎么发都报"企业号错误"。

## 跨租户：负向结果（重要）
换 `enterprise=333` + 沿用 779 的 token 启动 → 底层直接 `CON_NO`（拒绝）。
**token 是租户隔离的，不能横向复用。**

## HTTP 层的死路（别再走）
`/v2/com/user/login`、`/v2/com/sms/send` 在 666/333/111111/777 上都存在且共用，但
明文/空体/无效 base64/随机 base64/`{data:}`/`{encrypt:}`/text-plain/企业号放
body·header·Cookie·query·路径前缀·嵌套·大小写·Referer —— **全部同一句「企业号错误」**。
唯一免鉴权的是 `GET /v2/app/base`（按企业号子域返回 `loginTemp/init/link/reset/zegoId/pc`），
**所有租户 `zegoId` 相同** → 单一共享后端多租户平台。

## 环境坑（当次实测）
- LDPlayer 的 `/system` 只读、`mount -o rw,remount /` 失败 → `/etc/hosts` 改不了；guest `iptables` 可用。
- App 启动做出口 IP 探测（`api.ipify.org` / `api.ipify.cn` / `api-ipv4.ip.sb` / `ipv4.icanhazip.com`
  / `api.myip.la`）；宿主到这些域不通 → App **卡在「正在获取配置…」**，GoLog 是 `context deadline exceeded`。
- frida-server 用 `/data/local/tmp/<改名>`（别叫 frida-server），`adb forward 27042` + `frida -H` 才稳。
