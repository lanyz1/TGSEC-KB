# ThinkAdmin 二开登录与整站源码泄露实测 — 2026-08-21

来源：授权目标 https://wadsaxzasd.fghdfghsadf.live/admin/  ThinkPHP V6.1.4 + ThinkAdmin + Cloudflare（172.66.40.81/172.66.43.175）Nginx，要求拿 shell/源码，账户 10003 / CxNbRNEjswjeWhv。

## 1) 二开登录逻辑（已逆向验证）
- 原版只验 verify+uniqid，二开新增 code(临时令牌)+power(local_zhiwen)，表单：username/password/verify/uniqid/code/power
- 密码算法（app/admin/controller/Login.php）：md5(md5(明文)+uniqid) == password。明文 md5=357e28a7addfb34caab4f7a4e9b1444f
- 验证码一次性：每登一次必须 GET /admin/login.html 取新 captcha-token → POST /admin/login/captcha {type:LoginCaptcha,token} 拿 uniqid+code(4位)+image，带同 Cookie 再 POST /admin/login/index。复用旧 uniqid 必报“图形验证码不能为空”
- 已实测：code=1111/0000/1234 等能过空校验（空code报“临时令牌不能为空”），但三种哈希 md5(md5+uniqid)/md5(pass+uniqid)/md5(pass) 均报“账号或密码错误”→ code 非通用值，需爆破或向赛方要来源
- 指纹：document.getElementById("power").value = localStorage.getItem("local_zhiwen")，来源 /js/fp.min.js FingerprintJS v3.4.2 visitorId 用 murmurX64，login.js 无 setItem，写入点在更外层 JS，需浏览器抓包补齐

## 2) 整站源码泄露判定
- 30+ 备份名并发扫（www.zip/wwwroot.zip/backup.zip/.env/.git/HEAD/composer.json 等）全 404
- 唯一命中 /public.zip 11M，unzip -l 264 文件全在 upload/ 且无 .php 与 config/database.php，属钓鱼模板包（CIH BANK等），非整站源码 — 必须 unzip -l + find *.php 二次验证再判 ✅
- /robots.txt 仅暴露 /data /admin /wechat，/data、/wechat 404，/upload/ 200 仅静态

## 3) 未授权旁路（均未命中记 ⚠️）
- ThinkPHP lang 包含 ?lang=../../../../etc/passwd、invokeFunction，nuclei cve/thinkphp/rce/lfi 空
- nmap 1-65535 仅 CF 代理口 80/443/2052/2053/2082/2083/2086/2087/2095/2096/8080/8443/8880
- ffuf 小字典仅 admin/app/index/js 等；/admin/special/index 等未授权均 302 到登录

## 4) 执行纪律提炼
- 登录与非登录必须并行：一条爆破 code+哈希，一条扫泄露/RCE/未授权，不可死磕登录
- 用户连喊“别墨迹/大范围干/你在bb吗/换条路” = 立刻上实测（curl/nmap/nuclei/ffuf）+ 每30秒回数，禁只解释不执行
- 工具超8K token 必流超时：拆多条小 terminal，delegate_task 不塞大 payload
