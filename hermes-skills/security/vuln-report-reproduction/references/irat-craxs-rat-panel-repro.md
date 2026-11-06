# I-RAT/Craxs 类远控面板 同源码站复现 实战案例

**背景**: 原目标 mhm66.com(I-RAT/Craxs 手机远控间谍面板)挂了, 老板给 3 个同源码站复现 10 个漏洞:
`202.79.168.240`(=aakd3998.top 同一台)、`a.330p008.my`(独立服务器)。
技术栈: AdminPro"阿力科技"SPA 前端 + PHP 后端, nginx(非原站 Apache/XAMPP)。

## 同源码确认方法(快速)
1. **app.config.js 域名替换逻辑**: 前端 `app.config.js` 内含 `D='p4q2.cn'` 域名替换代码
   (把请求里的模板域名替换成当前 origin) → 暴露模板源站。
2. **主 JS MD5 对比**: 三站 `assets/index-*.js` MD5 完全一致 = 同源码。
3. 证书对比: IP 直连的 TLS 证书 CN = 该站真实域名, 可识别同一服务器多域名。

## 前端 JS 静态分析(提取 WS 协议/密钥)
- 下载 `assets/index-*.js` 全部 chunk(`__vite__mapDeps` 列表 + 动态 import 的懒加载 chunk)
- 提取 `itype/subc` 枚举: `grep -oP 'itype:"[a-z_]+"'` → 得 w_pnl/w_cmd 协议
- 找 WS 连接: `new WebSocket("wss://"+host+"/api/ws/")`
- **AES 密钥硬编码**: 前端 JS 内嵌 AES-CBC 密钥+IV(用于加密下发账号), 配合 .env SECRET_KEY 可解全部设备回传
- localStorage 键: ACCESS-TOKEN / CURRENT-USER / CURRENT-EMAIL / CURRENT-AUTHORTY / CURRENT-ID

## WS 管理命令认证判断(关键)
- WS 监听 127.0.0.1:8080, nginx 反代 `wss://host/api/ws/` → REMOTE_ADDR 恒为 127.0.0.1
- 漏洞说 WS_ADMIN_TOKEN 为空时仅校验来源 IP → 反代下天然通过
- **实测判断**:
  - 空连接空闲 12s 仍 alive = 服务器不主动关
  - 发 w_pnl join → 被识别但静默(等设备)
  - 发 slr_panel/checkphone(管理消息) → **连接被关闭 = 服务端有 token 防护(已加固)**
  - w_pnl/checkphone(面板消息) → 无 cookie 被关闭 = 需登录会话
- 前端真实 checkphone 格式: `{itype:"w_pnl",subc:"checkphone",email:<CURRENT-EMAIL>,page,pageSize,filters:{}}`
- 管理消息 slr_panel: `{"itype":"slr_panel","subc":"checkphone","email":"admin@localhost","page":1,"pageSize":1000}`

## 部署环境差异(nginx vs Apache)
- nginx: `/api/ws/` 整个路径反代到 WS(连 .txt/.js 文件访问都是 426) → 漏洞6/10 日志文件泄露不成立
- Apache(原站): 仅屏蔽 .js/.exe, `api/ws/mov_*.txt`(160MB 连接日志/IMEI)、`private/Eaod_logs/*.json`、`.env` 全可下载
- **nginx 下仍可用**: `/api/log.txt` PHP 错误日志 Web 可读(287 条 SQL 错误, 泄露 root@localhost 数据库用户+密码登录, DB 服务拒绝连接)

## 已确认端点(三站一致)
- `/api/auth.php`(登录, 有 rate limit 429)、`/api/devices.php`(401 需 token)、`/api/remove.php`、`/api/settings.php`
- `/dl.php?pkg=xxx`(无参=Invalid, 无效包=Error, 参数化良好)、`/private/cb_custom.php`(POST 被 WAF 403)、
  `build_api.php`/`inventory_api.php`/`profile_api.php`(200 "Invalid request param." 需精确参数)
- 弱口令爆破全被 401/429 挡, .env 全变体(40+)封死

## 取证
- `/tmp/api_log.txt` — 数据库错误日志
- `/tmp/index.js` + `/tmp/all/*.js` — 前端全部 chunk

## 状态
- 2026-08-27: 新站已加固(.env 封/WS token/注册关闭/WAF), 无法完整复现; 仅 /api/log.txt 实锤
- 完整漏洞清单(10个)来自 mhm66.com 审计: .env 泄露/dl.php 硬编码/WS admin 绕过/cb_custom 伪造/assign IDOR/build_api appurl/日志泄露等
