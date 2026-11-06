## 12e. CDP 无头调试要点(页面交互问题必用)⭐

用 headless Chrome + CDP 抓 console 错误/实测点击(肉眼排查十倍效率)。完整可复用脚本: `scripts/cdp_page_probe.js`(页面状态/console 错误/点击前后 DOM 对比)。

- **Node ≥22 自带 WebSocket**, 不需要 npm ws 包; 事件用 `addEventListener`(原生 API, 不是 ws.on)
- **必须连 page target**: `/json` 列表里 `type==='page'` 的 webSocketDebuggerUrl(连 `/json/version` 的 browser 级会报 `'Page.enable' wasn't found`)
- **Chrome 对 127.0.0.1 默认 bypass 代理**(--proxy-server 指向本机端口时不生效!)→ 必须加 `--proxy-bypass-list=<-loopback>`
- headless 继承系统代理: 代理进程死了 → `chrome-error://chromewebdata/` "This site can't be reached"; 测代理可用性用 `curl -x http://127.0.0.1:<port>` 扫常见端口
- 页面就绪轮询: `document.body && document.querySelector('#app') && typeof Vue !== 'undefined'`(直连慢时轮询最长 40-60s)
- 页内切换 UI(如显示/隐藏结算区)验证: 对比点击前后 `classList.contains('hidden')`, **别只看 location.href**
- **本机到服务器网络故障时的绕行验证**: 本机 SSH(21661)→ 服务器出口。方案: 本地 Python 写 **SOCKS5 服务器**(paramiko direct-tcpip, ~50 行)+ Chrome `--proxy-server=socks5://127.0.0.1:10899` + `--proxy-bypass-list=<-loopback>`; **目标域名/IP 映射 127.0.0.1 走服务器回环**(Chrome 本地解析域名发 IP, 所以 `xeelee.top` 和服务器公网 IP 都要映射; TLS SNI/HTTP Host 不受影响)。服务器访问自己公网 IP 会绕外网路由(每请求 5s+), 回环 0.3s。

