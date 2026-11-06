# bot DM 侧侦察原语(Telethon,第三方 bot 只读)

前提:bot 侧一律用 **int id**(`BOT = 7171312223`),绝不用 `@username`(走 ResolveUsername,最先被 FloodWait 冻结)。

## 1. 真回应判定(id 水位线 + 正控)
「读最新一条 incoming」会把上一轮的旧答复当成本轮回应 ⇒ 假阳性。正确写法:

```python
async def watermark(cli, peer):
    """发之前的 incoming 水位线"""
    ms = await cli.get_messages(peer, limit=20)
    return max([m.id for m in ms if not m.out], default=0)

async def wait_new(cli, peer, mark, wait=5.0):
    """发之后:只认 id > mark 的新 incoming,轮询到超时"""
    loop = asyncio.get_event_loop()
    end = loop.time() + wait
    while True:
        for m in await cli.get_messages(peer, limit=10):
            if not m.out and m.id > mark:
                return m
        if loop.time() > end:
            return None                     # 真·无回应
        await asyncio.sleep(0.8)

async def probe(cli, peer, text):
    mark = await watermark(cli, peer)
    await cli.send_message(peer, text)
    return await wait_new(cli, peer, mark)
```
- **每轮带正控**:`PROBE "/start"` 与 `"/help"` 必须返回非 None,否则整轮「无 handler」结论作废(报告里写「不可判定」)。
- 判定「命令不存在」= 水位线之后**确实没有任何新 incoming**;不是「文本看起来像我发的那句」(自发消息 `m.out == True` 必须排除)。
- 洪泛预算:≥8-11s/发;一次会话里命令列表控制在十几条以内,别把探测做成爆破。

## 2. 原始结构取证(封装层会骗你)
```python
def dump_markup(m):
    rm = getattr(m, "reply_markup", None)
    return json.dumps(rm.to_dict(), ensure_ascii=False, default=str) if rm else ""
```
Telethon 封装层的坑与真身对照:

| 你看到的 | 真身 | 处理 |
|---|---|---|
| `b.url is None and b.data is None` | **不是坏按钮** | 必须看原始 `to_dict()` |
| `InlineButtonTypeUserProfile{user_id}` | 用户名片按钮(点开=某人主页) | ⇒ 直接拿到**运营方管理员 user_id** |
| `InlineButtonUrl{url}` | 外链(官频/文档) | 记 URL |
| `InlineButtonCallback{data}` | 回调(白名单内才点) | 只读导航才 tap |
| `InlineButtonTypeWebView` / `UrlAuth` | WebApp / login_url | 常指向**面板类入口**,优先追 |

- 顺带 dump `media` 类型(首页常是 `MessageMediaPhoto`,文案在图里时 `text` 会为空)。

## 3. 声明式面先拿(合法、零成本)
```python
fu = await cli(GetFullUserRequest(bot_entity))
bi = fu.full_user.bot_info
print([(c.command, c.description) for c in (bi.commands or [])], bi.menu_button)
print(fu.full_user.about)          # bio 常含关联实体 @xxx(开发者群/商户侧/个人号)—— 高价值线索
```
⇒ 先拿到命令表,**再**按表逐条探;未声明命令(admin/mch/merchant/staff/panel/…)全部无 handler,才配写「无隐藏管理命令」。
★ bot UI 里 `👨‍💼 联系管理员` 这类按钮,文案 + 名片按钮就是运营方支持账号;`/help`、`/support` 常回同一条「👇 + 名片」。

## 4. 实体解析与 FloodWait 经济
```python
ent = await cli.get_input_entity(int_id)     # 缓存命中即零成本(对话里见过它就行)
ent = await cli.get_entity(int_id)           # 同上;失败=无缓存,不代表对象不存在
# 绝不主动 ResolveUsername 去「刷新」一个已经在缓存里的实体
```
- **一次解析 = 小时级 FloodWait**:脚本每个解析点都这样包:
```python
try:
    ent = await cli.get_entity(name)
except FloodWaitError as e:
    print("FloodWait %s 秒 ⇒ 立即停止(不烧额度)" % e.seconds); return
```
- **一撞罚就整体 `return`**,不要 for 循环里继续试下一个名字。
- `InputUser(id, access_hash=0)` 直构 ⇒ `UserIdInvalidError`,别浪费轮次。
- 解封后要追的目标:挂**一次性系统计划任务**(`:10` 三档错开),入口 `.bat` = `cd` 工作区 + `set` 代理/session env + `python -u <探针>.py >> <log> 2>&1`;Windows 中文区域下 `/SD` 要用 `dd/mm/yyyy`,否则报「无效开始日期」。任务跑完记得 `/Delete /TN … /F` 收尾。
- 会话/默认路径:`cli.iter_dialogs(limit=400)` 才够找到既有的自建群(`limit=30` 会假阴性);找不到就换**建它的那个 session**(见 SKILL §4.5 资产归属)。

## 5. 微信/Telegram 侧足迹
建的群、加进去的 bot、提的权都要**逐条列出来**,并在报告里给出可逆命令(`InviteToChannelRequest` 的反面 = 踢出;`DeleteChannelRequest` 删群)。改群状态前先问用户。
