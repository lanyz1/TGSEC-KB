# 以拿下节点为踏板（Egress Pivot）实战术

来源：2026-09 opensms 案 —— 从 `.225`（他们香港「中转层」节点）的订阅面板 LFI 出发。
适用范围：任何「节点/订阅/机场管理面板」型自建服务（SublinkX / v2board / sspanel 系套壳）。

## 0. 通道本身：一个字段 = 任意文件读 + SSRF
SublinkX：`POST /api/v1/subcription/add`，body `Config={"clash":"<target>"}`
- `<target>` = 绝对路径 → 读该机任意文件（面板 root 跑 ⇒ root 读）
- `<target>` = `http(s)://…` → **由目标机自己的 IP** 发起请求，响应体原样回显
- 判读：Go `net/http` 的错误原样回显 ⇒ 免费端口扫描器
  - `connection refused` = 端口关闭
  - `dial tcp …: i/o timeout` / `context deadline exceeded` = filtered
  - `no route to host` = 该网段不可达
  - 有响应 = 开放
- 输出通道多试：`client=clash` 回 500 空包 ≠ 洞关闭；`client=surge` 常原样回显

## 1. 先自证通道（别猜，读他们自己的日志）
同一条 LFI 读 `/var/log/nginx/access.log`，找自己刚发的请求：
- UA 应出现 `Go-http-client/1.1`
- 源地址是 `127.0.0.1` / 机器内网地址（本次 `10.0.20.2`）
⇒ 通道 + 「以他们身份出网」双证实；顺带从日志 Host 分布看本机真实承载 + 管理员自己的出口 IP。

## 2. 内网端口测绘 + 本机服务清单（本次实测）
逐个 `http://127.0.0.1:<port>/` 请求：
- `80` nginx 默认页 · `22` ssh · `53` dns
- `11111` **xray-core**（`/debug/pprof/cmdline` 直吐 `xray-linux-amd64 run -c bin/config.json`）
- `13788` 严格路由 Go 服务（任何路径 404 = 自研边缘软件）
- `15268` nginx/1.24.0 (Ubuntu)，仅 TLS
- `54321` 3x-ui（自签证书，已过期）
- `8000` 面板自身
判读：`/debug/pprof/cmdline` 是零成本进程识别，凡 Go 服务先打它；xray-core 的 pprof 无 RCE，别耗时间。

## 3. `/proc/net/tcp` → 外连 IP → 证书定性（本 case 转折点）
1. LFI 读 `/proc/net/tcp`：hex 解 `sl local:port rem:port st`，`st=01` = ESTABLISHED。
   本次唯一外连：`0x7A066077:01BB` → `119.96.6.122:443`。
2. 取证书：`openssl s_client -connect <ip>:443 -servername <任意域名> </dev/null | openssl x509 -noout -subject -issuer`
   本次 = `*.ctcdn.cn` / 「天翼云科技有限公司」⇒ **商业 CDN 边缘（天翼云），不是源站**。
   ⇒ 链路模型升级：`CF → 自建仿 CF 边缘 → 天翼云 CDN → 源站`。
3. `Host:` 撞它：`:80` + `Host: <面板域名>` → 200/12792B 真登录页（说明该 CDN 上配了这个域）；
   拿一票兄弟域名当 Host/SNI 撞 → 全 403 ⇒ **CDN 只认配置过的域名，撞不出来源站**。到此停止投入，转侧翼。

## 4. 用他们的 IP 打他们「只放行 CF」的兄弟机
以 SSRF 为跳板扫同段/相邻机，做 ACL 分类：
- `.221:80` → 返回体里带跳转 `https://dqjeqs.1ypmkva.com/...`（**新斗篷域名白拿**）
- `.230` → 自签证书（自建 HTTPS）
- `.227:80` → `connection refused`；`.10:80` 拒连；`.4/.16/.224` 超时
判读：**从他们自己的机器也进不去 ⇒ 所谓「只放行 CF」是边缘软件层的 Host/SNI 校验，不是源 IP 白名单**。
⇒ 别再把成本砸在「换个出口 IP 再过一次」。

## 5. 监控面板：优先于文件读
- Komari：`GET /api/nodes` **免鉴权**，标题/版本可从 HTML 直接读（本次「以针为友」，v1.1.9）。
  但公开清单**常不含 IP 字段**（本次 3 台：loc/cst/v5 香港）—— 别指望它直接吐源站。
- 真价值：**面板自带 Web 终端/命令执行**；agent token 明文躺在节点机 `/root/.bash_history`（本次抓到两个）。
- 面板自己不在 CF 后（本次 `tz.rvvr.eu.cc` → `103.244.91.81` 本机直连 200）= **无壳正面**，优先级最高。

## 6. 浏览器重登的省时前置
1. 先**一条 curl 经同一住宅代理**取目标域；`000`/超时/403 盾 ⇒ 代理线对该域不通，**别启动浏览器**
   （否则整轮死在 `Page.goto: NS_ERROR_NET_TIMEOUT`）。
2. 登录成功后的接口 dump 必须在**浏览器上下文内**（`page.evaluate(fetch)`），否则 `Event loop is closed! Is Playwright already stopped?`。
3. 破图形验证码用 ddddocr（`/root/pwenv/bin/python` 内有）；DOM 先 dump，别猜字段名。

## 7. 误判源：自建边缘「仿 CF」错误页
对裸 IP 打目标系域名，可能回来自制的 `error code: 1006` 页（**模仿 CF**）。
⇒ 看到 CF 品牌错误页**不能**判定「真 CF 边缘」或「CF 拉黑了我」。
真 CF 硬指标：TLS 证书签发方 + `CF-RAY` / `Server: cloudflare` 头 + 页面引用 `challenges.cloudflare.com`。
本次 `119.96.6.122` 正是靠证书 `*.ctcdn.cn` 才从「疑似 CF 节点」纠正为「天翼云 CDN 边缘」。
