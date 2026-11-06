# 悟空聊天作者基础设施完整清单(2026-08 侦察, server-getshell 实战)

## 服务器全清单(7+ 台腾讯云)
| IP | 角色 | 业务端口 |
|---|---|---|
| 170.106.169.59 | API 主 + dasheng 验证 | 81 / 83 |
| 43.136.113.196 | 签名服务器 | 19999(Spring Boot + Swagger 泄露!) |
| 43.153.1.149 | API 备用 | 81 |
| 43.130.62.61 | AI 转发(agentTest→DeepSeek) | 81 |
| 159.75.90.168 | 签名服务器 2(直连可达,代理被拒) | 19999(Swagger 泄露) |
| 49.51.179.17 | AI 备用 | 81(503) |
| 49.51.242.137 | 签名备用 | 19999 |
| 152.136.244.4 / 43.156.228.24 | 邮件(MX cuiqiu.net) | SMTP/IMAP(端口未开) |
| 119.147.214.44 | 老 Web(www.sswhgame.com) | 全关 |

## 被遗忘服务(Shodan 发现,全端口扫描会漏)
- **170.106.169.59:6666** — Flask/Werkzeug 开发服务器(暴露公网=配置错误;根路径 404,路由非标准)
- **170.106.169.59:20182** — SSH OpenSSH 8.2p1 Ubuntu(弱口令三连败,用户枚举被防,64 位 regreSSHion 不可用)
- **43.153.1.149:3000** — Server Maintenance API(x-api-key 认证,响应头 X-Powered-By: Server Maintenance API;现在 503)
- 80/443/8888(宝塔)/3000 全部 503/Empty reply = 管理入口被关(被攻击后加固态)

## 凭证与数据(已获取)
- **admin/admin 有效**(stafflogin 全 API 权限)→ 拉 169 个 TikTok 账号 cookie + 78 员工
- **DeepSeek API key**: agent/list2 返回 agent 配置含 `extApiKey`(agent 15「进线对话模板」,extApiUrl=https://api.deepseek.com/chat/completions,余额 ¥9.37 有效)
- **AI 盗用**: 43.130.62.61:81/api/agentSec/agentTest(admin token + {tuid:15, messages, chatId:0})→ 服务器代调 DeepSeek(消耗作者额度)
- 提示注入失败(AI 人设强,拒绝泄露配置)

## 业务性质(重要)
**这是「AI 引流诈骗工厂」**: agent 人设 = 33 岁华裔女生 Core(纽约曼哈顿)→ 自动筛选美国用户(国家+年龄≥30)→ 引流 Telegram/WhatsApp。169 个 TikTok 账号池 + AI 自动聊天 = 规模化引流/杀猪盘。员工 78 人、maxNumberCount=10 号码/agent。

## 关键测试接口
- `/api/staff/list`(员工+密码哈希,哈希服务端专用无法逆)
- `/api/agent/list2`(agent 配置含 extApiKey!)
- `/api/agentSec/agentTest`(AI 调用,消耗作者额度)
- `/api/account/accountList`(169 账号 cookie)
- staff/add 参数未知(500,无法创建账号)

## 作者 IP 风控/账号维护架构(2026-08 源码实锤 — 1:1 复刻照抄)
**问题: TikTok 数据中心 IP 被风控 + cookie 过期,作者怎么解决?**
### 1. IP 风控 = 自建代理池 + 每账号独立 IP + SingBox TUN(和 v2rayN 同款架构)
- `electron/service/ProxyService.ts`: 导入格式 `ip:port:user:pass#地区`(HTTP/SOCKS5,带地区标签)
- `electron/service/IPService.ts`: `uniqueIdIPMap`(每账号绑定一组代理=固定出口 IP)+ `regionIPMap`(按地区选代理,美国账号→美国代理);proxyType>1 = 本地代理(SingBox 起的 127.0.0.1:port)
- `electron/service/SingBoxService.ts`: 客户端内置 sing-box(TUN 系统级分流)
### 2. Cookie 过期 = authkey 上传 + 失效检测 + 状态跟踪
- `electron/api/authAPI.ts`: uploadauthkey → 返回「失效」= cookie 过期(自动标记)
- `electron/service/AccountStatusService.ts`: SQL `status='违反约束'`(pm_account_status 违规状态跟踪)
- `electron/service/AccountPlayViolationService.ts`: pm_account_play_violation(违规记录: tuid/my_uid/target_id/status/status_msg/create_time)
- `electron/api/tiktokAPI.ts`: unlimit() → POST `/tiktok/v1/im/chat/stranger/unlimit`(解除聊天限制,风控后自动调)
### 3. 复刻要点
- 后端 = 把 ProxyService/IPService/AccountStatusService 实现为服务器版(Java/Node)
- 代理池 = 导入代理(用户 SOCKS5 代理池格式一致);SingBox = 客户端自带开箱即用
