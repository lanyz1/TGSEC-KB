<!-- archived from /root/.hermes/skills/security/leftover-installer-takeover/SKILL.md on 2026-10-21 -->

---
name: leftover-installer-takeover
description: "Use when 目标暴露活体安装向导(install.php/setup.php)或重装面板。"
license: MIT
metadata:
  hermes:
    tags: [pentest, web, php, installer, credential-reuse, oracle]
    related_skills: [admin-credential-hunt, admin-cred-and-auth-bypass, recon-discriminators]
---

> 归档卡：原目录 `/root/.hermes/skills/security/leftover-installer-takeover`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/leftover-installer-takeover/…')`，不要相对 `references/legacy/` 解析。

# 残留安装向导:判定、DB oracle 与安全推进

「装完没删」的安装向导是一条独立入线:自带**非破坏性 DB 认证 oracle**(校验凭据 / 探库名存在性 / 验同族站凭据复用);潜在「重装重置管理员」路径;且因是独立端点,后台登录面被锁/限速时是**正交推进方向**。

## When to Use

- 目标暴露 `/install.php` `/install/` `/setup.php` `/setup/` `/api/init` 等安装/初始化向导(尤其「装完没删」的老站/自研站)
- 手上有兄弟站/调试页/报错帧/备份包泄露的 DB 凭据,要做**非破坏性**验证
- 后台登录面被锁定/限速,需要换不同机制的入口继续推进

## 流程

### 1. 判活与读全

```bash
curl -s http://T/install.php -o inst.out   # 抓全落盘, 别截断
```

读:步数(step 1/2/3)、表单字段名、默认值、隐藏 action、页内 JS 指向的 AJAX 端点。
**活体特征**:POST 空字段回**带错误文案的原表单页**(不是 404/静态壳)= 校验逻辑在跑。

### 2. 预检端点 = 非破坏性 DB 认证 oracle(核心)

单文件安装器常带 `?action=test_connection`(或 `check_db`/`test_db` 类)AJAX 端点:POST `host/username/password/database` → JSON `连接成功/失败`。**全部零副作用,可安全反复调用**:

```bash
curl -s -X POST 'http://T/install.php?action=test_connection' \
  --data-urlencode 'host=127.0.0.1' --data-urlencode 'username=U' \
  --data-urlencode 'password=P' --data-urlencode 'database=DB'
```

1. **逐条验证候选凭据**:多 host 变体各打一发(`127.0.0.1` / `localhost` / 内网名)。
2. **库名存在性枚举**:有效凭据 + 候选库名 → 成功 = 库存在且可访问;失败 = 不存在**或**无权限(两者不可区分,记录时写明)。`information_schema`/`mysql` 作权限基准;应用真库按命名惯例扩候选。
3. **同族站凭据复用测试**:同运营方多站常共用同一 MySQL —— 把从另一站(调试页/报错帧/备份包)泄露的库凭据拿去打本目标 oracle;命中即「跨站凭据有效」(实测成立)。**「库名不在候选」≠ 凭据无效** —— auth 与库名是两个维度,别混着判死。
4. 只有某个库可连时别停:继续枚举候选库名定位应用真库,或拿该凭据做其他服务的复用检测。
5. **同凭据随来源结果相反 ⇒ 先查授权 host 粒度(`@'%'` vs `@'特定IP'`)** —— 去服务端侧核实再判凭据对错;oracle 真伪核验 = 垃圾 host 必须失败 + 用自己独立验证过的凭据复现 success,才算证明「目标→我方库」链路。

### 3. 安装锁与 step 推进红线

