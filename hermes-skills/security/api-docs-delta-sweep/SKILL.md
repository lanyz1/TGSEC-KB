---
name: api-docs-delta-sweep
description: "Use when OpenAPI docs expose a multi-service API surface."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
---

# API 文档差集扫描:从文档全量到越权面

> **一句话**:前端 bundle 挖到的端点数,是**你的上限**,不是**目标的上限**。
> 实测同一白标平台:71 个 chunk 挖出 **84** 条端点;接上 `/v3/api-docs` 拿到 **1,255** 条;
> 差集 **38** 条 —— 全部有价值的越权命中都在这 38 条里。
> 顺序:**拿全量 → 做差集 → 打差集**。跳过一步就是在已知的 6% 面上撞运气。

## 触发

- 指纹出现 `swagger` / `knife4j` / `doc.html` / `springdoc` / `/v3/api-docs`
- 你只从 bundle / HAR / APK 挖到一部分端点,正准备开始「参数穷举」
- 平台是多服务网关(`/gtw/<svc>/...`、`/gw/<svc>/...`),每个前缀像一套独立 API
- 一整族端点打不动,想确认是「真封死」还是「入口找错了」

**不替代**:`spa-api-discovery`(只做前端挖掘)、`api-recon-and-docs`(文档路径清单)、
`api-probe-layer-triage`(单批读数判层)。本卡补的是中间那一环 —— **把文档侧的全量面接进来,并且只打差集**。

## Step 1 — 先找服务前缀,再找路径

springdoc 在网关下**按服务分区**暴露,形态固定:

```text
/<gw>/<svc>/v3/api-docs                springdoc 默认
/<gw>/<svc>/v3/api-docs/swagger-config
/<gw>/<svc>/v2/api-docs                springfox 老版
/<gw>/<svc>/doc.html                   knife4j
/<gw>/<svc>/swagger-resources
```

`<svc>` 从三处抠,别硬猜:

1. **前端 bundle 里的 base 常量** —— `"/gtw/ply"`、`"/gtw/prv"` 这类拼接前缀就是服务名;
2. **网关自报的路由段** —— 404/401 文案、错误页 service id、`iss`/`aud`;
3. **小字典整轮打一遍**(成本极低):`ply prtl mer mgr sys prv dc auth open admin cmo eai pay oms wlm`

```python
import requests
for svc in SVC:
    for p in ("/v3/api-docs", "/v2/api-docs"):
        r = requests.get(f"https://{HOST}/{GW}/{svc}{p}", timeout=15)
        if r.ok and r.headers.get("content-type", "").startswith("application/json"):
            print(svc, p, len(r.json().get("paths", {})))
```

## Step 2 — 逐套下载,按 `info.title` 建表

每套文档是**一份独立清单**,必须单独计数。**按 `info.title` 建表,不按 URL 建表** ——
同一平台常有 5~6 套,URL 前缀不说明它是什么服务。

```python
docs = {}
for svc in HIT:
    j = requests.get(f"{BASE}/{GW}/{svc}/v3/api-docs").json()
    docs[j["info"]["title"]] = j
    print(f'{svc:6s} {j["info"]["title"]:22s} {len(j["paths"]):4d} paths')
```

实测读数(白标平台,零鉴权):`player 214 / merchant 235 / system 99 / provider 553 / dc 154 = 1,255`。

★ **最大的那套通常是 provider / 资金面**,也最容易零归属校验 —— 优先打它。

## Step 3 — 差集是唯一有价值的东西

```python
front  = set(mined_from_frontend)                        # 84
alldoc = {p for d in docs.values() for p in d["paths"]} # 1255
delta  = alldoc - front                                  # 38
```

差集的典型成分(**按这个顺序看**):

| 形状 | 为什么值钱 |
|---|---|
| `GET .../get-by-id/{id}`、`.../dtl/{id}` | 纯数字主键,self-scope 最常漏挂 |
| `POST .../ls-page`、`/page`、`/list` | 必填参数里带 `usrnm`/`mbrId`/`tenantId` 的,身份常从参数取 |
| `POST /feign/*` | 内部服务间接口,多带网关白名单(403),但值得各打一发 |
| `PUT .../upd-*`、`reset-*`、`del-*` | 写面,按零写入方式探 |
| `/public/*` 下的管理类动作 | 公开命名空间最容易「以为没人会调」 |
| `.../crt`、`.../crt-*` | 创建类,`required` 常直接暴露真实身份参数 |

