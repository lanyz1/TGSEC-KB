# 归属采证配方(可直接复制的命令)

## 1. TG 侧:只读取运营方身份

```python
# Telethon;走本机代理或已就绪的出口;仅只读 API
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsAdmins

u  = await cli.get_entity("<运营方账号>")            # 客服号 / 公告落款 / 业务办理号
fu = await cli(GetFullUserRequest(u))
print(fu.full_user.about)                            # ★ bio = 产品目录,最有价值的一行

for ch in ("<产品频道1>", "<产品频道2>"):
    c  = await cli.get_entity(ch)
    fc = await cli(GetFullChannelRequest(c))
    print(ch, fc.full_chat.about)
    ps = await cli(GetParticipantsRequest(c, ChannelParticipantsAdmins(), 0, 100, hash=0))
    print([(x.id, getattr(x, "username", None)) for x in ps.users])   # 管理员 = 运营方多账号
```

纪律:这三类请求之外一律不做 —— 不发消息、不加入、不建群、不点按钮。

## 2. 免登录读频道帖(无 API/无会话时的兜底)

```bash
curl -s -A 'Mozilla/5.0' 'https://t.me/s/<channel>' -o ch.html
```
- 只读**最近帖子**;要翻旧帖用本地已有 dump(`*_posts.txt` / `shop*.log` / 已抓的 `tg/` 目录)优先。
- 帖文里重点搜:`github.com` / `http` / `@` 联系人 / `演示` / `开源` / `仓库`。

## 3. NS 对 = CF 账号指纹

```bash
for d in <目标域> <候选域1> <候选域2>; do
  printf '%s\t' "$d"
  dig +short NS "$d" @1.1.1.1 | sort | tr '\n' ' '
  echo
done
```
- **逐字符**比对,不要只比品牌(`*.ns.cloudflare.com` 人人都有,昵称前缀才是账号标识)。
- 一致 = 同一 CF 账号 = 同一主体(可并案);不同 = 不可据此并案。

## 4. 证书两层:边缘证书 vs 源站证书

```bash
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null \
  | openssl x509 -noout -issuer -subject -dates
```
| issuer | 判读 |
|---|---|
| Google Trust Services / Cloudflare Inc ECC CA | CF Universal SSL 边缘证书 ⇒ 无源站信息 |
| TrustAsia LiteSSL RSA CA(年份) | 源站自持证书,国内云免费证书系 ⇒ 源站大概率在国内云 |
| DigiCert / Let's Encrypt(非 CF 边缘) | 源站自持证书,按该云特征面继续找 |
| 证书 SAN 出现兄弟子域 | 直接扩充子域清单 |

## 5. 子域与标题枚举(只读)

```bash
for s in $SUBS; do ip=$(dig +short A "$s.<域>" @1.1.1.1 | head -2 | tr '\n' ','); \
  [ -n "$ip" ] && echo "$s.<域> -> $ip"; done            # 每项一行,只打印有解析的
```
```bash
# 标题采证:命中的域逐个看 title + 服务头(管理端常直接写在 title 里)
curl -s -k -m 15 -D /tmp/h.txt -o /tmp/b.txt "https://<域>/" \
  && { grep -iE '^(server|cf-ray|x-powered-by)' /tmp/h.txt; grep -oiE '<title>[^<]*' /tmp/b.txt | head -1; }
```
- 管理端候选词表:`admin|manage|console|ops|crm|monitor|dashboard|panel|care|boss|agent`。
- **站群里的诱饵页同样回 200** ⇒ 判断入口看**标题/前端 bundle/登录路由**,不看状态码。

## 6. 命中管理端后只读看契约

```bash
curl -s -k -m 15 "https://<域>/" | grep -oE 'src="[^"]+\.js"' | head            # 找入口 chunk
# 拉 chunk 后只提契约,不做任何提交:
grep -oaE '"/(api|admin|v1)[a-zA-Z0-9_/-]*"' chunk.js | sort -u | head -60
grep -oaE '(baseURL|baseUrl)[^,;]{0,80}' chunk.js | head -10
```
- 不要在该域名族上做登录爆破:自建反扫描欺骗层(假登录页 + `/gotcha.html` 类 whoami 采集真实 IP/UA/时区)
  是这类运营方的标配,提交即被记录。

## 7. 归属证据表(报告里就照这个列)

| 候选域 | NS 对 | 证书 issuer | 标题/服务头 | 归属证据 | 结论 |
|---|---|---|---|---|---|
| <目标域> | brett/lila.ns.cloudflare.com | CF 边缘 | — | 基线 | 目标本体 |
| <候选域A> | brett/lila.ns.cloudflare.com | TrustAsia | `<brand>-Admin` | NS 对一致 + 品牌 token | **同一运营方**,管理端候选 |
| <候选域B> | boyd/meadow.ns.cloudflare.com | CF 边缘 | 未知 | 无 | 暂不并案(仅同主题材) |

写报告时:每行**证据列必须可复现**(给出命令或查询串),「结论」列不写「疑似」除非标注缺哪条证据。
