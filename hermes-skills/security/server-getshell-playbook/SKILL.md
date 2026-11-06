---
name: server-getshell-playbook
description: "服务器抢shell实战: 十大getshell路径+2026在野利用案例+shell落地免杀。"
---

# 服务器抢 Shell 实战手册

针对「在目标服务器上获得命令执行能力(webshell/RCE/shell)」的完整方法论:六大攻击主路、十大 getshell 路径、2026 年在野利用案例、shell 落地与免杀、工具链。适用于授权渗透测试、CTF、服务器攻防。

## 何时使用

- 目标为 Web 服务器/中间件/CMS,需要 getshell(RCE/webshell/命令执行)
- 用户要求「抢 shell」「拿权限」「webshell」「getshell」
- 需要了解 2026 年正在被大规模利用的服务器漏洞
- 拿到 CMS/框架指纹后需要对应漏洞利用路径

## 实战纪律(2026-08 用户纠正)

```
0. 爆破是反复纠正的绝对禁忌(用户多次强烈纠正「不是说了别爆破了吗」「不爆破会死?」)
   - 短信验证码/密码/账号枚举的批量尝试都属于爆破范畴,禁止
   - 目标性弱口令仅限用户明确授权(「最多给你五分钟」),低频率 2-3s,超时立即转方向
   - 验证码绕过测试(任意值过格式校验)不是爆破 — 用【不存在用户】测,永不累计 loginfailure
1. 针对性优先: 只扫目标专属特征(品牌名/客服号/bot用户名/已发现域名),
   不要全网广撒网扫通用面板(用户明确纠正「不需要全网扫杂乱的面板,
   只要针对性扫目标专属bot面板」)。专属特征词命中数少, 免费引擎额度内即可覆盖。
2. 引擎选择: 优先 Fofa(中文特征强)/Shodan; Censys 是最后手段(免费版中文搜索弱,
   且新平台语法是 host.services.endpoints.http.* 不是 legacy 语法)。
   没有 key 时【教用户怎么注册】——给出注册步骤(网址/填什么/在哪拿 key),
   不要反复问「你有没有 key」(用户纠正「你教我怎么注册不就可以了吗,
   为什么要自作主张」)。
3. 复用已登录会话: 用户已登录的浏览器窗口不要要求重复登录(用户纠正
   「我不想重复登录了,你来找我已经打开登录的窗口吧」)。用 UI Automation
   直接控制已登录窗口: 枚举窗口(Get-Process chrome | Where MainWindowTitle)→
   地址栏导航(AppActivate + SendKeys "^l" + URL + {ENTER})→ 截图
   (GetWindowRect + CopyFromScreen)。保留 cookie 登录态, 不重启 Chrome 不丢 session。
4. 免费版限制(2026-08 实证): Shodan 免费账号只能看 2 页结果(会员 $69/月才能翻页);
   Shodan API OSS 计划 query_credits=0 搜索不可用(数据中心 IP 还常被 CF 403);
   Fofa 免费 100 次/天; Censys 免费 55 credits。→ 用【精准词】让命中 < 免费页数,
   而不是依赖大额度。
5. UI Automation 读取窗口文本: Add-Type UIAutomationClient → AutomationElement
   FromHandle → FindAll Descendants → Current.Name/ControlType。可读 Shodan 结果
   统计(1380 总数/TOP COUNTRIES/PORTS/ORGS), 但结果列表条目不一定全暴露。
6. 【绝不用本地真实 IP 干活】(用户纠正「哪有用本地真实ip干活的」)
   - 目标 IP 被封时: 自抓免费代理池恢复攻击(见「免费代理池自抓」),
     而不是关代理/断 TUN 直连暴露本机
7. 【先找已有方案,别重新发明】(用户纠正「直接去找之前的可执行方案不就行了吗」)
   - 卡住时: 先 session_search 历史 + 查已装 skill + 查攻击路径文档,
     再动手;猜新方案前先确认旧方案是否存在
8. 【卡住时自己抓资源别等用户】(用户纠正「你自己不会去获取点可用ip?」)
   - 代理池/验证码服务/漏洞 POC 都可以自抓: 免费 API/公开仓库/搜索引擎,
     不要停下等用户喂
9. 【收敛前确认全方向打尽】(用户纠正「你确定全部方向都打完了吗,
   我之前给你那么多参考的skill和路径」)
   - 想宣布"技术面穷尽/卡死"前, 先过一遍: 已装 skill 列表 + 攻击路径文档 +
     关联资产(邮箱域名/MX/工商法人/招聘) + 前端 JS 全量逆向 + 空间测绘
```

## 免费代理池自抓(IP 被封/需换出口时,2026-08 实战)

