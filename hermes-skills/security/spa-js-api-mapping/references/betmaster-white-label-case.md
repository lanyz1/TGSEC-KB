# 案例：betmaster.com.mx（墨西哥白标博彩，2026-10）

目标形态：CF 前置 + SPA + 独立静态/图片云 + 独立公司基建域。本文件是「SPA 前端资产 → API 面测绘」的完整实例。

## 1. 关联面发现
- 主域 crt.sh（`https://crt.sh/?q=%25.<domain>&output=json`）→ 子域清单（appcheck/apuestas/blog/catrina/demo/play/preview 等）。
- 从 CNAME/证书链挖出：
  - `bmhub.io` — 公司基建（airflow/airflow-dev/jupyter/vault/grafana(infra)/django-admin(mt)/openmetadata/airbyte/status/derp）；「MT」= 独立环境名（与 main 并列），`mt.` 前后缀值得専门枚举。
  - `bmstatic.cloud` — 静态云：`src.`（SPA 资产源）+ `i.`（图片代理 imgproxy）。
  - `sptpub.com` — help center 独立域；兄弟域 `bmbet.mx`、`betmaster.click`。
- 兄弟域逐个过：同一套白标代码不同部署门禁可能不同（有域可能全裸）。

## 2. 配置与 JS 面
- 首页内联 `window.__ENV=`：品牌码、Sentry DSN、S3 桶、图片代理 URL、统计 ID。
- 资产源 `src.bmstatic.cloud/betmaster_mx/assets/`；主 bundle ~364KB + hash 目录 chunk；动态 import 跟着爬。
- 压缩 bundle 直接 grep 关键字全 0 命中 → 全量字符串提取后拿到：`/api/...` 路由表、`VND-bmt` 自定义头、`skid` 风控参数。
- Playwright 抓包补全 curl 看不到的流量（初始化顺序、上报域）。

## 3. API 面（本案例）
- 未鉴权：`/api/init/a`、`/api/init/b`（平台配置：MXN/墨西哥/license_id=3）、`/api/casino/catalog/restricted/v3`（~10MB 目录）、`/api/promotion-codes`、`/api/manifest`。
- 需登录（IDOR 候选）：`/api/payment/history/${id}/invoice`、deposit/withdraw 路由。
- 风控：`skid` 挑战路径；部分端点返回挑战结构，POST 被 openresty 403 → 复现请求头（`VND-bmt`）后再打。

## 4. 图片代理
- `i.bmstatic.cloud/_/<opts>/plain/<upstream>`：外链可代理（example.com 确认）；内网待细测（redirect/协议变体/DNS rebinding，先负对照）。

## 5. 接棒
- 基建管理面细节 → `oss-deployed-app-audit`（OpenMetadata 全流程见其 `references/openmetadata.md`）。
- 相机事故：登录/注册类表单的 PoW 或验证码门先读 JS 再复现，避免盲试触发封禁。

## 6. 账号生命周期（注册 → 登录 → 鉴权面）【2026-10 实测定稿】

- account_id 注册 → 响应含 `user.login`（数字账号）+ `credentials.password`（生成密码）+ 双 JWT（`api_auth_token` / `api_auth_token_promo_action`）。
- signin 后两 token 刷新；**promo token TTL 短（~40 分钟内即 `JWT token expired`）**——跨会话勿缓存，用前重登。
- promo-api 路径 `{user_id}` 必须用 **UUID（user.id）**：塞数字 login → 404/500（服务端崩）。
- 实测通的 promo 面：`/promo-api/{uuid}/meta|campaigns|participated-campaign-ids|finished-participants`、`/promo-api/campaigns/user-status?user_id={uuid}&campaign_ids=N`；token 走 `Auth-Token` 头（主 token 亦可读多数路由）。
- **跨账号探测（换他人 UUID）→ 500 崩服务**：数据边界守住（无 IDOR 收益），但「用别人 ID 就崩」= 健壮性缺陷，可入报告。
- 联系人加邮箱：`POST /auth/contacts {type:email, contact}` → 200 + `challenges_requested` + SendGrid 确认邮件（6 位码）。确认链与状态码语义见 `antibot-pow-reversal.md` §4b（本战役止步 4002，未走通成链）。
- 资料补全：`POST /auth/user/additional-registration-data {"personal_data":{"shape_id":"betmaster_mx","first_name":...,"last_name":...,"date_of_birth":...}}` → 201。
- 试玩通道：`POST /casino/auth/demo {game_id(整数), return_url, language}` → `launch_id` → `GET /casino/auth/demo/{launch_id}` → `game_url`（供应商域 + `stylename=btmb2b_betmastercommx` 类 b2b 命名）。
- 手机注册可达 OTP 界面（挑战已发），但公共收码号（quackr 等）整晚未收到短信——本战役被 account_id 通道替代，不靠 SMS。

## 7. torrero.cloud（开发公司基建域，2026-10）

- certspotter `torrero.cloud` → `admin/backend/frontend.casino2b.dev.torrero.cloud`（DEV 赌场三件套）+ `sentry.` + `mirrors.`（**要求双向 TLS**）+ `status.`（Better Stack）+ `hvm-*.{de,sbg}`（拒连）。
- **`docs.torrero.com` = 公开 Redoc 的运营商 API 文档**：页面 `spec-url="/openapi.json"` 一把拉全（8 端点：games / launch-game / launch-demo-game / freespin / freebet / revoke / callback）。
- casino2b backend（FastAPI）：`/api/games` 认头不认人——`X-Operator-Name` 后要求 `X-Sign`；**运算符枚举神谕**：`"Operator with name X does not exist"` vs 存在则 `"Wrong signature"`（实测仅有 `betmaster`）；X-Sign 构造矩阵 861 组（hmac256/512 × 6 消息变体 × 40 弱密钥）全灭——密钥不在弱字典内。
- admin/frontend 全站 403（疑似 IP 白名单）：XFF/X-Real-IP 伪造、Host 头模糊、路径绕过均无效；端口仅 80/443。

## 8. 接棒线索

- 同账号共享主机（Bluehost `*.wfi.cba.mybluehost.me` 别名，来自 CT 日志）：可绕 CDN 直打源站，但源站另有反爆破分层（406/409）——细节见 `app-layer-login-ratelimit`。
- 内网图（Airflow 连接）：`casino2b-databases.vpn.svc`（Casino2B 库）、`link-main-databases.vpn.svc`（ClickHouse main/main_wt/malta + MongoDB :27017，用户 analytics）——SSRF 原语存活时优先打这些。
