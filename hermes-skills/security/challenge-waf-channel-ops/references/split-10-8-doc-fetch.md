## 8. 批量扫路径：逐路径 doc 导航，别用页内 fetch 扫
**反例（烧过一次）**：导航到 `https://host/` 后再在页内同源 `fetch` 循环扫 27 条路径 ⇒ 一旦某次导航失败/被 WAF 重置（`ERR_CONNECTION_CLOSED`），页面留在**上一个 origin**，此后所有 fetch 全部 `TypeError: Failed to fetch` ⇒ **整批 270 条结果零信息量**。
**正解**：每个 `(host, path)` 一次 `Page.navigate`（doc 导航是放行面，**但不是恒过 —— 见 §11 重试纪律**），读 `document.body.innerText` + `document.title` + 长度。代价 ~6-7s/条（80 条约 10 分钟），换来**每条结果都可信**。判读：`Whitelabel Error Page` = 应用层 404/403；`很抱歉…被阻断` = WAF 规则命中（**只证明有该规则，不证明组件存在**）；`Invalid encrypted request` = 命中信封过滤器；应用 JSON = 真业务响应。
**推论铁律**：`/actuator` 若返回应用自身 404，则 `/actuator/{env,heapdump}` 被 WAF 拦**不能**当作「组件已注册」的证据（WAF 规则列表是通用黑名单）。

