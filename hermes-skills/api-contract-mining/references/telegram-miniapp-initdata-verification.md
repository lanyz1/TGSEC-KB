# Telegram Mini App initData 签名校验测试矩阵

用途：判定目标服务的 initData 校验是否**实现正确**，以及能承受哪些伪装。全流程只读、零副作用。

## 算法基线（服务端应当如此实现）
- `data_check_string` = 除 `hash` 外全部字段，按 key 排序，`k=v` 用 `\n` 连接
- `secret_key` = `HMAC_SHA256(key="WebAppData", msg=bot_token)`
- `hash` = `HMAC_SHA256(key=secret_key, msg=data_check_string)` 的 hex
- 携带方式：`Authorization: tma <initData>` 或自定义头（`X-Init-Data` / `X-Telegram-Init-Data` 等）—— **哪种被承认必须实测**（用「不带头」的报错文案做对照）

## 测试矩阵
| # | 变体 | 期望（实现正确时） | 说明 |
|---|---|---|---|
| 1 | `hash` 改全 0 / 随机 hex | 401 | 基线：签名必须生效 |
| 2 | 删掉 `hash` | 401 | 不能因缺字段就放行 |
| 3 | 改 `signature` | 401 | 该字段同样被 HMAC 覆盖 |
| 4 | 改 `user` 里的 `id` / `username` | 401 | 身份字段不可篡改 |
| 5 | 改 `query_id` | 401 | 任何字段都不可改 |
| 6 | **追加**未签名新字段（`&user_id=1&is_admin=1&role=admin`） | 401 | 正确实现会把新字段一并算进 HMAC |
| 7 | **追加重复键**（`&user=<others>`） | 200 且身份不变 | Go `url.Values.Get()` **取首值** → 重复键塌缩，不可利用（PHP/Python 的 last-wins 才可能出问题） |
| 8 | **打乱参数顺序** | 200 | 服务端自行排序校验 → 实现正确 |
| 9 | 身份头注入（`X-User-Id`、`X-Telegram-User-Id`、`Telegram-User-Id`、`X-Remote-User`、`X-Auth-Request-User` …） | 零效果 | 只认签名里的身份 |
| 10 | 完全不带 initData 头 | 固定报错串（如 `missing auth`） | 用该文案确认「哪个头才被承认」 |
| 11 | 同一枚 initData 重放（20m / 45m / 70m / 2h / 6h 检查点） | 见下 | 判定是否校验 `auth_date` 新鲜度 |

（家族形态补充：该后端把 initData 当**登录载荷**而非请求头 —— `initData: btoa(raw)` 走加密信封里的 `login`/`web_login` 方法。判定「校验是否正确」仍用上表矩阵，只是注入点换成 body 字段。）

## TTL / 重放设计
- 用**同一枚** initData 在长时段检查点重放，**不要**每轮重新签发（否则测不到 TTL）
- 探针必须 `python3 -u` 后台跑并逐行 flush，否则整段缓冲，中间结论看不到
- 若长时段仍通过 → `auth_date` 未校验或窗口极宽 → 高价值结论（令牌长期可用）

## 取真 initData（服务端只认「那个 bot」签发的）
- 登录失败的第一嫌疑不是签名算错，而是**来源 bot 不对**：白标家族同一后端挂多个 bot（`@tmqb` 纯命令式、`@TiMiPGBot` 挂 Mini App），initData 必须由**后端认的那个 bot 的 Mini App** 产出。
- SPA 侧先确认取法：`initData: btoa(window.Telegram.WebApp.initData)` —— **要 base64**，并核对有无 `login_source` 之类额外字段。
- Telethon 取真链：`RequestAppWebView`（`app=InputBotAppShortName(bot_id, <short_name>)`，如 `"home"`/`"withdraw"`）→ 返回的 `url` 形如 `https://<host>/#tgWebAppData=<urlencoded initData>`，**自带新鲜 initData**，直接解析 `#` 后片段使用。纯命令式 bot 回 `BOT_APP_INVALID` ⇒ 该 bot 没有 Mini App，别在它身上耗时间。
- 取到的是**时效性凭据**（`auth_date`）：拿到即用，不缓存、不落报告。

## 编码坑（实测踩过）
- 变体串里的 `user` 字段含**中文昵称**时，用 latin-1 写 header 会抛异常并**打断整批测试** → 一律 `urllib.parse.quote(..., safe="")` 构造，或整体 `encode("utf-8")`
- `hash` 是 hex 串比较：保持 64 位长度，长度不对会走进「参数格式」分支而不是「签名无效」分支，结论会被带偏

## 结论表述纪律
- 送空串/缺字段得到的 `请输入 6 位动态验证码` 是**输入校验分支**，**不能**用来断言「服务端不校验验证码」
- 只有拿到**有效密钥**并带真实码测试后，才可对「enable 阶段是否校验」下结论；否则写「未验证」
- 若出现「已绑定，禁止重绑」类返回 → 这是**账户可用性缺陷**（用户自锁且无解绑路径），属高危资金可用性问题，别当普通报错略过；顺手核对管理端有无**用户级**重置 MFA 的路由（往往只有「管理员自己」的 reset-mfa）
