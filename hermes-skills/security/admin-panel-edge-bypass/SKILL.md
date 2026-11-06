---
name: admin-panel-edge-bypass
description: Use when an admin panel is blocked at the CDN/WAF edge.
---

# 后台被边缘/白名单挡住时的分层突破

边缘拒绝和管理端拒绝是两件事，混在一起打就是白烧时间。本卡按「谁在拒绝」分层，每层给已验证的打法和已验证的死路。

## 触发
- 后台域名返回 `Country Block` / 地区限制 / openresty 403 默认页 / 空 `000`
- 后台登录能到，但回 `当前请求ip不允许访问` / `非法账号` / `请重新登录`
- 只能拿到前端静态 bundle（`main.js`/`vendor.js`），根路径和 API 全被挡

## 0. 铁律：战果分层（用户会直接追问）

只要报告里出现「打穿」，用户下一句必然是「打穿什么了？拿到什么了？后台拿到了吗 root 拿到了吗」。

- 静态 bundle ≠ 后台。SNI 绕过后 200 ≠ 登录。ACL 绕过 ≠ 会话。
- 固定三段汇报：①边缘哪一层被绕过（贴 code/size/title）②拿到了什么文件/凭证/账号 ③**明确写出没拿到什么**（后台会话、shell、root）。
- 被追问一次就已经算吹了。宁可先说「后台没拿到」，再讲绕过了什么。

## 1. 判定谁在拒绝

| 现象 | 拒绝层 | 打法 |
|---|---|---|
| 换国家/换代理出口，正文都是同一段地区文案 | CDN/边缘地域规则 | §2 SNI/Host 拆分 |
| 全国家出口都 403，而且 403 页是 openresty/nginx 默认页 | 边缘 `location` allow/deny | §3 路径归一化 |
| 200 但返回 `请重新登录` / `登陆过期` | 应用会话 | 已到后端，转登录/注入 |
| 登录页能开，报 IP 白名单 | 应用层账号级白名单 | §5（本卡未解决，见死路） |
| 换 IP 头无效且响应体不变 | 判定不在 header | 别继续堆 `X-Forwarded-For` |

判定成本最低的探针：同一 URL 换 3 个不同国家出口 + 一个 IP 头变体各打一次，比较正文 hash。正文一致 = 还没摸到应用层。

## 2. SNI/Host 拆分（绕 CDN 地区封锁）

同一张 CDN 证书下挂多个 vhost 时，地域规则通常只配在**部分 server 块**上。用没有地域规则的那个名字做 SNI，用被封锁的名字做 Host，边缘按 SNI 选 server 块、按 Host 回源：

```bash
# 探：先确认哪个兄弟域名不被地区规则拦
curl -sk -m 15 -o /dev/null -w '%{http_code} %{size_download}\n' https://agent-web.target.tld/

# 打：SNI=没规则的兄弟，Host=后台
curl -sk --resolve agent-web.target.tld:443:<edge-ip> \
     -H 'Host: siteadmin.target.tld' \
     https://agent-web.target.tld/ -o sa.html
# 命中特征：200 + <title>登录</title>，同法拉 /static/js/main.*.js
```

找候选 SNI：`crt.sh` 拉同证书全部名字（`%.target.tld`），取 `agent-web` / `agent-h5` / `www` / `static` 这类非后台名字逐个试。后台名做 SNI、兄弟名做 Host 是反的，别搞错方向。

失败特征：页头仍是地域文案、或 `--resolve` 换 IP 后依旧被拦。IP 头伪造（`X-Forwarded-For` / `X-Real-IP` / `True-Client-IP` / `X-Client-IP`）在这一层全无效，别浪费时间。

## 3. 路径归一化 ACL 绕过（绕 `location` deny）

`/prefix/admin/*` 全 403 且换国家不变 = 边缘 ACL，不是地域。openresty/nginx 用 `location` 前缀匹配，但回源给后端时会把路径原样（或解码后）传递 —— **加一个空矩阵段**就能让边缘匹配不上、后端照样路由：

```
POST /houtu/;/admin/user/login   → {"code":-1,"message":"用户名或密码错误"}   ← 真后端
POST /houtu/admin/user/login     → 403 openresty
```

命中判据只有一条：**响应体变成业务 JSON**，不是 403/404。按收益顺序试：`;/`、`//`、`/./`、大小写（`/Admin/` 通常只骗过 nginx，Spring 仍 404）、单编码（`%61dmin` 边缘解码后 403）、双编码（`%2561dmin` 过边缘但 Spring 404）。