## Step 4 — 鉴权逐服务挂,结论不许跨前缀

**同一个路径名会出现在多个服务前缀下,是两个不同的 handler、两套不同的鉴权。**
实测:`/gtw/ply/prtl/wlt-txn/ls-page` 与 `/gtw/prv/prtl/wlt-txn/ls-page` —— 一个 self-scope,一个完全不看归属。

纪律:

- 每次探测记录**三元组**:服务前缀 + 路径 + 谓词;
- 「该端点判死」**不得跨前缀套用**,换前缀必须重打;
- 前缀错时的典型读数是 catch-all(`999999 Unknown Error`)或 `404` ——
  **别当成「端点不存在」**,先把同一路径在所有服务前缀上矩阵打一遍。

## Step 5 — 差集探针分档(真正花时间的部分)

顺序固定,**前一步不成立不许进下一步**:

**(a) 谓词自证。** 自研请求封装经常把 `method` 参数丢掉、一律 `POST`。
整批回同一个 `999999 Unknown Error` / `9999 系统繁忙` 时,**先怀疑自己**:
同一路径 GET 与 POST 各发一发,逐字节相同 ⇒ 谓词没到。修客户端后**整批作废重跑**。

**(b) 凭据作用域。** 玩家票打后台端点,有的平台回一句看似无关的
`Invalid oauth2 client id` —— **这不是路由不存在,是这张票不属于这个 client**。
同理:`需 refresh token` = 后台会话专属;`/feign/*` 的 `403` = 内部白名单。
⇒ 三态记录:**无票 / 普通用户票 / 特权票**,别写「带票」两个字了事。

**(c) 参数受信三发。** 证明服务端真拿客户端传的标识去查人:

| 发什么 | 期望 | 结论 |
|---|---|---|
| `<标识>=自己` | 走到业务闸门 | 解析到自己 |
| `<标识>=他人(已知存在)` | **同一句**闸门错误 | ★ 校验对象变成了他人 |
| `<标识>=不存在的号` | **另一句** `... Not Found` | 存在性 oracle,证明按该键查表 |

第三发给出专门文案,才同时排除了「参数被忽略」与「参数只影响展示」。

**(d) 零副作用。** 金额必填的动账端点,先发**必余额不足的天价**(`amt=99999999`)——
校验停在余额/风控闸门,**一分钱不动**,闸门文案照样证明身份参数被采用。
写/删类走「必然不合法」的载荷(缺必填、类型错、不存在的 id),让参数校验先失败。

**(e) self 还是全站。** 换一个**归属已知不同**的号打同一端点:随账号变 = self(零价值);
不变 = 全站(真发现)。只凭「200 有数据」就写越权是最常见的假阳性。

## Step 6 — 文档本身是情报

- `servers[].url`、示例里的内网域名/内网 IP → 下一跳靶子(实测泄 `prod-eai.<x>.local` / `10.74.x.x`)
- `securitySchemes` + 全局 `security` 声明 → 对照实际有没有挂
- **`required` 数组 → 身份参数候选**(`usrnm` / `mbrId` / `accNum` / `merCode` 出现在 required 里 = 客户端可传身份)
- 枚举/下拉接口 → **能力面**(这个商户到底开了哪些通道)

## 交付口径

- 报**四层数**,别报一个总数:文档全量 / 前端已知 / 差集 / 差集里实锤越权
- 每条命中给「前缀 + 路径 + 谓词 + 取到的字段 + 规模(N/N 命中、多少主体、多少金额)」
- 证据原样 JSON 落盘,**PII 不复述进正文**,只给路径

## 坑

- 把前端挖掘当「面已穷尽」—— 实测差 15 倍
- 只探一个前缀就判死 —— 鉴权逐服务挂
- catch-all 错误当业务结论 —— 先自证谓词/信封/凭据
- 差集里先打 `/feign/*` —— 白名单概率高,应先打 `get-by-id` 和 `ls-page`
- 文档能下就以为全裸 —— 逐条还要探,`security` 声明与实挂不一致很常见

## 参考

- `references/wtlb-1255-endpoint-case.md` —— 实测全案:5 套文档、1,255 端点、38 条差集、错误码表、命中端点与规模
- `references/payout-rail-determination.md` —— 差集顺带解决的能力面问题:判断某商户到底开了哪些出金通道(能不能提 U)