- 先探锁文件:`/install.lock`、`/install/install.lock`、同目录 `install.lock` —— 决定「重装重置管理员」线成不成立。
- **浅探 step1**:空字段/假凭据 POST,预期回原表单 + 错误(校验先于写入 = 零副作用)——这是证实 oracle 非破坏性的最便宜一发。**若空体竟进 step2/直接「安装成功」,说明该向导不校验就写,立即停。**
- 推进前**逐页读该步全部文案**:出现「清空/覆盖/删除已有数据/重建表」字样 ⇒ 停,不动。
- 安装器推进 = **写操作**(可能新建管理员/改配置)⇒ 属「动手前先答能不能恢复」范畴:用可辨识管理员名 + 自选强口令(便于事后清理);动工前告知用户。
- 不确定某步语义 ⇒ 收益 < 风险,收手,把「重装重置管理员面(未推进)」如实写进报告。

### 3.5 DB 权限墙绕过:把 host 指向自建假 MySQL

step2 稳定报「数据库权限不足，无法创建数据库」/「创建数据库失败：」(冒号后为空) = 安装器真在连库试建库,但服务端账号无 CREATE 权限,原路堵死。**换目标:把表单 host 指向我方公网机上的自建假 MySQL**(mysql-mimic)——任意用户名+任意密码直通、DDL/DML 一律回 OK,并全量记录连接事件与 SQL。

判读三件套(先仪器化再开火):
1. **报错文案差分 = 是否真外连的证据**: host=127.0.0.1 文案 A(权限不足) vs 换外网 IP 后文案 B(连接类失败)= 安装器确实按表单 host 发起了外连;冒号后为空 = 连接阶段通用失败,不是建库被拒。
2. **连接级日志必须先于开火**: 只在 handle_query 记 SQL 会漏「连上但没发 SQL」的场景;Session.__init__/get_user 也记(NEW_CONN/GET_USER)= 区分「根本没连」与「连上后失败」的唯一仪器。
3. **网络前置核验**: 先确认假库 host:port 从公网可达(本机直连探测;RST/refused = 路由可达且端口空闲,可立即绑定服务)。**表单无 port 字段 ⇒ 假库必须绑默认 3306**,不能挑端口。

完整配方(代码骨架/认证覆写/ResultColumn/坑)见 `references/fake-mysql-hijack.md`。
推进红线不变:「安装成功」= 目标开始用我方库 ⇒ 后续步骤仍是写操作,评估可恢复性再走。

### 3.6 重装落库:指向自有真库(配置写注入 / 建管理员)

假库(mimic)适合「让安装器以为成功」;更重的收成 = **把整条安装指向自己完全掌控的真 MySQL 跑完**:站点配置切到我方库(其业务数据可读可写)+ 安装器在我方库按给定字段建管理员(= 登活体后台的凭据)+ 配置写入点若为拼接实现 ⇒ **直接 RCE**。适用族:FastAdmin/ThinkPHP5 二开(先拿源码确认)。

**开火前四件事(缺一停手):**
1. **先拿源码定契约** — 产品多为 FastAdmin 二开换皮,GitHub 按后台标题/独有类名能搜到全套;安装逻辑看 application/admin/command/Install.php(public/install.php 常只是小路由器)。钉死:请求形态(单 POST 全流程 vs 多步 AJAX)、字段名、写入目标(.env 字符串 vs database.php PHP 代码)、有无 prefix 字段。**分析完前不发完整参数 POST**。
2. **恢复预案** — 原 DB 配置值常已泄露(debug 报错页的 PDO DSN/args = 活体配置),存档;**目标库已存在时重装会卡在「创建数据库」步中止 ⇒ 不能靠再装一次写回配置**,恢复只能靠 RCE/面板。
3. **自有库就绪** — 账号可连 + 有 CREATE 权限 + 库名全新;授权建议 @'%'(否则目标源 IP 不在范围内,症状 = 「凭据本机可连、目标报连接失败」)。
4. **单发纪律** — 探测全用垃圾 host/假凭据(oracle 零副作用),最后只发**一次决定性 POST**。

**密码即 payload** — host/user/db 都必须功能可用,只有密码是自由字段:**把自有 MySQL 专用账号的密码直接设成 payload 字符串**,连接照常成功,配置写入即注入。
**双用途 payload** — 该字符串同时是正确密码:写入路径若是安全实现(.env 无代码执行),站点照常工作、回退线(用安装器自建 admin 登活体后台)不丢;PHP 单引号拼接语境用:

