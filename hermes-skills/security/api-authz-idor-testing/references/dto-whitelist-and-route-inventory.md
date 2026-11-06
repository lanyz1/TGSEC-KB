# DTO 白名单族:DTO 白名单对越权的封杀 + 参数名 oracle + 路由清单来源

来源:9v111 / A7777bet(NestJS + Laravel/Filament 白标赌场平台)2026-09 实测。
价值点:**用一条请求判定「参数注入型越权」在这个后端上是否根本不存在**,以及**从框架报错反推路由 DTO 字段名**。

## 1. 鉴权中间件的三种报错家族(补充分类,与 SKILL.md §1 并列)

| # | 报错形态 | 含义 | 越权可能 |
|---|---|---|---|
| ① | `{"status":100004,"msg":"用户参数异常"}` 系业务文案 | 强绑中间件,uid 必须 == token 用户 | 否 |
| ② | `{"code":"1001","msg":"\"limit\" is not allowed"}` | **DTO 白名单**(class-validator `forbidNonWhitelisted`),框架在业务层之前拒绝 | **否,架构级封死** |
| ③ | `{"code":"1001","msg":"\"page\" is required"}` | 参数缺失(必填校验) | 未知,需补齐后重测 |
| ④ | 无报错、返回数据 | 弱实现(仅验 token 存在性),内部信任 `uid` | **是 ← 主战场** |

**第②族的关键推论**:未知字段被框架拦下 ⇒ 注入 `userId` / `uid` / `user_id` / `memberId` **永远到不了业务代码**。逐个试别名的整轮工作可以省掉。实测该平台 153 条路由的鉴权接口,查询类**一律只返回会话本人数据** —— 不存在参数注入型 IDOR。

## 2. 参数名 oracle:用报错把 DTO 字段名逼出来

```
缺参数  → "X is required"      → X 是必填字段名
多参数  → "Y is not allowed"   → Y 不是该 DTO 的字段
```

两个方向交替打,即可把该路由接受的字段名集合逐步收敛出来,**比前端 JS 逆向或字典盲猜省数轮**。对拿到的每个路由都跑一遍,等价于把后端的 DTO 契约做了一次测绘。

## 3. 转向:第②族下真正的越权出口

DTO 白名单只挡「body 里的额外字段」,挡不住结构性问题:

- **路径参数**:`/api/res/{id}`、`/api/order/{orderNumber}` —— 不受 DTO 白名单约束,是首选目标
- **列表接口白名单内的 filter/owner 字段**:字段合法但归属校验可能缺失(见 SKILL.md §3)
- **写接口的属主校验缺失**:改密码 / 绑卡 / 转移类,只验参数合法性不验归属

## 4. 路由清单从哪来(别靠字典猜)

本平台 153 条路由**全部从前端 SPA 的 JS bundle 里正则提取**,不是爆破出来的:

```bash
# 前端 chunk 里提取完整路由全集
grep -ohE '"/?api[A-Za-z0-9_/\-]*"' *.js | sort -u
grep -ohE '/(user|pay|hall|activity|game)/[a-zA-Z0-9_/]+' *.js | sort -u
```

实测提取结果按模块分组:`/user/*`(getUserInfo/getUserCard/changeUserPass/reloadToken)、`/pay/*`(find_recharge_order/find_withdraw_order/getOrderState/get_recharge_config)、`/hall/*`(setting/messages/list/version)、`/activity/*`(100+ 条:leaderboard/team_info/vip 各返利)、`/game/*`。
**先建清单,再逐条分类鉴权,不要按字典顺序猜。**

## 5. 实战判读速查

| 现象 | 判读 |
|---|---|
| `"X is not allowed"` | DTO 白名单 → 参数注入死路,换路径参数/写接口 |
| `"X is required"` | 字段名 oracle,补齐后重测 |
| `405` 无 body | 路由存在,方法错(实测两个接口都靠这条才被发现) |
| `{"code":"8888","msg":"用户身份失效,请重新登录!"}` | token 未送达/失效 → 先确认 Authorization 头真的发出去了,别误判成鉴权拒绝 |
| 带 token 后原本 8888 的接口变 200 | 证明该接口确实只认 token,**且不认参数** → 回到第②族结论 |
