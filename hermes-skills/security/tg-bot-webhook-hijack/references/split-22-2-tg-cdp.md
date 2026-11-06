## 第 2 步: 接管 TG 会话(指纹浏览器 CDP 最快)
1. 让用户在比特浏览器(BitBrowser)开一个 TG Web 窗口并登录、打开目标 bot 聊天
2. 扫调试端口:查 `D:\bitbrowser-cache\<profile>\DevToolsActivePort`(内容=端口+browser path),或 netstat 找新起的 BitBrowser.exe 进程
3. CDP WebSocket 必须 `suppress_origin=True`,否则握手 403(浏览器没带 --remote-allow-origins)
4. `curl http://127.0.0.1:<port>/json/list` 找 telegram.org 的 page tab
5. 读 DOM:innerText 全文 / `querySelectorAll('button')` 枚举可点按钮(含坐标)

Pitfall: 用户普通 Chrome 的 cua 绑定需 `computer_use.grant_existing_profile: true` + **重启服务 才生效**;指纹浏览器自带调试端口,无需授权更快。

