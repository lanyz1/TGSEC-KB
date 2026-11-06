# 案例：SublinkX v1.9.0 —— 源码直接给默认口令 + 未授权 LFI/SSRF

2026-09 实战：HK 真机集群上跑着 `SublinkX-admin v1.9.0`（节点订阅系统，GitHub 开源 944★）。
**三台（含监控/管理机）全部读穿；应用以 root 运行 → 任意文件读 = root 文件读。**
产品名/版本从前端主 bundle grep 得到（页面 `<title>` 为空）。

## 漏洞根因（源代码坐实）
```go
// 订阅模板渲染：同一字段既当 URL 又当文件路径
if strings.Contains(yamlfile, "://") { http.Get(yamlfile) } else { os.ReadFile(yamlfile) }
```
- 触发点：订阅的 `config.surge` / `config.clash` 字段（建订阅时可写）。
- 出口：`GET /c/?token=md5(<订阅名>)&client=surge` —— **免鉴权**。
- **出口要试多个**：`client=clash` 本案回 HTTP 500 空包（≠洞关闭），`client=surge` 把文件内容/错误原样回显。

## 入口（全部来自读源码，不是猜）
| 环节 | 实际实现 |
|------|----------|
| 首次启动 | `init()` 自动建管理员，**默认 `admin/123456`**，明文存 SQLite/配置文件 |
| 登录验证码 | `base64Captcha NewDriverMath` = 数学题 → ddddocr 可解 |
| JWT 中间件 | `AuthorToken` **只验签名不验用户** → 唯一门槛是配置里的 `JwtSecret`（同一份配置，被 LFI 读到后即可伪造任意身份） |

## 集群复用
- 同产品 + 同默认口令 + 同漏洞在**监控/管理机同样成立**；先挑与管理链路互通的那台做第二发。
- 舰队清单从暴露的监控面白拿：Komari `/api/nodes` 无需鉴权（服务器名/系统/CPU/内存）。

## 读穿后先取这些（按价值）
`/etc/shadow` · `/root/.bash_history` · `/proc/self/cmdline` · `/proc/self/environ` ·
`/proc/net/tcp` + `tcp6` · `/root/docker-compose.yml`(+`.env`) · `nginx.conf` + `log/nginx/access.log` ·
`/etc/x-ui/x-ui.db` · acme/certs 目录 · `crontab`
- `/proc/net/tcp` 的**外连** = 基础设施地图（谁连谁、有无 CF 隧道 `:7844`、自建面板地址）。
- `docker-compose.yml` 常直给 MySQL root 口令；`.bash_history` 给安装脚本与**监控 agent token**。
- nginx access.log 的 Host 分布 = 本机真实承载域名，常带**管理员出口 IP**。
- `/etc/x-ui/x-ui.db` = 3x-ui 的 admin bcrypt + `webBasePath` + `secret`（会话密钥，可伪造 cookie）。

## 陷阱（本次踩过的假阳性）
- 「新密码不能为空」类报错是**空值短路**，不是族校验被绕过 → 补全字段再判，否则会把
  「admin 可被重置」写进报告。
- 响应异常（`HTTP/0.0`、500 空包）先怀疑**协议/出口格式不对**，再判漏洞有无。
- `os.ReadFile` 类洞只给读；写路径多半被 `safeFilePath` 挡住 —— 别为追 RCE 反复砸同一个洞。

## 可迁移三步（下次遇到不认识的面板照做）
1. 抓主 bundle → grep 产品名/版本 → GitHub API 搜仓库 → `git clone -c http.proxy= -c https.proxy=`。
2. 源码只读三处：首启自建账号、验证码实现、鉴权中间件。
3. 找**免鉴权出口** + 用户可控的**路径/URL 字段**：一个字段同时给 LFI + SSRF。
