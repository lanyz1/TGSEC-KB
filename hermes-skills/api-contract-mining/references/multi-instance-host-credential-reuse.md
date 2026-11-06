# 多实例主机的凭据复用（一破全破）

## 形状
一台 VPS 上跑 N 套**同源码不同部署**。本案 48 开放端口 / 25 个后台：同源码有 7 个「TG Ledger Bot」（8000/8001/9000/9110/9501/9505/9507 是 13 接口版，9521 是 58 接口完整版）、3 个双向群管机器人、4 个转发/广播控制台。**归族之后，攻击面从「25 个登录」塌缩成「4~5 个族的登录」。**

## 四步
1. `nmap -Pn -p- --min-rate 3000` 全端口 → 逐端口 HTTP 指纹（`title` / `Server` / `Set-Cookie` / `/openapi.json` / `/docs` / `/health`）→ **按标题+指纹归族**。
2. 每族挑一个实例打登录，先找**用户枚举形态**：本案 `POST :9521/api/login` 三态 —— `{"success":false,"message":"登录失败：密码错误"}` = 用户名**存在**；`"登录失败：用户名不存在"` = 不存在；`{"success":true,"message":"登录成功","token":"eyJ…"}` = 通。
3. 列出有效用户名（本案整族只有 `admin`），再试口令 —— 本案第 2 发 `admin:123456` 即通。
4. **★ 立刻把这组凭据在整个族 + 其余端口上横向重放。** 本案 8 个 ledger bot 一次破 5 个（8000/8001/9110/9507/9521），各实例的业务量就是战果表（9507 210 群 / 8001 充值 3643 万 / 9521 充值 **9.67 亿**、4485 条用户租约）。

## 命中判定：302 不是成功（本案最大的假阳性源）
服务端渲染型（Flask/Jinja）登录对**所有**失败登录都回 `302 → /login`。把 301/302/303 当成功 → 570 条假命中。

- `Location` 指向 `/login` 或带 `?next=` ⇒ **失败**
- 判定必须**带 session 再取一次受保护页**：

```python
def really_logged_in(s, base, login_path, form):
    pre = s.get(base + "/"); pre_len = len(pre.content)
    s.post(base + login_path, data=form, allow_redirects=True)
    post = s.get(base + "/")
    return len(post.content) != pre_len and "password" not in post.text[:3000].lower()
```

本案 16 端口 × 3 用户 × 12 口令 ≈ 570 次「命中」严格复核后为 **0**。

## 同名不同版本
同族实例常是同一代码的不同版本（13 接口版 vs 58 接口版），**凭据相同**；接口最多的那个是主目标，口径最全、数据最厚（也最值得先 dump）。

## 本案族谱（2026-09-29，143.14.49.16）
| 端口 | 系统 | 备注 |
|---|---|---|
| 8000/8001/9000/9110/9501/9505/9507/9521 | TG Ledger Bot 记账机器人 | 13 接口版 ×7 + **58 接口完整版 @9521**；`/docs`+`/openapi.json` 全暴露 |
| 8088/8091/8099 | 双向群管机器人 | 登录页用户名预填 `admin` |
| 14460/18000 · 18001/18100 · 14502 · 14454 · 14459 | 转发控制台 / 广播控制台 / 私信管理 / 内容中台 / 频道消息中心 | 8 套 `/openapi.json` 全暴露（9.5–45KB） |
| 8888 | E Strategy Platform 多角色策略托管 | 总后台/代理/客户端，托管客户 **Gate.io 交易所 API 密钥**；**开放注册** |
| 18090 | 钱包管理后台 | `/api/wallet-secret/treasury`，可配 `treasuryAddress`+`treasuryPrivateKey` |
| 8080/8083 · 9509/9530/14542 · 8765 · 9513/9518/16804 · 8081 | GuajiAdmin / Flask 后台登录 / BaseHTTP 后台 / .NET / TG监听系统 | 各自独立闸 |

## OpenAPI 与权限的关系
8 套 FastAPI 的 `/openapi.json` 全暴露，但 **spec 里没写 `security` 不等于无鉴权**：本案 62 个 `security` 缺省端点运行时一律 `401 请先登录`（全局中间件兜底）。spec 只用来拿**端点清单**（路径/方法/multipart 标记），权限一律回运行时实测。

## 会话票形态速查（同族常见）
`b64(json).b64(ts).b64sig`（27 字符签名 = SHA1-HMAC）⇒ 框架签名会话。
- 载荷形如 `{"_flashes":[{" t":["error","请先登录"]}]}` ⇒ **Flask**（`TaggedJSONSerializer` 把 tuple 编码成 `{" t":…}`），salt = `cookie-session`。
- 载荷只含 `{"csrf_token":"…"}` 且是 FastAPI 站 ⇒ Starlette `SessionMiddleware`，salt 走 `itsdangerous`。
- 先解载荷**认出框架与字段名**，再谈撞密钥；**把该框架的全部 salt 候选都放进主循环**（本案曾只在「小字典」阶段测过 `b"itsdangerous"`、rockyou 全量阶段漏掉它，等于白跑一轮）。
- 签名被严格校验时（改 payload / 空签名 / 2 段 / 4 段变形全 401）⇒ 记「密钥为强随机，伪造路径判死」，转去别面（静态目录穿越读 `.env`、其它实例的弱面）。
