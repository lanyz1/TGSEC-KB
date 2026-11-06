# SQLMap Tamper 脚本速查表(69 个全量著译)

> 每个脚本: 作用一句话。完整版含"什么时候需要使用"见原始 Excel。

| 脚本 | 作用 |
|------|------|
| 0eunion.py | 在 UNION 操作符前添加 0e 前缀(0eUNION SELECT),绕过对常见 UNION 的过滤 |
| apostrophemask.py | 处理单引号(')字符,掩盖/替换以绕过输入过滤 |
| apostrophenullencode.py | 用 NULL 字符替换单引号,绕过单引号过滤 |
| appendnullbyte.py | 在 payload 末尾添加空字节(\x00),截断字符串绕过过滤 |
| base64encode.py | 对 payload 数据进行 Base64 编码,改变外观绕过过滤 |
| between.py | 将条件语句(age>18)替换为 BETWEEN 语句(age BETWEEN 18 AND 100) |
| binary.py | 处理二进制数据,逐字节提取大文本/二进制数据 |
| bluecoat.py | 针对 Blue Coat 安全代理的绕过技术 |
| chardoubleencode.py | 字符双重 URL 编码,绕过单次解码的过滤器/WAF |
| charencode.py | 字符 URL/十六进制编码,绕过字符过滤 |
| charunicodeencode.py | 字符转 Unicode 编码(\u0041),绕过字符过滤 |
| charunicodeescape.py | 字符转 Unicode 转义序列,绕过字符过滤 |
| commalesslimit.py | 不使用逗号实现 LIMIT 子句功能(绕过逗号过滤) |
| commalessmid.py | 不使用逗号实现 MID 函数功能(绕过逗号过滤) |
| commentbeforeparentheses.py | 在括号前添加注释符号,改变查询结构 |
| concat2concatws.py | 将 CONCAT 函数转换为 CONCAT_WS(MySQL) |
| decentities.py | 处理/解码 HTML 实体 |
| dunion.py | 处理 UNION 查询,合并多个 SELECT 结果 |
| equaltolike.py | 将 =(等于) 转换为 LIKE 操作符 |
| equaltorlike.py | 将 =(等于) 转换为 LIKE 操作符(变体) |
| escapequotes.py | 处理引号转义,绕过引号过滤 |
| greatest.py | 利用 GREATEST 函数返回最大值,改变查询结构 |
| halfversionedmorekeywords.py | 处理半版本信息 + 更多 SQL 关键词注入 |
| hex2char.py | 十六进制编码字符串转字符 |
| hexentities.py | 字符转十六进制实体编码 |
| htmlencode.py | 特殊字符转 HTML 实体编码(&lt; &gt; &amp;) |
| if2case.py | IF 条件语句 → CASE 语句 |
| ifnull2casewhenisnull.py | IFNULL 函数 → CASE WHEN ISNULL 语句 |
| ifnull2ifisnull.py | IFNULL 函数 → IF(ISNULL(...)) 语句 |
| informationschemacomment.py | 利用注释符号获取数据库架构信息 |
| least.py | 利用 LEAST 函数返回最小值,改变查询结构 |
| lowercase.py | payload 全部转小写,绕过大小写过滤 |
| luanginx.py | 处理通过 Lua 语言进行的 SQL 注入(nginx/lua) |
| misunion.py | 变形 UNION 查询(故意引入错误),绕过 UNION 过滤 |
| modsecurityversioned.py | 绕过 ModSecurity WAF(版本化编码) |
| modsecurityzeroversioned.py | 绕过 ModSecurity WAF(零版本策略) |
| multiplespaces.py | 插入多个空格,绕过标准格式过滤 |
| ord2ascii.py | ORD 函数 → ASCII 函数 |
| overlongutf8.py | 利用过长 UTF-8 编码字符 |
| overlongutf8more.py | 过长 UTF-8 编码(更多变体) |
| percentage.py | 使用百分号(%)符号 |
| plus2concat.py | 加号(+) → CONCAT 函数 |
| plus2fnconcat.py | 加号(+) → FN_CONCAT 函数(PostgreSQL) |
| randomcase.py | 随机改变字符大小写 |
| randomcomments.py | 插入随机注释符号 |
| schemasplit.py | 分割数据库架构查询 |
| scientific.py | 使用科学记数法(指数记数法) |
| sleep2getlock.py | SLEEP 函数 → GET_LOCK 函数(MySQL) |
| sp_password.py | 利用 SQL Server sp_password 存储过程(日志隐藏) |
| space2comment.py | 空格 → 注释符号 /**/ |
| space2dash.py | 空格 → 破折号(--) |
| space2hash.py | 空格 → 哈希符号(#) |
| space2morecomment.py | 空格 → 多种注释符号组合 |
| space2morehash.py | 空格 → 多个哈希符号(##) |
| space2mssqlblank.py | 空格 → MSSQL 特有空白字符 |
| space2mssqlhash.py | 空格 → MSSQL 特有注释(--) |
| space2mysqlblank.py | 空格 → MySQL 特有空白字符(如 \t \n) |
| space2mysqldash.py | 空格 → MySQL 特有双破折号(-- /*) |
| space2plus.py | 空格 → 加号(+) |
| space2randomblank.py | 空格 → 随机空白字符 |
| substring2leftright.py | SUBSTRING 函数 → LEFT/RIGHT 函数 |
| symboliclogical.py | 使用符号逻辑运算符(&& \|\| !) |
| unionalltounion.py | UNION ALL → UNION |
| unmagicquotes.py | 移除/绕过 PHP magic_quotes(宽字节注入) |
| uppercase.py | payload 全部转大写 |
| varnish.py | 绕过 Varnish Cache(前向代理) |
| versionedkeywords.py | 利用不同数据库版本特有关键词(/*!...*/) |
| versionedmorekeywords.py | 版本化关键词(更多扩展) |
| xforwardedfor.py | 利用 X-Forwarded-For 头进行 SQL 注入 |

## 组合策略

| 场景 | 推荐组合 |
|------|---------|
| 通用 WAF 绕过 | `space2comment,apostrophemask,equaltolike,randomcase` |
| ModSecurity | `modsecurityversioned` 或 `modsecurityzeroversioned` |
| 空格过滤 | `space2comment,space2dash,space2hash,space2plus` |
| 单引号过滤 | `apostrophemask,apostrophenullencode,unmagicquotes` |
| UNION 过滤 | `0eunion,dunion,misunion,unionalltounion` |
| 逗号过滤 | `commalesslimit,commalessmid` |
| 关键字过滤 | `charencode,charunicodeencode,hexentities,randomcase` |
| MySQL 环境 | `space2mysqlblank,space2mysqldash` |
| MSSQL 环境 | `space2mssqlblank,space2mssqlhash,sp_password` |

> 注意: tamper 不是越多越好,过多会破坏 payload 可用性。按目标环境(WAF 类型/DBMS/过滤规则)精确选择。
