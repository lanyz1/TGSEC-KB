# 深链载荷 / 回调探测 · 可复制骨架

## 1. 载具矩阵(同一份载荷,三种吃法)
| 载具 | 形态 | 吃 |
|---|---|---|
| bot `/start` | `t.me/<bot>?start=<tag><payload>` | 只吃**带标签**;裸载荷静默忽略 |
| App Mini App | `t.me/<bot>/<short>?startapp=<payload>` | 只吃**裸载荷** |
| HTTP API | `GET ...?token=<payload>` | 只吃**裸载荷**;带标签 ⇒ 业务错误码 |

⇒ 从深链抠出的载荷**先剥标签再送 HTTP**。
角色:`rpl_`=分享/预览(零凭据可读名单)、`rpu_`=解锁(服务端查归属)、`startapp=`=App 内领取。

## 2. 载荷解码 + 自证
```python
import base64

def unb64u(s: str) -> bytes:
    """URL-safe base64。标准 b64decode 会静默丢弃 - 和 _ ⇒ 长度错 → Incorrect padding。"""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

raw = unb64u(token)
enc = base64.urlsafe_b64encode(raw).decode().rstrip("=")
print("LEN raw=%d enc=%d selfcheck=%s" % (len(raw), len(enc), enc == token))  # 必须 True
obj_id = int.from_bytes(raw[:8], "big")        # 大端 u64;前导 00 是补零不是魔数
print("object_id=%d mac_tail=%s" % (obj_id, raw[8:].hex()))
```
- 尾部 MAC 硬:换尾 / 相邻 id / 全 0 尾全拒 ⇒ 不可伪造、不可枚举。
- 熵:18 字节样本字节熵上限 **4.17**,别拿「≈8.0 才叫随机」当尺子(这是错的)。

## 3. callback 探测:探什么、怎么判
```python
WL = {"menu_home", "menu_gamecenter", "gbh_list:1:all"}   # ★ 白名单:只放导航/只读 data

async def home(cli):                       # ★ 优先点键盘自带「返回/主菜单」(零洪泛成本)
    m = (await cli.get_messages(BOT_INT_ID, limit=1))[0]
    for row in m.buttons or []:
        for b in row:
            if (getattr(b, "data", None) or b"").decode() in ("menu_home", "back"):
                return await b.click()
    await cli.send_message(BOT_INT_ID, "/start")   # 无回家按钮才重发 /start(计入洪泛预算)
    return (await cli.get_messages(BOT_INT_ID, limit=1))[0]

# 改造 data 探 IDOR
r = await cli(GetBotCallbackAnswerRequest(peer=BOT_INT_ID, msg_id=mid, data=b"gbh_list:<val>:all"))
```
- 白名单外的 data 一律不点;**永不 tap**(tap 才是资金动作)。
- 改造 data ⇒ `DataInvalidError` = **通道级**拒绝(不是业务拒绝);★ 字面常量能过而本人 id 不过 ⇒ 该段是**固定常量,此处无 IDOR**。
- ★★★ **先查入口,它是首位成因**:取值/点击**只用 `msg.buttons`(MessageButton)**;`msg.reply_markup.rows[].buttons[]` 在 Telethon 1.45 上读不到可点 data(类名 `KeyboardInlineButton`/`InlineButtonTypeCallback`) ⇒ 拿它手搓请求只会得到同样的 `DataInvalidError`。其余成因按序:② 消息被点过后原地改写(旧 data 失效,重导航即好)③ 页上下文不对 ④ 参数真无效。
- ★★ 平台级校验的成因 = **data 必须与该条消息键盘逐字节一致** ⇒ 参数不可伪造、不可枚举,但**不得记成目标的防护能力**,也不能反向证明应用层有授权校验。
- 每步先复位(否则子页里主菜单项缺失 ⇒ 后续面被**静默跳过**,误报「不存在」)。
- 节奏 ≥8-11s/发;bot 冷却后升级为**只答 `/start`、永久忽略菜单文本**。
- bot 侧一律用 **int id**(`@username` 走 `ResolveUsername`,最先被 FloodWait 冻结)。

## 4. HTTP 路由存在性 oracle(双向)
```
已知存在路由(匿名) ⇒ 401/业务错误码          阳性对照(不跑 = 不可判定)
已知不存在基线 /ping ⇒ 404 "404 page not found"(Go 文案)   阴性对照
bot callback 前缀(rp_/sw_/yb_/vas_/pf_/sc_/gbh_/mrch_/bp_)≠ HTTP 路由:实测 52/52 全 404
```

## 5. 只读结构保证(写探测脚本时的硬约束)
- 模板里**根本不实现** `open`/`claim`/任何 POST 资金端点 ⇒ 结构上不可能动钱(比「记得别调」可靠)。
- 导航脚本用**硬编码白名单**;渲染只做 `send_message` + `get_messages` + 读 `msg.buttons`(MessageButton)的 `.data`;`inline_query`(纯查询)可留,但**严禁 `InlineResult.click()`**(发送语义,会把卡片投进会话)。
- 资金类端点即使有明确授权也要**单发、串行、先读后写**,并在报告里标出「已动/未动」。
- 定稿前自审:把钱操作全列一遍,确认脚本中不存在到它们的调用路径。

## 6. 取「活 token」+ 换身份铸票(全只读)
```python
# 6a. switch-inline 按钮直接泄出活载荷 —— 无需铸票、无需监听频道
for row in (await cli.get_messages(BOT_INT_ID, limit=1))[0].buttons or []:
    for b in row:
        if getattr(b.button, "type", None) == "InlineButtonTypeSwitchInline":
            tok = b.button.query          # ★ 这就是该对象的分发 token(实测 rp_ + 24 字符 base64url)
            res = await cli.inline_query(BOT_INT_ID, tok)   # 纯查询;★ 永不调 res[i].click()

# 6b. 换身份铸票(要用另一个自有账号领取/取样时)
#     cp acc.session acc_probe.session(连 .session-journal 一起拷)再铸;
#     同一账号连铸:首个 platform 会挂到超时(实测 45s,别当网络故障)⇒ 依次换 android → ios → tdesktop
r = await cli(functions.messages.RequestAppWebViewRequest(
        peer=await cli.get_input_entity(BOT_INT_ID),          # ★ int id,不用 @username
        app=types.InputBotAppShortName(bot_id=peer, short_name="<真实短名>"),
        platform="ios", start_param="<裸载荷>"))                # start_param 必须 = 目标对象的活 token
init = parse_qs(r.url.split("#", 1)[1])["tgWebAppData"][0]     # fragment 是 query string,不是 initData 本体
```
- 活 token 的正当来路(按性价比):① switch-inline `.query`(最快) ② 只读监听官方频道/群新推送 ③ 自有对象自建。**枚举他人 token = 第三方资金红线,不做**。
- `start_param` 填活 token 才会把会话与该对象绑定;platform 竞态同时是**无上限续期**手段。
