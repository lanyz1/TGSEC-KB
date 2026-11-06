# SOCKS5 认证桥 + Windows 交付工具打包（PyInstaller）

来源: TikFlow 抓 CK 工具 v3,2026-08 实测。两类可复用知识:① 让 Chrome 走带认证 SK5 代理;② 把 Python 工具打成客户零依赖 exe。

## 一、为什么需要桥

- **Chrome 的 `--proxy-server` 不支持 SOCKS5 账号密码认证**(`socks5://user:pass@host:port` 里的认证信息被忽略/失败)
- 住宅代理(如 ga6x.com/青果)几乎都是**带认证 SK5**——用户给的格式常带备注标签:`socks5://账号:密码@主机:端口#美国`
- 方案:**本地起一个无认证 HTTP CONNECT 桥**,Chrome 连 `http://127.0.0.1:随机端口`,桥用 SOCKS5 协议(带认证)连上游 → 双向转发。认证信息不进 Chrome 参数。

## 二、纯标准库桥实现(python,socket + threading,零依赖)

```python
import re, socket, threading

def parse_proxy(raw: str):
    s = (raw or "").strip().replace("#", " ").split()[0].strip()  # 剥离 #美国 备注
    m = re.match(r"^(socks5h?|https?)://(?:([^:@/]+):([^@/]*)@)?([^/\s:]+):(\d+)$", s, re.I)
    if not m: return None
    scheme, user, pwd, host, port = m.group(1).lower(), m.group(2), m.group(3), m.group(4), int(m.group(5))
    return {"scheme": scheme, "user": user, "pwd": pwd, "host": host, "port": port}

def _socks5_connect(sock, host, port, user, pwd):
    if user:
        sock.sendall(bytes([0x05, 0x02, 0x00, 0x02]))  # 无认证+用户名密码
    else:
        sock.sendall(bytes([0x05, 0x01, 0x00]))
    ver, method = sock.recv(2)
    if ver != 0x05: raise ConnectionError("SOCKS5 版本错误")
    if method == 0x02 and user:
        u, p = user.encode(), (pwd or "").encode()
        sock.sendall(bytes([0x01, len(u)]) + u + bytes([len(p)]) + p)
        v, st = sock.recv(2)
        if st != 0x00: raise ConnectionError("SOCKS5 认证失败")
    elif method != 0x00: raise ConnectionError("SOCKS5 协商失败")
    h = host.encode() if host else b""
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
        addr = b"\x01" + socket.inet_aton(host)
    else:
        addr = b"\x03" + bytes([len(h)]) + h
    sock.sendall(bytes([0x05, 0x01, 0x00]) + addr + port.to_bytes(2, "big"))
    resp = sock.recv(4)
    if len(resp) < 2 or resp[1] != 0x00: raise ConnectionError("SOCKS5 连接目标失败")
    # ★★★ 必须读完响应剩余地址部分:ATYP 后跟地址+端口,不读完会残留字节污染隧道 → TLS 握手 ERR_SSL_PROTOCOL_ERROR
    atyp = resp[3] if len(resp) > 3 else 0
    if atyp == 1:   sock.recv(6)      # IPv4: 4+2
    elif atyp == 3:                    # 域名: 1长度 + n + 2
        b = sock.recv(1)
        if b: sock.recv(b[0] + 2)
    elif atyp == 4: sock.recv(18)     # IPv6: 16+2

def start_socks_bridge(proxy):
    """本地 HTTP CONNECT 桥 → 上游带认证 SK5。返回 (端口, stop函数)"""
    listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen.bind(("127.0.0.1", 0)); listen.listen(32)
    port = listen.getsockname()[1]
    stop = threading.Event()
    def handle(client):
        try:
            client.settimeout(20)
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = client.recv(4096)
                if not chunk: return
                data += chunk
                if len(data) > 65536: return
            first = data.split(b"\r\n")[0].decode(errors="replace")
            m = re.match(r"^CONNECT ([^:]+):(\d+) HTTP", first)
            if not m:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n"); return
            up = socket.create_connection((proxy["host"], proxy["port"]), timeout=15)
            up.settimeout(60)
            _socks5_connect(up, m.group(1), int(m.group(2)), proxy["user"], proxy["pwd"])
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            client.settimeout(None); up.settimeout(None)
            def pump(a, b):
                try:
                    while not stop.is_set():
                        buf = a.recv(65536)
                        if not buf: break
                        b.sendall(buf)
                except Exception: pass
                finally:
                    for s in (a, b):
                        try: s.close()
                        except Exception: pass
            threading.Thread(target=pump, args=(client, up), daemon=True).start()
            threading.Thread(target=pump, args=(up, client), daemon=True).start()
        except Exception:
            try: client.close()
            except Exception: pass
    def accept_loop():
        while not stop.is_set():
            try:
                c, _ = listen.accept()
                threading.Thread(target=handle, args=(c,), daemon=True).start()
            except Exception: break
    threading.Thread(target=accept_loop, daemon=True).start()
    return port, stop.set
```

