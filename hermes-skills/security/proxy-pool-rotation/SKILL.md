---
name: proxy-pool-rotation
description: Use when 部署 proxy_pool+proxyServer 代理池轮换IP。含接入与排障。
---

# 代理池轮换 IP（proxy_pool + proxyServer）

## 架构（两层）
```
[免费代理源 fetcher/sources/*.py] ──抓取──> proxy_pool(Python, 5010 API) ──验证入库──> Redis
[住宅代理 自定义fetcher] ─────────────────>          │
                                                     ▼
                        proxyServer(Java, 1080) ──> 每次请求从 /get/ 取代理转发，轮换出口IP
```
- proxy_pool 仓库: github.com/jhao104/proxy_pool（Python3.10 venv，依赖 Redis 存 hash `use_proxy`）
- proxyServer 仓库: github.com/safe6Sec/proxyServer（Java8+，Maven 编译，需打 shade fat jar 才能 `java -jar`）

## 部署步骤（实测）
1. `apt install redis-server maven`；redis 启动后 proxy_pool 的 `setting.py` 改 `DB_CONN='redis://@127.0.0.1:6379/0'`（无密码）+ `VERIFY_TIMEOUT=3`
2. proxy_pool: `python3.10 -m venv venv && venv/bin/pip install -r requirements.txt`；启动 `python proxyPool.py server`（5010）+ `python proxyPool.py schedule`（抓取调度）
3. proxyServer: pom.xml 加 maven-shade-plugin（Main-Class=com.caspar.ProxyServer）打包 fat jar；`java -jar proxyServer.jar 1080`（端口避开小兵默认 8080）
4. systemd 用户服务 3 个（防 gateway 重启杀进程）：proxypool-server / proxypool-schedule / proxyserver，均 `Restart=always`，`Type=simple`，`WorkingDirectory` 指到项目根

## 关键坑：proxyServer 的 CONNECT 隧道 bug（必修）
- 症状：成功率只有 50%，日志 `Unable to tunnel through proxy. Proxy returns "HTTP/1.1 400 Bad Request"`
- 根因：原版 `new Socket(ProxyUtil.getProxy())` 用 Java `Proxy.Type.HTTP`，对 **HTTP 目标也强制发 CONNECT 隧道**；而免费代理是普通转发代理（期望 `GET http://host/path HTTP/1.1` 绝对URI格式），返回 400
- 修复：ProxyUtil 加 `getProxyAddress()` 返回 `InetSocketAddress`；ProxyTask 直接 `new Socket()` 连代理地址，**HTTP 目标发 requestLine+headers 普通转发，HTTPS(CONNECT) 才发 `CONNECT host:443` + 读状态行 200**；代理失效重试 3 次重新 getProxyAddress()
- 修复后成功率 50%→70%（免费代理固有上限；成功时出口 IP 每次不同=轮换正常）

## 接入代理源
- fetcher 放 `/opt/proxy_pool/fetcher/sources/*.py`，继承 `BaseFetcher`，`name`/`url`/`enabled=True`，`fetch()` yield `"ip:port"`。schedule 用 `_discover_fetchers` 按 mtime 热更新自动发现新文件
- 免费源 HTML 表格解析正则：`r'<tr><td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d+)</td>'`（free-proxy-list.net / sslproxies.org / hidemy.name 同构）
- 住宅代理接入：自定义 fetcher yield 住宅 `ip:port`（HTTP 协议；验证器只要求 HTTP `head(httpbin.org)` 200 即入库，HTTPS 只是标记 https 属性不影响 last_status）
- 手动触发抓取入库：`python -c "from helper.fetch import Fetcher; from helper.check import DoValidator; from handler.proxyHandler import ProxyHandler; ..."`（Proxy 类路径是 `helper.proxy` 不是 `proxy`）

## 批量导入已有代理列表（绕过 fetcher，最快）
- 用户给的代理文件（socks5.txt / valid_*.txt）→ 先并发验证质量，再直接写 Redis，比走 fetcher+schedule 快一个量级
- 并发验证脚本：`requests.get("http://httpbin.org/ip", proxies={"http": f"http://{p}"}, timeout=5)`；socks5 用 `proxies={"http": f"socks5://{p}"}`（需 PySocks，系统 python3.10 已装 requests+PySocks）。ThreadPoolExecutor 40 线程，2619 个代理约 4 分钟跑完。实测免费列表 HTTP 79%、socks5 26% 可用率
- 直接写 Redis：`r.hset("use_proxy", p, json.dumps({...}))`，JSON 字段 `{proxy,https:false,fail_count:0,region:"",anonymous:"",source,check_count,last_status:true,last_time}`。redis 模块在 proxy_pool 的 venv（`/opt/proxy_pool/venv/bin/python`），系统 python 没有
- socks5 代理不走 proxyServer（它只做 HTTP 转发），单独生成 proxychains4 配置：`random_chain` + `[ProxyList]` 每行 `socks5 ip port`，用法 `proxychains4 -f /root/proxychains_socks5.conf <工具>`
- 灌入刚验证的高质量代理后，proxyServer 成功率可从 70% 拉到 100%（20/20）

