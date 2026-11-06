<!-- archived from /root/.hermes/skills/security/hama-apt-redteam/SKILL.md on 2026-10-21 -->

---
name: hama-apt-redteam
description: "APT 红队与 SRC 漏洞挖掘（WAF 内网免杀）"
---

> 归档卡：原目录 `/root/.hermes/skills/security/hama-apt-redteam`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hama-apt-redteam/…')`，不要相对 `references/legacy/` 解析。

# hama · 国家级APT攻防 & SRC漏洞挖掘总纲

全域攻击体系知识库：APT全生命周期 + 全栈漏洞挖掘 + SRC实战。结论先行、curl演示、输出完整PoC。

## 触发场景
- 任何 Web 漏洞挖掘 / 代码审计 / SRC 赏金 / 红队任务
- 注入类漏洞深度利用(SQLi/XSS/命令注入/文件上传/SSRF/反序列化/SSTI)
- WAF/EDR 绕过、内网域渗透、免杀、持久化、云原生攻击

## 核心章节索引（完整细节见 references/hama.md）
- 1.5 SRC高价值漏洞类型(中高危优先) + 实战思路（资产测绘/入口定位/逻辑漏洞套路）
- 3 漏洞类型全景 A-S（认证/越权/注入/XSS/CSRF/文件/SSRF/反序列化/业务逻辑/竞态/信息泄露）
- 5 可利用性评估模板（复现/前置条件/影响面/成本/优先级P0-P2）
- 6 输出格式（结论先行→复现证据链→根因→修复）
- 7 代码审计危险函数速查(PHP/Java/Python/Node/Go)
- 10 30秒快速排查清单
- 11 高级注入技术体系：
  - 11.1 SQL注入（各DB深度利用+WAF绕过全集）
  - 11.2 XSS（mXSS/CSP绕过/DOM XSS/Blind XSS）
  - 11.3 命令注入（盲注/反弹shell/无字母数字RCE）
  - 11.4 文件上传（后缀/内容/二次渲染绕过+WebShell/内存马）
  - 11.5 SSRF（gopher全协议+云元数据+绕过）
  - 11.6 反序列化（Java/PHP/Python/.NET Gadget链）
  - 11.7 HTTP请求走私（CL.TE/TE.CL/H2走私）
  - 11.8 缓存投毒与缓存欺骗
  - 11.9 认证协议（OAuth2/JWT/SAML）
  - 11.10 前端攻击（原型污染/Service Worker/WebSocket/DOM Clobbering）
  - 11.11 SSTI（Jinja2/Velocity/Freemarker/Thymeleaf/Twig等引擎）
  - 11.12 中间件漏洞（Nginx/Apache/IIS/Tomcat/WebLogic/JBoss/Spring/Django/Laravel）
- 15.5 攻击链组合/WAF对抗/竞态/GraphQL/边界设备
- 16-17 APT生命周期(MITRE ATT&CK)+初始访问(钓鱼/水坑/供应链/近源)
- 18 武器化（Shellcode/Loader/诱饵文档/代码签名）
- 19 内网域渗透（AD攻击路径/横向移动/提权）
- 20 免杀与EDR对抗（AMSI/ETW/直接系统调用/Unhooking）
- 21 C2基础设施（Domain Fronting/流量伪装）
- 22 高级持久化（用户态/内核级/Linux）
- 23 反取证与OPSEC（日志清除/时间戳/内存取证对抗）
- 24 0day研究（漏洞挖掘方法论/利用开发/浏览器漏洞）
- 25 云原生攻击（AWS/Azure/容器逃逸/K8s）
- 26-29 工控SCADA/隐蔽信道/硬件固件/无线电
- 30 APT工具武器库 / 31 实战心法

## 关键速查
- 危险函数: PHP(eval/assert/system/unserialize) Java(Runtime.exec/readObject/JNDI/SpEL) Python(eval/pickle/yaml.load) Node(eval/child_process/__proto__) Go(os/exec/text/template)
- 工具: Burp/Yakit/nuclei/xray/sqlmap/dalfox/dirsearch/ffuf/subfinder/amass/ysoserial/phpggc
- Web请求统一 curl，不用 fetch
- 常用云元数据: AWS 169.254.169.254 / 阿里 100.100.100.200 / 腾讯 metadata.tencentyun.com
