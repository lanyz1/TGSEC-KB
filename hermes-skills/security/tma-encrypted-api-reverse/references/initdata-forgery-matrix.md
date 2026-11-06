# initData 伪造/篡改矩阵 —— 判“能不能冒用别人的身份”

用户问“能不能伪造别人的 TG 身份”时，**不要用架构常识答，跑矩阵出硬证**。核心事实：`initData` 由 Telegram 用 **bot token 派生密钥**签名，所以问题等价于两问：①**token 有没有泄露** ②**服务端有没有真验签**。两问分别取证。

## 签名规格（写报告要引）

```
data_check_string = 按 key 排序的 "k=v" 用 \n 连接（排除 hash）
secret_key        = HMAC_SHA256(key=b"WebAppData", msg=<bot_token>)
hash              = HMAC_SHA256(key=secret_key, msg=data_check_string).hexdigest()
signature         = Ed25519（Bot API 7.x，第三方用 bot 公钥验）
```

爆点类的实现缺陷（矩阵要逐个对应）：① 不验签 ② 错用密钥（拿 token 当 key，没做 `WebAppData` 派生）③ 不查 `auth_date` ④ 不查一次性 ⑤ 身份取自未签名通道（query/body/`start_param`）。

## 铸真票（Telethon，一次即可）

```python
app = types.InputBotAppShortName(bot_id=types.InputUser(ent.id, ent.access_hash), short_name="<short_name>")
r = await c(functions.messages.RequestAppWebViewRequest(
    peer=ent, app=app, platform="android", write_allowed=True, start_param="A"*24))
raw = urllib.parse.parse_qs(r.url.split("#", 1)[1])["tgWebAppData"][0]
```
关键：`start_param` **内容 Telegram 不校验**，随便填 24 字符也能铸 ⇒ 所以 `start_param` **不是身份字段**，别把它当“可伪造身份”的证据。

## 矩阵（同一脚本、同一出口、紧邻时刻，串行 0.4s）

| # | 形态 | 期望 |
|---|---|---|
| N0 | 不带头（负控）| 401 |
| V1 | 篡改 `user.id` 为他人，**保留原 hash** | 401 ⇒ 证明真验签 |
| V2 | 删 `hash` | 401 |
| V3 | `hash` 全 0 | 401 |
| V4 | 追加未签名字段 | 401 |
| V5 | `auth_date` 移出窗口（-100000s）| 401 ⇒ 证明查 TTL |
| **V6** | 篡改 `user.id` + **按官方算法用随机密钥重算 hash**（无 token 伪造者的能力上限）| 401 ⇒ **主要结论** |
| V7 | 用 `bot_id:WRONGTOKEN` 派生密钥签名 | 401 |
| **P0** | **原样正控** | **200 + session_id** ⇒ 排除假阴性 |
| **P1** | 同一 initData 立即重放 | `40704` ⇒ 一次性成立 |

打分端点用 `POST /api/miniapp/v1/handshake`（体 `{"client_pub": b64(32B X25519), "curve":"x25519"}`，头 `X-Telegram-Init-Data`）—— 它最轻、不需会话，失败形态统一是 `401 / 63B / 40701`。

## 纪律与坑

- **正控必须在同一脚本内紧接跑**：否则 8 个 401 可能全是环境问题。P0 拿到 200 后判决才成立。
- **initData 一次性** ⇒ 篡改形态**先**发、正控**最后**发（无效请求不消耗真票的假设要被结果验证，P0 返回 200 即验证成立）。
- **要留日志**：`python -u x.py 2>&1 | tee x.out`。第一次跑忘了 tee 就得**重跑**——重跑正好当第二独立运行（换新 `session_id` ⇒ 证明是新铸票，不是缓存回放）。
- `requests.Session().trust_env = False` 避免系统代理扰动；Telethon 侧显式 `proxy=(...)`。
- **token 泄露核查要分开写**：线上 bundle、上游/供应商仓、本地语料三处分别搜 `[0-9]{8,11}:[A-Za-z0-9_-]{33,40}`。**命中不等于目标**：先核 `bot_id` 是否等于目标的 bot_id，不是就归为第三方资产（不取用、写入报告）——本目标三处命中均为他人机器人。
- 结论措辞纪律：**“不能伪造” ≠ “不能冒用”**。伪造需 token；冒用只需**取得**凭据（会话文件 / 900s 内一次性 initData）。会话窃取是现实路径，且若资金动作无 PIN 闸门则“会话即身份即资金” ⇒ 两个缺陷要合写。
