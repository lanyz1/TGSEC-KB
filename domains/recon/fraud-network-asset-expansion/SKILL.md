---
name: fraud-network-asset-expansion
description: Use when a fraud domain must expand into its whole network.
---

# 诈骗/博彩网络的资产扩展

## 何时用
拿到一个诈骗盘 / 资金盘 / 博彩站域名，需要回答「背后是谁、还运营哪些站、基础设施是什么、能否拿到源码或密钥」时。配合 `gambling-platform-pentest`、`pentest-execution` 使用：那些技能管单站打法，这个技能管「从一个站扩成一张网」。

## 核心原则
单站只是入口。先把「一个站」扩成「一张网」，再做技术突破——组织链、资金链、开发链的证据价值通常高于单台 root。每一层扩展开一个报告附录，最后用结构图收口。

## 执行顺序

### 1. 数字/品牌域名段枚举
数字品牌域名习惯同段注册，命中率高：
```bash
for i in $(seq 389930 389999); do r=$(dig +short $i.cc A +time=2 +tries=1 | head -1); [ -n "$r" ] && echo "$i.cc -> $r"; done
```
- 同源站 IP 的直接并案（同一台服务器就同一运营者）。
- 解析到 Cloudflare 的先记下，用下一步的「共享指纹」定归属，别急着当独立目标。

### 2. 共享统计 ID 是最强的归属主键
渲染页里 grep 统计代码：
```bash
curl -sk https://target/ -o page.html
grep -oE "LA\.init\(\{[^}]*id: '[^']+'" page.html   # 51.LA
grep -oE 'hm\.baidu\.com|cnzz|google-analytics|gtag' page.html
```
同一个统计 ID = 同一个运营者。拿 ID 去搜索引擎 / LeakIX / urlscan 反查同 ID 的其他站点，一次能拉出整批导流页。

### 3. 导流页就是「站点目录」
空壳 welcome 页常直接列出同团伙其他盘口（博彩/诈骗），带品牌名。抓全量 `<a href>`，逐个并案，得到品牌清单（金沙 / 博牛 / 亚博 …），这是后续所有关联分析的索引。

### 4. C 段 title 指纹
```bash
nmap -Pn -p 22,80,443,9001,36328 --min-rate 2000 -T4 --max-retries 1 <ip>/24 -oN seg.txt
# 再对每台开 80/443 的取标题
curl -sk --max-time 6 -H 'User-Agent: Mozilla/5.0' https://<ip>/ | grep -oE '<title>[^<]*'
```
认这些指纹：`恭喜，站点创建成功！`（宝塔默认页 = 同部署习惯）、`SaiAdmin`、`welcome`、`lobby`、外包公司官网。
AWS 的 /24 是共享的：只认「同品牌 / 同框架 / 同标题」的主机，不认「同段」。

### 5. APK → API 契约（两条路线）
**uni-app**：解包后 `assets/apps/__UNI__*/www/app-service.js` 是明文 JS，直接出 API 契约、apiKey、加密参数：
```bash
unzip -q app.apk -d app_x
grep -oE '"/api/[a-zA-Z0-9_/.-]{2,60}"' app_x/assets/apps/__UNI__*/www/app-service.js | sort -u
grep -oiE '(apiKey|appKey|secretKey|accessKey)[^,;}]{0,80}' app_x/assets/apps/__UNI__*/www/app-service.js
grep -oE '(baseURL|baseUrl)[:="]"[^"]*"' app_x/assets/apps/__UNI__*/www/app-service.js
```
顺带记录 AES 参数（常见 `AES-CBC key=apiKey iv=apiKey[:16]`）与签名式（`MD5(SHA1(参数排序后 & 连接))`）。注意：打包配置错误时 `baseURL` 会被写死成 `http://127.0.0.1:9001/api`，属开发环境残留，不要把该地址当真实后端。

**Flutter**：`blutter libapp.so out/` 之后读 `out/asm/*/apis.dart`、`out/asm/*/urls.dart` 拿端点与字段名；`operationID` 常是动态防重放（`millis % 60`）；出现 `flutter_openim_sdk` 说明 IM 走 OpenIM，业务 API 是另一套独立后端。

**云凭据扫描**（整个解包目录）：
```bash
grep -raoE 'LTAI[A-Za-z0-9]{12,20}|AKIA[A-Z0-9]{16}|AKID[A-Za-z0-9]{20,40}' app_x
```
客户端通常没有凭据（后端签名直传），扫不到就转攻存储桶本身。

