# 社媒筛选 SaaS（appfilter / 智域筛选 / Nexora 类）

## 指纹

- 官网 `www` 营销静态；业务常在 `app.` / `data.`（**data 可能 IP 限制，Tor/换出口**）
- `login.php` / `register.php`；cookie **`SM_PLATFORM_SESSION`**（HttpOnly，SameSite=Lax）
- robots 典型：`/user/` `/admin/` `/uploads/` `/config/` `/includes/`，data 还见 **`/scripts/`**
- 金币余额；USDT-TRC20 充值；`upload_task` 号码包；筛选类型 `filter_type_id`+单价
- 客服 TG：`@hoh5505` / `@appfilter`；data 页可能链 **`@exeprog_com`**（同收款生态）

## 用户指令：停爆破时（CRITICAL）

用户说「停止爆破 / 换手段 / 别只会爆破」→ **立即停** admin/MySQL/SSH 字典与 hydra。
优先非爆破面（顺序可并行）：

1. Session fixation / 会话固定钓鱼
2. 充值订单 **读** IDOR + proof 公网
3. 上传绕过 / MIME / 解析（RCE）
4. 业务逻辑（天价单、无 CSRF 下单、改密 CSRF）
5. 存储 XSS 饵挂待审（**审核端**）
6. 源码/配置路径、robots `/scripts/`、子域证书 SAN
7. app↔data 会话交叉、`error=disabled` 类中间件差异

字典只有在用户明确要喷雾、或其它面穷尽后长间隔补刀。

## 攻击顺序

1. 注册（余额 0 需管理员充值文案常见）
2. 弱口令 test/demo（**会失效**；失败就换注册号，别空转）
3. 用户面摸清：
   - `/user/dashboard.php` `/user/upload_task.php` `/user/tasks.php`
   - `/user/download_result.php?id=` `/user/download_uploaded.php?id=`
   - `/user/recharge.php` → 收款地址；**下单字段可能无 csrf_token**
   - `/user/recharge_detail.php?id=` + `action=upload_proof`
4. **Session fixation**：登录前固定 `SM_PLATFORM_SESSION`，登录后若 **不轮换** → 可钓（产物示例 `fixation_phish_*.html`）
5. **订单 IDOR 读**：登录后扫 `recharge_detail.php?id=1..N`（金额/状态/proof/TXID）
   - **写入**必须第二账号验证；同账号旧「待上传」单被自己 upload ≠ 跨用户写
6. download：未登录应 302；登录后跨用户 id 看 **Content-Disposition + 文件哈希**，勿只看 200 HTML 壳
7. proof：公网 `/uploads/proofs/`；试 polyglot/html.png/svg.png；看是否 `<img>` 引用、有无 `X-Content-Type-Options`、nginx 是否解析 PHP
8. 后台：`/admin/login.php`；**data 可能多 hidden `step=credentials`**（错 step 仅失败文案，未必已进 2FA）
9. 源站 nmap：22/3306 公网常见；config 路径 **200 空 body** = 执行无输出，不是没有文件
10. 特权用户名可注册（admin/root/administrator）**≠ 管理角色**；进 `/admin/*` 仍 302 登录才算

## XSS / 编码坑（必读）

- 用户端 TXID 常进 **`<code class="font-mono">` + HTML 实体**（`&quot;&gt;&lt;img...`）→ 源码里能搜到 `onerror` 字符串也 **不是执行型 XSS**
- 判定真 XSS：属性/标签未编码、或出 `<code>` 文本节点可打断 DOM
- 用户端编码 ≠ 放弃：payload 仍可进库，**赌审核后台未编码**；记录 oid 到 `XSS_HIT.txt`
- proof 用 `<img src="/uploads/proofs/...">` 时，HTML/SVG 内容默认不执行

## 认证中间件怪象

- **未登录 200 壳页**（dashboard/tasks/recharge GET）很常见；看「欢迎回来，」空用户 / 固定「用户」
- 敏感 **POST** 或 upload_task 仍可能 302 登录——GET 壳 ≠ 未授权写
- app 会话打到 data → 可能 `login.php?error=disabled`；data 注册「成功」后登录仍「错误」= 半残会话，换出口/浏览器/Turnstile
- 顶栏金币数字可能和实际上传校验不一致；以 upload 报错「需要: x 当前: y」为准

## 锚点 2026-09-10（appfilter）

- IP `43.128.88.176` · app / data / www · 证书 `line.appfilter.site`
- 活号示例：`api6rhbfw:Ap060154x`（会轮换；见目录 `ACTIVE_CREDS.txt`）
- TRC20 `TKSjmC4WhMJESoDVoTnHggKL76DJtbE5sa`（与 order 商城同址）
- 汇率常见 1U=6.7 金币、最低约 200U；ft=4 WhatsApp SVIP ≈ 0.00015/条 · min 2000
- 已验证：fixation、订单读 IDOR、天价待审单、proof 不解析 PHP、充值无 CSRF
- 未拿下：后台、getshell、MySQL；战报目录 `/root/pentest/data.appfilter.site/REPORT.md`
- test/test123 曾 1346 金币+任务 61/62 下载；后可能改密

## 坑速查

| 现象 | 含义 |
|------|------|
| download 200 大 HTML | 无权限壳，不是文件 |
| admin 200 → user dashboard | 无管理权限 |
| 注册成功同页 | 不一定自动登录 |
| 同账号 proof 写上「别人的」oid | 先确认 oid 归属，双号验证 |
| `onerror` 在 view-source | 检查 `<code>` / `&lt;` |
| config.php 200 空 | 执行无泄露 |
| `/scripts/` 业务 403 | 真实目录，非裸 nginx；试 IP/内网/认证后 |
| 子域全 403 | SAN 有名 ≠ 有站 |
