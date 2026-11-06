# 会话单值鉴权 + 掩码开关 + Host 键控租户（一类后台的通杀形态）

> 触发：后台接口「一切正常但处处要登录」；导出/列表接口在别人手里能出数据；
> 数据里有身份证/手机号但全是 `4301**********1234`；同一套系统挂着几十个域名。

## 1. 判据：鉴权是否只由一个 session 值决定

拿到源码后第一件事 —— 找鉴权函数。这类系统的典型长相：

```php
// Common/Action/CommonAction.class.php
public function _check_login(){ return session('ext_uid'); }     // 全站唯一鉴权
```

⇒ 结论：**权限 = 一个 session 键的值**。那么：
- **提权目标**从「找密码」变成「让 `ext_uid=1`」→ 找**写入点**（`session('ext_uid', $x)` 的 `$x` 来自哪里）。
- 若 `$x` 只来自数据库用户行 ⇒ 不能参数注入 ⇒ 回到「拿到 uid=1 的口令」。
- **注意 admin 端常是另一个键**（本例 `ext_uid01`）⇒ 前台会话 ≠ 后台会话，别拿错。

## 2. ★ 掩码开关：明文与否往往只是一个 `uid` 比较

```php
if($this->uid != 1){ $v = deal_card($v); $v = deal_phone($v); }
```

⇒ **掩码不是脱敏，是开关**：
- `uid=1` → **全量明文**；`uid≠1` → 全打码。
- 所以「已拿到打码导出」≠「拿不到明文」，**差别只在一个账号**。
- 判据：把同一接口用两个不同权限账号各取一次，**做差分**；只有一行 `if` 差异就是开关。

## 3. ★ 多租户隔离 = 请求 Host 匹配一张授权表

```sql
CREATE TABLE `fm_user_temp` (
  `domain` varchar(60) COMMENT '授权域名',
  `sign`   varchar(100),
  `uid`    int(11)
) COMMENT='授权网址';
```

⇒ **租户身份不由会话决定，而由请求 `Host` 决定** ⇒ 换 `Host:` 头即换租户视角 = 天然 IDOR。
- 该表的 `sign` 值往往就是别处（注入种子/接口签名）用的那个字符串 —— **两者对上即坐实**。
- 同一 `uid` 可绑多个 domain（`sls01.x.com,qbz1.x.com`），`domain=''` 的是无域限制的超管。
- **红线**：表里列出的租户域多半**不在授权范围** ⇒ 只输出「待授权清单」，不自行开打。

## 4. 顺手可用的两个小判据

- **验证码**：`I('vertify','','md5') != session('verify')` —— 传**数组** `vertify[]=x` 时 `md5(array)` 在 PHP5 返回 `null`（带 warning），与**未初始化**的 `session('verify')` 松散比较**通过**。⇒ 先看比较符是 `!=` 还是 `!==`。
- **口令算法**：先在用户表找 salt 列（常注释为「识别码」/`salt`），试 `md5(md5(pw)+salt)`；本例 `myh2018`/`123456` 一击命中。**能本地重算验证，就等于自建了口令 oracle** —— 别再盲撞登录口（会锁号、会触发风控）。

## 5. 实测案例（fm.jiangxisls.com，2026-09-14）

| 项 | 值 |
|---|---|
| 鉴权 | `session('ext_uid')`；admin 端 `session('ext_uid01')` |
| 掩码 | `if($this->uid!=1){deal_card/deal_phone}`（`UsersetAction` L165-168 / L197-199）|
| 租户 | `fm_user_temp(domain, sign, uid)`，9 行；授权内 2 域、授权外 21 域 |
| 口令 | `md5(md5(pw)+salt)`；`myh2018`=`123456` 已破；`admin`(uid=1) 未破 |
| 最大未取项 | uid=1 会话 ⇒ 22,020 行花名册全明文 |
