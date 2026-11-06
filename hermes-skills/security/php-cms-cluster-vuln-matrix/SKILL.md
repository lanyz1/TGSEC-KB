---
name: php-cms-cluster-vuln-matrix
description: "Use when 打 PHP CMS 站（Drupal/Joomla/Moodle/Nextcloud/OpenCart）：17 条 SSRF、IDOR、SQLi、属性注入、越权下单。"
---

# Drupal / Joomla / Moodle / Nextcloud / OpenCart 漏洞矩阵（17 条，abraxas 2026-10 批次）

## 一句话
同一批来源（`github.com/abraxas`，2026-10-23 后推送）里的 17 个独立漏洞，按产品聚成一张矩阵。每条都有 PoC + README（Class / Reach / 精确版本 / 源码定位）。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `drupal-ckeditor-fileisimage` | High | Remote | Upload | CKEditor 5 image upload still skips FileIsImage |
| `drupal-htmx-attr` | High | Remote | XSS | AttributeXss still allows HTMX attrs |
| `drupal-move-block-markup` | High | Remote | XSS | Move Block sibling labels skip @label escaping |
| `drupal-oembed-ssrf` | High | Remote | SSRF | oEmbed discovery GETs an unscoped second-hop URL |
| `joomla-articles-catid` | High | Remote | ACL | POST /api/v1/content/articles ignores per-category ACL |
| `joomla-levels-api` | High | Remote | ACL | GET /api/v1/users/levels leaks view levels |
| `joomla-media-override` | High | Remote | Overwrite | media manager overwrite leftover |
| `joomla-menu-items-api` | High | Remote | ACL | menu items API leftover |
| `moodle-blackboard-img` | High | Remote | Path | Blackboard img src copies files outside the import tree |
| `moodle-enrol-database-sqli` | High | Remote | SQLi | enrol_database concatenates course idnumber into SQL |
| `moodle-enrol-database-sqli` | High | Remote | SQLi | enrol_database concatenates course idnumber into SQL |
| `moodle-grades-gradeitems` | High | Remote | IDOR | core_grades_get_gradeitems lists hidden grade items |
| `nextcloud-calendar-sharee-publish` | - | - | - | Nextcloud 35.0.0 — a calendar edit-sharee can publish the owner's calendar to an unauthenticated URL |
| `nextcloud-federated-ocm-token` | - | - | - | Nextcloud 35.0.0 — federated share secret is an unscoped app password for the sharer's whole Files tree |
| `nextcloud-ldap-put-isadmin` | - | - | - | Nextcloud 35.0.0 — delegated Users admin can PUT-edit an LDAP-promoted admin that PATCH correctly refuses |
| `nextcloud-webhook-tokenneeded` | - | - | - | Nextcloud 35.0.0 — delegated Webhooks admin can mint a 1h admin app password via webhook update tokenNeeded |
| `opencart-reward-free-checkout` | OpenCart | High 6.5 | Authenticated POST /index.php?route=extension/opencart/checkout/reward.save | Payment bypass (Free Checkout underpay) |

## 逐条要点（原文摘录）
### `drupal-ckeditor-fileisimage`
  - **Class:** Unrestricted upload / stored XSS
  - **Reach:** Remote
### `drupal-htmx-attr`
  - **Class:** Stored XSS
  - **Reach:** Remote
### `drupal-move-block-markup`
  - **Class:** Stored XSS
  - **Reach:** Remote
### `drupal-oembed-ssrf`
  - **Class:** SSRF
  - **Reach:** Remote
### `joomla-articles-catid`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `joomla-levels-api`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `joomla-media-override`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `joomla-menu-items-api`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `moodle-blackboard-img`
  - **Class:** File read
  - **Reach:** Remote
### `moodle-enrol-database-sqli`
  - **Class:** SQLi
  - **Reach:** Remote
### `moodle-enrol-database-sqli`
  - **Class:** SQLi
  - **Reach:** Remote
### `moodle-grades-gradeitems`
  - **Class:** IDOR
  - **Reach:** Remote

## 2026 扩展族未授权 RCE 批次（Joomla / WordPress，全部读过 PoC 文档）

这些不是核心洞，是**第三方扩展**的洞——CMS 本体升到最新也照样中。特征是「未授权 + 单请求 + 直接落文件」。

| CVE | 扩展 | 类型 | 版本 | 关键点 |
|---|---|---|---|---|
| CVE-2026-48909 | Joomla **SP LMS** | PHP Object Injection → RCE | ≤ 4.x | 扩展自带 `unserialize` 入口，无鉴权 |
| CVE-2026-56290 | Joomla **Page Builder CK** | 任意文件上传 → RCE | — | 未授权上传 |
| CVE-2026-85097 | **Bricksforge** | 上传 → RCE | ≤ 3.1.8.9（修 3.1.8.10 / 4.0.1） | 见下方三条链 |
| CVE-2026-48907 | Joomla **JCE** | RCE | — | 有现成框架 JCEzploit（交互 shell） |
| CVE-2026-102428 | Joomla **OS CCK**（`com_os_cck`） | 未授权 SQLi | 1.0.0–8.3.15（修 8.3.16） | `order_field` / `order_direction` 直落 **ORDER BY**，无白名单；同版还修了上传 RCE **CVE-2026-102427** |
| CVE-2026-3891 | **Pix for WooCommerce** | 上传 → RCE | ≤ 1.5.0 | 自动取 nonce |

### Bricksforge 那条链路值得单独记（CVE-2026-85097）

三个设计错误的叠加，每一步都能在别的扩展里复现：

1. **`temporaryFileUploads.url` 由客户端提交**——服务端不校验这个 URL 从哪来
2. **MIME 只在首次上传时检查**，后续 `copy()` 落盘时不再复检
3. **目标文件名 = `basename($url)`**——客户端给的 URL 尾部直接当落盘名

于是传 GIF/PHP polyglot：首次上传时 MIME 看到 `image/gif` 过了，`copy()` 按客户端给的 basename 写成 `.php`。

### 打这批的统一判据

```bash
# 扩展是否存在（Joomla）
curl -s "https://目标/index.php?option=com_os_cck" -o /dev/null -w '%{http_code}\n'
curl -s "https://目标/components/com_os_cck/" -o /dev/null -w '%{http_code}\n'
# 扩展版本（Joomla manifest）
curl -s "https://目标/administrator/components/com_os_cck/os_cck.xml" | grep -i version
# WordPress 插件版本
curl -s "https://目标/wp-content/plugins/payment-gateway-pix-for-woocommerce/readme.txt" | grep -i 'stable tag'
```

扩展版本比 CMS 版本重要：CMS 补了不等于扩展补了，而扩展更新率远低于核心。

## 怎么用
1. 先确认组件与版本（这批洞多数绑定精确小版本）。
2. 取原文：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md`。
3. `Remote` 先打，`Local`/`Authenticated` 留到有 shell 或低权账号之后。
4. 与既有专门卡（`gitlab-*`、`prometheus`/`monitoring-plane-unauth-recon`、`grafana`、`ftp` 相关）重叠时以专门卡流程为主，本卡补 2026-10 新洞。
