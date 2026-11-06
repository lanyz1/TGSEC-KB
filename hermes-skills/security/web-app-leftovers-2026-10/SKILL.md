---
name: web-app-leftovers-2026-10
description: "Use when 打 Magento/PrestaShop/Moodle/Plausible/OpenMeetings/PHP 自研栈：10 月批次 6 组「安全版本后残留」，含 0.01 改价、可预测重置令牌。"
---

# Web 应用「安全版本后的残留」6 组（2026-10 批次）

## 一句话
这批全是**厂商刚发完安全版本、公告没覆盖到的相邻代码**：拿它当「最新版就安全」的反例，也是找新洞的标准位置——安全发布日就是猎场开张日。

---

## 1. Magento 2.4.8-p5 Instant Purchase：`custom_price` 改价（未分配 CVE）
- 根因：`InstantPurchase` 把**每个 POST 字段**塞进 `buyRequest`，因为 `$knownRequestParams` 是**列表**而代码用 `isset()` 查**键** → 过滤形同虚设。
- 差别：Checkout 的 `RequestInfoFilter` 会剥 `custom_price`，**Instant Purchase 不剥**；随后 Quote Processor 调 `setCustomPrice`。
- 效果：目录价 99.99 的商品，实验室下单实付 **0.01**。访客加购**不是**这个洞（那是另一条路）。
- PoC：`abraxas/magento-instant-purchase-custom-price`（loopback lab，含 `InstantVault` 模块）。
- 测法：登录用户走 Instant Purchase（需已存地址/支付），POST 里加 `custom_price=0.01`，看订单行 `price`。

## 2. PrestaShop 9.1.5 前台找回密码：令牌可预测 → 未授权 ATO
- 公式：`token = sha1(time() . id_customer . '-' . secure_key)`。
- 关键：**订单确认页的 `key=` 就是 `secure_key`**（游客下单即可拿到），`id_customer` 是自增。
- 另一脚：`POST /password-recovery` **即使发信失败也会写 token** → 不需要邮箱、不需要收信。
- 于是：`time()` 在一个可枚举窗口内 → 秒级爆破出 token → 重置任意用户密码。
- 定级：CWE-330/CWE-640，CVSS3.1 **9.1**（`AV:N/AC:L/PR:N/UI:N`）。PoC：`abraxas/prestashop-reset-token-predict`。

## 3. Moodle 5.2.3 `core_grades_get_feedback` 组间 IDOR
- 只校验 `gradereport/grader:view`，**缺 separate-groups 检查**（MSA-26-0016 只补了别的成绩服务）。
- 条件：非编辑教师、课程开「Separate groups」、攻击者在 A 组。
- 效果：AJAX 读 B 组学生的评语 + **邮箱**。PoC：`abraxas/moodle-grades-feedback-idor`。

## 4. Plausible Analytics master `d44e104`：两条叠加 = 站点接管
- ① 访客编辑能在 People 页 HTML 里读到**待确认的所有权转移 nanoid** → 自己注册后 `accept` → 拿到站点所有权。
- ② `PUT traffic-change-notification` 仍强制 `site_id` → 自己站点的编辑把「流量突增通知」重挂到受害者站点（钓鱼/骚扰面）。
- 注：CE 最后 tag `v3.2.1` 落后 5 个月，SECURITY.md 让运营跑 `:latest` —— 等于跑 master。

## 5. Apache OpenMeetings 9.1.0（刚修完 CVE-2026-49488）残留四条
- **日历覆盖**：LOGIN 用户保存日历事件会覆盖别人的会议，并把公开房间关掉。
- **`/install` 向导**残留：可再种一个 **ADMIN**。
- **官方 KMS docker**：`8888` 上 **未授权 JSON-RPC**。
- **ADMIN_BACKUP 导入**仍跳过 `Path.of` 校验（路径穿越写）。

## 6. PHP2Shell：CVE-2026-109618 / 109619（引擎层，先于应用代码）
- 版本：PHP **8.2 < 8.2.35、8.3 < 8.3.36、8.4 < 8.4.27、8.5 < 8.5.12**（2026-10-21 修）。lab 钉 `php:8.4.26-apache` / `php:8.5.11-apache`。
- **109618**：multipart 解析期 **OOM → longjmp**，发生在应用代码之前（未授权可达）。
- **109619**：同一 worker 上**陈旧 fatal 回溯的 UAF**。
- 作者实测结果是 **OOM abort + UAF/崩溃**；公告推断的 RCE 未在其 lab 复现 —— 判定时按「崩溃/DoS 已证、RCE 未证」处理，别直接当 RCE 用。
- 探测：`POST` 大 multipart 打 `mod_php` 目标，看 500/进程崩溃与 `error_log` 里 longjmp/OOM 痕迹。

---

## 通用打法
1. 拿到版本先看**最近一次安全公告修了什么**，然后去打公告**没提**的相邻功能（同模块的兄弟接口、同参数的其他消费者）。
2. 电商三条永远值得看一眼：`custom_price` 类字段是否被下游消费者信任、找回密码令牌的随机源、组/租户隔离检查是否只加在一个入口。
3. 「最新版 = 安全」是错的，这批 6 组里 5 组都在最新版上。

## 出处
`abraxaslabs.tech/research/`：`magento-instant-purchase-custom-price`、`prestashop-reset-token-predict`、`moodle-grades-feedback-idor`、`plausible-analytics-leftovers`、`openmeetings-9-1-0-leftovers`、`php2shell`；对应 PoC 仓同名。
相关卡：`business-logic-payment`、`gambling-password-reset-ato`、`php-framework-debug-leak-pentest`。
