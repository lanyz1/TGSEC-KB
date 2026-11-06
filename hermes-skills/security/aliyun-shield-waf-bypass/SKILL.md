---
name: aliyun-shield-waf-bypass
description: "Use when 目标前置阿里云盾(yundunwaf) WAF 返回 405。尾斜杠/查询参数绕过直达源站。"
version: 1.0.0
tags: [waf, aliyun-shield, yundunwaf, bypass, 阿里云盾]
---

# 阿里云盾 (yundunwaf) WAF 绕过

阿里云盾前置在大量国内/港台站点前面。它拦截「无尾斜杠路径」和「敏感后缀」，但放行「尾斜杠」和「带查询参数」的同一路径——绕过它就能直达源站 Apache/Nginx。

## 识别阿里云盾

- DNS CNAME 落到 `*.yundunwaf1.com` / `yundunwaf2.com` / `yundunwaf3.com`（每子域一个随机前缀，如 `hb0kv16cvga6dav7bkzekwsrhrp2tdgd.yundunwaf3.com`）
- 拦截响应：HTTP 405，HTML 内嵌 `errors.aliyun.com/images/...` 图片 + `<textarea id="renderData">{"traceid":"...","lang":"cn"}</textarea>`
- 响应头 `Server: Tengine`（阿里云）

## 两种防护模式（先判断，别套错招）

阿里云盾有**两套**拦截，手法完全不同，混用会白耗时间：

### A. 405 拦截（尾斜杠/查询参数可绕）
特征是返回 405 HTML，内嵌 `errors.aliyun.com` 图片 + `traceid`。用下方「绕过技巧」打。

### B. JS 质询（尾斜杠/参数无效，只能无头浏览器）
- 特征：返回 HTML 含 `<meta name="aliyun_waf_aa">`/`aliyun_waf_oo`/`aliyun_waf_00` + `<textarea id="renderData">{"_waf_..."}` + 混淆 JS（函数名 `aliyunwaf_*`）；或 403 响应带 `Set-Cookie: aliyungf_tc=` / `acw_tc=`。
- **陷阱**：尾斜杠 / `?x=1` 在此模式下返回的是「200 质询页」（HTML，非业务 JSON）——**判定是否放行看内容类型，不看状态码**。200 的 HTML 质询页 ≠ 穿透。
- 绕过：无头浏览器导航到目标 → 浏览器执行质询 JS → 自动种 cookie（`ssxmod_itna`）+ localStorage 签名（`<host>_dySig`）+ 追加 `md5__1713` 参数到 URL → 之后**同一浏览器会话**里发请求才真正到后端（能拿到业务 JSON）。
- XHR/fetch 不带 `md5__1713` 会被重新质询（阿里云盾区分「导航」vs「XHR」）；要在已经过质询的页面里用 `js()` fetch，别从 curl/Python 直发。
- Python/curl 无法复现质询（混淆 JS + 浏览器指纹绑定），别硬刚；正确姿势是无头浏览器过质询后，在页面内 fetch 目标 API，再把加密响应传回 Python 解。

## 绕过技巧（核心，已验证）

### 1. 尾斜杠绕过（判路径是否存在）
WAF 拦「无尾斜杠」，放行「带尾斜杠」→ 请求穿透到源站：
```
/admin/orders   → 405 (WAF 拦)
/admin/orders/  → 301/200 (直达源站, 响应体露 Apache/2.2.15 Server 头 = 已穿透)
/admin/data      → 405
/admin/data/     → 200
```
- 判定命中：响应带 `Apache/2.2.15 (CentOS) Server at <host> Port 443` 的 301 = 已到源站
- 陷阱：301 重定向回「无尾斜杠」又会被 WAF 拦。尾斜杠只证明路径存在、可枚举目录结构，不能直接读内容。

### 2. 查询参数绕过（读敏感文件/后缀）
对「敏感文件/后缀」被拦的情况，追加 `?x=1` / `?v=1` 放行：
```
/app/szjy_client.apk    → 405 (拦 .apk)
/app/szjy_client.apk?x=1 → 200 (完整下载)
/admin/login.php         → 405
/admin/login.php?x=1     → 200
```
- 用 `?t=$(date +%s)` 每次随机参数规避固定参数封禁
- 下载二进制(APK)务必带参数，且用 `file` 校验输出是 `Zip archive`(APK 本质是 ZIP) 而非 HTML 405 页

### 3. 动态拦截 vs 代理池
- 阿里云盾是**动态**的：同一路径、同一代理出口 IP 会从 200 逐渐变 405（IP 被标记）
- debug 泄露(`$_SERVER` dump：`REMOTE_ADDR/REQUEST_URI/HTTP_HOST/REQUEST_TIME...`)是**间歇性**的，取决于命中的代理 IP
- 被拦/超时/501 交错是常态 → 用重试 + 代理池换 IP（`proxychains4 -f /root/proxychains_socks5.conf`）而非硬刚单个被封 IP
- 数据中心出口 IP 会被永久封，必须走住宅/动态代理池

## 源站 IP 被完全隐藏时

- 阿里云盾 + 源站只放行 WAF 回源时，MX/SPF/历史 DNS 全是阿里云(mxhichina.com/alidns.com)，真实源站 IP 挖不到
- 此时无法绕过源站，只能靠代理池换 IP 穿透 WAF 本身，继续打 WAF 后面的应用

## 组合链（实战验证）

1. 首页 `?x=1` 绕过 → 拿到 HTML → 从 ObjectId 风格 URL(`/news?id=5a787d21...`)定位 MongoDB 后端 + 关联域名
2. `/admin/xxx/` 尾斜杠 → 枚举后台目录(orders/export/data/user/member/api)
3. `/app/xxx.apk?v=1` 下载 APK → jadx 反编译 → 定位 APP API 子域(同走阿里云盾)
4. APP API 继续用代理池 + 参数绕过打