## 「替身 IP」= 池里的代理，用非 HTTP 协议打目标（MySQL/SSH/RDP）

被目标 ban 掉后，HTTP 走 `1081`/`1080` 就够；但 **MySQL 3306 / SSH 22 / RDP 3389 不吃 HTTP 代理**。

### ❌ 先排除的错误做法
- **socat 不支持 SOCKS5**：`socat TCP-LISTEN:29999,fork SOCKS5:...` →
  `E unknown device/address "SOCKS5"`（Debian/Ubuntu 的 socat 编译未启用 SOCKS）。
  同理 `ssh -o ProxyCommand='nc -X 5 -x ...'` 依赖 nc 的 SOCKS 支持，不可靠。
- **proxychains4 走 SOCKS5 能用但极慢**：默认只吃**第一个**代理，22180 组合 4 分钟才跑 300 发。
  要轮换得给每个代理生成一份 conf，切换成本高于收益。

### ✅ 正解：PySocks 自建 TCP 转发器（本地端口 → SOCKS5替身 → 目标端口）
```python
import socks, socket, threading
# 每个替身开一条本地监听，双向 pipe
class Forwarder:
    def __init__(self, proxy, target, local_port): ...
    def start(self):
        self.srv.bind(("127.0.0.1", self.port)); self.srv.listen(64)
        threading.Thread(target=self._loop, daemon=True).start()   # accept → _handle
    def _handle(self, c):
        u = socks.socksocket(); u.set_proxy(socks.SOCKS5, px[0], px[1], rdns=True)
        u.connect((target_ip, 3306))          # 双向 pipe 线程
```
调用方（pymysql / paramiko）连 `127.0.0.1:<local_port>` 即可，**无需改库代码**。

**必须用 `/root/pentest-venv/bin/python`** —— 系统 python3 没有 `socks`（PySocks）模块，
`ModuleNotFoundError: No module named 'socks'`（系统 pip 装它会被 PEP668 拦）。

### ⚠️ 替身必须先筛选，否则隧道 0 条
331 个替身里**只有 25 个（7.5%）能连通目标 3306**（免费代理只能到部分目标/部分端口）。
直接拿 `/all/` 前 15 个开隧道 → **活隧道 0，白等**。
先跑筛选（socket 连目标端口 + 读 banner 校验归属），把能用的写 `good_proxies.json` 再开隧道。
筛选时**用 banner 校验**（MySQL 前 4 字节 `J\x00\x00\x00` + 版本串），别只看 connect 成功。

## IP 封禁是「端口级」不是「全 IP DROP」—— 判据与切换

**实测**：对同一目标爆破过猛后，本机出现
`HTTP 000` + `MySQL FAIL` + **`SSH 仍 OK`**。
→ 说明封禁按**端口/连接类型**施加（或按失败频率触发 fail2ban 规则），**不是整台 DROP**。

**切换判据（出现任一条立刻上替身）**：
- curl 返回 `000` / `Connection timed out`（之前正常）
- TCP `connect` 超时但 ICMP 还通
- 服务端错误页突然变成防火墙页（如 FortiGate 的 `Web Page Blocked`）

**注意**：换替身后要**降并发**。60 线程打 MySQL 会把替身也拖慢/拖死，
15 条隧道 × 4-5 线程（`len(fwds)*4`）比较稳。

## 验证与使用
```bash
curl -x http://127.0.0.1:1080 http://httpbin.org/ip   # 每次请求轮换出口IP
curl http://127.0.0.1:5010/get/                        # 取单个代理
redis-cli hlen use_proxy                              # 代理池数量（hash类型，别用 zcard）
systemctl --user restart proxyserver                  # 管理
```

## ⚠️ 关键盲区：验证器只测 HTTP，HTTPS 全挂（实测）

