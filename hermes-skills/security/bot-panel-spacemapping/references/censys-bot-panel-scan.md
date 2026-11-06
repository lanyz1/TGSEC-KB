# Censys 平台迁移 + bot 面板空间测绘实测(2026-08-09)

## 背景

search.censys.io 已迁移到 platform.censys.io。Legacy 查询语法(services.http.response.*)已禁用,Free 用户会看到 "Censys Legacy Search has been disabled for all Free users"。Query Converter 自动给出新语法,直到 2026-09-30。

## 登录态恢复(chrome_censys profile)

本机 `C:\Users\Administrator\chrome_censys` 是之前登录过 Censys 的 Chrome profile,存有有效 cookies:
- `auth_v1`(.censys.io)
- `search.censys.io.session.id`
- `csrf_v2` / `csrf_token`
- `cf_clearance` + `__cf_bm`(Cloudflare 通过标记)
- expires 到 2090 年

用法:CDP 加载该 profile 即自动登录,无需账号密码:
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9227 \
  --user-data-dir="C:\Users\Administrator\chrome_censys" --no-first-run about:blank
```

注意:
- Cookies 在 `Default/Network/Cookies`(sqlite)。Chrome 锁定时 shutil.copy2 会 WinError 32(文件被占用)——别硬读,直接用 CDP 加载 profile。
- 页面显示 "Register/Log in" 不代表未登录——`document.cookie` 看不到 HttpOnly cookie,直接导航到 platform.censys.io 看左侧菜单(Home/Search/MY WORK/Collections)才确认登录。
- 账号名: 梵梵, Free Plan, 55/100 credits, 每月重置。

## 新旧语法对照

| Legacy(已禁用) | Platform(有效) |
|---|---|
| services.http.response.body:"bot_token" | host.services.endpoints.http.body:"bot_token" |
| services.http.response.html_title:"bot" | host.services.endpoints.http.html_title:"bot" |
| services.http.response.body:"X" and services.http.response.body:"Y" | host.services.endpoints.http.body:"X" and host.services.endpoints.http.body:"Y" |
| — Web Properties | web.endpoints.http.body:"X" |
| — 双查 | (host.services.endpoints.http.body:"X" and ...) or (web.endpoints.http.body:"X" and ...) |

搜索 URL: `https://platform.censys.io/search?q=<urlencode(query)>`

## 实测结果(2026-08-09)

```
查询: host.services.endpoints.http.html_title:"bot" and host.services.endpoints.http.html_title:"panel"
结果: 853 Hosts (SOFTWARE: express 713 / nginx 1.2K / python 467 / werkzeug 321)
      PORTS: 22(689) 80(513) 443(456) 8080(249) 3000(226)
      SERVICE LABELS: LOGIN_PAGE 935 / REMOTE_ACCESS 1K
```

CDP 提取 IP 技巧:导航后多次 `Runtime.evaluate` `window.scrollBy(0,1500)`,每次读 `document.body.innerText`,正则 `\b(?:\d{1,3}\.){3}\d{1,3}\b` 抓 IP,去重 → 一次拿到 99 个候选 IP。

## 批量验证结果(99 IP → 6 真面板)

| IP:端口 | 面板 | 登录特征 |
|---|---|---|
| 89.232.188.12:443 | BOT - Admin Panel(俄语, lang=ru) | password/login/username |
| 45.155.102.26:443 | RustBot Panel – Rust Discord Bot Control | — |
| 217.76.48.37:443 | WhatsApp Bot - Panel | — |
| 213.146.184.197:443 | EsenlerNodes | password/login |
| 50.114.206.57:443 | IRTools Autohost — Sewa Bot Otomatis | password/login |
| 152.53.110.238:8080 | AMP - Application Management Panel | password/login/username |

验证方法: Python socket + ssl(443 用 wrap_socket server_hostname=IP)+ 正则 title + 关键词 password/login/username 计数。

## 面板登录分析(89.232.188.12 = paynet.zone)

- 表单: `POST /index.php` + `action=login&login=<邮箱>&password=<密码>`(login 是邮箱格式 <EMAIL-REDACTED>)
- 失败响应: 303 See Other + Location: / + Set-Cookie PHPSESSID(域名 .paynet.zone)
- **暴露真实业务域名 paynet.zone → 142.93.168.254**(独立服务器,跳转 /az = 阿塞拜疆区)
- 坑: 登录失败和成功都可能是 303,无法从状态码区分 → 必须带 cookie 跟随重定向看是否进 dashboard 才判定成功
- 面板 JS: /assets/js/script.js?ver=1.3(含登录后 API 逻辑,未完全逆向)