### 6. CDN 回源的「path 当 query」重建
WAF 把 `/api/*`、`/assets/*` 统一 301 到 `https://<origin>:<port>/?cid=<siteCode>/<path>` 时，换一种拼法就能取到静态资源：
```bash
# 直连路径被 301：
curl -sk https://target/assets/theme-0/index.XXXX.js            # 301
# 改写成 path + query：
curl -sk 'https://<origin>:<port>/assets/theme-0/index.XXXX.js?cid=<siteCode>'
```
拿到入口 JS 后，里面 `window.__MANIFEST_ASSETS='assets/theme-0/manifest.<hash>.json'`，manifest 列出全部 chunk，再按 chunk 名逐个取。

SPA 的 HTML 里 `window.LOBBY_SITE_CONFIG=JSON.parse(M)`，`M` 是「base64 + URL 编码」两层：先 `base64.b64decode` 再 `urllib.parse.unquote`，得到 200KB+ JSON，含 `INJECT_DATA`（SSR 预取的 API 响应，等于免鉴权的数据快照）、`siteCode` / `parentSiteCode`、访客 token、`baseURL`。细节与脚本见 `references/spa-config-and-cdn-origin-recovery.md`。

### 7. 存储桶三查
**AWS S3**：
```bash
curl -s "https://<bucket>.s3.<region>.amazonaws.com/?acl"        # 看 AllUsers / READ + READ_ACP
curl -s "https://<bucket>.s3.<region>.amazonaws.com/?versions"   # 是否开版本控制
curl -s "https://<bucket>.s3.<region>.amazonaws.com/?delimiter=/&max-keys=1000"
```
**阿里云 OSS**：打错 region 的 403 会在 XML 里直接回 `<Endpoint>oss-cn-hongkong.aliyuncs.com</Endpoint>`——读它再重试，不要逐个 region 盲试。桶开了静态网站托管时根路径返回 index.html、列桶被禁，只能按已知路径取文件（`siteadmin/...`、`cocos/...` 等前缀从配置文件里收集）。

### 8. 百万级对象统计
分页上限会截断（`max-keys=1000`）。用「按月并发前缀」统计，再用「按天并发」补大月，Python 聚合出精确值；报告写精确数字 + 统计口径，绝不拿被截断的下限当结论。

## Pitfalls
- **Cloudflare 泛解析**：`mail/smtp/ftp/direct/origin/api/admin` 全解析到同一 104.x/172.x = 通配符，不是源站；别当成「发现了一堆子域」。
- **WAF 假开放**：nmap 显示一台机器几十上百个端口全 open、redis/mysql/mongo 全部「Connection reset」= WAF 端口欺骗。不是金矿，立刻停手改走应用层。
- **Go 后台不是若依**：响应格式 `{code,data,msg,tid}` 且 `/admin/` 回「xxx-admin已启动」= Go 自研后台，Shiro / Actuator / Druid / Spring 路径绕过全部不适用，别烧时间。
- **CORS 反射任意 Origin**：只有 token 存在 Cookie 时才可跨域自动认证；token 在 `Authorization` 头时只能算中危，报告别夸大。
- **上传路径穿越**：服务端用 MD5 重命名、且忽略 `dir/path/folder/prefix` 参数时，URL 编码、双写 `../`、`.../` 全是白费，试一轮就停。
- **空 header 测试**：`curl -H "token: "` 会丢弃空值头，要验证「空 token 是否放行」必须用 Python 构造真正空字符串 header。
- **grep.app / urlscan**：常被 Vercel / Cloudflare 的 JS 检查挡回；改用 LeakIX、certspotter、Google 站内搜索。
- **crt.sh**：高频 502；证书枚举统一走 `https://api.certspotter.com/v1/issuances?domain=<d>&include_subdomains=true&expand=dns_names`。
- **不要用真实公民证件做实名验证**：抽样确认照片真实性即可；拿泄露证件去「通过实名」属于冒用，会污染数据且越界，报告中作为设计缺陷描述即可。

## 输出
- 每层扩展开一个附录：同段测绘 / 开发者线索 / 客服与 Telegram / API 清单 / 存储桶 / 诈骗话术样本。
- 用「诈骗盘 → 博彩盘 → IM 后台 → 外包开发方」的结构图收口，比罗列 IP 有用得多。
- 明确写清哪些是「已确认漏洞」、哪些是「设计缺陷」、哪些只是「线索」，不要混为一谈。

## 参考
- `references/spa-config-and-cdn-origin-recovery.md`：双层 base64 配置解码、chunk 枚举、回源路径重建的完整脚本片段与决策表。