```python
# 1. 抓取(ProxyScan 免费 API,无需 key)
curl "https://www.proxyscan.io/download?type=http" -o proxies.txt   # 数千个
# 2. 验证: 并发 HTTP 代理连接目标,12s 超时
#    - HTTP 代理存活率远高于 SOCKS5(53/3611 可用 vs SOCKS5 免费池全灭)
#    - 验证标准: 能访问目标且非 403/超时 = 可用,存 working_http_proxies.txt
# 3. 使用: urllib ProxyHandler + 每请求轮换 + 失败重试(免费代理常 Remote end closed)
```
- 关键坑: 免费代理不稳定,多代理轮换 + 单请求重试;验证目标必须带 UA/X-Requested-With
- SOCKS5 免费池(proxyscan socks5/公开列表)存活率极低,优先抓 HTTP 代理

## 六大攻击主路

```
1. 文件上传 → webshell        (最经典, 占比最高)
2. 反序列化 → RCE              (Java/PHP/.NET, 高频)
3. 命令注入/表达式注入          (SSTI/OGNL/SpEL, 框架漏洞)
4. SQL 注入 → 写文件/读文件     (MySQL OUTFILE / MSSQL xp_cmdshell)
5. 已知 CVE 直接打             (Log4j/Struts2/WebLogic/Confluence/ThinkPHP)
6. 弱口令/配置错误 → 管理面     (后台/SSH/数据库 → shell)
```

## 2026 年在野利用热点(实时威胁,批量自动化是主流)

| 目标 | 时间 | 利用链 |
|------|------|--------|
| **ShowDoc**(中文开源) | 2026-04 | SQLi 拿 user_token → PHAR 反序列化(phpggc Guzzle/FW1 生成 phar.png)→ uploadImg 上传 → 触发反序列化写 webshell |
| **SharePoint** | 2026-07 | Web 请求 → 域接管(Resecurity) |
| **React2Shell** | 2025-12 | CVE-2025-55182 React Server Components 反序列化 → RCE |
| **Magento PolyShell** | 2026-03 | 多后缀图片 → 未认证上传 → RCE |
| **Coldcard 硬件钱包** | 2026-08 | 固件 PRNG 路由错误 → 种子复现 → $116M |

**核心趋势**: 2026 抢 shell 主力 = 已知 CVE 的批量自动化利用(nuclei + POC 脚本全互联网扫),不是 0day。中文开源项目是重灾区(ShowDoc)。

## 十大 Getshell 路径

### 1. 文件上传 → Webshell(最经典)
```
测试点: 头像/附件/导入/编辑器图片上传
绕过: 后缀黑名单(php5/phtml/phar) / Content-Type 伪造 / 图片马+包含 /
      双扩展名 / 大小写 / 空字节 / PolyShell(多 MIME 解析差异)
落地: /uploads/ 目录可执行性;蚁剑/冰蝎连接
案例: ShowDoc phar.png、Magento PolyShell、SPIP
```

### 2. 反序列化 RCE(Java/PHP)
```
Java: 找反序列化入口(HTTP头/请求体/Redis/Session)→ ysoserial payload
PHP: 找 unserialize() → phpggc 生成 phar → phar:// 触发
      → Guzzle/Monolog/Symfony gadget 链
案例: ShowDoc(unser.py + phpggc Guzzle/FW1)、Jenkins(CVE-2024-43044 文件读→RCE)
工具: ysoserial(Java)、phpggc(PHP)、ysoserial.net(.NET)
```

### 3. 框架表达式注入(SSTI/OGNL/SpEL)
```
SSTI: {{7*7}} 探测 → Jinja2/Twig/Freemarker
OGNL: Struts2 (%{...})、WebLogic
SpEL: Spring (#{...})
案例: WPML Twig SSTI → RCE(2024)
```

### 4. SQL 注入 → 写文件/命令执行
```
MySQL: SELECT ... INTO OUTFILE '/var/www/html/shell.php' (FILE 权限+目录可写)
MSSQL: xp_cmdshell 'whoami' → 开启后命令执行
PostgreSQL: COPY TO PROGRAM / lo_import
案例: ShowDoc 第一步就是 SQLi 拿 token
```

### 5. 已知 CVE 直接打(批量)
```
优先级: Log4j > Struts2 > WebLogic(CVE-2020-14882 路径穿越) > Confluence >
        SharePoint > Spring4Shell(CVE-2022-22965) > ThinkPHP 老 CVE
工具: nuclei(模板批量)、metasploit、searchsploit
要点: 老 CVE 批量自动化利用是 2026 主流(ThinkPHP/ShowDoc)
```

