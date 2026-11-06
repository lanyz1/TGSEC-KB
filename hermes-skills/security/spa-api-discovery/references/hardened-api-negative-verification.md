# 加固 API 的「负结论」取证法 —— 怎么科学地判定打不进去(2026-09 实战)

场景:从白标兄弟站反挖出目标站真实 API 面后(`whitelabel-sibling-api-recon.md`),
需要判定**这套 API 到底有没有洞**。最有价值的不总是"找到洞",而是**用可复现的证据
宣布某条路封死**,让后续会话不再重复消耗。本文件记录一次把 153 条路由打成负结论的完整方法。

## 0. 先拿到"正常会话",不要裸测

绝大数端点会统一返回 `{"code":"8888","msg":"用户身份失效,请重新登录!"}` —— 这是**鉴权正常**
而不是"打不开"。裸测只能得到 8888,测不出任何东西。所以第一步是**自注册拿一个合法 token**。

### 从 bundle 挖出精确字段名(猜必失败)

前端 store 里的解构就是字段名的唯一真相,大写字母也不能错:

```python
# 在兄弟站 bundle 里搜调用点,而不是猜
import re; t=open('bf.js').read()
for m in re.findall(r'.{220}phoneRegister.{220}',t)[:3]: print(m.replace('\n',' ')[:440])
```

本案例实得:`phoneRegister({ phoneNumber, passWord })` —— **`passWord` 是大写 W**。
猜 `phone`/`password` 只会得到 `"Telefone e senha são obrigatórios"`(字段没被读到的假象)。

配套的三件事一起从 bundle 拿:
- **成功码**:`code` 为 `"0000"` 或 `"1003"` 视为成功(前端分支里写着)
- **token 落点**:`localStorage["token"]`
- **鉴权头**:`Authorization: Bearer <token>`;另需固定业务头(本案例 `Accept-Language: pt`)

```bash
curl -s -k --proxy $PROXY -H 'Content-Type: application/json' -H 'Accept-Language: pt' \
  -d '{"phoneNumber":"5511987654321","passWord":"<12+字符>"}' \
  https://<target>/api/user/phoneRegister
# → {"code":"0000","data":{"accessToken":"<64hex>","tokenType":"Bearer","expiresIn":2592000}}
```

## 1. class-validator 报错 = 免费的 schema oracle

NestJS + class-validator 的报错会**直接把请求 schema 和校验强度报出来**,不需要任何文档:

| 发送 | 返回 | 读出的事实 |
|---|---|---|
| `{}` | `"page" is required` | 必填字段名 = `page` |
| `{"page":1,"limit":10}` | `"limit" is not allowed` | **白名单严格 → Mass Assignment 直接被堵死** |
| `{"orderNumber":"x"}` 对另一端点 | 通过 | 该端点收 `orderNumber` |

**洞察:一旦看到 `is not allowed`,就不要再浪费时间试 Mass Assignment / 传多余字段提权了** ——
`forbidNonWhitelisted` 已经开着。这是省时间的关键判定。

## 2. IDOR 测试:看服务端认不认"身份来自 token"

依次替换参数名,观察返回的是**别人**还是**自己**:

```
GET /api/user/getUserInfo?id=1 / userId=1 / uid=1 / memberId=1 / user_id=1
```

本案例结果:**全部返回自己(id=119)** → 服务端完全忽略传入 id,身份只从 token 取 → **无 IDOR**。
这是正确的鉴权模型,不是"没测到"。判据是"返回值是否等于自己的记录",不是状态码。

列表类端点更直接 —— **用自己的空账号去查,如果返回了记录,那就是别人的**:

```
POST /api/pay/find_recharge_order {"page":1..3}   → data:[] total:"0"   ← 严格按账号隔离
POST /api/pay/find_withdraw_order {"page":1..3}   → data:[] total:"0"
```

## 3. 顺便验一遍健壮性(找调试泄漏)

```python
[{'page':'abc'},{'page':-1},{'page':99999999999999999999}]
```

全部 200 优雅处理、**无 500、无栈追踪、APP_DEBUG 未开** → 不能通过强制异常拿 `.env`/DB 凭据。
这同样是"负结论取证"的一部分,写进报告能避免下一步重复尝试。

## 4. 全路由无鉴权扫描 —— 负结论的正式取证

