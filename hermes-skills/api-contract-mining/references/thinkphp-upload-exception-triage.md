# ThinkPHP/FastAdmin 公共上传异常分级（prosunss，2026-10-01）

## 可复用判据

1. 从前端配置确认真实 `uploadurl` 与存储类型，再分别送不带文件的 GET 和单个合法、随机名的纯文本 multipart POST。每次保存 HTTP 状态、内容长度、异常类、调用栈和脱敏后的响应摘要。
2. 比较调用栈：`Ajax->upload()` 若调用 `action()` 后抛 `ClassNotFoundException`（缺被委派的 API 控制器），只能说明公开路由可达且执行停在委派处。无返回 URL/ID、无精确文件路径回读时，不宣称落盘；更不能宣称 PHP 执行。
3. `500 System Error` 中的 `PHP_APP_DEBUG`、框架版本、`PHP_DATABASE_*`、路径是独立的未认证信息泄露。原始异常页限权存储，报告只写字段名和脱敏影响；泄露了回环地址数据库凭据，不等于公网可连数据库或服务器 shell。
4. Nginx 对未知方法或控制器可能展示与静态文件缺失相同的 404 页。先取随机不存在路径的响应作基线，再用业务 JSON/异常栈作为命中证据；静态 `/assets/js/backend/*` 可读只证明代码资产公开，不证明后台入口存在。

## 本案观察（非成功接管配方）

- `https://prosunss.com/index/ajax/upload`：GET 500，POST 两个不同随机纯文本标记也均 500；调用栈 `Ajax.php:62 → action() → Loader.php:490`，异常指向缺失 `app\\api\\controller\\Common`。对照 FastAdmin 官方公开 `application/index/controller/Ajax.php`，该方法只是 `return action('api/common/upload');`；直接访问 `/api/common/{upload,init}` 和 `index.php?s=/api/common/...` 的 GET/POST 变体也均为同形 nginx 404。故这条上传链没有执行到真正的文件处理器，未获得上传 URL 或可回读文件；不能以源码版本推断其它未测上传点。
- `POST /index/index/check_user.html` 的数组型 `address[]` 触发 ThinkPHP 类型异常，调试页暴露数据库连接字段及明文口令。普通字符串请求返回业务 JSON。原件不放进技能库。
- 同 IP 的 `.com` 与 `www.prosunss.top` 为同站页面；公开后台 JS 可读，常见管理路径和两个额外 HTTP 端口未出现后台登录业务响应。ThinkPHP 旧 `invokefunction` 固定哈希探针均为同形 404；不能据此断言所有 RCE 都不存在。
- `/index/ajax/lang` 的 GET/POST `controllername[]=index` 均触发 `InvalidArgumentException: variable type error：array`，栈指向 `Ajax.php:34`；普通 `controllername` 的无效名、相对/绝对路径及 `lang` 变体均返回相同语言包（17,302 字节），没有任意文件读取证据。已知 FastAdmin CVE-2024-7928 的公开 PoC 同时设置 `lang=..//..//...` 和 `Cookie: think_var=..%2F%2F..%2F%2F...`；本案用公开语言文件与不存在文件作差分，均与基线同形。先前 `think_lang` cookie 同形的结果**不构成对此 CVE 的阴性验证**，因 cookie 名不同；即使用 `think_var`，同形也只说明本次没有观察到文件内容差异，不能断言版本已修复。注意：框架异常页源码窗口展示 `Request.php`，栈里有应用调用行 **不等于**读到应用源码。
- `/index/index/do_login.html` 中逐个替换 `address[]`、`signature[]`、`message[]`，都在 `Request::typeCast()` 处 500，应用栈行依次为 `Index.php:88/89/90`；`check_user.html` 的 `address[]` 指向 `Index.php:77`。这些与公开上传和语言包异常属于**同一类生产调试配置泄露**，报告合并根因、列独立触发条件，不堆成多个漏洞。
- 与随机不存在 action `zzz_noexist` 做 GET/POST 基线：它及匿名投资接口跟随 302 后都为登录 HTML；公开 `check_user` 为 `{"code":0}`，`do_login` 为 `{"code":0,"msg":"用户不存在"}`，`ajax/lang` 为语言包。不要按跟随跳转的 200 判“路由可用”。合成地址、零地址、非法地址及页面固定收款地址均得“用户不存在”；没有已注册身份时，此结果只表明用户查询先于签名验证，不足以判断签名校验或重放防护。
- 此案的交付状态为信息泄露确认，后台登录、文件落盘、RCE 和 root 均未确认。不要把这一串阴性探针当作通用成功打法。