使用:`port, stop = start_socks_bridge(proxy)` → Chrome 参数 `--proxy-server=http://127.0.0.1:{port}` → 用完 `stop()`。

## 三、验证桥(不经过 Chrome,直接测 TLS 全链路)

```python
import socket, ssl
s = socket.create_connection(("127.0.0.1", port), timeout=15)
s.sendall(b"CONNECT api.ipify.org:443 HTTP/1.1\r\nHost: api.ipify.org:443\r\n\r\n")
resp = b""
while b"\r\n\r\n" not in resp: resp += s.recv(1024)
assert b"200" in resp
tls = ssl.create_default_context().wrap_socket(s, server_hostname="api.ipify.org")
tls.sendall(b"GET /?format=json HTTP/1.1\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n")
# 读 body → {"ip":"199.239.16.12"} 即出口 IP,确认走了代理
```
- 出口 IP 验证:`api.ipify.org?format=json`(轻量无重定向);在浏览器里导航会因桥内数据问题显示 ERR_SSL_PROTOCOL_ERROR = CONNECT 响应残留字节未读完(见上 ★)
- 注意:桥只服务 CONNECT(TikTok 全 HTTPS),普通 HTTP 请求直接 502

## 四、PyInstaller 打包 Windows 交付工具(客户零依赖)

交付物 = 文件夹(或 zip):`抓tk登录ck.bat` + `抓tk_ck.exe` + `使用说明.txt`(GBK 编码,记事本不乱码)

```bash
python -m venv <build-env> && <build-env>/Scripts/pip install pyinstaller websocket-client
<build-env>/Scripts/pyinstaller --onefile --name 抓tk_ck --distpath dist --workpath build --specpath . 抓tk_ck.py
```
- **★onefile 模式 `__file__` 指向临时解压目录(_MEIPASS)**,不是 exe 所在目录!读配置/写数据文件(proxy.txt、profile 目录)必须:
  ```python
  HERE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
  ```
- **★exe 在 cmd(GBK 控制台)里 print emoji(✅⏳🌐📋💾🎉)会 UnicodeEncodeError 崩溃**(python 脚本在 UTF-8 终端跑没事)。交付 exe 的脚本**一律纯中文/ASCII 输出**,不加 emoji;MessageBoxW 是宽字符 API 不受影响但保险起见也去掉
- 测试 exe 注意:后台无 stdin 时 `input()` 会 EOFError——这是环境问题不是 bug;双击场景(有黑窗口)正常。测"读配置"分支要先把配置文件放到 exe 旁边(别放错目录)
- bat(GBK+CRLF)只做壳:`@echo off` + 调用 `"%~dp0抓tk_ck.exe"`(中文 exe 名 OK,%~dp0 保证路径正确)

## 五、抓 CK 工具 v3 架构(内置代理版)

- 脚本自己启动 Chrome(不再由 bat 启动):检测 9222 → 无则 `subprocess.Popen(chrome, [--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=<工具目录>/profile --no-first-run])`
- 代理流程:读 proxy.txt(无则 input 一次保存)→ 有代理起桥 → Chrome 加 `--proxy-server=http://127.0.0.1:桥端口` → 用户登录 → 轮询 sessionid(2s,连续 2 次一致,`len>=25` 才算真实登录)→ 自动抓取 → ctypes 剪贴板 + MessageBoxW 弹窗(提示:绑定平台时把同一代理也填上,保证抓取IP=登录IP=采集IP)
- 用户侧价值主张:**抓取 IP = 登录 IP = 采集 IP 三合一,风控最小**——抓 CK 时就走代理,而不是抓完再找"与登录 IP 一致的代理"

