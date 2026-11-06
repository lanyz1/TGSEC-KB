---
name: tiktok-ck-tool-dist
description: >-
  测绘引擎·用 when 打包/发版 TikFlow 抓CK客户端工具（GUI exe + 内置Chrome + 云端更新下发）。
owned: true
tier: ops
pack: survey-skill
---

# tiktok-ck-tool-dist（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/tiktok-ck-tool-dist/`

溯源（仅标记）：`hermes/software-development`

---

# TikFlow 抓 CK 工具打包与云端更新

## 触发条件
- 用户要"打包抓CK工具 / 发给客户 / 下发云端更新 / 工具改版"

## 工具链位置（本机）

| 项 | 路径 |
|---|---|
| GUI 源码 | `C:\Users\Administrator\Desktop\ttck\tk_ck_gui.py`（主推，内置代理+更新） |
| bat 版源码（旧） | `C:\Users\Administrator\Desktop\ttck\抓tk_ck.py` |
| 打包 venv | `%LOCALAPPDATA%\Temp\pybuild`（pyinstaller + websocket-client） |
| 交付目录 | `C:\Users\Administrator\Desktop\TikFlow-CK抓取工具\`（exe + chrome/ + 使用说明.txt） |
| 全量 zip | 桌面 `TikFlow-CK抓取工具.zip`（~205MB 含 Chrome） |
| 老客户更新包 | 桌面 `TikFlow-CK更新包.zip`（~12MB：新exe + 更新.bat + 更新说明.txt） |

## 打包命令（GUI 版）

```bash
cd /c/Users/Administrator/Desktop/ttck
"$LOCALAPPDATA/Temp/pybuild/Scripts/pyinstaller" --onefile --windowed --name 抓CK工具 \
  --distpath dist2 --workpath build2 --specpath . tk_ck_gui.py