**症状**：`curl -x http://127.0.0.1:1080 https://目标` 全是
`Proxy CONNECT aborted` / `Received HTTP code 400/405/500` / `wrong version number`。
而同一时刻 `curl -x http://127.0.0.1:1080 http://目标` 正常轮换 IP。

**根因**：proxy_pool 的验证器只测 `head(httpbin.org)`（**HTTP 转发**）就入库，
所以池里混了大量「只支持普通 HTTP 转发、不支持 CONNECT 隧道」的代理。
实测 170 个池内代理：**CONNECT 可用仅 41 个（24.1%）**，
其中 77 个是「HTTP 能用、HTTPS 必挂」。`https:true` 这个字段是空头支票，**不可信**。

**先隔离根因再动手**：拿池里代理直接 `curl -x http://<proxy> https://api.ipify.org`，
能过 CONNECT 的代理回 `HTTP/1.1 200 Connection established`。
如果**直连代理也挂**，问题在代理本身，不是 proxyServer —— 不要瞎改 proxyServer。

### 解法：CONNECT 能力验证器 + 专用轮换代理

`/root/proxy_health/`（systemd 用户服务，见下）：

| 文件 | 作用 |
|---|---|
| `proxy_connect_check.py` | socket 级 CONNECT 探测（连代理 → 发 `CONNECT host:443` → 读状态行是否为 200），并发 60 线程，170 个代理 18 秒跑完 |
| `pool_keeper.py` | 循环：Redis `use_proxy` 全池 → CONNECT 验证 → 原子写 `connect_proxies.txt`（默认 15 分钟一轮）|— 防止把池子清空：本轮 0 可用时**保留旧清单不动** |
| `rot_proxy.py` | 本地轮换代理（默认 `127.0.0.1:1081`），**只用 CONNECT 验证过的上游**；HTTP 转发 + CONNECT 隧道都支持；每请求换 IP，失败自动换下一个（默认重试 4 次）；上游连续失败 3 次临时拉黑 180 秒 |

服务：`systemctl --user enable --now rotproxy.service proxykeeper.service`
（+ `loginctl enable-linger root`，否则 gateway 重启会被 SIGTERM 连坐）。

**效果：HTTPS 轮换 0% → 60%**（10 次里 6 次拿到不同出口 IP）。
剩下的失败是免费代理固有：撒谎（ CONNECT 回 200 后立刻掉线）、
MITM 插证书（curl 报 `EE certificate key too weak` → 工具加 `-k` 绕过）。

### 写 CONNECT 隧道的两个必须（都踩过）

1. **把上游 CONNECT 响应的整段头部读到空行为止**。只读状态行的话，
   尾部残留的 `\r\n` 会被原样转给客户端 → TLS 握手前多两字节 →
   curl 报 `error:0A00010B:SSL routines::wrong version number`。
   这个 bug 极难查，因为 CONNECT 看起来是成功的。
2. **HTTP 转发要剥掉 hop-by-hop 头**（`Proxy-Connection` / `Connection` /
   `Keep-Alive` / `Upgrade` / `Proxy-Authorization`），否则部分代理行为异常。

### 用法
```bash
python3 /root/proxy_health/proxy_connect_check.py --http-check   # 全池体检
curl -x http://127.0.0.1:1081 https://api.ipify.org             # 验 HTTPS 轮换
curl -x http://127.0.0.1:1080 http://api.ipify.org              # HTTP 仍走 proxyServer
tail -f /root/proxy_health/keeper.log                           # keeper 刷新日志
```

## 批量代理源可用性台账（2026-09-28 实测）

**结论：给了 37 个源 → 实测 20 可用；修正 2 个 URL 错误；追加 9 个新发现可用源 → 共 36 个源入库，单轮抓取 116,280 条。**

### ❌ 确认失效（别再浪费时间）
| 源 | 真因 |
|---|---|
| `openproxy.space/list/{http,socks4,socks5}` | **HTTP 521**（Cloudflare 源站长期挂），首页也挂，换入口无用 |
| `raw.githubusercontent.com/UserR3X/proxy-list/*` | **404**，仓已删 |
| `raw.githubusercontent.com/manuGMG/proxy-365/main/SOCKS5.txt` | **404** |
| `www.proxy-list.download/api/v1/get?type=*` | **502 / 429**，服务不可用 |
| `www.proxyscan.io/download?type=*` | **301 跳 whoer.io 后 404**，API 已废弃 |
| `raw.githubusercontent.com/Volodichev/proxy-list/main/http.txt` | 返回 54 字节提示 **仓库搬家** → 新家 `proxy4parsing/proxy-list`（19031 条，见下） |

