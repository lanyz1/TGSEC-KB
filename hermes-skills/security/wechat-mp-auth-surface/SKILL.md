---
name: wechat-mp-auth-surface
description: "打微信公众号扫码登录/事件回调时用: openid/签名/token。"
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pentest, wechat, oauth, openid, callback, account-takeover]
    related_skills: [oauth-attack, api-param-name-discovery, wxmini-static-audit, account-takeover-chain]
---

# 微信公众号/小程序 认证面渗透(扫码登录 + 事件回调)

## 触发
目标带微信公众号扫码登录 / 事件回调 / openid 绑定 / 小程序 jscode2session / `scene_str`。

## 0. 先分类认证面(不要默认「登录=一套鉴权」)
- 同一站常有多套登录入口: 管理端 / 业务端 / 扫码端 / 小程序端, **各自独立**。一套打不动**不代表**另一套也锁 —— 换前缀复测是 0 成本的。
- 判定「登录要不要加密」看前端 bundle, 不靠猜: grep 管理端 bundle 里 `auth/login` 的定义点,
 `In({url:"/admin/auth/login",headers:{isToken:!1,isEncrypt:!1,...}})` ⇒ **`isEncrypt:false` = 明文 JSON 登录**(无 key、无 clientId、无验证码)。
 反之出现 `isEncrypt:true` 就必须先从 bundle/接口把加密层(publicKey/encrypt)拿出来。
- 字段名用字段预言机(§3)定, 不要盲爆破。

## 1. 素材收割(零流量, 优先做)
从已落地的日志/前端里捞, 成本最低、价值最高:
- **真 openid 格式 = `o` + 27 字符**(如 `oGsXV7…`)。**不要按 `openid` 字样 grep 后直接取值** —— 字段名常被错用, 捞到的多是 appid(`wx…`)。先按格式正则筛, 再回头核对上下文字段名。
- 同类素材: appid(`wx…`)、公众号原始 ID(`gh_<12>`)、32 位密钥、EncodingAESKey(43 位)、转发目标域名、事件处理器类名 + `http-nio-<port>`(反推真实监听面)。
- **签名三元组** `signature=<40hex>, timestamp=<unix>, nonce=<n>` 是 §2 的输入, 见到就存下来。

## 2. ★ 离线反推公众号服务器 token(零流量, 本面唯一可离线的一步)
微信签名算法: `signature = sha1(sorted([token, timestamp, nonce]).join(""))`。
拿到任意一组 `(signature, timestamp, nonce)` 就能**离线穷举 token, 不回目标发一个包**:
```python
sha1("".join(sorted([tok, ts, nonce])).encode()).hexdigest() == signature
```
- **多组三元组一起用**: 先用第 1 组筛, 幸存者再验其余全部 ⇒ 排除碰撞假阳性(同时验证多组彼此自洽)。
- 顺序: 业务字典(公司名/域名/拼音 + 数字/下划线) → 小写+数字 长度 1–5(约 6×10⁷, 分钟级) → 长度 6(2×10⁹, 后台跑)。
- **判据**: 长度 6 全穷尽仍 0 命中 ⇒ token 是随机串, **放弃这条线**(公众号 token 可任意长随机, 暴力没有出路)。
- 拿到 token 只是「签得了」; 还要 §4 可达性 + §5 加密模式都满足, 才能伪造事件推送。

## 3. 扫码登录字段预言机(`wxLogin` 类端点)
逐字段加、只读错误文案差分, 比盲爆破省流量、低足迹:
```
{}                        → "授权凭证不能为空"   ⇒ 有第一个必填字段
{"code":"x"}              → "登录状态不能为空"   ⇒ 字段 = code, 还缺第二个
{"code":"x","state":"y"} → 第二个字段 = state
传 openid/openId/unionid/wxCode/jsCode 而文案不动 ⇒ **不认这些名字**
```
- ★ **探测下一个字段时必须回填已确认字段**: 少带一个, 服务端永远先报那个缺字段 ⇒ **你的所有候选名都「看起来不认」**, 据此会把整条路判死。
 判据: **错误文案对所有候选完全一致 = 你在漏字段, 不是候选名不对**。
- 拿到字段名后按 §4/§5 判定这条链能不能走。

## 4. 回调可达性(先判定再投入)
- 回调端点通常在 `/wx/**`、`/mp/**`、`/wechat/**` 命名空间。**整个前缀统一 401 = 网关级鉴权, 回调不在公网面** ⇒ 需要微信后台注册的确切 URL 才能继续, **停止在路径枚举上加投入**。
- 判据式探测(先校准真假两档): 同前缀下**连不存在的路径也回 401** ⇒ 是前缀级过滤器, **不是**「端点存在需鉴权」; 而放行前缀(`/portal/**` 类)会回真实的 404 / 静态资源 500。

## 5. 不可伪造判定(省一整轮)
- **错误文案来自上游(带 rid / request id)⇒ 服务端确实拿你的输入去上游换了凭据** ⇒ 该步不可伪造, 整条链关闭。
 形态: `invalid code, rid: <uuid>` 这种由上游侧返回的文案, 一旦出现就说明校验是真的。
- `state` / `scene_str` 一次性: 首次调用即消耗, 自申请的 UUID 只对本次会话有效。
- **结论模板**: 扫码登录 = 需真微信授权码; 想接管只能 ①拿到真实用户授权码 或 ②伪造签名事件(需 §2 token + §4 可达 + §5 加密模式全过)。
 ①②都不成立就**明确关闭这条链并写清卡在哪一步**, 不要只说「登录不可绕」。
- 拿到「不可伪造」结论后**回 §0 换登录入口**, 别把它当成整站的结论。

## 6. 比死磕扫码登录更划算的面
- 日志里的 **openid / 手机号 = 后续靶向登录的账号来源**(可配框架初始口令, 如 `sys.user.initPassword`; 单账号试 1–2 次, 不触发锁定)。
- 小程序侧是**另一个 appid**, 走 `jscode2session` 同样不可伪造, 但它的业务接口鉴权面(`/wx/genCode/*` 类)与公众号不同, **单独测**。
- 事件处理器常把所有事件当同一类处理(把 `TEMPLATESENDJOBFINISH` 也记成「关注事件」)⇒ 一旦可达, 事件类型 / `EventKey` / `FromUserName` 的可控性就是弱点所在。
- 公众号加密模式看推送体的 `encType`: `aes` = 安全模式(需 EncodingAESKey 解), 出现明文 `<xml>` 可被处理 = 兼容模式 ⇒ 伪造成本低一档。

## 交付
- 每条链写「走到第几步 / 卡在哪个判据 / 为什么关闭」, 不是只写「登录不可绕」。
- 素材(openid / appid / gh_id / 签名三元组)落 `evidence/`, 报告里对真实 openid 与密钥脱敏。
- 离线穷举要能复现: 留存词表与脚本, 命中与否都写清试过的空间大小(如「长度≤6 小写+数字全穷尽」)。