cp -f dist2/抓CK工具.exe "/c/Users/Administrator/Desktop/TikFlow-CK抓取工具/"
```

## 发布新版（3 步）

1. **改版本**：`tk_ck_gui.py` 顶部 `APP_VERSION = "x.y.z"`（必须 != 服务器 version.json 里的版本号，否则不触发）
2. **打包**：上面的命令（自动进交付目录 + 更新包）
3. **上传服务器**（SSH 118.107.3.134:14003，密码见 memory）：
   - SFTP 上传 exe → `/srv/tikflow/public/tool/抓CK工具.exe`
   - 改 `/srv/tikflow/public/tool/version.json`：`{"version":"x.y.z","url":"https://tiktide.com/tool/抓CK工具.exe","note":"更新说明","size":<exe字节>,"force":true|false}`
   - **无需 build/重启**（Caddy 静态服务直接生效）
   - 验证：`curl https://tiktide.com/tool/version.json` 返回新版本
   - 最后：刷新桌面 `TikFlow-CK更新包.zip`（`rm -f` 后重新 Compress-Archive，目录 `桌面\TikFlow-CK更新包\`）

客户端行为：**60 秒轮询** version.json → 版本不同 → 弹窗：
- `force:true`（强制）：弹"需要更新，更新后才能继续使用"，无"稍后"，点关闭=退出程序；更新失败也退出（下次重开再试）
- `force:false`（可选）：弹"发现新版本"可稍后，5 分钟冷却后自动再提示
→ 下载 exe → update.bat（杀进程→覆盖→重启）

## Caddy 静态服务配置（已配好，勿动）

```caddy
tiktide.com, www.tiktide.com {
    @tool path /tool/*
    handle @tool {
        root * /srv/tikflow/public   # 必须 public（file_server 用 root+URI 拼接查找）
        file_server
    }
    handle { reverse_proxy 127.0.0.1:3000 }
}
```
注意：Next 生产模式不实时服务 public/ 新增文件（404），必须走 Caddy handle。

## 内置 Chrome（CfT 便携版）

- 位置：交付目录 `chrome/`（chrome.exe 等，152.0.7977.42）
- `find_chrome()`：**优先 `HERE/chrome/chrome.exe`**，找不到退回系统 Chrome
- 更新 Chrome 版本：npmmirror 镜像下载（Google 直连极慢）：
  `https://registry.npmmirror.com/-/binary/chrome-for-testing/<版本>/win64/chrome-win64.zip`
- 版本查询：`https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json`

## PyInstaller / tkinter 坑位（血泪）

1. **frozen 路径**：onefile 模式下 `__file__` 指向临时解压目录！必须：
   `HERE = os.path.dirname(sys.executable if getattr(sys,"frozen",False) else os.path.abspath(__file__))`（data.json/profiles/proxy.txt 都在 HERE）
2. **GBK 控制台**：cmd 下 exe 输出中文正常，但 **emoji（✅⏳🌐等）UnicodeEncodeError 崩溃**——print 里禁用 emoji；windowed 版无控制台但 messagebox 也避免
3. **simpledialog.askstring 不支持 width 参数**（TypeError 被 tkinter 吞掉→点击无反应）
4. **tk.Frame 构造参数不支持 pady 元组**（`pady=(0,10)` → "bad screen distance"；pack() 才支持元组）
5. **update.bat 必须 GBK 编码**（含中文路径），CRLF
6. 中文 exe 名打包 OK（--name 抓CK工具），但 taskkill 引用注意

## SOCKS5 认证桥（Chrome 不支持 socks5 认证）

- Chrome `--proxy-server` 不支持 socks5 账号密码 → 本地起 HTTP CONNECT 桥转发到上游 SK5（`SocksBridge` 类，纯标准库）
- **必须读完 SOCKS5 CONNECT 响应的剩余地址字节**（ATYP 后 IPv4 6B/域名 1+n+2/IPv6 18B），否则残留字节污染 TLS 流 → ERR_SSL_PROTOCOL_ERROR
- 支持 `#美国` 备注标签（parse 时剥离 `#.*$`）
- 带认证 http(s) 代理：Chrome 走 `page.authenticate`（服务器端）或 URL 直带（客户端抓取场景）

## 老客户手动更新包（无更新机制的旧版）

- `TikFlow-CK更新包.zip`：抓CK工具_new.exe + 更新.bat + 更新说明.txt
- 更新.bat：`taskkill /f /im 抓CK工具.exe` → `copy /y new.exe 抓CK工具.exe` → `del new.exe` → `start 抓CK工具.exe` → 自删
- 客户：解压到工具文件夹 → 双击 更新.bat（数据 data.json 保留）
- 老客户升一次后即纳入云端更新体系，以后全自动

## 版本历史与机制演进

| 版本 | 关键能力 |
|---|---|
| 1.1.0 | 内置 Chrome + 首个云端更新（启动时检查） |
| 1.1.1 | 页面加载校验（防误抓旧 Cookie） |
| 1.1.2 | 30 分钟定期检查 |
| 1.1.3 | 标题栏版本号 + 手动"检查更新"按钮 + 网络失败可见提示 |
| 1.1.4 | **60 秒轮询**（发版后分钟内同步）+ 拒绝后 5 分钟再提示 |
| 1.1.5 | **强制更新**（version.json force 字段，不更新退出） |
| 1.1.6 | **★多账号隔离**：profile 按代理 host:port 固定（`profile_dir_for` md5(host:port)[:10]，同一代理保留登录态/不同代理互不串号；旧版按调试端口命名会串号）+ 右键「清除该代理登录态/缓存」（删 profile 目录）+ 已登录检测提示（轮询首轮即见 sessionid → 提示"检测到已登录，直接抓取，换账号先退出登录"）+ 抓取成功提示加"每账号独立代理 IP" |
| 1.1.7 | **★修复自动更新必败 bug**：`_do_update` 里 `info["url"]` 是中文文件名 URL（`/tool/抓CK工具.exe`），urllib 直接 `UnicodeEncodeError` → 下载从未开始 → 用户"点更新没反应/无进度"。修复：`quote(info["url"], safe=":/?&=#%")`。**教训：工具下载地址若含中文，必须 quote；version.json 的 url 保持原文+工具端 quote（quote 对已编码 % 安全）**。v1.1.5/1.1.6 客户自动更新坏 → 必须发手动更新包 |
| 1.1.8 | **★修复"登录成功后跳转 ERR_PROXY_CONNECTION_FAILED"（用户实测必现）**：根因 = 桥 CONNECT 正则 `^CONNECT ([^:]+):(\d+)` **不匹配 IPv6 目标**（`CONNECT [2606::1]:443`）→ 502；Chrome 走代理时自己解析 DNS，TikTok CDN 域名解析出 IPv6 → 登录后资源爆发 IPv6 命中率高 → "首页能开、登录后必炸"。修复：① 正则 `^CONNECT\s+(\[[0-9a-fA-F:.]+\]|[^:\s]+):(\d+)\s+HTTP` + `strip("[]")`；② `_socks5_connect` 加 IPv6 分支（`":" in host` → ATYP=4 `inet_pton(AF_INET6)`，否则 IPv6 地址被当域名 ATYP=3 发上游必失败）；③ listen(32)→128（登录后 30-50 并发爆发拒连）；④ fail_count 诊断计数。**验证法：向桥发 `CONNECT [2606:4700::1]:443` 应非 502；40 并发压测全过**。规律：Chrome 对显式代理自行解析 DNS，CONNECT 里是 **IP 而非域名**，IPv6 地址必带 `[]` |
| 1.1.9 | **★修复"登录后必断、未登录正常"第二根因（1.1.8 仍复现）**：SOCKS5 握手响应用 `sock.recv(4)` **单次读取**——上游响应分片时读不全 BND.ADDR → **残留字节污染后续 TLS 流量 → 连接必断**（症状：Chrome "未连接到服务器"）。低并发时上游响应快不分片→正常；登录后并发爆发响应慢/分片→必现。修复：`_recv_exact(sock,n)` 循环读满（协商/认证/CONNECT 三段全改）+ 诊断日志 `debug.log`（HERE 目录，失败写 时间+CONNECT目标+异常）。**验证法：假 SOCKS5 服务器分片发送响应（0.05s 间隔分 2-3 片），旧代码必残留脏字节/新代码无残留**。教训：协议栈读响应永远按"可能分片"处理，recv(n) 不保证一次读满 |
| 1.2.0 | **★更新链路彻底加固（用户多次报"点更新没反应"后重写）**：① **多源回退**：`UPDATE_URLS=[https://tiktide.com, http://118.107.3.134]`（Caddy 有 http://IP 块），主域名被墙/DNS 污染自动走 IP 直连；② **点击"检查更新"立即 hint 反馈**"正在检查更新..."，杜绝无反馈；③ **结果必弹窗**（新消息类型 `upd_done` 已是最新 / `upd_check_err` 检查失败弹窗不退出）；④ **★修复误退出**：检查更新失败之前走 `upd_err(force=True)` → `root.destroy()` 程序直接闪退（"没反应"真相之一），现独立消息只弹窗；⑤ **下载 sha256 校验**：version.json 加 `sha256` 字段，下载后 hashlib 比对（http 明文源防篡改），失败删文件重试；⑥ 下载也 IP 回退。**发布脚本必须算 sha256 写 version.json**（`sha256sum`） |
| 1.2.1 | **★修复"浏览器启动失败"误报**：GrabTask 启动 Chrome 后等调试端口只给 **10 秒**——慢电脑/首次启动 CfT 可达 30-40s → 必误报（Chrome 窗口明明出来了还报失败）。修复：① 等待 10s→**45s** 且每 5s 状态提示"正在等待浏览器启动... Ns"；② `p.poll()` 检测 **Chrome 进程退出 = 确定性失败**（杀软拦截/缺组件）→ 立即报"浏览器启动失败（Chrome 进程被退出）。可能是杀毒软件拦截，请将整个工具文件夹加入信任区"，不等超时；③ 45s 超时报错文案含杀软/退 Chrome 提示。**另：CfT 启动页面顶部"Chrome 仅适用于自动测试"黄色提示条 = CfT 官方 branding，无功能影响**（登录/抓取/绑定正常），客户问起直接解释，别当 bug 改 |
| 1.2.2 | **★代理链路第三轮加固（客户机仍"登录后断/白屏"）**：① **代理域名 DNS 预解析缓存**：`SocksBridge.__init__` 里 `gethostbyname(proxy.host)` 存 IP，`_connect_upstream` 优先连缓存 IP、失败重新解析再回退域名——客户机 DNS 解析海外代理域名（ga6x.com）慢/污染/超时会全断，登录后连接爆发时每连都解析必炸；② **握手并发信号量 30**（`BoundedSemaphore`）：登录后 Chrome 瞬间 30-50 个新连接同时向上游握手，无限制会打爆住宅代理并发封顶（50-100）→ 排队握手；③ **白屏检测**：等登录循环 30s 后 title 仍空且 URL 含 tiktok.com → 报"页面加载失败（白屏）"，错误页检测（chrome-error://）已有。**验证：60 并发压测 60/60 成功 1.6s**。规律：客户机问题 = 三个叠加（IPv6 502→分片污染→DNS/并发），每次修完让客户重测+发 debug.log |
| 1.2.5 | **更新链路加固（网络层）**：① `with ThreadPoolExecutor` 退出 `shutdown(wait=True)` 会等卡死的 DNS 线程（改 `wait=False`）；② http://IP 的 80 端口国内运营商普遍拦截 → IP 直连必须走 HTTPS 443（服务器 `https://118.107.3.134` 块 `tls internal` 自签，客户端 `_ssl_ctx_for` unverified context，内容 sha256 校验兜底）；③ 提示明确化：源 x/2 进度 + 失败原因 + 弹窗 |
| 1.2.6 | **★★终极根因（v1.1.5 起所有"点更新没反应/一直检查更新"的真凶）——消息泵崩溃**：`_drain` 解包 `it, typ, data = msg_q.get_nowait()`（三元组），但 check_update 发的 `("status2",...)`/`("update",info)`/`("upd_done",...)` 全是**二元组** → **ValueError → _drain 崩溃 → root.after 不再注册 → 消息泵永死** → hint 停在"正在检查更新..."、弹窗永不出现。修复：① `_drain` 解包防御兼容 `len(msg)==3` 三元 / 二元（`it=None`）；② 单条消息处理包 try/except 写 debug.log，**泵永不崩**；③ 顺带修 `upd_err` 消息格式错位。**教训：Tkinter 消息泵是单点，任何格式不一致/异常都会静默杀死整个 UI 消息流；新增消息类型必须与解包格式一致 + 单条异常隔离。排查"点了没反应"先搜全部 `msg_q.put` 与解包是否匹配** |
| 1.2.8 | **★修复更新后启动报 "Security validation failure: failed to obtain executable path for parent process"**：PyInstaller onefile bootloader 启动时校验**父进程可执行路径**——update.bat 用 `start "" exe` 从 cmd 启动，bat 随即 `del "%~f0"` → cmd 父进程退出 → bootloader 拿不到父进程路径 → 报错退出（客户机慢 onefile 解压 5-10s、Win11 24H2 必现；本地 SSD 解压快+cmd 存活窗口内校验完成→难复现）。修复：**`start "" explorer.exe "exe"`**（父进程=常驻 explorer 模拟双击，校验必过）+ `timeout /t 5` 保底 + copy 失败 errorlevel 检查。**教训：PyInstaller onefile 从 bat/cmd 启动必须用 explorer 中转或保持父进程存活；排查"更新完报 Security validation"先看启动方式** |
| 1.3.0 | **★全面检查修复（用户要求"找到并修复所有 bug"）**：① **抓取结束 Chrome 不关闭**（泄漏+重复抓同代理 profile 冲突+clear_profile 失效）→ finally 加 `_kill_chrome()`，stop() 也 terminate；② **防重入判断 bug** `it["task"]._stop is False` 恒假（Event 对象 `is False` 永假）→ 改 `not ._stop.is_set()`，否则并发重复抓取；③ `get_all_cookies` ws.recv 无超时→`ws.settimeout(30)`；④ **自动检查更新失败常驻状态栏"检查更新失败"骚扰**（即用户报的"提示检查网络"来源之一）→ force=False 失败静默；⑤ 抓取成功弹窗取消（批量烦人）→ hint+状态列+剪贴板；⑥ free_port 死循环→上限 200；⑦ error 消息 it=None 判空；⑧ Chrome 启动加 `--hide-crash-restore-bubble --disable-session-crashed-bubble`（terminate 后下次无恢复气泡） |
| 1.3.2 | **★作品同步通道（服务端 Linux 浏览器被 TikTok 深度指纹风控后的替代方案）**：TikTok 2026 对 Linux 服务器浏览器环境账号页深度风控（platform/WebGL/时区伪装全无效，页面 200 但无 SSR/无 item_list；外部签名重放 200 空）→ **作品采集只能在客户端真实 Windows 环境做**。新增：① `CDPClient` 极简 CDP（单 recv 循环 + id 回调——websocket 非线程安全，多线程 recv 必乱）；② `collect_videos_cdp`：游客 profile + `Page.addScriptToEvaluateOnNewDocument` 隐藏 webdriver + `Network.enable` + 滚动 8 次触发原生 item_list + `Network.getResponseBody` 拿响应（**完整 Chrome 上 getResponseBody 可用**，Node/CDP 空 body 是延迟获取问题）；实测 95 条/4 分页；③ `upload_videos_sync` POST tiktide.com/api/tiktok/videos/sync（syncToken 认领 + upsert）；④ GUI「同步作品」按钮 + Toplevel 弹窗（同步码/handle，代理用选中行）。服务器配套：TikTokAccount.syncToken（randomBytes(6)）+ 绑定 API 返回 + 绑定页成功弹窗显示同步码 + sync API。**教训：TikTok 采集 2026 = Linux 服务器环境指纹不可伪装（platform 只读、WebGL 无 GPU、Intl 覆盖失败），唯一可靠 = 客户端真实浏览器** |
| 1.3.3 | **★修复"同步作品没反应"（用户实测必现）**：① **线程静默死亡主因**：`f"guest_{abs(hash(proxy['host'] + proxy['port']))}"`——`proxy['port']` 是 int（parse_proxy 转 int），str+int → TypeError 在 `try` 外 → 线程崩溃零回调 → GUI 无任何反馈 = "没反应"。修复：host 转 str 拼接 + **SyncTask.run 整体 try/except（任何异常必须回调 error，严禁静默死亡）** + 每步 status 事件 + debug.log 日志（HERE 目录）；② 上传回调签名不匹配：`upload_videos_sync(on_status=self.on_event)` 单参 vs on_event 双参 → TypeError 上传前崩 → 改 `lambda s: self.on_event("status", s)`。**教训：新增线程任务必须①整体 try ②回调签名一致 ③每步进度事件；"点了没反应"先查线程是否异常死亡（traceback 写日志）** |

## 客户端更新逻辑要点（tk_ck_gui.py）

- `APP_VERSION` 常量 + `UPDATE_URL`（https://tiktide.com/tool/version.json）
- 启动即查 + `root.after(60_000)` 循环查
- `_update_cooldown_until`：可选模式提示后 5 分钟冷却
- `_do_update(info, force)`：下载到 `抓CK工具_new.exe` → 写 update.bat（**GBK 编码**）→ cmd 执行 → 杀进程/覆盖/重启/自删
- 强制模式更新失败 → messagebox + `self.root.destroy()`（不能继续用旧版）
- 错误提示可见：`status2` 状态栏 + `upd_err` 弹窗

## 验证清单（发版后）

- [ ] 本地打包成功（pyinstaller Build complete）
- [ ] `curl https://tiktide.com/tool/version.json` 返回新版本号
- [ ] `curl -o /dev/null -w '%{http_code}' https://tiktide.com/tool/抓CK工具.exe` = 200
- [ ] 交付目录 exe 已更新（大小一致）
- [ ] 老客户：更新包 zip 重新压缩（若 exe 有变）
