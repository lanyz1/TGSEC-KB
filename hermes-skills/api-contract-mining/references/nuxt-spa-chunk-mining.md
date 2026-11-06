# Nuxt/Vite SPA 全量接口面挖掘

**适用**：Nuxt3 / Vite / webpack 单页站。页面只露少数接口，需要拿到完整 API 契约（含上传、改状态、钱包这些不在任何 UI 上的端点）。

## 0. 为什么必须做

黑盒逐个猜路径命中率极低。topuplive 案例：首页只出现 8 个接口，递归下载 34 个 lazy chunk 之后正则出 **113 个接口**；其中 `/charge/user-audit-upload`（文件上传）、`/charge/user-audit-status-update`（改订单状态）、`/v4/user-wallet/pre-pay` 全部不在可见页面里。这一步是整个案子的转折点。

## 1. 找入口 bundle

- Nuxt3：HTML 里 `/_nuxt/XXXX.js`（entry）；另有 `<script id="__NUXT_DATA__">` 内联 payload，可能直接含接口字段和商品数据
- Vite：`/assets/index-XXXX.js`
- 先下 entry（topuplive 262,820 B），**不要试图整篇读**——用正则挖

## 2. 递归展开 chunk（关键一步）

entry 里是 `import("./BLXW11dM.js")` 这种相对导入。提取全部 → 拼 `/_nuxt/<name>` → 全下。
topuplive：entry + 33 lazy = **34 个文件**，最大 1 MB。

顺便试构建清单：`/_nuxt/builds/latest.json`、`/_nuxt/builds/meta/<id>.json`（Nuxt3 才有，不是每个站都开；打不开无所谓，不阻塞）。

## 3. 从 chunk 提接口

按信号强度从高到低扫：

- `f("/charge/xxx"` / `("/v4/xxx"` —— 路径字面量
- `.post(` / `.get(` / `method:"POST"` —— 方法与路径配对
- `baseURL` / `serverBaseURL` / `VITE_.*_API` —— 接口根与备用根
- `.svc.cluster.local` —— K8s 内部名，直接反推服务拓扑（本例泄露 `api-topuplive-4.topuplive.svc.cluster.local`）

产出格式：`METHOD PATH 参数名列表`。参数名从同函数的 `params:{...}` / `data:{...}` 里抄，别猜。

## 4. 同源多主机（最高价值的一步）

bundle 里常同时存在 `baseURL:"/"` 和 `baseURL:"/pro-api"`。

- 主站前缀（`www.x.com/pro-api`）经常挂 Cloudflare Managed Challenge（响应头 `cf-mitigated: challenge`）
- 独立 API 主机（`api.x.com/user`）常常**直连源站 ALB，完全不过 CF**

两套都打一遍，逐接口比对响应。topuplive 就是这么从“全部 challenge”变成“接口全通”的。

## 5. 请求形状：不要在报错上连猜

submit-order 的反面教材：`The channel must be an array` → `The client field is required` → `折扣参数不全` → 500。四轮之后才回 chunk 读调用点，发现真实调用是 **POST JSON body**，body 里是嵌套的 `charge_params` / `discount_params` 对象，不是扁平表单字段。

**规则：同一个端点连续 2 次以上报“缺字段/类型错”，立刻停手去读前端调用点。** 继续猜是纯浪费时间。

## 6. 动态 id

`payment_id` 每次 `payment-list` 重新生成（实测 8157 → 7396 → 16841 → 16789）。拿旧 id 提交会得到 `The current payment method is unavailable` —— 这**不是**通道被关，是 id 过期。每次下单前重拉一次。

## 7. 探测顺序

1. 无鉴权 GET/POST 全跑一遍，记录 status 与 data 结构
2. 拿 token 再跑一遍，差异就是鉴权边界
3. **只对“未登录返回业务错误而非 401/请先登录”的端点做深挖**——那才是鉴权缺口
4. 最后才做注入类（大概率被 WAF + 参数化挡掉）

topuplive：106 个接口无鉴权探测，约一半直接吐数据（分类 112 KB、语言表 478 KB、1154 条脱敏买家评论），其余明确“请先登录”。

## 8. 案例数据

- entry `/_nuxt/BKLmxa9H.js` 262,820 B
- 34 chunk → 113 端点
- 网关 APISIX（`x-apisix-upstream-status`）
- WAF 长亭雷池（`x-apisix-chaitin-waf: yes` / `blocked by Chaitin SafeLine`）：拦 `<?php` 与 SQL 关键字（`and`/`or`），但**不拦** 数组类型混淆——`charge_account[]=x` 直接打到 500
