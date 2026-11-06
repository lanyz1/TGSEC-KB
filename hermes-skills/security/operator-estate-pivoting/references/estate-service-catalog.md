# Estate Service Catalog —— 一个「TG号商/灰产集团」的标准布局

这灰产运营者的资产簇结构高度同质。拿到任一组件就能推其余组件的存在与入口。**每个组件都建一个目标，逐个做限流/鉴权判定**。

| 组件 | 典型实现 | 探测入口 | 鉴权/限流指纹 |
|------|----------|----------|----------------|
| 记账机器人后台 | FastAPI + uvicorn，`<title>TG Bookkeeping Bot Admin</title>` | `GET /login`；`POST /login` form-urlencoded | cookie `admin_auth`；`401 「后台访问令牌无效。」`（body 长度恒定 = 验签先于路由）；`/public/groups/{id}/bill?expires=&sig=` 无鉴权但验签 |
| 同上，卖克产品/代理商版 | 页面导航「机器人实例 / 授权用户 / 群后台」；`/admin/instances`、`/admin/users` | `/openapi.json` | 有 `clone_contact`/`instances`/`owner_tg_user_id`/`feature_flags_json` 字段即代理商后台；**管理员只挂 TG id，新增接口 body 无 password 字段** → 无默认口令可撞，转 `references/vendor-product-identification.md` |
| 发卡/商城 | 独角数卡 Dujiao-Next（Gin + JWT HS256 + Casbin） | `/admin` 登录；`/api/v1/admin/login`；公开面翻到**商品详情**（`/api/v1/public/products/{slug}`，列表常不带正文）——服务类商品的正文会写明运营者集团身份/服务清单，源码类商品爱带演示站与口令 | 签名含 `token_version`；限流按 IP，5 次/300s 封 900s；**先算熵再决定碰不碰兑换码**：礼品卡码为 `<前缀><YYMMDDHHMMSS><序号4位><10位随机hex>` ≈ 40 位 crypto/rand → 码爆破不可行 |
| 支付网关 | BEpusdt（Go） | `/api/v1/pay/info`、`/pay/update-order`、`/pay/notify`、`submit.php` | 下单/回调面，先看回调验不验签 |
| TG Mini App（红包/转盘/抽奖） | Vue3 SPA + `telegram-web-app.js`，`/api/v1/miniapp/*` | 请求头 `X-Telegram-Init-Data`；常另带独立 `/admin` 后台 | initData 错误码 `missing_init_data_or_bot_token` / `missing_hash` / `invalid_hash`；后台口令登录**按用户名分桶**限流 |
| 便签/OA | Next.js App Router | `/_next/static/chunks/*.js` 里扒 `/api/*` | nginx `limit_req` + 应用层**双限流**，应用层会递进到 1000s+ |
| 网络控制面 | FastAPI WireGuard 管理 API | `/login`、`/refresh`、`/devices` | JWT（token + refresh_token），适合差分预言机；未配置时 `/devices` 可能无鉴权（见到就立刻遍历 `/api/v1/devices/register`） |
| 群发/云控 | 见 `pentest-execution/references/platform-attack-chains.md` | `/openapi.json` | Worker 节点常 `admin:admin` + form-data |
| 开发机 | Windows：RDP 3389 + WinRM 5985 + 高位端口 | `code.<domain>` 这类命名的子域 | 凭据面；扫完常见面确认无 SMB/MSSQL 就不要在那里耗——裸 Win 主机不是弱点本身 |
| 跳板/出口 | SSH 高位端口 | — | 被封判据是连接重置，不是 `Permission denied` |

同一 IP 的非标端口常挂**另一套面板或纯静态资源服务**（如 Go 服务目录列举、`Vazirmatn` 波斯字体 = 另一品牌/运营者的前端资源）。它能坐实「同一主机多租户」，也可以当路径穿越/源码泄露的试点，但**别把它当成主目标的战果**上报。

## 从 API 契约里挖运营者身份

`/openapi.json` 不只是端点清单：`components.schemas` 里字段的**默认值/示例值常写死真实值**（默认联系 TG 号、默认品牌、默认域名）。一行把全部默认值抽出来：

```bash
curl -s https://<host>/openapi.json | python3 -c "
import sys,json; d=json.load(sys.stdin)
for n,s in d.get('components',{}).get('schemas',{}).items():
    for f,v in (s.get('properties') or {}).items():
        if isinstance(v,dict) and v.get('default') not in (None,''):
            print(n,f,'=',v['default'])"
```

子断言：`Body_<func>_<path>_post` 这类 schema 名带内部函数名，可反推未列出的端点，也是「同款产品」的硬证据。返回体长度恒定（如 401 恒 40 字节）说明验签/鉴权在路由之前，不要指望靠报文差异做枚举。

## 报错指纹的用法

同一位开发者写出的多个后台，**报错文案和字段名几乎一模一样**。抽到一次 JWT 伪造的差分响应、一次限流文案，就拿去在其余面板上复用判断，能省掉大量重复爆破：

- 「签名无效 / 令牌无效」= 校验在路由之前（先修 token 再谈路由）。
- 「校验码/字段缺失」与「值不对」是两档：能区分就说明校验确实存在，用它确认绕过是否真的失败，而不是「看着不像」。
- 面板返回 `303 跳 /login?error=`（而不是 401 页面）时，**登录失败与未认证后台是两条不同分支**：前者说明 username/password 处理完了，后者说明 cookie 中间件先拦；分别测。
- 登录失败文案对所有用户名统一（例：`账号或密码错误`）且存在 dummy-hash 恒定时延时 = 无用户名枚举，别再花时间在这上面。
- 非常规输入能拿到 500 说明参数进了 DB 层（如非 ASCII cookie、越界整数）；**但 500 体纯文本无栈** 是常态，别把它当成能升级的洞。

## 克隆实例比对表

判「同款产品」时逐项对齐，三项全中即可视为同一份镜像：

| 证据 | 怎么拿 | 说明 |
|------|--------|------|
| 登录页字节数 | `curl -s \| wc -c` | 模板未改过的直接相等（例：13846） |
| `/health` 体 | `curl -s /health` | 同一个 handler 的固定返回 |
| `/openapi.json` | path 集合 + `components.schemas` 名 | FastAPI 自动生成，含内部函数名（如 `Body_<func>_<path>_post`），能反推未在 path 里列出的端点并证明同源 |
| 边界响应码 | 越界 ID（`gid=-2147483649`、`id=0`）的返回码 | 同一份代码不同**数据/版本**只在这里看得出（如本类案例一边是 404「群不存在」、一边是 403「签名无效」→ 同代码但数据面不同）；顺带能把 DB 类型坐实（int32 越界 500 = PostgreSQL INTEGER） |

注意：`/openapi.json` 的 size 不同不一定不同版本——把两边 dot-path 集合与 schema 名 normalize 后再比。
