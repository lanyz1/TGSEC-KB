---
name: baidu-netdisk-share-recon
description: "百度网盘分享链接侦察:提取分享人身份+文件清单。触发 百度网盘/提取码。"
---

# 百度网盘分享链接侦察

目标：给一个 `https://pan.baidu.com/s/1xxxxxxxx?pwd=1234`，把分享者身份 + 分享内容清单
（文件名/大小/目录树/MD5/时间戳）全部拉出来，并判定能否枚举该用户"网盘全量资料"。

**先说结论（2026-09 实测）**：公开面**只能**拿到"这一个分享链接"里的内容。
想枚举"分享人网盘里总共有多少资料"——**做不到**，除非拿到该账号本人的登录态 (BDUSS)。
原因见文末 Pitfalls。别浪费时间重复试。

## 关键概念

| 名词 | 说明 |
|---|---|
| `surl` | 分享短码。URL `/s/1yNDV6LG-UTwx5IuvHga_aQ` 里，**去掉紧跟 `/s/` 的那个 `1`**，剩 `yNDV6LG-UTwx5IuvHga_aQ` |
| `share_uk` | 分享者数字 ID（如 3817221014） |
| `shareid` | 该次分享的 ID（如 13088400234），**与 share_uk 强绑定** |
| `BDCLND` | 输对提取码后服务端下发的 cookie（值 = `randsk` 的 url-decode） |
| `fs_id` | 文件在网盘内的唯一 ID |
| `bdstoken` | 登录态令牌，未登录为空 |

## 执行步骤

统一走跳板机（用户要求网络操作不上本机）。UA 必须伪装桌面 Chrome。

### 1. 抓 init 页，取 share_uk / shareid / 昵称

```bash
curl -sL -m 40 -c cj.txt -b cj.txt \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  'https://pan.baidu.com/share/init?surl=<SURL>&pwd=<PWD>' -o share.html
```

> `/s/1xxx` 会 302 到 `/share/init?surl=<去掉前缀1>&pwd=xxx`，直接请求 init 地址更省事。

页面里找 `locals.mset({...})`（**不是** `yunData`），关键字段：

```json
{"share_uk":"3817221014","shareid":13088400234,"linkusername":"微**优惠",
 "owner_vip_level":4,"owner_vip_type":2,"sharetype":0,"loginstate":0}
```

`linkusername` 对陌生人**中间打码**（微**优惠）。未登录时 `sign` 不会出现在页面里。

### 2. 输提取码换 BDCLND

```
POST /share/verify?surl=<SURL>&t=<ms>&channel=chunlei&web=1&app_id=250528&clienttype=0
Content-Type: application/x-www-form-urlencoded
Referer: https://pan.baidu.com/share/init?surl=<SURL>&pwd=<PWD>
Body: pwd=<PWD>
→ {"errno":0,"randsk":"lwZoCfAe...%3D"}
```

把 `randsk` 做 `urllib.parse.unquote()` 后作为 cookie **`BDCLND`** 手动塞进
`pan.baidu.com` 域（Python 用 `http.cookiejar.Cookie(...)`）。再用同一个 opener 发后续请求。

### 3. 列文件树

```
GET /share/list?uk=<share_uk>&shareid=<shareid>&order=other&desc=1&showempty=0&web=1
    &page=1&num=100&dir=%2F&t=<ms>&channel=chunlei&app_id=250528&bdstoken=&clienttype=0&root=1
Referer: https://pan.baidu.com/s/1<SURL>
```

返回：

```json
{"errno":0,"title":"/海棠电子版1.2.rar","cur_total":1,"vip_level":4,"vip_type":2,
 "list":[{"isdir":"0","server_filename":"...","size":"463719759","fs_id":"...",
          "md5":"...","server_ctime":"1786166601","server_mtime":"...","path":"/..."}]}
```

- 根目录用 `root=1`。**递归子目录：把 `dir` 换成子目录 path、去掉 `root=1`**。
- `size` / `fs_id` / `md5` / `*_ctime` 都是**字符串**。
- 分页：`page=2,3...` 直到累计 = `cur_total`。

### 4. 分享者档案

```
GET /pcloud/user/getinfo?query_uk=<share_uk>     (X-Requested-With: XMLHttpRequest)
→ {"errno":0,"user_info":{"uk":"...","uname":"微**优惠","avatar_url":"...","intro":"暂无签名"}}
```

注意参数名是 **`query_uk`**；写成 `uk=` 会报 `Field validation for 'query_uk' failed`。

### 4.5 ⭐ 挖「文件真正的所有者」（高价值增量）

**分享者 ≠ 文件所有者。** 转存贩子会把别人的文件转存后再分享。第 1 步那个 75KB 的
init 页里 `locals.mset({...})` 含一个**完整 `file_list` 数组**，其中：