### 🔧 修好就能用（原提供 URL 是错的）
```
✘ jetkai/.../txt/proxies-http%2Bhttps.txt   → 404 文件名错
✔ jetkai/.../txt/proxies-http.txt    1801 条
✔ jetkai/.../txt/proxies-https.txt   2161 条
```
> **教训**：同仓 socks5/socks4 都 200 而 http 404 → 一定先 `api.github.com/repos/<owner>/<repo>/contents/<dir>` 列真实文件名，别臆测。

### ★ 新发现可用源（原清单里没有，量大）
| 源 | 路径 | 条数 |
|---|---|---|
| proxy4parsing（Volodichev 新家）| `proxy4parsing/proxy-list/main/http.txt` | **19031** |
| 同上百代理表 | `.../main/hproxy.txt` | **11395** |
| proxifly（全量文本版）| `proxifly/free-proxy-list/main/proxies/protocols/http/data.txt` | 4884 |
| proxifly SOCKS5 | `.../protocols/socks5/data.txt` | 27050 |
| hookzof SOCKS5 | `hookzof/socks5_list/master/proxy.txt` | 27050 |
| monosans | `monosans/proxy-list/main/proxies/{http,socks4,socks5}.txt` | 470/73/276 |
| hideip.me | `zloi-user/hideip.me/main/{http,socks4,socks5}.txt` | 272/313/505 |
| ALIILAPRO | `ALIILAPRO/Proxy/main/http.txt` | 1244 |
| yakumo（自带存活校验）| `elliottophellia/yakumo/master/results/http/global/http_checked.txt` | 382 |
| ShiftyTR | `ShiftyTR/Proxy-List/master/{http,socks5}.txt` | 40/279 |

> ⚠️ **proxifly 有两个 fetcher 不要搞混**：已有 `proxifly.py`（JHao 原版）走 jsdelivr **JSON 端点且只筛 CN+http**；
> 新增 `proxifly_http` / `proxifly_socks5` 走 **raw 文本端点取全量**。两者并存互补，不是重复。

### 入库实操（已落地）
- 36 个源写成**一个模块** `/opt/proxy_pool/fetcher/sources/hanli_sources.py`（`_RawFetcher` 基类 + 每源一个子类），
  `helper/fetch.py` **自动扫描 sources/ 目录**发现，无需改任何注册表。
- 单源失败不能拖垮整池：基类 `fetch()` 里 **try/except 吞掉异常返回空**。
- 加源后 **`systemctl --user restart proxypool-schedule`** 强制重扫目录（调度器 5 分钟一轮，
  虽热更新但重启最稳）。命令行验证：`python proxyPool.py fetcher` 列出全部 active 源。
- 增长实测：池 **158 → 285**，其中 **120 条（42.1%）来自新源**（74 条纯新源独供）。

### ⚠️ `/count/` 的 `source` 字段是多源共标，不能直接求和
一个代理可同时被多个源报出，标签形如 `hendrikbgr/aliilapro/speedx_http/proxifly_http/proxyscrape_http`。
**按源求和会大于总数**（实测 source 求和 516 vs 池内 285）。要算准确占比必须先 `GET /all/` 拉全池，
按 `/` 拆标签再统计（脚本：`/root/proxy_health/pool_stats.py`）。

### 源验活脚本
`/root/proxy_health/test_proxy_sources.py` —— 并发拉取所有源 URL，正则抽 `ip:port`，输出可用/失效清单 + JSON。
```bash
python3 /root/proxy_health/test_proxy_sources.py --json /root/proxy_health/sources_status.json
```
**定期跑**：免费源生命周期短，隔几周就要重验一遍（尤其 GitHub raw 仓会改名/搬迁）。

### 周更自动巡检（已落地）
- 脚本：`~/.hermes/scripts/proxy_source_monitor.py`（**纯 stdlib**，cron 环境的 python 不一定有 requests）
- cron job `49bd7941b9a9`「代理源健康巡检」，`every monday 9am`，`deliver=origin`，挂 `proxy-pool-rotation` 技能
- **用 Hermes 的 `monitor` 门控**（不是 `script`）：脚本输出经哈希比对，**不变就完全跳过 agent**，只有源状态变了才唤醒 → 平时零 LLM 成本
  - 脚本输出必须**严格确定性**（无时间戳/无条数波动），否则每轮都像变了
  - monitor 输出契约：`DEAD=<url>` 每行一个确认失效源；全好则 `DEAD=none`
  - 首次运行只建基线不报警（否则会把全部源当“新失效”炸出来）
