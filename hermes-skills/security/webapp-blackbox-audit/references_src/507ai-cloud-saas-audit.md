# 507.ai 云控 SaaS 审计笔记（2026-08-28 会话）

> 实战目标: 507.ai 出海云控平台（主站 Vue SPA + app.507.ai uniapp + tg/wa.507.mx shop_hq FastAdmin 子系统 + pay.507.ai ThinkPHP USDT 收银台）
> 完整漏洞清单与凭据落盘: /root/work/507_ai/（SUMMARY_PROGRESS.md、credentials.json）

## T1. Cloudflare 拦截 Python 的判据与最终通道
- 判据: requests/curl 得到 `200 + 空响应体`（无报错无跳转），而浏览器正常 → CF bot 检查在拦非浏览器客户端；浏览器 tab 里已持有完整 cf challenge cookies。
- 对策: **所有 API 调用改走 Playwright `browser_evaluate` 里的 fetch**（同源、自动带 cookie，server 端只看 UA/头毫无意义）。Python 仅做本地计算（AES 解密、数据整理）。
- 陷阱: 直接 `fetch` 到另一子域（pay.507.ai → 507.ai）会被 CORS 拦，需要切到对应 origin 的 tab 再发；FastAdmin 接口要带 `X-Requested-With: XMLHttpRequest`。

## T2. 前端加密体系恢复（SaaS 登录加密常见布局）
- 登录链: RSA 加密账号+密码 + 图形验证码 + CSRF/keeplogin。API 请求/响应 `data` 字段 AES-CBC 加密。
- 恢复手法: 全局 grep `AES_Decrypt|setPublicKey|JSEncrypt`。uniapp 里加密模块在 **shared chunk**（`shared_*.js`）而非页面 chunk；SPA 主站则在主 bundle 的 string-table 混淆段（`n={ARLqP:t(250)...}` 形态）。
- key/iv 是 16/32 字符 ASCII 常量，RSA pubkey 常随 `getConfigV2`/login 配置下发（先 AES 解配置再拿 pubkey）。
- 证据: 本例 AES key/iv 均为 bundle 硬编码 → 全平台加密流量可解 = 高危发现。

## T3. uniapp/webpack 懒加载 chunk 收割
- 页面 HTML 只引 index+vendors，业务 API 在懒加载 chunk（`pages-login-login.{hash}.js`）。
- 从 index.js 提取 webpack `chunk name → hash` 映射 → 直接拼 `/static/js/<name>.<hash>.js` 批量下载（404 说明 hash 不对，从映射重取）。
- 价值: 登录/我的/数据页 chunk 里含完整 API 路径与请求参数名，比目录爆破快 10 倍。

## T4. XHR hook 学请求 schema（不猜字段名）
- 包一层 `window.__log` + `XMLHttpRequest.prototype.send`（fetch 也 hook），从 UI 触发一次真实提交 → 精确 body 一次到手。
- 本例: vuln_report/submit 真实字段是 `target_url/reproduce_steps/show_in_hall/hall_alias` 且为 JSON body —— 猜 `steps/affect` 全被「请填写复现步骤」卡住。
- 适用于一切自研表单（漏洞提交、开户、工单）。

## T5. 三态错误 oracle = IDOR/对象枚举器
- 例: `/shop_hq/dashboard/buyuser/id/{n}` → '商家有误'(不存在) / '商家已停售'(存在) / 正常表单(在售)。
- 40 次请求画全对象地图；同类 oracle: '用户不存在' vs '密码错误'、'未绑定token' vs 'api_token无效'。
- 纪律: 只读枚举 + 区分「存在性证明」与「数据获取」。

## T6. total 与 rows 不一致 = 过滤缺口强信号
- 列表接口 `total:1` 却返回 2 行、且混入非本人记录 → 查询条件有缺口（他人数据泄露）。发现后立即换 limit/page 复测并保存原始响应。
- 同族信号: `total:0, rows:[...非空]`。

## T7. 验证码 OCR 链
- `getcaptcha_new` 返回 `{key, base64 图片}` → 构造 `data:image/png;base64,...` dataURL 交 vision_analyze → 识别码填回登录。一次通过率可用；失败就重取新图重试，别在旧图上死磕。

## T8. SaaS 多产品 SSO 链路
- 主站绑定产品 (`activateProduct`) → `getAuthLoginUrl` 返回子系统 `authlogin/token/{UUID}` URL → 访问即免密登录子系统。
- SSO token 可反复生成；但绑定按产品隔离（TG token 进不了 WA），子系统账号与主站账号体系分离。

## T9. 支付面审计纪律（复用 webapp-blackbox-audit §5）
- 「手动确认支付」按钮端点必须实测 POST 后查余额——本例 payed.html 确认后余额未变，链上校验有效（写进 positive verification）。
- 收银台 `cashier.html?osn=` 订单号可枚举、状态轮询 `api.html?osn=` 无伪造面；固定收款地址 + 链上金额匹配 = 伪造成本高。

## 战果摘要
- 8 项漏洞（加密体系全泄露/手机号泄露/报告越权/商家 IDOR/内网端口泄露/500 异常/客服配置/商户密钥字段），3 项防住（支付链上验证/后台数据隔离/SSO 产品隔离）。
