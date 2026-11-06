---
name: php-error-based-sqli
description: "PHP报错泄露/SQL报错注入时用: 定界符越狱取数+FILE权限判定。"
---

# PHP 报错泄露 → 报错型 SQL 注入取数

适用: PHP 站点出现 `Database Error` / `Notice` / `Warning` 回显(CodeIgniter、自研 MVC、ThinkPHP alike),或需要一条稳定的脱库读链。
不适用: display_errors 与 db_debug 全关的站点(改走盲注/时间盲注,本技能只提供前置探测思路)。

## 行动纪律(先读)

1. **分阶段推进,读到写**:读阶段(注入取数/接口遍历)先做完并汇报,再提写与破坏性动作(落文件、SQL outfile、SSH 凭据尝试、改目标业务字段)。用户说“先把目前的做完,然后再考虑 shell”时严格遵守。
2. 任何对目标业务数据的写入(改字段/建号),动手前确认能还原,测完**立刻用同一个接口改回原值并复验**。
3. 长任务主动给结构化进度(已完成/进行中/待办),别长时间沉默。

## 第 1 步:报错 oracle 测绘

1. 每个参数尾加 `"` `'` `)` `\`,看响应是否变成 500 或 `Database Error` 页。
2. 500 页(CodeIgniter 风格)会回显**整条 SQL + 文件名 + 行号** → 一次拿到注入点、表名、列名、代码绝对路径。
3. 单引号被拦而双引号报错 = 后端用 `"` 作 SQL 字符串定界符 → **双引号就是越狱口**(定界符不匹配导致的 1064)。
4. 站点自带“安全模块”(如 `third_party/phpcode_shield.php`)常只按固定模式拦(`' or '1'='1`、`and 1=1`、`/**/or/**/`),`"` `--` `#` `union` `select` `extractvalue` 全放行;它自身写日志失败时还会把日志绝对路径的 fopen 警告回显出来(顺带拿到服务器目录结构)。
5. PHP Notice/Warning 是免费源码结构 oracle: 少传参数即可拿到 `controllers/xxx.php line N`。
6. **数组参数(`param[]=`)不是绕盾口**:自研盾把数组拼成字符串后照旧过正则(实测反而触发告警页),别在这条上耗轮次。

## 第 2 步:取数(三种互为备份)

```
" and extractvalue(1,concat(0x7e,<EXPR>))#
" or  extractvalue(1,concat(0x7e,<EXPR>))#
" union select extractvalue(1,concat(0x7e,<EXPR>))#
```

- 单次回显上限 ~32 字符 → 分片 `mid((EXPR),offset,30)`,循环到返回空/不足。
- **多字节(中文)内容必须先 `hex((EXPR))` 再本地解码**:直接 mid 切 UTF-8 会在字符边界截断,循环提前收尾,看起来像“数据就到这里”。
- 库/表/列枚举: `database()`、`information_schema.tables/columns`(表多时用 `limit i,1` 逐个取,好做断点续跑)。
- dump 行用 `concat_ws(0x7c, col, ifnull(col2,0x2d))`;**concat_ws 会跳过 NULL**,列会错位,别据错位结果断言“某字段为空”。
- 字符串被过滤时用 `0x...` 十六进制字面量代替引号。

## 第 3 步:先判 FILE 权限,再决定要不要想 webshell

```
select group_concat(privilege_type) from information_schema.user_privileges  -- 只有 PROCESS/REPLICATION* = 无 FILE
@@secure_file_priv        -- NULL 表示未限制,但仍需 FILE 权限
load_file(0x2f6574632f706173737764)  -- 返回 NULL = 没 FILE 权限
```

无 FILE 权限 → `load_file` / `INTO OUTFILE` 全废,**不要在“SQL 写 webshell”上继续花时间**,转去: 接口越权、上传点、管理后台、WS/业务层。

**写库可行性一句话判定(堆叠查询)**:`<param>=1";select sleep(3)#` 回 500 且**耗时无变化**(≈0.3s)= 多语句未执行(mysqli 单语句),`注入改管理员/插马`整条线作废,别为它再排计划;补一发 `select sleep(0)` 做对照即可。

## 第 3b 步:PROCESS 权限 = 独立的第二条取数通道(最常被忽略)

`user_privileges` 只列**全局**权限;一旦出现 `PROCESS`,别只把它当"没有 FILE"的负面信号:

```
select group_concat(concat_ws(0x7c,id,user,host,db,ifnull(info,0x2d))) from information_schema.processlist
```

- `info` 非空 = 该会话正在执行的**原始 SQL**:轮询采样可活捉后台/运营端的登录或写入语句(常含**明文口令**);
- `user` / `host` 两列直接暴露**尚未公开的主机与 DB 账号**(后台服、授权服),是新攻击面来源 → 立刻记进资产表,再决定打不打;
- `current_user()` 若回 `<dbuser>@%` ⇒ 该 DB 账号**可从任意 IP 连接**(只缺口令),值得为它专门找配置文件/口令;
- 边界:能读 processlist ≠ 能读 `mysql.*`(`select ... from mysql.user` 通常 1142 SELECT denied),别把两者混为一谈。

## 第 4 步:令牌会话链(此类商业系统通例)

- 站点令牌常**内联在登录页**:`var t = '…'`(每会话一枚),API 都要带;页面里还可能直接写着另一实例的 `apiUrl`。
- 登录成功返回 `{wwid, code, tk}`;业务接口鉴权 = `Authorization: Bearer <wwid>`(源码里常写成 `' Bearer ' + wwid`,带前导空格)。
- 旁路:前端自动登录端点(如 `/site/lg?wwid=&t=&return_url=`)换到 cookie 后再调业务接口。
- **未登录时鉴权过滤器对任意路径都渲染登录页** → “404 vs 登录页”只有拿到会话后才有判定意义;登录后的 404 才是真不存在该控制器。
- 同一 URL 一个 403 一个 200 时,先用 curl 复核再判断是否落到 IP/风控段,不要用两个 HTTP 客户端的差异下结论。

## 网络与源 IP

- 全端口扫描会招致目标云防火墙按源 IP 封禁(特征: 业务口断而另一端口/另一主机仍通)→ 立即换源,渗透流量走跳板池。
- 部分站点整段拒绝云厂商 IP(阿里云跳板 403、电信/家宽 200)→ 跳板要备非云厂商出口。
- 从配置表翻出的域名先被动核实再动手:这类表里大量条目是 NXDOMAIN 的历史残留。

## 交付

- 报告结构: 摘要 / 漏洞分级(附实网返回的原始 SQL 或响应片段)/ 复现命令 / 影响评估 / 修复建议 / 本地产物路径。
- **诚实分级**: 数据库读权限、管理身份会话 ≠ 拿到 shell;分开写,并单列“尚未突破/遗留”。

## 参考

- `scripts/error_sqli_extract.py` — 现成取数器(hex 分片、抗多字节截断、自动抓站点令牌 `t`、支持 and/or/union/updatexml 四种 payload);改 prefix/参数名即可跑
- `references/xiaomuzhi-commonxmz-family.md` — 小木子(Commonxmz/xiaomuzhi)系棋牌平台实例:指纹、资产分层、接口面、表结构、实战要点
