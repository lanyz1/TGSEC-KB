# 页内驱动 + 自动重放：绕过 JS 质询层的运输层

适用：目标有可访问的**真前端页面**（SPA / TMA / web 钱包 / 商家后台），且它自己就在调用同一 WAF 实例保护的 API。
目标：拿到「真路径 + 任意 HTTP method + 自定义头 + POST body」的通道，并**能把响应读回来**。
与主卡 §3b 的关系：主卡讲“识别与定性”，本文只讲“怎么把请求发出去并读回来”。

## 1. 一次实验定生死（先证机制，再谈打法）

1. 带调试端口的 Chrome 打开**目标自己的前端页**（不是质询页残留、不是静态落地页）。
2. `Page.addScriptToEvaluateOnNewDocument` 注入 §3 的 hook，再 `Page.navigate` 到该页。
3. 等它**自己的业务请求跑完**——这一步是“页面已被武装”的证明：观察它自己的 XHR URL 是否已带令牌。
4. 在**页内**发一次目标请求（跨源、跨主机都可以；可带业务信封/签名）。
5. 读 hook 记录：
   - 出现**同一请求两条 URL**：第一条裸路径（响应=质询页），第二条带令牌且 **method/body 逐字相同** ⇒ **重放已发生**，运输层成立。
   - 只有一条裸 URL ⇒ 该页的脚本未覆盖那个 host，换页面/换源；**不要**据此判定“页内 XHR 不行”。
6. 同时看 CDP `Network.responseReceived`：重放那条通常回 200，但这**不能**当作成功（见 §4）。

## 2. 读回响应（绕 CORS 的标准手法）

```python
cdp("Network.enable")
ids = []
# 事件循环里收：
#   Network.responseReceived -> d["params"]["response"]["url"] 命中目标
#                             -> d["params"]["requestId"]
for rid in ids:
    r = cdp("Network.getResponseBody", requestId=rid)
    body = r["body"]
    print(len(body), ("renderData" in body or "_waf_" in body), body[:300])
```

- `Network.getResponseBody` **不受 CORS 约束**：浏览器因缺 ACAO 而拦住 JS 的响应，照样能读。
- 用 `Network.*` 被动事件即可；**不要**为了读响应而 `Fetch.enable`（会阻塞/改写，污染证据）。
- 需要改请求时才上 `Fetch.*`——注意改**导航**的 method 会被降级成 GET（主卡 §4）。

## 3. 观测 hook（必须在页面脚本之前注入）

```js
(() => { if (window.__h) return; window.__h = 1; window.__log = [];
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u, ...r) { this.__m = m; this.__u = String(u); return oo.call(this, m, u, ...r); };
  XMLHttpRequest.prototype.send = function (b) {
    window.__log.push({ m: this.__m, u: this.__u,
                        tok: /(md5|refer|type|timestamp)__\d+/.test(this.__u),
                        b: String(b || '').slice(0, 200) });
    return os.apply(this, arguments); };
})();
```

读数：`JSON.stringify(window.__log.slice(-6))`。hook 记录的是**传入 `open` 的 URL**，所以若脚本是先改写 URL 再 `open`，这里就能看到带令牌的那条。

## 4. 判读：状态码无意义，只看 body

| 观察到 | 含义 |
|---|---|
| JS 侧 `onerror` / `Failed to fetch` / axios `status: 0` | **仅表示读不到**（缺 ACAO），请求已发出、响应已回 |
| CDP 侧 200 + body 含 `renderData` / `_waf_` | **仍是质询页** —— 通道未通，别宣布成功 |
| CDP 侧 200 + body 是业务 JSON（`code`/`msg`/数据）或框架错误体 | **真通道** |
| CDP 侧 401 / 403 / 应用自定义错误体 | 已过 WAF，问题在应用侧（信封/鉴权/权限） |
| body 为空 / URL 变成 `?alichlgref=<原URL>` | 该形态被降级（常见于导航式 POST），换 XHR 形态重试 |

## 5. 边界与坑

- **令牌参数名随机、每次部署不同**：`md5__<数字>`（XHR）、`refer__<数字>`（导航/重放）、`type__<rand>`、`timestamp__<rand>`。**按形态正则识别，不要 match 字面量。**
- **导航令牌与 XHR 令牌共用同一段盐前缀** ⇒ 可据此判断“多主机是否同一 WAF 实例”；同一实例的页面能为另一主机铸造令牌，**跨主机也就成了可行面**。
- **令牌与完整 URL（路径+查询串）绑定**：A 路径的令牌挪到 B 路径仍被质询。要打 B 就发 B，让脚本为 B 铸 token。
- **不要用 `;x=.js` 去凑**：那是命令行绕行手段；页内天然能用真路径，别自找“WAF 后缀白名单 × 框架 permitAll”双重匹配的麻烦。
- **低频**：一次业务请求实际会发出两次，控制节奏（每批少量、间隔数秒）。
- **先做严格 A/B**：同一出口同一时刻，命令行发 → 质询；页内发 → 重放。若两者相同，说明该页未武装，不是“机制不存在”。
- ★ **别在业务 bundle 里 grep 令牌名**：令牌由 WAF 脚本铸造，0 命中是正常的；据此否掉整条路线是浪费一整轮。
- ★ **白盒/二手笔记里的“正规管道已通”结论必须单变量实测**：本次实测带 `Origin`/`Referer`= 同族宿主仍被质询，而真页面内 XHR 才通 ⇒ 结论是“绑定浏览器上下文”，不是“补对某个头”。
- ⚠ **收尾必须落到 body 核实**：本类目标上“看到带令牌的 URL + 200”是最容易骗人的中间态。
