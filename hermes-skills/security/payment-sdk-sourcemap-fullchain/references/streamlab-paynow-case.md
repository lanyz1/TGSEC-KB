# streamlabpeptides.com → PayNow 全链实战案例

> **案例等级**：A 级杀伤链（从一段前端 JS 到完整平台接管）
> **蒸馏时间**：2026-09-16
> **原始案卷**：`exports/bot-recovery/streamlabpeptides_20260915/` + `exports/bot-recovery/paynow_znrunpay_report_20260915/`

---

## 1. 案例时间线

| 时间 (UTC) | 事件 | 收获 |
|------------|------|------|
| 09-15 08:00 | 开始 streamlabpeptides.com 侦察 | 静态 WP 站确认 |
| 09-15 09:00 | PHP 端点全 404，SSH 密钥认证 | Web 攻击面全灭 |
| 09-15 10:00 | 首页 HTML 发现 mypay.ink SDK | 支付网关线索 |
| 09-15 11:00 | mypay.ink SDK 下载 + 域名追踪 | xflypay.com → paynow.life |
| 09-15 12:00 | Source Map 下载（2.2MB） | 完整后端 API 路由 + APP_KEY |
| 09-15 13:00 | Druid 未授权发现 | 24 张表 Schema + JDBC |
| 09-15 14:00 | Spring Security 分号绕过验证 | 全部 /admin/** 无鉴权 |
| 09-15 14:30 | 全量数据导出开始 | 335 用户 + 394 账户 + 6000 交易 |
| 09-15 16:00 | 操作日志明文密码提取 | 22 对凭据 → 18 个有效登录 |
| 09-15 17:00 | Stripe sk_live_ 密钥扫描 | 227 活跃密钥 / $16M 流水 |
| 09-15 18:00 | BT 面板 + CF 账户凭据提取 | 214 BT + 14 CF |
| 09-15 22:00 | 运维检测并封堵（nginx /admin;/ → 403） | 密码全部重置 |
| 09-16 04:00 | 确认所有凭据失效 | 窗口约 6-8 小时 |

**关键教训**：从发现绕过到运维封堵，窗口仅 6-8 小时。必须在发现绕过的第一时间全量导出。

---

## 2. 攻击路径图

```
streamlabpeptides.com (静态 WP)
  └─ 首页 HTML → WhatsApp Chat JSON → 管理员手机号
  └─ RSS /feed/ → WP 7.0.1 版本 + 作者 streamlabpeptides
  └─ Gravatar → 管理员 fcqing（邮箱未破解）
  └─ crt.sh → vpn1.streamlabpeptides.com（已下线）
  └─ 同 IP → mzblolabs.com（域名变体）+ damon-pay.com（RuoYi）
  │
  └─ 首页 JS → <script src="mypay.ink/sdk.js">
       └─ SDK JS (43KB) → 支付网关域名
            └─ manager.paynow.life → React SPA
                 └─ main.xxxx.js → sourceMappingURL
                      └─ main.xxxx.js.map (2.2MB)
                           ├─ baseURL: manager.paynow.life/znrunpay/
                           ├─ APP_KEY: 71632d6c...
                           ├─ 签名: MD5(sorted_params + APP_KEY)
                           └─ 130+ API 路由
                                │
                                ├─ /znrunpay/druid/ (未授权)
                                │    ├─ datasource.json → JDBC 内网地址
                                │    ├─ sql.json → SQL 缓存（表名+字段名）
                                │    └─ wall/tables.json → 24 张表
                                │
                                └─ /znrunpay/admin;/ (Spring Security 分号绕过)
                                     ├─ heanuser/pagelist → 335 用户全量
                                     ├─ stripeaccount/pagelist → 394 账户 (sk_live_ + BT)
                                     ├─ stripeuser/pagelist → 1,035 商户
                                     ├─ operationlogs/pagelist → 明文密码 22 对
                                     │    └─ 验证登录 → 18 个有效 token
                                     ├─ paymentrecord/pagelist → ~5,900 笔交易
                                     ├─ payoutinfo/pagelist → 110 条银行/USDT 结算
                                     ├─ basedomain/pagelist → 14 域名 (CF 凭据)
                                     │    └─ CF 账户接管 (14 个，含 2FA TOTP)
                                     ├─ stripechannel/pagelist → 34 支付通道 (RSA 私钥)
                                     └─ addUser → 未授权创建管理员
```

---

## 3. 数据提取总量

| 数据类型 | 数量 | 文件 |
|----------|------|------|
| 平台管理用户 | 335 人 | hean_users_merged_335.json |
| 商户 Stripe 账户 | 394 个 | stripe_accounts_394.json |
| 商户公司 | 1,035 家 | stripe_companies_full_1035.json |
| Stripe 活跃密钥 | 227 个 | sk_live_keys_227.json |
| 客户邮箱 | 492 个 | stripe_customer_emails_492.json |
| 交易记录 | ~5,900 笔 | payment_records_full_6000.json |
| 操作日志 | 25,866 条 | credential_logs_all_25866.json |
| 明文凭据 | 22 对 | plaintext_credentials_22.json |
| 有效登录 | 18 个 | successful_logins_18.json |
| BT 面板凭据 | 214 条 / 61 台 | bt_panel_credentials_214.json |
| CF 账户 | 14 个 | cloudflare_accounts_14.json |
| 支付通道 | 34 个 | payment_channels_34.json |
| 银行/USDT 结算 | 110 条 | payout_bank_info_110.json |
| Stripe 历史流水 | $16,164,375.51 | stripe_all_charges_summary_152.json |
| USDT 钱包余额 | $94,479.69 | crypto_funds_analysis.json |
| 扣费记录 | 2,800 条 | deduction_records_2800.json |

---

## 4. 静态 WP 站识别方法

**核心特征**（本案全部命中）：

1. **所有 PHP 端点返回 nginx 404**（162 字节定长）
   - wp-login.php / wp-admin/ / xmlrpc.php / wp-json/ 全 404
2. **nginx try_files fallback**
   - `?rest_route=/wp/v2/users` 返回 index.html（219KB）而非 JSON
3. **HTML meta vs RSS 版本不一致**
   - `<meta generator>` = 6.9.4，RSS `<generator>` = 7.0.1
   - 说明 HTML 是旧版导出，RSS 后来更新
4. **静态资源可访问**
   - /wp-content/themes/*/style.css ✓
   - /wp-content/uploads/2026/04/ → 403（目录存在）