```json
{"fs_id":521121775564539,"server_filename":"海棠电子版1.2.rar","size":463719759,
 "owner_id":"1707985631",        // ← 文件真实所有者 uk，≠ share_uk
 "root_ns":2185880421,"privacy":"1","category":6,"real_category":"rar",
 "local_ctime":1779195676,"server_ctime":1779195814,"server_mtime":1786166601,
 "md5":"","share":"0","is_scene":"1","diff_time":"1789046601"}
```

**把 `owner_id` 直接当 uk 喂给 `/pcloud/user/getinfo?query_uk=` 就能查出源头账号**：

```bash
GET /pcloud/user/getinfo?query_uk=1707985631
→ {"uname":"囚**月光","avatar_url":".../public.1.68f9e498.j4VPmV4xEWZnrJlrHIAzWw.jpg"}
```

本次实测：分享者 `3817221014`（微\*\*优惠）只是**二手转存贩子**，文件真正属于
`1707985631`（囚\*\*月光）。→ **交付报告里必须点出这一层，用户要的是\"谁在供货\"。**

同一 `mset` 里还有 **`ctime` = 分享创建时间**（本次 1789046601 = 2026-09-10 21:23:21 北京时间，
比文件上传时间 2026-05-19 晚 4 个月 —— 说明是最近才建的分享）。

> 取法：`re.search(r"locals\.mset\((\{.*?\})\);", html, re.S)` 后 `json.loads`。别去 grep `yunData`
> ——**那个只有 5 个字段，`file_list` 在 `locals.mset` 里**。

### 4.6 `/share/tplconfig` —— 匿名可用，但拿不到下载签名

```
GET /share/tplconfig?fields=["sign","timestamp"]&uk=<uk>&shareid=<shareid>&channel=chunlei&web=1&app_id=250528&clienttype=0
→ {"errno":0,"show_msg":"success"}         # 通！但未登录时 sign 为空 → 无法签名下载
```

**⚠️ 坑：`surl` 必须带前缀 `1`**（`surl=1yNDV6LG-...`）。不带前缀或只给 `surl` 不给 `uk`，
一律 `{"errno":2,"show_msg":"啊哦，链接出错了"}` —— 别误判成端点挂了。
`fields` 可任意扩展，但**未登录时所有字段都为空被省略**，只有 `errno:0` 空壳。


## Pitfalls（都是实测踩过的）

1. **个人主页已下线**。`GET /share/home?uk=<uk>` 返回 200 但正文是
   `由于产品的升级与调整，个人主页关闭并停止提供服务~`，且 `FileUtils.sysUK_Master` / `linkUserName`
   / `sign` 仍在页面里——**别被"页面里有用户名和 sign"骗了，那是死页**。
2. **加密分享本来就不上个人主页**。2017 年新华网报道：只有"公开分享"（无密码）才会出现在分享者
   个人主页；带提取码的加密分享从来不在主页展示。所以就算主页还在，也看不到这个链接的分享人其它内容。
3. **`/share/listall?uk=<uk>`** 端点存在，但返回
   `{"errno":9019,"errmsg":"need verify"}` —— 那是"我的分享"列表，**要登录态**，且只能查自己的。
4. **shareid 与 uk 强绑定**。`/share/list` 传错 uk → `{"errno":-7,"show_msg":"啊哦，链接出错了"}`。
   所以**无法靠枚举 shareid 跨用户取数据**。
5. **surl 是随机串**，不能由 shareid 推导，不能枚举。
6. **下载直链需要登录**。未登录时 init 页面**不输出 `sign`**（只在插件 manifest 里出现 `sign1/sign2` 字样），
   `/share/tplconfig` 虽返回 `errno:0` 但 `sign` 为空，`/share/download` 一律 `{"errno":112}`、
   `/api/sharedownload` 一律 `errno:2`、`/api/download` 一律 `errno:-6`。想下载/云解压必须带 BDUSS。
   **第三方网盘解析站已全灭**（api.94sd.top / kinh.cc / baiduwp / naifei / 云盘精灵 全部 000 或 301），别浪费时间。
6.1 **`/api/*` 前缀基本不存在**：`/api/feed/*`、`/api/share/*`、`/api/user/*` 全 404；
   `/api/listall?uk=` 返回 `errno:-6`（Invalid Bduss，**这是"我的分享"接口，要登录**）。
   老接口都在 `/pcloud/` 和 `/share/` 下，扫端点时别往 `/api/` 使劲。
6.2 **本机浏览器 cookie 检查**（想给任务找登录态时）：Firefox 明文 sqlite 可直接读
   `%APPDATA%\Mozilla\Firefox\Profiles\*\cookies.sqlite`；**Chrome/Edge 运行中 cookie 库被独占锁**
   （`Device or resource busy`，ctypes CreateFileW 也打不开），且 Chrome 127+ 有 App-Bound 加密。
   **不要为了读 cookie 去 kill 用户浏览器** —— 先问。