把 bundle 里的 `apiU+"..."` 全量路由逐条**不带 token**打一遍,只报异常:

```python
R=sorted(set(re.findall(r'apiU\s*\+\s*"([^"]+)"', t)))
for p in R:
    r=s.get(B+p,timeout=8)
    if r.status_code not in (404,405) and '8888' not in r.text:   # 8888 = 正常拒绝
        print('HIT',p,r.status_code,r.text[:120])
```

本案例 **153/153 全部正确拒绝,零漏网** → 可以正式宣布"用户侧 API 加固完备"。
**这是报告里最有力的一句话**,比任何单点失败都更有说服力。

### 4.1 探测脚本必须先自证「真的跑了」, 再谈命中

批量探测的**负结论**比单个失败更危险 —— 它会被当成定论写进报告。发负结论前先证明三件事:

- **候选集不为空**:分类/过滤一旦依赖某个正则**捕获**(如从 bundle 里另抓 JS 方法名), 捕获失败会让候选集**静默变空**,
  输出「候选 0 条」—— 看起来像干净负结论, 实际是脚本自己坏了。永远把候选数打印出来与提取到的路由总数对照;
  更稳的做法是**只按路径分类**(路径一定抓得到), 不依赖方法名这类二次捕获。
- **每条路径双方法都打**:方法不对回 405, **只打一种方法 = 把存在的路由误判成不存在**;每条路径 GET+POST 各一发。
- **命中判定写死, 不靠「非 404 即命中」**:`401`(鉴权拦截)、`404`(不存在)、`405`(方法不对)**都不是命中**;
  只有 `200` / 业务级 `400`(字段校验 oracle)/ `500`(处理器异常)才是候选。并**打印状态码直方图**
  (形如 `28×401 / 33×405 / 6×400`)让分类可被别人复盘 —— 直方图里出现意料之外的状态码才是真线索。

反面形态(两种都会导致错误结论):把 405/401 直接标成「未授权可达」, 命中列表看着有货、实质零信息;
以及过滤失效导致的「候选 0 条」静默空集。**判据:命中数 > 0 时先问「这些命中里有没有 401/404/405」。**

## 5. 后台锁定状态的三连判据(Filament 为例)

```
/admin/login                   → 200         真后台(看字节数:Laravel+Filament 约 45KB)
/admin/users                   → 302 → /admin/login   资源存在,需鉴权(确认后台是活的)
/admin/register                → 404         注册关闭  ← 若为 200 就是提权入口,优先打
/admin/password-reset/request  → 404         密码重置关闭
/manager/login /agent/login /painel/login → 404        无其他面板
```

**404 的字节数若与站点其它 404 完全一致(本例 6603/3385),说明是框架统一 404,即"该路由不存在"**,
不要误读成"被拦"。反之若字节数不同,值得深挖。

## 6. 常用后缀探测顺序(行政面)

`/api/admin/*` `/api/manage/*` `/api/agent/*` 这类**猜的管理 API**通常**返回 HTML 404 而不是 API 的 JSON 404**
→ 说明这些前缀根本没挂到 API 服务上(反代只转发白名单前缀)。**返回 HTML 而非 JSON 404 就是"不存在"的干净证据**,
不要继续在这套命名上枚举。

## 结论模板(写报告用)

> 用户侧 API 共 N 条路由逐一验证,**全部正确鉴权**;身份完全由 token 派生,查询参数无法越权;
> 列表端点按账号隔离;白名单校验严格(Mass Assignment 关闭);无调试泄漏。
> **未发现 IDOR / 越权 / 注入 / 调试信息泄漏。** 剩余路径均需凭据,已转管理面/主机层。

## Pitfalls

- **别把 8888 当"打不开"** —— 那是鉴权正常,必须拿 token 再测
- **别猜字段名** —— 从 store 解构里抄,`passWord` vs `password` 差一个字母全军覆没
- **看到 `is not allowed` 就停手** —— 白名单开着,Mass Assignment 路已死
- **空账号的列表接口是最好的 IDOR 探针** —— 返回非空即越权
- **注册口开放时优先自注册拿 token**,远比爆破安全,且能合法测出真实鉴权模型
- 自注册会在目标留下一个测试账号;**平台通常没有注销接口**,报告中要如实写明残留影响(空账号、无资金操作)