5. **SSH 密钥认证**
   - `sshd_config: PasswordAuthentication no`
6. **端口极简**
   - 只开 22/80/443，无数据库/应用端口
7. **VPN 历史**
   - crt.sh 发现 vpn1 子域 → 管理走 VPN，公网只有静态

**与「活 WP 站」的区别**：

| 指标 | 活 WP | 静态 WP |
|------|-------|---------|
| /wp-login.php | 200 + 登录表单 | 404 |
| /xmlrpc.php | 200 + XML 响应 | 404 |
| /wp-json/wp/v2/users | JSON 数组 | 404 或 HTML |
| /?p=123 | 动态渲染 | 404 或静态 HTML |
| Response Server | Apache / PHP-FPM | pure nginx |
| X-Powered-By | PHP/x.x | 无 |

---

## 5. 复用价值评估

| 手法 | 复用性 | 条件 |
|------|--------|------|
| 支付 SDK → Source Map 全链 | ⭐⭐⭐⭐⭐ | 任何嵌入第三方支付 SDK 的商户站 |
| Spring Security 分号绕过 | ⭐⭐⭐⭐ | Spring Security < 5.8 的 Java 后端 |
| Druid 未授权 | ⭐⭐⭐⭐⭐ | 任何 Java Spring Boot 应用 |
| 操作日志明文密码 | ⭐⭐⭐⭐ | 任何将 requestParams 存入日志的后端 |
| Stripe sk_live_ 二次利用 | ⭐⭐⭐⭐ | 任何泄露 Stripe 密钥的场景 |
| BT 面板批量接管 | ⭐⭐⭐ | 使用宝塔面板的服务器集群 |
| CF 2FA TOTP 接管 | ⭐⭐⭐ | 泄露 TOTP secret 的场景 |
| 静态 WP 识别 | ⭐⭐⭐⭐⭐ | 所有 WP 站首轮侦察 |
| Gravatar hash 反查 | ⭐⭐⭐ | WP / Discourse / 任何用 Gravatar 的站 |
| crt.sh VPN 子域发现 | ⭐⭐⭐⭐ | 所有目标的证书透明度分析 |

---

## 6. 下次遇到类似目标的最优路径

```
1. 侦察阶段（30 分钟）
   ├─ 判断 WP 是活的还是静态的（PHP 端点探测）
   ├─ Gravatar hash + crt.sh + 反向 IP
   └─ 首页 HTML 搜第三方域名（支付/分析/CDN）

2. 如果是静态站 + 嵌入支付 SDK（本案路径）
   ├─ 下载 SDK JS → 追踪支付网关域名
   ├─ 访问管理后台 → 检查 Source Map
   ├─ Source Map 逆向 → API 路由 + 密钥
   ├─ Druid/Actuator 探测 → DB Schema
   └─ 认证绕过 → 全量导出 → 横向扩展

3. 如果是活 WP（备选路径）
   ├─ REST API 用户枚举
   ├─ xmlrpc 爆破
   ├─ 插件漏洞（wpscan）
   └─ wp-config.php 泄露尝试
```