### 6. 管理后台 → 上传点/插件
```
后台弱口令/绕过 → 上传插件/主题/备份恢复点 → webshell
案例: WordPress 插件上传、Axis2 默认凭据(2024)
```

### 7. 中间件管理端
```
Tomcat Manager(弱口令 + WAR 部署)、WebLogic 控制台、JBoss jmx-console
```

### 8. 配置错误/信息泄露
```
.git 泄露 → 源码 → 密钥/接口;备份文件(.bak/.sql/.zip)→ 数据库凭据 → getshell
debug 模式开启 → LFI → RCE($15k writeup)
```

### 9. 供应链/依赖混淆
```
未声明 npm/pip 包 → 抢注同名包 → 供应链 RCE($2,500 writeup)
```

### 10. 基础设施信任链(高级)
```
过期域名/子域接管 → WHOIS/DNS 流量劫持 → 下游软件 RCE
案例: .MOBI TLD($20 买过期 WHOIS 域名 → phpWHOIS RCE + fail2ban 命令注入)
```

## Shell 落地与免杀

```
1. 落地位置: 优先 /uploads/ /tmp/ 或框架缓存目录(可写可执行)
2. 伪装: 图片马(合法头+代码)、日志马、缓存马
3. 连接: 蚁剑(AntSword PHP/JSP/ASP) / 冰蝎(Behinder AES加密) / 哥斯拉(Godzilla 强混淆)
4. 免杀: 编码混淆、内存马(Java Agent/Servlet)
5. 持久化: 计划任务/cron、开机自启、内存马、注册表(Win)
```

## WebShell 自愈(不死马/Phoenix)设计与 PHP 宿主注入陷阱(2026-08 实测)

**不死鸟 webshell 核心设计**(完整代码与清理流程见 `references/webshell-persistence-phoenix.md`):
- 三重不死: 母体落地即繁殖多副本后自毁 → 副本自带繁殖核心(副本数 < N 自动补种) → 宿主 index.php 注入内联繁殖器(全副本被删后访问 `index.php?phx_load=PASS` 可重生)
- 伪装: 随机文件名(cache_xxx.php,php 扩展名优先)+ 时间戳篡改(30-400 天前)+ 载荷双层 base64(解析安全 + 静态混淆)
- 副本模板用 base64 内嵌(避开复杂字符串拼接的引号/花括号解析问题),母体 PHP 用 `base64_decode('...')` 还原后 str_replace 密码占位符
- 落地验证: 本机 PHP CLI 内置服务器沙盒实测(`php -S 127.0.0.1:8899 -t sandbox/web`),验证 认证404/繁殖/自毁/副本功能/宿主重生

**⚠️ PHP 宿主注入经典陷阱(实测踩坑)**:
1. **注入到 `?>` 之后的代码不执行** — 宿主 index.php 结尾 `?>` 之后的注入内容被当纯文本输出,必须重新开 `<?php` 块
2. **剥掉 `?>` 再追加 `<?php` 是错的** — 变成 `<?php ... <?php` 嵌套开始标签,Parse error(unexpected token "<")。正确做法: **保留 `?>` 并在其后追加新的 `<?php ... ?>` 块**
3. **注释/字符串里的 `<?php` 会开启新 PHP 模式** — 注释行里写 `<?php` 字样会让词法器误判,导致后面字符串中的 `?>` 提前结束 PHP 块、括号失配。注释里写"PHP 开始标签"不要写字面 `<?php`
4. **块注释嵌套** — 块注释里写 `/*phx*/` 字样,内层 `*/` 会提前关闭外层注释。注释里写"phx 标记"不要写字面 `/* */`
5. **扩展名兼容性**: .php5/.phtml 在 PHP 内置服务器/部分 nginx 配置下不当 PHP 解析(直接吐源码)。副本首选 `.php` 扩展名

**FastAPI/Python 后端 RCE 攻击面优先级**(惊蛰量化实战,详见 `references/fastapi-rce-attack-surface.md`):
管理端执行引擎(backtest/run) > 指标/模板代码字段(indicator-definitions 可存任意 code) > 爬虫/同步接口(白名单) > 用户端编译器(pine/compile)
- "执行引擎活"判断: 错误从"参数校验"变成"业务执行错误"(不支持周期/数据不足)= 已进入执行链
- 白名单参数先探明(传 URL 看响应是否变化)再放弃,别浪费轮次


## 全文导航（已拆分）

主卡保留前 8 节；其余 4 节在 `references/full.md`：

- 方法论铁律
- 工具链
- 渗透报告交付工作流(2026-08-09 用户偏好)
- 参考文件

加载：`skill_view(name='server-getshell-playbook', file_path='references/full.md')`
