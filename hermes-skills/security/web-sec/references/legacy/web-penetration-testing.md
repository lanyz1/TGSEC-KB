<!-- archived from /root/.hermes/skills/security/web-penetration-testing/SKILL.md on 2026-10-21 -->

---
name: web-penetration-testing
description: >-
  测绘引擎·针对中文博彩/会员系统的Web渗透测试实战方法论。涵盖API参数探针、ThinkPHP漏洞利用、WAF指纹识别与绕过、域名关联分析、多站点横向渗透等核心技术。
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/web-penetration-testing`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/web-penetration-testing/…')`，不要相对 `references/legacy/` 解析。

# web-penetration-testing（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/web-penetration-testing/`

溯源（仅标记）：`hermes/security-research`

---

# 🎯 Web渗透测试实战方法论

> 基于真实渗透实战：9581kk.com / 6533388.com / 72886mm.com / 9599wm.net + 42关联域名

---

## 一、核心原则

| # | 原则 | 说明 |
|:-|:-----|:-----|
| 1 | **API错误消息是最大的信息泄露源** | `缺少必要参数X` → 直接告诉你下一个参数名 |
| 2 | **主站不通就切域名** | 同一网络42个域名，总有一个防御最弱 |
| 3 | **先批量扫，再精确定位** | 不要一开始就深度分析，全端口+全路径扫一遍再说 |
| 4 | **WAF阻挡≠无漏洞** | 换编码/注释/Content-Type，总有一种绕过方式 |
| 5 | **JS文件是金矿** | 总有API端点、后台路径、硬编码凭证藏在JS里 |
| 6 | **同一个账号可能跨站可用** | 博彩站群的账号体系常常互通 |
| 7 | **永远不接受"被封"作为终点**  | IP被封、端口被关、WAF拦截都不是死路——换子域名、追源站IP、换端口、换协议、换工具链，先找10种替代方案再报告失败。用户不接受"因为被封所以做不了"的理由。用户会说"想办法解决不就行了"——那就解决。 |
| 8 | **验证码0延迟交给人类** | 遇到验证码时，**不要尝试任何 OCR/自动化识别/暴力破解**——BetWin验证码是字母数字混合（36^4空间）且纯色图像不可解析。直接一句话告诉用户"验证码在桌面，帮我看一下"，把图片路径用 `MEDIA:` 协议发给用户。用户已因 OCR 尝试失败而明确表达不满——听他的，别试。 |

---

## 分册索引（references/ · 按需加载）

> 主体只留原则/流程/偏好；细节按主题外置，避免单文件撞 100K 上限。

| 分册 | 内容 | 何时读 |
|------|------|--------|
| `references/core-techniques.md` | 核心技术：API 参数探针、ThinkPHP 漏洞利用、WAF 指纹识别与绕过、域名关联分析、多站点横向渗透 | 起手通用手法 |
| `references/system-fingerprints-gambling-cms.md` | 识别速查 A：**BetWin CMS** 全套(4.8-4.12 注册/登录/代理注册 API)、JSFuck 反爬（4.0）、jQuery 版本（4.2）、备份文件探测（4.3）、隐藏表单绕过（4.5）、`is_login` 陷阱（4.6）、ThinkPHP VIP 充值账户枚举（4.15）、GET 设备模拟 | 摸到博彩站框架后 |
| `references/system-fingerprints-frameworks.md` | 识别速查 B：GetCompany 域名集群（4.14）、外链提取关联域名（4.16）、ASP.NET MVC 多层架构（4.17）、New API 中转站（4.18）、ASP.NET WebSocket GenerateSign+JWT（4.19） | 判框架 / 找同后端站 |
| `references/finance-systems.md` | 金融/券商专项：**Spring Boot Actuator 信息泄露检测**（401≠404）、外汇券商/金融 IB 系统 API 探测模式 | 打到金融/券商系统 |
| `references/toolchain.md` | 工具链：Python 便携端口扫描（无 nmap/dev-tcp 时）、BitBrowser API 不可用时的 CDP 替代、SearXNG、puppeteer | 环境搭建 |
| `references/authorization-fraud.md` | 授权书真伪验证（识别伪造授权）与欺诈防范 | 接单前合规 |
| `references/ai-pentest-tools.md` | AI 渗透测试工具部署（Strix 等） | 部署 AI 辅助 |
| `references/` 下另有 48 个**按目标/主题命名**的实战案例分册（9581kk / betwin-cms / ecmarkets / x3891-vip / kk-tg / faka-epay / captcha 等） | 命中同类目标时直接查 | — |

## 30 秒速查

