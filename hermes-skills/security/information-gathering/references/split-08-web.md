## 七、Web 指纹与内容识别

### 7.1 技术栈识别
```bash
# httpx 批量指纹（信息收集标配）
httpx -l subs.txt -status-code -title -tech-detect -server -ip -cname -cdn -web-server -json

# whatweb 单点深扫
whatweb -a 3 https://target.com

# 指纹维度
# Server 头 / X-Powered-By / Cookie 特征 / 静态资源路径 / 报错页面特征
# favicon hash（空间引擎万能钥匙：同一图标=同一产品）
python3 favihash.py -u https://target.com/favicon.ico
# → 拿 hash 去 FOFA: icon_hash="xxx" / Shodan: http.favicon.hash:xxx → 发现同产品全部暴露资产
```

### 7.2 CMS/框架/中间件指纹特征库
| 产品 | 关键特征 |
|------|---------|
| WordPress | `/wp-content/` `/wp-includes/` `wp-login.php` |
| ThinkPHP | `/?s=/`、`X-Powered-By: ThinkPHP`、TP 报错页 |
| Spring Boot | `/actuator`、`/swagger-ui`、`/v3/api-docs`、whitelabel 报错页 |
| Shiro | `rememberMe=deleteMe` Cookie（→ 反序列化链） |
| 通达OA/泛微/致远 | 特定登录页+版本号（OA 0day 高发） |
| Jenkins | `/manage`、`X-Jenkins` 头（未授权脚本控制台） |
| Nacos | `/nacos/` 未授权（配置泄露→凭据） |
| 若依(RuoYi) | `/prod-api/`、`ruoyi` 标识（默认弱口令高发） |
| Fastjson | 畸形 JSON 报错泄露版本（详见 fastjson-exploitation 技能） |

### 7.3 目录与敏感文件扫描
```bash
# 常规扫描（多引擎交叉验证，减少误报）
ffuf -u https://target.com/FUZZ -w wordlist.txt -t 30 -mc 200,301,302,403 -o ffuf.json
gobuster dir -u https://target.com -w wordlist.txt -x php,asp,aspx,jsp,html,json,bak,zip,sql
dirsearch -u https://target.com -e php,asp,aspx,jsp,html,js,json,bak,zip

# 备份文件专项（红队高收益：源码=审计金矿）
# www.zip / backup.zip / web.zip / site.zip / 域名.zip / 域名.tar.gz / dump.sql / db.sql
# 工具：Test404备份文件扫描器 / ihoneyBakFileScan

# 版本控制目录（完整源码提取）
# .git/（GitHack 提取） .svn/ .hg/ .DS_Store（泄露文件列表）

# 配置文件
# .env / .env.bak / config.php / config.inc.php / web.config / .htaccess / .user.ini
# application.yml / bootstrap.yml（Spring 配置可能含数据库口令、AK/SK）

# 管理入口
# admin/ manager/ manage/ backend/ system/ oa/ sso/ /phpmyadmin/ /actuator/ /console/
```

### 7.4 JavaScript 分析（API 与密钥挖掘）
```bash
# 收集 JS：当前页面 + 历史归档 + JS 目录枚举
echo "target.com" | waybackurls | grep -E "\.js" | sort -u > js.txt
cat subs.txt | getJS --complete

# 分析：LinkFinder / SecretFinder / JSFinder / Burp JS Miner
python3 LinkFinder.py -i https://target.com/js/app.js -o cli
python3 SecretFinder.py -i https://target.com/js/app.js -o cli

# 从 JS 提取的核心情报
# - 未公开 API 端点（/api/v2/internal/...）
# - AK/SK、JWT 密钥、加密密钥
# - 内部域名/内网 IP（→ 直接访问或 SSRF 目标）
# - 云配置：Firebase/Supabase/Cognito/OSS 桶名
# - 前端路由（React/Vue 路由 → 未公开页面）
# - 注释中的测试账号/开发接口

# 批量自动化：转子（Windows，爬取+提取AK/SK/手机号/邮箱+漏洞分类）
```

### 7.5 Source Map 源码还原
```bash
# 生产环境误发布 .js.map → 可还原几乎完整的前端源码
curl https://target.com/js/app.js.map -o app.js.map
# 工具：source-map-restore / unwebpack-sourcemap / SourceMapReader
# 还原后可审计：加密算法、签名逻辑、硬编码密钥、接口鉴权逻辑
```

### 7.6 403/401 绕过与认证页面
```bash
# 403 绕过（访问控制缺陷，红队常规动作）
# 路径变形：/secret → /secret/ /secret/. /./secret/./ %2f / //secret // /SECRET
# 方法切换：GET→POST→PUT→OPTIONS（部分 WAF/规则只拦 GET）
# 头部伪造：X-Forwarded-For: 127.0.0.1  X-Original-URL: /admin  X-Rewrite-URL: /admin
# Referer: https://target.com/admin（部分访问控制按 Referer 判断）
# 附加扩展：/admin.json /admin%00 /admin/..;/admin（Tomcat/Spring 路径解析差异）

# 401 页面：抓取 WWW-Authenticate 头判断认证类型（Basic/表单/SSO/OAuth）
# 常见默认口令：admin/admin、admin/123456、test/test（结合泄露情报撞库）
```