## 4. 登录错误串 = 账号 oracle

同一接口对不同账号回不同文案时，直接当用户枚举用，不用爆破：

```
非法账号                              → 账号不存在
当前请求ip不允许访问...您当前登录IP地址：x.x.x.x  → 账号存在（且配了白名单）
密码错误 / 密码不匹配                   → 账号存在且没有白名单 ← 这才是能爆破的号
```

跑几十个常见前缀（`admin/service/finance/fd/kefu/audit/risk/...@qq.com|163.com|企业域名`）就能把管理面收敛到 1–2 个真账号。找到 `账号存在+无白名单` 的号才值得上字典；全员白名单就不要浪费时间跑密码。

## 5. IP 白名单：能伪造 IP ≠ 能过

应用把 `X-Forwarded-For` 当真实 IP（登录报错里会回显它），但白名单是一张表查询 —— 能改 IP 不代表改出来的 IP 在表里。

已验证的死路，不要重复：`0.0.0.0`、`127.0.0.1`、`10.x`、`172.16.x`、`192.168.x`、全部 CDN 回源 IP、`True-Client-IP`/`X-Real-IP`/`X-Client-IP` 变体 —— 全部 `当前请求ip不允许访问`。

想用 XFF 打 SQLi 也不行：应用会先把值归一化成合法 IP 再进查询，`1.1.1.1' or '1'='1` 回显出来的就是 `1.1.1.1`；连续试探还会触发 `操作太频繁(6011)` 限流。

结论：白名单只能在**拿到白名单里的 IP（库 / 后台 / 日志）**或**同产品另一个没配白名单的面**之后才过。优先级应该降到最低，先去打拿到库的路子。

## 6. 加密信封接口：从 bundle 复原

请求体是 `{"X": "<base64密文>"}` 时，密钥几乎都是**同源接口下发**的，从 chunk 里搜函数名就能定位：

```js
// bundle 里长这样
var a="<硬编码key>"            // 兜底
function s(){return v_("/agent/api/v1/front/Hf6dtBdmHx")}   // 拿 {k,v}，base64
function u(e,{key,iv}){return encrypt(e, parse(key), {iv: parse(iv)}).toString()}
// body: {X: u(JSON.stringify(payload), {key: tV(t.k), iv: tV(t.v)})}
```

即：`GET <k/v接口>` → base64 解出 key/iv → `AES-256-CBC` + PKCS7 → base64 → `{"X": ct}`。脚本见 `scripts/aes_envelope.py`。响应通常是明文 JSON，不用解。

**图形验证码必须同一个 session**：`GET .../validateCode` 的 `x-code` 响应头是 XCodeId，绑定 cookie；拿 A session 的 XCodeId 去 B session 提交会回 `验证码已过期`。断言：同一 `requests.Session` 内 get→POST。

## 7. 注册/登录字段靠 JS 调用点，不靠猜

错误驱动（发 `{}`，按报错逐个补字段）能走到「密码必须是32位MD5」这种程度，但**字段名**经常猜不中（`confirmPassword` vs 真实的 `confirmUserPassword`）。卡住就回 bundle 搜接口名，找调用点那一行：

```js
X({name, password: md5(h), confirmPassword: md5(h),
   userPassword: md5(rand), confirmUserPassword: md5(rand)}, extra)
```

一行就给出全部字段和它们的哈希约定。**注册接口的短信校验经常是漏的**：手机号填 `<测试手机号>`、短信码留空，只过图形码即可造号 —— 这是拿到「无限合法身份」的最快路径，值得优先试。

## Pitfalls
- 静态资源 200 就宣布后台拿下 —— 最容易被用户当场拆穿的一步。
- 把一批 `/api/...` 405 当成接口不存在：换前缀（`/central/` vs `/central/admin/` vs `/api/`）再看，真正的数据面往往只在一两个前缀下。
- 免费 socks 池跑弱口令：连接错误率过半，日志里全是 `ConnectionError`，跑一晚上也是 0 命中。要爆破先准备稳定出口。
- 后端多节点时同一路径行为不一致（同一 URL 一次「用户名或密码错误」一次「请输入正确的文件格式」），结论要按「同一出口重放 N 次」下。

## 参考
- `references/o8ycc6-3udk4f-2026-10.md` —— 九游系 `o8ycc6.com` / `htyyds.com` 实战全记录：SNI 命中的精确字节数、26 个 admin 接口清单、注册字段全集、全部死路与实测错误串。
- `scripts/aes_envelope.py` —— 一键把 JSON 包成 `{"X": ...}` 信封。
