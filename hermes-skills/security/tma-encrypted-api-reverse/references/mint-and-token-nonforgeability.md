# 铸票 / initData 注入 / token 不可伪造性 —— 可直接复用的检查清单

## 1. 铸票（按需现铸 initData）
```python
from telethon import functions, types
r = await cl(functions.messages.RequestAppWebViewRequest(
        peer=await cl.get_input_entity(BOT_INT_ID),          # ★ 用 int id，别用 @username
        app=types.InputBotAppShortName(bot_id=peer, short_name="<真实短名>"),  # 别名 ⇒ BOT_APP_INVALID
        platform="android", start_param="<载荷>"))             # 变 platform/start_param 可无限续期
from urllib.parse import parse_qs
init = parse_qs(r.url.split("#", 1)[1])["tgWebAppData"][0]     # ★★ 关键：fragment 是 query string
meta = dict((k, v[0]) for k, v in parse_qs(init).items())       # auth_date/user/hash/start_param
```
- **自检 1**：`len(init)` ≈ 600–900、`meta` 有 `auth_date`/`user`/`hash`/`query_id`。
- **自检 2**：注入必须是**单层 URL 编码**形态；**绝不用 `sed`**（`&` 会展开），用 Python 生成 run 脚本 + `content.count(init)==1` 逐字回验。
- **自检 3**：initData **一次性**（同张重复握手 ⇒ `40704`）⇒ 铸币与握手**同进程一气呵成**，龄 <30s。

## 2. 鉴权阶梯 oracle（判别式）
| 送什么 | 期望码 | 说明 |
|---|---|---|
| 无 initData | `40701 登录状态无效` | 凭据缺失 |
| 陈旧 initData（>~2.8h） | `40702 登录状态已过期` | ★ 签名已过，仅新鲜度不过 |
| 现铸 + 空体 handshake | `40710 安全信道未建立` | ★★ **凭据已过，只差 ECDH 会话** |
| 现铸 + `{client_pub,curve:"x25519"}` | `200` + `session_id` | 会话建立（TTL 900s） |
| 同张再握 | `40704 请求已失效` | initData 已被消费 |
| 伪造 token | `40671 解锁链接无效` | 业务层（排在 body 校验前） |
| 乱造路径 | `404 page not found`（18B） | Go 原生 = 路径不存在 |

**看到 `40710` 就说明凭据链没问题**，别再去换号/爆破/换面，回去查 POST 体加密与签名串。

## 3. token 不可伪造性 —— 变异矩阵（只读，10 步）
1. `GET /rp/detail?token=<裸载荷>` 对照 ⇒ 200 + `packet_id`；
2. `b64decode` 出字节，`hex` 打印，**与响应 packet_id 对账**（实测 `6×00 ‖ uint16 BE pid ‖ 10B 随机`）；
3. 变异：id 首字节 ±1/±2/±3 · 尾部字节翻转 · id 段反转 · `struct.pack('>Q', pid∈{0,1,2,100,真实,真实±1}) + 零尾` · `'<Q' + 真尾`；
4. **判定**：任一变异出 200 / 换出别的 packet_id ⇒ **可伪造（IDOR）**；全 `40671` ⇒ **不可伪造**（负控通过，收面）；
5. 交叉对照：`GET /media/bg?token=<真>` ⇒ 200 真图（实测 115,618B JPEG）· `<改过>` ⇒ `404/0`；
6. 用 `struct`/`base64` 拼装时**先 base58check/长度自证**，别把「形似」的串当合法载荷（假地址/假 token 陷阱）。

## 4. 纪律
- 只读（GET/OPTIONS + handshake）；`claim`/`open` 等写入面留到有明确资金授权；
- **枚举他人 token 抢红包 = 第三方资金红线，一律不做**；正路 = 只读监听官方频道新推送捞新鲜 token；
- 每轮探测**重铸一次** initData，绝不缓存复用。