- **2 次连续失败才判 DEAD**（strikes 计数存 `source_state.json`）—— 免费源经常瞬时 502/521，不防抖就是周周狼来了
- 手动看完整报告：`python3 ~/.hermes/scripts/proxy_source_monitor.py --report`
- **报警器必须验证**：`bash /root/proxy_health/test_alarm.sh` 注入必然失效的假源，
  验证①第1次失败被压制②第2次触发 DEAD③报警态下输出仍确定性。
  不验证的报警器等于没有。

## ⚠️ 代理撒谎：CONNECT 200 + 有数据 ≠ 目标可达

**实测案例**（查 `18.136.26.221:8853` 是否开放时踩到）：
某代理对目标的 **80(closed) / 443(closed) / 8853(filtered) / 9999(不存在)** 四个端口
**全部返回「有数据」**，内容里 `Server: squid/3.5.28`、`REMOTE_ADDR` 恒等于代理自己的 IP。
→ 它压根没连目标，而是把任何 CONNECT 都回了自己的 Squid 页面。

**假阳性有多危险**：会得出「端口开放，只是封了我 IP」的完全错误结论，
进而误判目标资产状态。**内容 md5 有微小差异也不能当证据** —— 差异常只来自
`REQUEST_URI` 里带的端口号，关键字段（Server / REMOTE_ADDR）完全一致就是铁证。

### 识别方法：对照组（必做）
拿同一个代理去连**已知必然关闭的端口**（目标的 80、或不存在的 9999）：
- 「死端口」也返回数据 → **代理撒谎，它给出的所有结论全部作废**
- 死端口无数据而目标端口有数据 → 代理诚实，数据可信

脚本：`/root/proxy_health/control_test.py`（多代理 × 多端口交叉对照，自动判谎）

### 拿 real banner 的正确姿势
不能只看 CONNECT 状态码。拿到响应后**必须校验归属**：
- 响应里的 `REMOTE_ADDR` / `SERVER_ADDR` 若等于**代理自己的 IP** → 假响应
- 对比多个不同代理拿到的响应是否**互相矛盾**
- 实在拿不准就用**本地直连 + tcping** 做基准

## 端口状态三分类（别把 filtered 当 closed）
| nmap 状态 | 含义 | 判读 |
|---|---|---|
| `open` | 有服务监听 | 目标端口开 |
| `closed` | 回了 **RST** | **主机活着**，但该端口无监听 |
| `filtered` | **无任何响应** | 包被防火墙/安全组静默 DROP |

**关键推论**：云上（AWS/阿里等默认 DENY）对比同主机多个端口能读出安全组画像 ——
`closed` 说明安全组**放行**了（包到了主机，只是没人听）；
`filtered` 说明安全组**没放行**或规则限定了源 IP 白名单。
所以「某端口 filtered」往往是「没有对应 allow 规则」，而**不是**「服务挂了」。

**tcping 基准命令**（比 nmap 直观，能区分超时 vs 秒拒）：
```bash
nping --tcp -p 8853 -c 4 --delay 500ms <IP>       # 发4收0=被DROP；收到RST=closed
nmap -sS -Pn -p 8853,80 --reason -T4 <IP>          # --reason 打 no-response/reset
```
> `ping` 在本机被一个坏的 Python wrapper 覆盖了（报 `inet_aton` 错），
> 用 `nping` 或原始 socket。**注意原始 socket 抓 ICMP 会收到无关杂包**，
> 必须校验回包源 IP 是否等于目标，否则又是假阳性。

## 排障
- `redis-cli zcard use_proxy` 报 WRONGTYPE → 键是 hash，用 `hlen`
- **某源抓不到先分类再动手**：①URL 404 → 用 GitHub contents API 列真实文件名（文件名常与直觉不同）②HTTP 521 → CF 源站挂，换入口无用，直接弃 ③返回 200 但只几十字节 → 打开看是不是「仓库搬家」提示 ④301 跳转 → 跟 `curl -sL -w '%{url_effective}'` 看新域名，通常 API 已废弃
- 某源抓不到 → curl 手动测源站；openproxy.space/proxylist.me 全站 521（Cloudflare 拦源站，放弃）；hidemy.name 返回 Cloudflare 假 IP（172.67.x/141.193.x，验证必失败）
- 免费代理质量：验证通过后几分钟就失效，池里 50% 左右实际可用，是固有特性，靠 proxyServer 重试 + 使用方工具重试兜底
