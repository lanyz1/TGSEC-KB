<!-- archived from /root/.hermes/skills/security/time-sensitive-credential-diagnostics/SKILL.md on 2026-10-21 -->

---
name: time-sensitive-credential-diagnostics
description: "Use when TOTP/OTP/时间戳签名被拒:先校服务器时钟再重算。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, totp, otp, 2fa, clock-skew, timestamp, nonce, signature, diagnostics]
    related_skills: [signed-api-gate-oracle-hunt, 2fa-otp-bypass, captcha-registration-bypass]
---

> 归档卡：原目录 `/root/.hermes/skills/security/time-sensitive-credential-diagnostics`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/time-sensitive-credential-diagnostics/…')`，不要相对 `references/legacy/` 解析。

# 时间敏感凭据被拒的诊断序(TOTP / OTP / 时间戳签名 / nonce / TTL)

## When to Use
你**已经拿到**密钥/算法/字段名(或自认为拿到了),但服务端仍回:
「验证码错误」「动态码不正确」「时间戳无效」「签名已过期」「nonce 失效」「请求过期」「链接已失效」。
这类「推理都对了但就是不过」的场景,第一嫌疑永远是**时钟**,不是算法。

## ★ 铁律 1:先校时钟,再怀疑任何东西
TOTP 30s 一步 ⇒ 本机钟偏 >±60s 时怎么算都错;HMAC+timestamp 闸同理(窗口常 ±300s)。
执行环境可能是容器/VM/沙箱,钟是虚拟化或被漂移过的 —— **永远不要假设本机钟是对的**。

### 读目标服务器时钟(按可靠度排序)
1. **`Date` 响应头(首选,最权威)** —— 走 HTTP 库出网读,不要用页内 fetch:
   跨源 fetch 的 CORS 只暴露 safelisted 头(`content-type`/`cache-control`/...),`Date` **读不到**(读到 `null` 别据此判「目标不回时间」)。
   **被 WAF 挑战、答 403/302/500 都照样带 `Date`** ⇒ 拿不到正文也能测钟。
2. **响应体里的服务端时间字段**:`serverTime`/`now`/`timestamp`/订单创建时间 —— 任何由服务端生成的毫秒值都能当基准。
3. **服务端自签的 token**:JWT 的 `iat`/`exp` 是服务端钟算出来的,解出来即基准。
4. **TLS 证书 `notBefore`/`notAfter`、`Last-Modified`**:精度差(天级),只当兜底。

### 判定是哪边的钟坏
多打几台主机(含一个**无关大站**)比 `Date`:几台一致 ⇒ 本机偏;只有目标偏 ⇒ 目标偏(同样按目标钟重算)。

### 修正与扫描
```python
skew = parsedate(Date) - time.time()          # 本机快为正
step = int((time.time() + skew) / 30) + delta # 用服务端时间推进
```
- **先扫 `delta ∈ {-1,0,1,2}`**(±1 覆盖 30s 边界翻转,+2 覆盖慢钟超过半步的情形),命中即停。
- **绝不要一上来扫 ±960(时区假设)或全 6 位** —— 30s 步长下「时区」不是有效假设,真正偏差是秒级的;大范围空扫只会烧掉尝试配额,还得出「密钥/算法错」的假结论。
- 非 TOTP 的闸:把 timestamp 参数改成 `本机时间 + skew`,nonce 窗口按修正后的时间重取。

### 验证与再校准
- **用状态回读确认成功**,不要用错误文案:绑定/启用后回读状态接口(`googleBound`/`googleEnabled`/`status` 一类字段),文案可能滞后或只报最先失败的那一步。
- 长作业里**每进入一个新阶段就重测一次 skew**:沙箱重启、隧道重连、跳板切换都会改变本机钟源。

## 铁律 2:校完钟再按序排查
| 症状 | 真因 | 做法 |
|---|---|---|
| 有正确 secret 仍「验证码错误」 | 时钟偏差(最常见) | 铁律 1 |
| 同上,钟已校准 | 字段名与前端源码不一致 | 以 bundle 调用点为准:同产品会混用 `code`/`googleCode`/`otp`/`verifyCode`,猜字段能白跑十几轮 |
| 同上 | 算法/参数错位 | 逐项试:标准 HMAC-SHA1 / 误把 base32 字符串当 key / SHA256 / SHA512 / 6 vs 8 位 / period ≠ 30 |
| 同上 | 密钥未持久化 | `create`/`setup` 每次返**新** secret 但服务端只存第一次 ⇒ 把历史 secret 逐个重试 |
| 报的是密码/支付密码类错误 | 前置校验被同类文案吞掉 | 按**前端源码**把 body 字段凑齐(如 `bind` 需 `{paymentPassword, googleCode}` 两个字段) |
| 单步成功但功能没生效 | 该流程是两步 | 常见 `create → bind → enable`,bind 成功 ≠ 生效,补 `enable` 并回读状态 |

## 铁律 3:尝试计数器纪律(授权边界)
回显「还剩 N 次机会」= 服务端按 **username 记账的锁定计数器**。
- **他人账号零盲试**:默认 `admin` 这类账号 1-2 次即停 —— 继续试会锁死真实管理员账号,不可逆且超出授权。
- 多组凭据/多轮 code 尝试只在自己持有或自己注册的账号上做;别人的账号先拿到正确凭据再打。

## 随附脚本
`scripts/skew_probe.py` —— 一条命令同时给出「各主机 skew / 推荐 delta / 候选动态码」:
```bash
python3 scripts/skew_probe.py https://target/api/health --host-compare www.baidu.com --secret BASE32SECRET --proxy socks5h://127.0.0.1:1086
# 输出: 每台主机 skew + 本机偏/目标偏判定 + delta∈{-1..2} 候选 6 位码 + 各自剩余有效期
```

## Pitfalls
- 页内 fetch 读 `Date` 得 `null` **不是**「目标不返回时间」,是 CORS 只暴露 safelisted 头 ⇒ 换 HTTP 库出网读。
- 别把「大范围偏移扫描无命中」当证据去否定 secret/算法 —— 先测实际 skew,再在小范围里扫。
- 被 WAF 挑战/403 的响应同样带 `Date`,别因为状态码就丢掉这个情报。
- 对齐时钟后**立刻**重试,不要等下一轮;30s 步长在边界附近抖动,连打 2-3 次比只打一次稳。
- 校准结果写进**单一共享常量**(一个 `skew.py` / 配置项,所有脚本与函数 import 它),而不是每个脚本/每个 mint 函数各写一遍:多份时钟修正并存时,漏写的那一处会把**自己的 bug 伪装成服务端拒绝**(报「验证码错误」),让人回头去怀疑 secret / 算法,白跑几轮。页内(浏览器侧 mint)与后端脚本侧两处用同一个值,并在报告里披露 skew —— 后续复现依赖它;报「谷歌验证码错误」时**先 grep 自己所有算码处**是否都乘上了 skew。
- 用 `requests` 测钟时把 `trust_env` 关掉并显式给代理,否则系统代理会静默接管出口,测到的是代理的钟。