```bash
# 5 步法: 指纹采集 → 框架判定 → 漏洞匹配 → 利用验证 → 横向扩展
# 通用手法(API 探针/WAF 绕过/域名关联) → references/core-techniques.md
# 已识别 CMS/框架 → references/system-fingerprints-*.md
# 拿到源码包先查后门 → references/php-source-audit-methodology.md
# 环境/工具 → references/toolchain.md   |   金融券商 → references/finance-systems.md
```

---

## 二、五步法渗透流程

```
Step 1: 情报搜集
  ├─ **子域名枚举**: crt.sh JSON API → 提取 name_value 中的子域名
  ├─ **DNS 链追踪**: nslookup 逐级解析 CNAME 链找到真实基础设施（CDN背后服务器）
  ├─ **DNS 爆破**: 对60+常见子域名用 nslookup 逐一检测
  ├─ **全端口扫描**（80/443/8080/8443/8888/7777/9090 + 21/22/3306/3389）
  ├─ **多端口 HTTP 探测**: 同一域名在不同端口可能跑不同服务面板
  ├─ 提取关联域名（页面外链、JS CDN、客服系统域名）
  └─ JS文件提取所有API/后台路径

Step 2: WAF指纹识别
  ├─ 发送已知攻击payload → 观察拦截特征
  ├─ 测试关键payload: ' , <script>, ../, OR 1=1, UNION SELECT
  └─ 识别WAF类型（ModSecurity 406 / Cloudflare / 阿里云WAF等）

Step 3: API参数探针（核心）
  ├─ 找到API入口（/api/、/?service=、模块路由等）
  ├─ 发送最小参数 → 读"缺少必要参数X"错误
  ├─ 添加参数X → 重复直到"缺少"错误消失
  └─ 逐层逼近完整参数集

Step 4: WAF绕过 + 漏洞测试
  ├─ ModSecurity: /**/OR/**/、URL编码、%00、%0a、%09 绕过
  ├─ ThinkPHP: ?s=路由、/runtime/log/ 日志泄露、Debug模式信息收集
  ├─ 验证码: 检查JS是否注释掉HTML验证码块；yzm.php返回值分析
  └─ 注册接口: 参数名猜测（username/uname/account）

Step 5: 横向渗透 + 权限提升
  ├─ 用已发现的凭证尝试登录所有关联域名
  ├─ 从会员权限找管理后台入口
  ├─ 从ThinkPHP Debug页面提取数据库/SQL信息
  └─ 检查Cookie安全（HttpOnly/Secure）、Session固定
```

---

---

## 🚫 用户偏好（从历史会话提取 — 必须遵守）

| # | 偏好 | 说明 |
|:-|:-----|:------|
| **任务绝对隔离** | 每个渗透目标必须独立对待，**绝不能把不同系统的资产/发现混在一起分析**。用户说\\\"不要和之前的混在一起\\\"、\\\"这是底线不要触碰\\\"——那就一个字都不关联。建独立的报告、独立的变量、独立的 skill 记录。用户发一个全新URL时,意味着\"和前面所有对话完全无关的开始\"——当前对话中前面的渗透目标、域名、凭证、发现全部丢弃,只聚焦新URL。特别地：**博彩站(gambling/BC站/BFCP) 和 外汇券商(forex broker/EC Markets/IB Portal) 是完全不同的项目**，不能混用同一个分析上下文、同一个API模式或同一套凭证。|
| 2 | **行动优先，解释靠后** | 用户说\"你不要逃避\"、\"想办法解决不就行了\"——先动手找出至少一种可行方案，再简要报告。不要长篇分析为什么做不了。失败后提供替代路线，不要停在\"做不了\"上。 |
| 3 | **直接给结果** | 用户不要你问\"你想怎么做\"，直接执行最优方案，用户会自己说下一步。问决策问题等于在推卸判断责任。 |
| 4 | **不接受"被封"作为终点** | IP被封、CDN限流、WAF拦截都不是死路。换子域名、追源站IP、换端口、换协议（HTTP/HTTPS/WS）、换工具链、用BitBrowser等，永远有替代方案。 |
| 5 | **不逃避问题** | 当用户说"不能逃避问题"时，意思是**必须攻克当前阻塞点**，而不是绕过。用户不接受"这路不通了咱们换个方案"——报告真实状态可以，但不能停在"做不了"上。先穷举所有可能的数据源（API/DOM/Vue Store/WebSocket/DNS/隐藏元素），逐个确认不存在数据后才报告不可行。诚实报告比绕过问题更重要。 |

---

---

**拿到 PHP 源码包先查后门**（header-eval 后门 / register_globals 变量注册 / IP 白名单伪造 / 2FA 绑定缺陷等模式与审计顺序）见 `references/php-source-audit-methodology.md`；实战案例 `references/kk-telegram-gambling-source-audit.md`。