## 六、GUI 整合版（tkinter,2026-08 用户拍板"完整 exe：IP 列表 + 右键抓取 + CK 列复制"）

源码 `tk_ck_gui.py`（ttck 目录），PyInstaller `--onefile --windowed` 打包。

- **界面**：ttk.Treeview 三列（代理 IP / 状态 / Cookie）+ 顶部按钮（＋添加 IP / 复制 Cookie / 删除选中）+ 右键菜单（**登录 TK 并抓取 CK** / 复制代理 / 复制 Cookie / 删除）；双击行 = 复制 Cookie；Cookie 列截断显示（`ck[:60]+...`）
- **添加 IP**：输入 `socks5://user:pass@host:port#美国` 等格式（parse_proxy 校验，留空=本机直连）；数据存 `data.json`（exe 旁，`{proxy,status,ck}[]`），关闭重开不丢
- **每 IP 独立浏览器实例**：独立 user-data-dir（`profiles/p<端口>`）+ 独立调试端口（`free_port(9222)` 找空闲）+ 独立认证桥 → **多 IP 并行抓取互不干扰**，且各 IP 登录态独立保留（再抓免登录）
- **线程模型**：每个 IP 一个 GrabTask 线程 + `queue.Queue` 发消息 + `root.after(200)` 轮询消息泵更新 Treeview/存盘——**绝不直接在线程里操作 tkinter 控件**（tkinter 非线程安全）
- 抓取成功：自动复制剪贴板 + messagebox 提示（提醒绑定平台填同一代理）
- 交付包结构（用户偏好）：文件夹放桌面 = `抓CK工具.exe` + `chrome/`（内置便携 Chrome）+ `使用说明.txt`(GBK)，再压 zip 发给客户

## 七、内置 Chrome for Testing（客户零依赖,2026-08）

- CfT 官方便携版（免安装、无自动更新、无残留），查最新 Stable win64 URL：`https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json`（`channels.Stable.downloads.chrome` 里 platform=win64 的 url）
- **★Google Storage 直连巨慢（202MB 下 3 分钟才 2.3%）→ 用 npmmirror 国内镜像**：`https://registry.npmmirror.com/-/binary/chrome-for-testing/<版本>/win64/chrome-win64.zip`（3 分钟下完 202MB）
- 分发结构：工具目录下 `chrome/chrome.exe`（解压 chrome-win64.zip 后把 chrome-win64 目录重命名/复制为 chrome）；体积 ~440MB（zip ~205MB）
- `find_chrome()`：**优先内置 `HERE/chrome/chrome.exe`**，找不到再回退系统 Chrome 路径（双保险，老客户无内置也能用）
- CfT chrome.exe `--version` 单进程测试会打 crashpad 噪音日志——正常，别当 bug

## 八、tkinter GUI 打包新增坑（PyInstaller,2026-08 实测）

- **★simpledialog.askstring 不支持 `width` 参数**：`_QueryDialog.__init__() got an unexpected keyword argument 'width'`——异常被 tkinter 回调**静默吞掉**，表现为"点击添加没反应"（症状极隐蔽）。去掉 width 即可；以后自定义弹窗优先用 Toplevel
- **★tk.Frame 构造参数不支持元组**：`tk.Frame(root, pady=(0,10))` → `bad screen distance "0 10"` 启动即崩（**pack/place 的 pady 才支持元组**，构造参数只接受标量）
- **--windowed 模式错误完全不可见**（无控制台 stderr），崩了表现为"点了没反应/一闪而过"。**调试法：先打 console 版（不带 --windowed）跑一遍看 traceback，修完再打 windowed**；console 版名称加 `_dbg` 后缀区分
- GUI 版用 `--windowed`（无黑窗口）；命令行工具保留 console 版
- 测试 exe 的完整交互（点按钮/弹窗）无法自动化——至少验证：进程存活、MainWindowTitle 正确（PowerShell `Get-Process 抓CK工具 | Select MainWindowTitle`）、find_chrome 返回内置路径