```
x') . system($_GET[0]) . ('x
```

**必须保持配置文件可解析** — 截断数组/引号失配 = parse error = 代码永不执行且站点一起打挂。

**FastAdmin 经典原语(读到源码才用;二开可能改写,改写过按改写后代码重新推):**
- mysqlPrefix 无校验 → 表前缀整份替换 + `exec()` 多语句:错误语句之后的跳过、之前的已提交;替换在每处前缀处重复出现 ⇒ 动作语句用 `INSERT IGNORE` 等幂等写法。
- 配置写(preg_replace_callback 类)把 host/user/pass 单引号包裹塞进 database.php 且不转义 = PHP 注入(上面 payload 的出处)。
- 成功副作用:admin.php 被 rename 为 Random::alpha(10).php、响应体带 adminName、install.lock 上锁 —— 当场捕获。

配方(请求契约/注入点代码/恢复清单/核验坑)见 `references/own-db-reinstall.md`。

### 4. 凭据掩码纪律(全程)

- 值**永不进**会话明文/报告正文/日志;报告只写「auth 有效/某库可连」类结论 + `[REDACTED]`。
- **掩码两段式**脚本作业:①掩码脚本只打印上下文中的非密字段(host/port/dbname/用户名/长度)确认格式;②用途脚本从落盘文件读凭据发请求,只打印判词(SUCCESS/FAIL),不 echo 凭据。
- 正则提取失败(格式假设错)时,先跑掩码脚本看真实形态再修正,不要连续换正则硬猜。
- 「实测成功连接某库」这类事实结论可以写进报告;凭据本身不写。

### 5. 与登录面风控的配合(何时取这条线)

- 登录面被锁(「失败次数过多,请 N 分钟后再试」)= 硬信号:**不要在登录面上空转/换用户名重打** —— 计数常按端点/IP 记账、与用户名无关,自动化过验证码也不豁免服务端计数(登录枚举纪律详见 `captcha-gate-triage` §5)。换**正交端点**:安装器线正是其一。
- 反向注意:安装器**写操作**仍可能触发站点级风控(机器验证/封卡等价机制)——推进前确认边界与可恢复性。

## Pitfalls

- **空字段 POST「无副作用」只在「校验先于写入」时成立** —— 先用一发验证这个前提,再依赖 oracle 反复调用;不验证就批量打 = 拿站点数据赌。
- **「库名不存在」与「无权限」不可区分** —— 记录时写明,别把前者写成「该库不存在」的绝对结论。
- **同族站泄露凭据要先过非破坏性复验再判死** —— 同运营方多站常共用同一 MySQL/口令体系,跳过复验会漏掉有效凭据。
- **装完没删 ≠ 一定可重装** —— 常有锁文件/数据库标记;锁在但 oracle 在,仍可做凭据验证(只读面成立)。
- **不要把 oracle 调用当「已打进」** —— 控制权口径 = shell/数据库写权限/管理员登录;凭据验证只是一步,别提前结案。
- **假 MySQL 判「连没连」只认连接级日志 + 文案差分** —— SQL 日志为空 ≠ 没连上(可能握手阶段即失败);先读安装器表单字段(有无 port)再部署假库,别挑了端口才发现必须 3306。
- **重装落库前先答「能不能恢复」** —— 目标库已存在 ⇒ 重装会卡在「创建数据库」步,无法写回配置;没有 RCE/面板恢复通道就开火 = 把目标配置切走且无路回退。
- **双用途 payload 是重装链的安全带** —— payload 必须同时是有效凭据(写入安全实现时站点照常、回退线不丢);PHP 语境 payload 必须让配置文件保持可解析,parse error = 站点全挂且注入不执行。
- **admin.php 改名与 adminName 必须当场记录** —— 安装成功的 rename 副作用不捕获,后台入口即丢。
