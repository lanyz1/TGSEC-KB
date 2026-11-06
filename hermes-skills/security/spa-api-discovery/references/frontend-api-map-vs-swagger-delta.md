# 前端 API 图 × Swagger 差集 + 路由前缀陷阱

2026-09 Nightplay 实战验证。两件事:**(a)** 怎么用前端 chunk 把"没人审过的路由"逼出来;
**(b)** 一个会让整条侦察线跑偏的低级坑。

## 1. 差集法:90 秒找到没人审过的路由

把"从前端 chunk 还原出的全部接口"与目标自带的 **OpenAPI/Swagger 文档**做**差集**。
**差集里的路径就是没被文档覆盖、通常也没被人审过的路由。**

实战数字:204 个 Vite chunk → 提取 95 条路径 → **79 条不在 swagger 里**,其中包括:

```
/skills/*            (24 条:脚本/模板/工具/打包 —— 像能存脚本的模块)
/sysApiToken/createApiToken     (能造持久化 API 令牌)
/casbin/updateCasbin            (权限写面)
/autoCode/mcpStart              (某 CVE 的 RCE 触发器)
/card/* · /listenSoft/* · /deviceAdmin/touchPin/* · /sysLoginLog/*
```

**swagger 里"有"、线上却 404 → 文档与构建不同步**,真实路由名要试**大小写变体**:
实测 `/casbin/updateCasbin`(小写)存在,而文档记的 `/casbin/UpdateCasbin` 直接 404。
(所以"404"必须先排除大小写与前缀,再判定不存在。)

## 2. 第二轮:对差集做鉴权差集

差集路由拿到后,无票 / 低权票各打一遍,按响应分三类:

| 响应 | 判定 |
|---|---|
| `{"code":7,"msg":"权限不足"}` | 路由存在,**被 Casbin 拦住** |
| `404 page not found`(Go 风格 `text/plain`) | 该实例**未挂载**这条路由 |
| 其它任何响应(业务错误 / 参数校验失败 / code:0) | **可达** —— 真正要挖的就是这些 |

本次由此捞出 5 条完全不受 Casbin 管辖的接口(含一个吐用户名单的、一个黑名单型 session 接口)。

## 3. ⚠️ 路由前缀陷阱(本次白绕一圈的坑)

**裸路径的 nginx 404 ≠ 路由不存在 —— 极可能只是你漏了路由前缀。**

真实经过:对 `/device/init` 探测 → 返回 nginx 的 404 页面 → 判定"设备 API 没挂载"。
实际路由是 **`/api/device/init`**,加上前缀后 `code:0` 直接通了。同一次还漏过
`/api/casbin/...`。

**固定做法:**

1. 先从 SPA 首页的 main JS 里读出 `baseURL`(见本 skill 主文档),它就是前缀
2. 前缀要么全局拼好(`BASE = f"https://{host}/api"`),要么在每次请求前显式确认
3. **判别两种 404**:nginx 默认页(`<html>\r\n<head><title>404 Not Found</title>`,548B 左右)
   = 反代层没匹配上,**高度怀疑前缀/路径写错**;Go 的 `404 page not found`(text/plain 18B)
   = 前缀对了但该实例确实没挂这条路由
4. 用**免认证的健康接口**校准前缀:很多 GVA 系有 `GET /api/health` → `{"instance_role":"..."}`
   既确认前缀又泄漏实例角色

## 4. 多实例:同一域下不同模块可能在不同实例

`/api/health` 的 `instance_role` 会告诉你这是哪个实例。同一域下不同模块可能由**不同实例**服务,
时间戳时区会露馅(管理面 `+05:30`,device/media 服务 `+01:00`)。
→ **一个路径在 A 主机 404,不代表整个平台没有;换主机/换实例再确认。**

## 5. 生成式客户端 bundle:唯一权威的 (path, method) 路由表

现代 gRPC-gateway / Connect / protobuf 生成的前端 client, 每个方法长这样:

```js
name:(t,s={})=>this.request({path:"/api/buckets/GetBuckets",method:"POST",body:t,...})
```

**坑:只抽裸路径只能拿到方法名, 全部打不通。** 实测 `grep -oE '"/api/[A-Za-z]+"'` 得到 84 个方法名(如 `GetUserInfo`),
逐个 `POST /api/GetUserInfo` → **全部 404**。原因: 真路径带**名字空间** —— `/api/buckets/GetBuckets`、`/api/users/GetUserInfo`、
`/api/objects/ListObjects`、`/api/metrics/GetStatOverview`。方法名单独不是路由, **`path:"..."` 才是**。

正确的提取(一次拿到全部 82 条真实路由, 带 verb):

```python
PAIR = re.compile(r'path\s*:\s*"(/api/[^"]{2,120})"\s*,\s*method\s*:\s*"([A-Z]+)"')
```

可直接跑 `scripts/extract_route_table.py`(提取 + 只读探测一体)。

### 探测纪律

1. **每条路径 GET 与 POST 各打一发** —— 方法未知时只发一种, 405 会被误读成「路径不存在」
2. **分类必须按响应语义分桶, 401/405/404 都不是命中**:

| 响应 | 含义 |
|---|---|
| `401`(空体或统一信封) | 路由存在且**鉴权有效**, 受保护 |
| `405` | 路由存在, **方法不对** ⇒ 换 verb 再打 |
| `404 page not found`(Go text/plain 18B) | 该实例**未挂载**此路由 |
| `400` + 字段级报错(`field "x" is not set`) | **已穿过鉴权中间件** ⇒ 未授权面候选 |
| `200` | 命中 |

3. **筛候选要按 PATH 正则, 不要按旁路抓来的辅助字段** —— 第一版脚本用「正则捕获到的 JS 函数名」筛只读候选,
   而函数名没抓全 ⇒ 候选 **0 条**、静默空跑(日志里「候选 0 条」与「探测 0 次」同行, 一眼可辨)。
   **跑完必须回读日志确认探测条数 > 0**, 不能只看脚本 exit 0。
4. **不确定路径是否还活的, 用同一族的路由名做交集**: 老一代产品源码里的特征路由在新一代全 404、两边路由名零交集
   ⇒ 两代不同代码库。这是判断「手上这份前端/源码对应哪一代线上栈」的最快手段。