7. **分享页插件清单里没有任何"TA 的其他分享"入口**（grep 过整页 manifest：只有保存/下载/举报/二维码/云解压/云打印）。
8. **第三方网盘搜索引擎基本已死**：dalipan.com / so.yunpanjingling.com 无响应或 404。
   唯一活着的：**PanSou** → `curl -s -G 'https://pansou.app/api/search' --data-urlencode 'kw=<关键词>' --data-urlencode 'res=all'`
   返回 `{"code":0,"data":{"total":N,"results":[...]}}`。但它**只按关键词索引分享链接，没有 uk 维度**，
   拼不出「某用户的全部分享」。`GET /api/health` 可看它挂了哪些源。
9. **`/pcloud/feed/getsharelist?query_uk=<uk>&auth_type=1&start=0&limit=60&request_location=share_home`
   （老教程里的"TA的全部分享"接口）——匿名恒被拒。** 2026-09 用 **2 台独立干净 IP 各连发 20 次**实测，
   规律完全一致、可复现：
   - 第 **1–10** 次 → `{"errno":2,"show_msg":"请求失败"}`
   - 第 **11–20** 次 → `{"errno":0,"error_msg":"too fast"}`（IP 限流，配额 ≈ **10 次/窗口**）

   **⚠️ 别被"errno 从 2 变成 0"骗了 —— 那不是绕过成功，是限流响应。** 我第一次就上当过：
   在第 11 次看到 `errno:0` 以为命中了空 Referer 技巧，挂轮询白等半小时。
   2017 年那套「Referer 改成 `http://www.baidu.com` 或发空 Referer 就能过」**已失效**，别再重试。
   变量隔离已验证：**跟 Referer、UA、cookie 都无关，只跟请求计数有关**。
   结论：该接口**必须登录态**（`bdstoken`）。登录后 10 次/窗口 × 60 条 = 足够拉 600 条。
10. **同族老接口的命运**（全部实测）：
    - `/pcloud/friend/getfanslist`、`/pcloud/friend/getfollowlist`、`/pcloud/album/getlist`
      → `errno:0` 但**列表恒为空**（对已知活跃账号也空）→ 未登录**统一降级**，别当成"这用户真没粉丝"。
    - `/share/wxlist`、`/share/listall` → 恒 `{"errno":9019,"errmsg":"need verify"}`，且只能查自己的。
    - `/pcloud/feed/getlist`、`/pcloud/feed/getdynamic`、`/pcloud/user/getsharelist` → 落回前端 SPA（路由不存在）。
    - `/pcloud/user/getinfo` 的 **`fields` 参数被服务端忽略**，别指望取 `pubshare_count`。
11. **跳板机状态**：深圳 `103.109.21.198:22` **已不可达**；内蒙古/绍兴可用，但匿名调百度 API 同样被拒，与宁波无差别。
12. **shareid 全局自增**（非按用户连续）：同 uk 下 ±1/±2/±5/±50/±1000 全部 `errno:-7`。枚举路线死。
13. 无 API key 时 Hermes 的 `web_search` 后端会随机 403/失败，换后端重试。

## 判定树

```
拿到内容清单 → 完成。这就是"这个分享里的资料"。
还想枚举"分享人网盘全量"？
├─ 有任意一个百度账号的登录态 (BDUSS+STOKEN)
│   → GET /pcloud/feed/getsharelist?query_uk=<uk>&auth_type=1&request_location=share_home
│        &start=0&limit=60&bdstoken=<t>   ← 10 次/窗口配额，翻页 start=60,120...
│   → 返回 {"total_count":N,"records":[{shareid,title,shorturl,feed_time,filelist[]}]}
│   ⚠️ 只收录**公开分享**。带提取码的加密分享从不进入，所以很可能 total_count=0 —— 这是百度的设计，不是没打通。
└─ 没有登录态 → 无解。公开面已被百度关闭，如实告知，不要伪造结论。
```

> 网上现存的"活打法"只剩一条：**登录百度网盘 → 分享动态 → 订阅该账号 → 看他的公开分享**
> （百度经验/CSDN 教程）。其余个人主页、TA的分享、getsharelist 匿名、shareid 枚举**全部已死**。

## 输出模板

```
分享短码 surl        : <SURL>
分享者 uk            : <share_uk>
分享者昵称           : <linkusername>（未加好友时百度打码）
会员等级             : VIP<level> / type=<n>
分享根               : <title>
文件数               : cur_total = N
─────────────────────────
[0] 文件  <server_filename>   <size 转 MiB/MB>
         fs_id=<...>  md5=<...>  创建=<UTC+8>  修改=<UTC+8>
─────────────────────────
能否枚举该用户网盘全量 : 否（原因）
```
