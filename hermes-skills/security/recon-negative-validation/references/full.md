# recon-negative-validation — 全文续篇

> 主卡保留前 1 节；本文件从第 2 节起。原文件：`/root/.hermes/skills/security/recon-negative-validation/SKILL.md`

## 1. 三类假阴性源（全部实测）

### A. 探针本身死了（出口 IP 被 WAF 封）

跳板在扫描过程中被目标 WAF 纳入黑名单 → **所有请求返回 `000`（连接失败）**。
而典型探测脚本的过滤器长这样：

```bash
if [ "$size" != "$BASELINE" ] && [ "$code" != "000" ]; then echo "HIT ..."; fi
```

`000` 被当成「无响应」静默丢弃 → **整批 1748 个路由被吐成「总计 0」**。
真相是「探针全死」，不是「目标全无」。

> 识别法：换一个出口（Tor / 另一台跳板）重跑同一批请求，立刻出结果。

### B. 枚举形式本身写错

某 PHP 应用路由**区分大小写**且只认全小写（`/?模块-控制器-操作`）：

| 请求 | 结果 |
|---|---|
| `?admin-repass-repass` | **200 + JSON（正常工作）** |
| `?Admin-Repass-Repass` | 自定义错误页（1640） |

用驼峰形式枚举 → 全部 1640 → 长度≠非命中基线 → 被当噪声过滤 → 输出「0 命中」。

同类坑：路径分隔符（`?a-b` vs `/a/b`）、入口前缀、尾斜杠、`.php` 后缀、URL 编码形式。

### C. 错误页基线混入过滤器

批量请求返回**同一个异常长度**时，你分不清那是「错误页」还是「命中」。
必须在跑之前先拿一个**保证不存在**的路径测定基线，再叠加一个**保证存在**的路径测健康度。

### C2. 兑底页 / SPA catch-all 把「全部命中」伪装成发现（Next.js / Vite / SPA / 静态 nginx try_files 必看）

`historyApiFallback`（Vite/React/Vue）、Next.js App Router catch-all、以及 **nginx `try_files $uri /index.html`** 的纯静态落地页，**对任意未知路径回 `200` + 首页/外壳 HTML**。
于是最常用的过滤器「非 404 = 命中」会**把整张敏感文件表全判成命中**：

```
/.env         -> 200   (实为首页 HTML)
/.git/config  -> 200   (实为首页 HTML)
/.gitignore   -> 200   (实为首页 HTML)
/package.json -> 200   (实为首页 HTML)
/backup.sql   -> 200   (实为首页 HTML)
```

实测（akunosai，Next 16 App Router）：**46 条敏感路径全部 200、体量几乎一致**，
其中只有 `robots.txt`、`sitemap.xml` 是真文件。不验内容就写「配置泄露」是最容易出丑的假阳性。

同形态（tgetitx.com 静态能量租赁壳，nginx try_files）：任意 path 200 同 index；**真文件仅** `/robots.txt` `/sitemap.xml`；logo/og 引用 404。
**额外动作**：空壳域名别死磕 —— 读证书 SAN + 无 SNI 默认 CN，同 IP 兄弟 vhost 才是主战场（见 `multi-app-farm-pentest` §0.25）。

**判据（做一条就够）**：

1. **Content-Type**：catch-all 回 `text/html`；真 `.env`/`.json`/`.sql` 回 `text/plain`/`application/json`/`application/octet-stream`。
2. **body md5 对照**：取根路径 + ≥2 个「保证不存在」的随机路径，**md5 相同 = catch-all**；真文件 md5 必然不同。
3. **魔法字节**：真配置文件开头是 `#`/`{`/`--`/`SQLite format 3`，catch-all 开头是 `<!DOCTYPE html>`。

**更要紧的推论**：这类站上 **HTTP 状态码对「路径存在性」零信息量** —— 别再拿 200/404 当 oracle。
改读**框架自己的 JSON 错误体**（如 `{"message":"Not Found","statusCode":404}` + `Content-Type: application/json`）
或响应头差异，才能区分「真路由」与「外壳兑底」。
（同族的 WS 面：未知路径同样回 200/307，**只有 `101 Switching Protocols` 才是真 WebSocket 端点**。）

### D. 探针自己的 HTTP 客户端配置写错（实测，最阴）

Python `requests` 版批量扫描器里，**代理参数写错会让每个请求都在客户端抛异常**，
调用处的 `except: pass` 把它吞掉 → 函数返回 `None` → 判定分支跳过 → 输出「0 hits」。

```python
# 致命笔误：'none' 是字符串，不是 None
requests.get(url, verify=False, proxies={'http': None, 'https': 'none'})
# 作业机默认走 Tor 时（env 里有 ALL_PROXY/HTTPS_PROXY=socks5h://127.0.0.1:9050），
# 不显式断开代理还会把整批请求导向已死/被封的出口
```

**两个必做**：

1. `proxies={'http': None, 'https': None}` **且** `session.trust_env = False`（Python）/
   `unset http_proxy https_proxy ALL_PROXY all_proxy` + `--noproxy '*'`（shell）。
2. **在同一个函数体内**先打一条已知 200 的路径并断言：

```python
KNOWN = "/healthz"            # 已确认 200 的路径
code, _, _, _ = G(KNOWN)
assert code == 200, f"探针自检失败({code}) — 本批结果作废，不许当 0 命中"
```

> **壳层 curl 自检保护不了 Python 脚本。** 自检必须走**与批量请求完全相同的那条代码路径**
> （同 session、同 proxy 参数、同一 `except` 语义），否则等于没测。
> 识别信号：**「我明明知道 `/login` 会 200，结果报 0 命中」** —— 这个自相矛盾就是笔误的暴露点，
> 别放过它、更别把它解释成「目标加固了」。

### E. 字典维度缺失（条数够 ≠ 维度够）

目录/资源爆破跑出「0 命中」，常常不是因为目标没文件，而是**字典根本没覆盖那一维**。

实测：某自研 FastAPI 应用用 7552 条字典扫完，全 404，看上去「webroot 很干净」。
事后补测 **`/static/<名>.js|.css|.map|.json`**，立刻挖出 `collection.js`、`reports.js`
——两个前端脚本直接给出核销流程字段（`payload_hash` / `source_hash` / `verified` /
`receipt_id`）与内部接口**入参名**（`start` / `end`），是高价值情报。

**字典要按维度自查，不是按条数自查。** 最少四维：

| 维度 | 覆盖 |
|---|---|
| 扩展名 | `.js .css .map .json .txt .bak .old .save .zip .sql .db .sqlite .env .yml .ini .conf .log .swp` |
| 目录 | `/static/ /assets/ /js/ /css/ /img/ /images/ /dist/ /vendor/ /media/ /uploads/` |
| 派生名 | **用已泄露的路由/spec 反推文件名**（路由 `/merchant-settings` → 试 `merchant-settings.js`），命中率比通用字典高一个量级 |
| 大小写/前缀 | `/admin.js` vs `/static/admin.js`；`/login` vs `/index.php/login` |
| **框架特有维** | FastAdmin/ThinkPHP：`/addons/<plugin>/<ctrl>/<action>`（插件前台路由，**不受 admin 模块 `deny_module_list` 影响**，值得单独刷插件名——返回体含 `当前插件暂无前台页面` 就是插件存在）；`/index/ajax/<action>`；入口脚本名变体。**通用字典永远不会包含这一维。** |
| **嵌套资源维** | 父子嵌套路径（如 `/api/v1/user/userInfo/register/`，子动作挂在父资源下）——通用词表必不含；**回前端 bundle 挖完整路径**，别只扫一级目录 |
| **注释/遗留路径** | **必须读前端 JS 与页面注释**：代码注释常留着改造前的旧接口。实测从一个 `// 接口URL: /index/shequ/sou_list.html?ac=save` 注释里挖出全库字典都没有的 action 名（而 `shequ` 控制器已改名）。这类名字只能从业务 JS 里读出来，扫不出来。 |

> 另：**应用层控制器的 `文件:行号` 可以用「数组参数」换出来**——向公开端点发 `?param[]=x`，
> 框架抛 `variable type error：array`，调试页会打印**应用侧调用点**（`application/index/controller/<Ctrl>.php line N`）与整套 env/常量。
> 一次小范围参数名枚举就能拿到「哪个参数由哪个文件处理」，比盲扫省事。

> 同理：**前端脚本是「无凭据可用情报」的最后一块**。拿到 `.js` 要 grep 三样：
> `fetch(`/URL 字面量 → 内部接口与入参名；`name="..."` → 表单字段；`data-*` → 服务端渲染的开关。

### F. 响应体「长度」当 oracle 时被 UA 污染（nginx `msie_padding`，实测）

**同一条 URL、同一个页面，只因为换了 UA，长度就从 146 变成 548。**

nginx 在 UA 像 MSIE/Chrome 时会给错误页追加 6 行
`<!-- a padding to disable MSIE and Chrome friendly error page -->`（每行 ≈67B ⇒ 共 ≈402B）。
于是**同一个 nginx 404**：

| 客户端 UA | 同一 404 页的长度 |
|---|---|
| `curl/8.5.0` | **146** |
| 浏览器 UA（`Mozilla/... Chrome/...`） | **548**（146 + 402） |

**为什么危险**：本会话前半段用壳层 `curl`（146B）测了一轮，中途换成 Python `requests` + Chrome UA，
同一个 404 长到 548B —— 看上去像「响应变了 / 这次请求进到框架了」，
于是围着这个纯假信号绕了近半小时（还差点把结论写成「nginx 关键词拦截」）。

**纪律**：
- **一整批探测固定一个 UA**，别混用壳层 `curl` 与 Python `requests`（后者常带浏览器 UA）。
- 判定**永远不要只看长度**：同记 `status + Location + Content-Type + 一个「保证不存在」的对照路径`。
- 同一台机上看到 **~146 与 ~548 成对出现**，先怀疑 padding，不要怀疑目标改了行为。
- 想读框架真实错误页时**主动触发 500**（框架 500 通常原样返回），别指望从被换页的 404 里挖信息。

### G. 协议层「沉默」= 探针少了触发帧（握手成功之后才发生的假阴性，2026-10-02 连踩两次）

前面 A–F 都是「探针没到达」；这一类相反：**探针到达了、握手成功了，但没走完协议**。

实测（akunosai，`wss://host/api/user?userId=<uuid>`）：

| 探针行为 | 读回 | 我的错误解读 |
|---|---|---|
| 握手 `101` 后**只被动静听** 8s | **0 字节**（两次都是） | 「这个 UUID 没有通知」 |
| 握手 `101` 后补发一帧 `{"type":"SUBSCRIBE","payload":{"type":"auth"}}` | **57 KB / 88 条** | —— |

**同一个 UUID、同一条连接，唯一差别是发没发那一帧。** 服务端是「先收订阅帧才推全量」，
只做被动接收就会把「88 条真实数据」稳定地读成「空流」。

**纪律：非 HTTP 协议上的「没数据」必须先把该协议的协商帧发完，才能计作阴性。**

- WebSocket：先被动 10s，**再补一帧订阅**，两次都空才算空；`0x9` PING 要回 `0xA`。
- 同族协议同理（每个都是「不发帧就没后续」，且**不发帧时不报错**，静默得像空数据集）：
  socket.io/EIO4 要发 `40`（命名空间连接）+ `42["ev",payload]`；STOMP 要发 `CONNECT`；
  MQTT 要 `CONNECT`+`SUBSCRIBE`；gRPC streaming 要先把请求流打开。
- 判定信号：**握手成功但读回恒定为 0 字节** —— 这是「协议没走完」的指纹，不是「空集合」的指纹。
  「空集合」通常仍会回一个**结构完整的空壳**（`{"payload":[]}`），而不是什么都不回。

> ⚠️ **注意它与「我没事，是目标没数据」的区别，两栏写：**
> 「通道接受了任意身份」（如拿他人 UUID 也回 `101`）= 鉴权缺陷，实锤；
> 「读到了他人的数据」= 必须有**一个有数据的对照臂**。本次拿流里捡到的三个他人 UUID 去订阅，
> 全部回 `101` + 0 条（大概率本身无未读，**不是被拒**）—— 这种 0 只能写「无法确认他人是否为空」，
> **不能**写成「已读取这三人数据」。

### H. 一次性凭证被复用 / 必填字段先于校验（2026-10-02 同案第二轮）

前七类都是「探针没到达」或「没走完协议」；这一类是**探针自己把整批测试搞脏了**：

**(1) 一次性 challenge 不能复用。** PoW / nonce / OTP 类凭证**一个只能用于一次请求**。批量测试里复用同一个 solution：

- 第 1 条正常，**第 2..N 条全部回 `400 Challenge expired or invalid`**
- 极容易被误读成「目标拒绝这些字段/载荷」——实际是**探针只对第一条有效**

实测：一次批量赋值（mass assignment）注册测试 8 条里 7 条如此，若不复测就会写成「目标拒了 roleId/kycLevel」。
**纪律：每个 attempt 重新 `GET` challenge 并重解**；看到「第 1 条成、后面全败」先怀疑凭证复用。

**(2) 必填字段的 400 先于真判决发出。** 端点常先做请求体形状校验，再做 token/签名校验：

```
POST /api/auth/verify/reset {"token": <伪造>}                     → 400 "New Password is required."   ← 掩盖
POST /api/auth/verify/reset {"token": <伪造>,"newPassword":"…"}   → 401 "Invalid token"                ← 真判决
```

**同一个 400 对真 token 和假 token 长得一模一样** ⇒ 少字段时**任何**伪造结果都一个样，
批量伪造测试会被整批读反（本次把「签名真在校验」误读成「校验通过、只少个字段」）。
**先凑齐必填字段再发**（字段表用「验证器 schema 泄露」那套：从空 body `{}` 逐轮补齐）。

**判据（一句话）**：错误文案里出现 `is required` / `must be` / `expired or invalid` 这类**形状/时效**词时，
**先把输入补齐再解读**；只有 `invalid` / `unauthorized` / `forbidden` 才是对**凭据本身**的判决。

### I. 「空响应 / len=0」≠ 不存在（WAF 静默断连 & 出口抖动，2026-10-04 实测）

宝塔类 WAF 对**高危特征**会用两种截然不同的方式回应，其中一种**完全不可见**：

| 探针行为 | 读回 | 极易得出的错误解读 |
|---|---|---|
| 发 `?s=/index/\think\app/invokefunction` | **空响应 / len=0** | 「TP5 RCE 被补丁堵死了」 |
| 发 `?s=/index/\think\Request/input&filter[]=…` | 1002B `网站防火墙` 页 | （同一 WAF 的另一种表达） |
| 发已知良性路径 `/index/info.html` 走**同通道** | 200 + JSON | —— |

**同一个 WAF 有两种响应粒度**：

- **回 1002B「网站防火墙」页** → 拦截**可见**
- **直接断连（空 body / `curl` 那一路连 `-o` 文件都不生成 / 报 `000`）** → 拦截**不可见**，
  长得和「路由不存在」「超时」「出口被封」**一模一样**

⇒ **判据：任何「空响应 / `000`」的批次，必须在同一通道、同一客户端、同一参数下先打一条已知 200 的对照。**

```
对照也空        → 通道坏了（出口被封 / WAF 全封）→ 整批作废，换通道重跑
对照 200 而目标空 → 才可能是 WAF 静默断连 → 仍**不等于「路由不存在」**，
                   只等于「这个载荷被静默丢弃」→ 报告要按「未确认」写，不按「不存在」写
```

**两个最会骗你的通道：**

- **Tor / 慢代理抖动**：同一 URL 连发 6 次可能 5 次 `000`。本次因此**两次**把「没试成」当成「试过且无效」
  （一次是 TP5 RCE「被补丁堵死」，一次是上传路径命名假设「不成立」——后者其实是算错了 md5 字符串，与通道无关，但同样被空响应掩盖）。
- **域名通道被墙、源站 IP 通道仍通**：WAF/nginx 规则常按 vhost 下，换通道结果不同（见 §I2）。

**纪律：结论必须写成「在 X 通道、有对照、N 次里 M 次成功」。** 不许把「没试成」写成「该漏洞不存在」。

### I2. `--resolve` 在 `--socks5-hostname` 下是无效的（实测）

想「绕过域名层 WAF、直连源站 IP」时很容易这样写：

```bash
curl -sk --socks5-hostname 127.0.0.1:9050 --resolve fengcin.com:443:217.194.134.12 \
     https://fengcin.com/index/info.html          # ← 无效！仍然走域名（含 WAF）
```

**原因**：`--socks5-hostname`（= `socks5h`）把**主机名交给代理远端解析**，`--resolve` 的本地 DNS 覆盖被忽略。

**正确写法：URL 直接用裸 IP，域名走 `Host:` 头**

```bash
curl -sk --socks5-hostname 127.0.0.1:9050 -H 'Host: fengcin.com' \
     https://217.194.134.12/index/info.html
```

注意 **TLS SNI 会是 IP**，nginx 可能落到 default vhost —— 所以**必须带 `Host:` 头**，
且**先打一条已知 200 的对照**确认这个 vhost 真能路由到目标应用（拿到 JSON 而不是默认页）。

实测：域名通道被 WAF 封死（连发全 `000`）时，这条 **IP+Host 通道仍稳定 200**，是继续作业的关键。

---

### J. 慢站三态模型 & 「恒定墙钟超时」分类法（2026-10 实测）

**三态：nginx 静态层 / PHP 应用层 / DB 层会独立坏。** 探针要按层摆「层专用已知阳性」：

| 层 | 层内已知阳性 | 判读 |
|---|---|---|
| nginx 静态 | `/favicon.ico`、`/style.css` | ms 级 200 = 静态层活 |
| PHP 应用 | 已确认的应用端点（如 `/uploads/<存在的名>`） | 200/302 = PHP 层活；`000` = PHP 层死或间歇 |
| DB | 一处必读库的页面 | 200 / 「数据库错误」页 = DB 层飘 |

**实测**：`favicon` 恒 200（nginx 直出）、`/uploads/*` 间歇 302（PHP）、其余路径 404 且延迟 6–12s
（毫秒级 404 = nginx 直出；多秒级 404 提示过了应用层——只作分层信号，别单独当证据）。
⇒ **只许写「PHP 层间歇可用」，不许写「站点死了」**——静态层明明活着，「半死站」是三态读数。

**恒定墙钟超时 = 超时边界，不是「链被拒」。** 端点在**任意载荷**下都于同一墙钟（实测 ~100–110s）
被掐成 `502 Bad Gateway` ⇒ 那是 nginx `fastcgi_read_timeout` / PHP-FPM `request_terminate_timeout`
边界。**先跑对照齐射定因**：

1. 同端点 **不带载荷**（裸字段）
2. **换方法**（GET/POST 互换）
3. **换端点**（姊妹路由 / 同类端点）
4. **换出口 IP**（第二台跳板）

四项都在**同一墙钟**死掉 ⇒ **环境阻塞**（与 payload 可能无关）；只写「环境阻塞（附对照）」——
**「环境阻塞」≠「洞不存在」**，是两个结论，报告不许混写。反之只有带载荷才崩 = 载荷真触发，值得追。

**跨出口 A/B 分类法（分清「限速」还是「环境」）**：同站、同探针组，从两个出口各跑一遍：

| 观察 | 判定 |
|---|---|
| 通用请求速度差异大（27s vs 5s）**但端点级失败签名一致** | 出口只影响「快慢」；一致失败 = **目标环境缺陷** |
| 速度差异大**且**端点结果不同（A 通 B 不通） | 出口级问题（封 IP / WAF 分级）→ 换出口重跑 |

**实证**：本机首页 27.5s、h107 4.8s → 先疑「IP 被限速」；但两侧 REST 端点同为 502@~104s →
终判「服务器环境级缺陷」。**单臂永远得不出这结论，两臂都要跑。**

**间歇窗口姿势**：PHP 层间歇可达（窗口时长实测几十秒）时，**把守望器部署在跳板上**
（循环探测真 PHP 端点；窗口一开立即抢抓全套资产落盘），不要用自己的会话轮次轮询。
模板：`pentest-execution` → `scripts/jumpbox_window_watcher.sh`（HTTP 层抢抓）；纯 TCP 端口态感知 → `scripts/port_state_sentinel.sh`。

### K. 端口传感的假阳性：「TCP 通」≠ 服务可用（2026-10 实测）

（A–J 防的是**假阴性**；这一类相反——传感侧的**假阳性**。）

- 边缘 tarpit / 防 DDoS 清洗下：**SYN 偶尔完成、应用层数据全丢** → socket 探测报 open，HTTP 永无响应；据此自动开火 = 反复撞墙（实测重链被误触发多轮，白跑还可能引起目标注意）。
- 实测（dev58）：探测器把「TCP 通」当复活信号；同一目标从跳板看 TCP 可连、HTTP 从所有 vantage 静默——是边缘假象，不是服务窗口。

**纪律**：

1. 「端口开」要两级证据：TCP 通过 → **必须补 HTTP GET，任意状态码返回才算真活**（超时=假活）。
2. `connect_ex` 返回码**不许合并**：`0`=通；`111`=RST 秒拒=**真没监听**（等窗口）；超时/其他=drop（多为被封，换出口）。「全 RST」与「全超时」是**两种结论、两种行动**。
3. 传感器与动作出口分离：跳板低频 TCP 状态感知（`pentest-execution` → `scripts/port_state_sentinel.sh`），HTTP 动作走代理出口。
4. 报告按两层写：`TCP: open / HTTP: timeout`——不许折成一格「可达/不可达」。

### K2. 「200 + 完整正文」也可能是缓存复读旧窗口（2026-10 实测）

公共代理/relay 常内建 HTTP 缓存。目标**早先真开过窗**（哪怕现在已经关死），代理会持续回放
当时的 200 + 完整真页面——正文校验照样通过（它真是那个页面），但**那是缓存快照，不是活窗**：

| 响应信号 | 含义 |
|---|---|
| `X-Cache: HIT`（或 `CF-Cache-Status: HIT`） | 命中缓存，未回源 |
| `Date` 冻结在过去某时刻（如当前 13:26 而 `Date=12:18:42`） | 快照时刻 = 上一轮真窗口 |
| `Age: 0` + 旧 `Date`、`ETag` 恒定 | 缓存器把旧响应当新回放 |
| URL 追加 **cache-buster**（`?_<rand>`）后回 0/超时 | **回源路径已死 → 原 200 纯属缓存** |

**纪律**：对每个「热命中」跟发一条 `path?_<rand>`——buster 也 200 才算真活；
buster 死而原路径 200 = 缓存复读，**只记日志，不开火、不庆祝、不算战果**。

> 实测代价：捕手把三只 relay 的缓存回放报成「HOT 窗口」，storm 资产实为旧快照；`?_` 复验后全部 0 字节。
> **命中后的第一个动作是 cache-buster，不是欢呼。**

---

### L. 「满屏 401」掩护真 404：判定必须带票重刷（2026-10 Django DRF 集群实测）

有些后端把**全局鉴权中间件**挂在 `/api/*` 最前：**未匹配到任何路由的请求也被中间件兜住，统一回 401**（如 `{"code":401,"message":"请先登录"}`）。

| 探针行为 | 读回 | 错误解读 |
|---|---|---|
| 无票 fuzz `/api/*` 词表 | **满屏 401** | 「发现一批需登录端点」（可能全是假的） |
| 带真票重刷**同一词表** | 未知路径露**真 404**（`Cannot GET /x`）；有响应的才真是端点 | —— |

**纪律**：先注册/登录拿一张真票 → 带 `Authorization` 头重刷同一词表；**「无票 401」不作存在性证据**。

两条推论：

- 「未知路径也回 401」= 全局鉴权中间件指纹（不是路径存在）；
- 反向版本同样要防：**无票 401 / 带票 404-200** 说明 401 只是中间件礼貌，不是逐路由鉴权。

**顺手：鉴权方案指纹**——发 `Bearer junk` / `Token junk` / `JWT junk` 比对错误文案：`Given token not valid for any token type`（或中文「此令牌对任何类型的令牌无效」）= simplejwt（Django REST）→ Bearer 方案。

**同案另一坑（嵌套资源路径）**：`/api/v1/user/register/` 404，真注册口在 `/api/v1/user/userInfo/register/`（子动作挂父资源下）——通用词表必不含，回前端 bundle 挖**完整**路径；挖到即实测闭环（注册造号→拿票→用票解锁鉴权面）。

---

### M. 间歇门多路线判读：反代 502 = 「路线已确认」，不是「打不开」（2026-10 dev58 实测）

后端端口时通时阻（防火墙间歇 / 后端随用随起）时，别死盯目标端口。同机其它**常开** nginx 端口常配了前缀反代（`/admin-api` `/app-api` → 目标后端），同一探针（真登录 POST）打三条路线：

| 探针返回 | 判读 |
|---|---|
| 目标端口 TCP `111`(RST) | 此刻没监听 → 挂伏击等窗（§K） |
| 目标端口超时/drop | 多为被封 → 换出口复测 |
| 兄弟端口 `POST <prefix>/...` → **502** | **反代存在、上游没起** → 路线已确认，上游一起来即直插（金矿） |
| 兄弟端口同路径 → **405/404** | 该端口无反代或不同配置 → 换端口找 |
| 兄弟端口同路径 → **200/JSON/401** | 后端已起 → 借这条反代干活，**不需要目标端口对公网开放** |
| 直连 `000` vs 反代 `502` | 分开记：502 = nginx 活着且配了转发；000 = 不通 |

**纪律**：① 探针用真请求（登录 POST），TCP 传感不单独下结论（§K）；② 三路线（直连/反代/代理池）并行巡检 + 命中冷却；③ 伏击脚本**每轮重读**代理池；④ 多租户后端命中先确认「一个后端服务多商城」（前端 bundle `base_url` grep 是判据）。完整伏击模式与实测细节：`multi-app-farm-pentest` → `references/flappy-door-capture-dev58.md`。

**反模式**：把 502 当「打不开」收手 —— 它是「等上游」；把某次 timeout 写成「端口死了」—— 间歇门只能判「此刻关」。

**二级判活（2026-10 二轮实测，修假警报）：** 判「后端已起」不能只认「非 502」——**504 / 超时 / HTML 错误页都会冒充活**。严格判活 = `status==200` **且** body 以 `{` 开头（JSON API 的实际响应）；504 与空体一律记「未起」，跟一条 cache-buster（§K2）同批校验。

**窗口 = 负载调度（同族多机通用结论）：** 间歇门的开/关与运维在岗负载联动（实测：运维在岗 load 29 时全关、全天仅数次分钟级窗口），**不是固定时窗**，按作息推测会白等。策略：① 25s 循环捕获器（跳板部署，别用会话轮询）；② 连上第一优先**固化授权材料**（新私钥写 `authorized_keys`、抄 shadow/history），之后每个窗口都能复用；③ 窗口内自动化跑「拖库 + 预打 tar + 富版取证包」，别手工抢。完整二轮战果（一窗自动拖 6 库）见 `multi-app-farm-pentest` → `references/flappy-door-capture-dev58.md`。

---

## 2. 纪律：每批枚举都塞「已知阳性自检」

```bash
B="https://target"
KNOWN_GOOD="/login"        # 你已确认存在的路径/端点
BASELINE=$(curl -s -o /dev/null -w '%{size_download}' "$B/$(date +%s)-definitely-not-real")

selfcheck() {              # return 0 = 探针健康
  local r=$(curl -sk --max-time 10 --noproxy '*' -o /dev/null -w '%{http_code}' "$B$KNOWN_GOOD")
  [ "$r" = "000" ] && { echo "!! 探针已死(出口被封?) — 本批结果作废"; return 1; }
  echo "自检: $r"; return 0
}

selfcheck || exit 1        # 开头跑一次，之后每 100 个请求重跑
```

**并且别把 `000` 静默丢掉，要计数并超阈值中止：**

```bash
DEAD=0
probe() {
  local code=$(curl -sk --max-time 12 --noproxy '*' -o /tmp/r -w '%{http_code}' "$B$1")
  [ "$code" = "000" ] && DEAD=$((DEAD+1))
}
# 批末
[ "$DEAD" -gt 20 ] && { echo "探针批量死亡($DEAD) — 结果作废，换出口重跑"; exit 1; }
```

### 判读规则（三条，缺一不可）

| 现象 | 正确解读 | 错误解读 |
|---|---|---|
| 大量 `000` 且自检也 `000` | **探针/出口废了** → 结果作废，换出口重跑 | 「目标没有这些路由」 |
| 批量返回同一异常长度 | 那是**错误页/兑底页基线** → 先记基线再过滤 | 「命中了一大片」 |
| 枚举结果与**源码路由表**不一致 | 优先怀疑**枚举形式** | 「部署版魔改了」 |
| **已知存在的路径也报 0 命中** | 探针**代码**写错（异常被 `except` 吞 → 全返回 `None`） | 「目标加固了」 |
| **批量凭据测试「命中」一大片（几十/几百条）** | **假阳性**：判定把 `302 → /login` 记成了成功 | 「一把命中了几百个账号」 |
| **灌 `Host: <目标域名>` 后 grep 目标域名「命中」** | **假阳性：Host 反射** —— ZBlog/CMS 的 `canonical`/导航链接、**catch-all 框架应用（`<meta name="app-url">` / `file-base-url` / 绝对资源 URL / `302 Location` 全部按请求 Host 生成）**、小 CDN 的「域名未绑定」页会把请求的 Host（连同你自己的出口 IP）回显到正文。判据只能是 **md5 对照**：同 IP 再灌一个**随机不存在**的域名，**md5 相同 = 默认站/无关**，不同才是真 vhost；几字节长度差是噪声。**反射页越长越像证据，越要先跑对照**——实测 `app-url` 跟着 `tlgramhq.com`/`www.baidu.com`/随机域一变一份 md5，差点被当成「应用配置写死了目标域名」写进报告 | 「找到了绑定了目标的机器」 |
| **同一路径两次请求长度不同（如 146 → 548）** | **误判源**：UA 不同触发 nginx `msie_padding` → 固定 UA 重测 | 「目标行为变了 / 这次请求进了框架」 |
| **框架自己的 404 正文看不到（被换成一页通用 nginx 页）** | 前置 nginx 的 `error_page`/`fastcgi_intercept_errors` 在替换框架 404 | 「nginx/WAF 把这条路由拦了」 |
| **整张敏感文件表全部 200（含 `/.env`、`/backup.sql`）** | **兑底 / SPA catch-all**：比 `Content-Type` + body md5，全同类 = 假命中 | 「发现一批配置泄露」 |
| **未知路径回 200/307 被当成「端点存在」** | SPA 外壳 / Next catch-all；WS 端点**只认 `101`** | 「隐藏接口已定位」 |
| **协议握手成功（101/200）但读回 0 字节** | 探针**没走完协议**：缺订阅/CONNECT 帧，服务端静默不推 | 「该用户无数据 / 通道是空的」 |
| **批量测试第 1 条 OK、第 2..N 条全回 `expired / invalid`** | 探针**复用了一次性 challenge**（PoW/nonce/OTP）—— 每条都要重新取 | 「目标开始拒绝这批载荷了」 |
| **伪造/爆破测试全回 `X is required` 这类缺字段文案** | 形状校验先于凭据校验 → 先补必填字段，才能看到真判决 | 「凭据校验通过了，只差个字段」 |
| **编码绕过路径规则后回 200（而非 403）** | 可能只到达了 **SPA/Next 外壳**而非后端：比 `content-type` 与正文首字符（`{`/`[` = API；`<!DOCTYPE` = 外壳） | 「鉴权规则已被绕过」 |
| **高危载荷回空响应/`000`，而同批良性请求能 200** | **WAF 静默断连**（宝塔类不返回错误页）；只等于「载荷被丢弃」，**不等于路由不存在**（§I） | 「这洞不存在 / 已被补丁堵死」 |
| **同一 URL 连发多次，时而 200 时而 `000`** | 出口/代理抖动（Tor 常见）；结论要按「M 次成功」记，不许按单次空响应下断言 | 「目标不稳定 / 偶发拦截」 |
| **代理回 200+完整真页面，但 `X-Cache: HIT` / `Date` 停在过去** | **缓存复读旧窗口**（§K2）：补 `?_<rand>` buster 复验，buster 死 = 假活 | 「窗口开着，快抢抓！」 |
| **端点在任意载荷下都于同一墙钟（~100s）被掐成 502** | 超时边界（nginx `fastcgi_read_timeout` / PHP-FPM terminate）→ 跑对照齐射定因（§J） | 「链被拒 / 不可利用」 |
| **无票 fuzz 满屏 401「请先登录」** | 全局鉴权中间件兜住未匹配请求；**401 不是存在性证据**——带真票重刷，真 404 才作数（§L） | 「发现一批需登录端点」 |
| **根路径/任意路径回产品默认 404/错误页** | 先当**产品指纹**读：frp（fatedier）默认页 `<title>Not Found</title>` → 查 7000 bind / 7500 dashboard；同族产品各有默认错误页，拿到指纹按该产品默认端口/面板续查 | 「默认站点，没货 / 无路可走」 |

---

## 3. ground truth 优先：能拿源码就拿

**最高性价比的验证：把源码/官方仓库的注册表当 ground truth 对一遍。**

本会话对某 Laravel 应用用 2500 词字典 fuzz `/index.php/<word>`，只得到 6 个路由。
**这 6 个与官方源码 `routes/*.php` 完全一致** —— 所以「无隐藏路由、部署版未魔改」这个结论才立得住。
反过来说：**没有 ground truth 的「0 命中」不算结论**，它只是「我的字典没命中」。

拿到源码后的标准动作（每条都很快）：

1. 读 `routes/`（或框架等价物）列出全部注册路由 + 中间件
2. 看 `composer.lock` / `package.json` 定**精确版本**
3. 用版本去比对该库**部署日期之后**的安全修复提交（`git log --since=<资源戳日期>`）—— 有修复就有 N-day，没修复就别编

---

## 4. 顺带：路径签名拦截下的路由存在性 oracle

CDN/WAF 按「**方法 + 路径**」签名拦截时，有个几乎免费的判定：

| 你发的方法 | 返回 | 含义 |
|---|---|---|
| 错误方法（如 GET） | **405 + `Allow: POST`** | 路由**存在**，该组合被放行 |
| 正确方法（如 POST） | **404** | **WAF 拦的就是这个组合** → 路由存在但被挡 |

「**错误方法给 405、正确方法给 404**」= 一次拿到「存在」+「被拦」两个结论。
（同时也能区分「路由真不存在」：两者都是 404，且响应体是框架默认 404 页。）

### 绕过：加应用入口脚本前缀（实测穿透 Cloudflare）

```bash
# 全被拦
POST /api/v1/tokens        -> 404
GET  /login                -> 404
# 加入口前缀 -> 直达框架
POST /index.php/api/v1/tokens -> 401 {"message":"Unauthenticated."}
GET  /index.php/login         -> 500（框架内异常，已越过 WAF）
POST /index.php/login         -> 422（到达密码校验）
GET  /index.php/api/v1/strategies -> 200 未授权
```

**原理**：nginx 把 `/index.php/<rest>` 的 `<rest>` 作为 `PATH_INFO` 交给 PHP-FPM。
WAF 的「方法+路径」签名匹配的是 `/api/v1/tokens`，匹配不到 `/index.php/api/v1/tokens`。

**适用**：单入口脚本 + 前端伪静态的框架（Laravel / ThinkPHP / CodeIgniter）。
入口脚本名从指纹取，可能被改名。

次级尝试：大小写变体、URL 编码（`%6E`）、路径双写、换出口 IP。

---

## 5. 节流（throttle）key 判定与出口轮换

准备做定向凭据测试前，先把节流 key 弄清楚：

| 观察 | 推论 |
|---|---|
| 同邮箱连试 → 出现「次数过多」 | key 含**邮箱** |
| 换 IP 后立刻恢复 | key 含 **IP**（或仅 IP） |
| 换 IP 后仍限速 | key 不含 IP → 别白折腾出口 |

**能读源码就直接读**（如 Laravel `LoginRequest::throttleKey()`）：

```php
return strtolower($this->input('email')) . '|' . $this->ip();   // 5 次 / (邮箱+IP)
```

**`$request->ip()` 伪造的边界**：

- `TrustProxies::$proxies = '*'` 时 `ip()` 取 `X-Forwarded-For` → 看起来可伪造
- **但 Cloudflare 会覆写 XFF** → 直连伪造**无效**（实测）
- **可行：Tor `SIGNAL NEWNYM` 轮换出口 IP**，每个出口拿满配额

```bash
printf 'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n' | nc 127.0.0.1 9051
curl --socks5-hostname 127.0.0.1:9050 ...
```

实测：16 次轮换、63 次尝试，零限速提示。

### 更快的替代：SOCKS 用户名隔离（不用控制端口、无 NEWNYM 冷却）

Tor 默认 `IsolateSOCKSAuth=1` ⇒ **每个不同的 SOCKS 用户名 = 独立 circuit = 独立出口 IP**：

```python
proxies = {'http':  'socks5h://<任意用户名>:x@127.0.0.1:9050',
           'https': 'socks5h://<任意用户名>:x@127.0.0.1:9050'}
```

- 换用户名即换 IP，**不用 `SIGNAL NEWNYM`**（不需要控制端口认证，也没有 10s 冷却）
- 同用户名复用同 circuit → 并发时**每个 worker 固定一个用户名**，否则互相踩同一条被封
- `socks5h` 的 `h` 必须带，否则 DNS 本机解析（泄露 + 常解析失败）

实测（`:8081`，6 次/窗）：单条 circuit 第 7 次即 429；按用户名隔离后**连续 12 次全过、零 429**。

> ⚠️ **绕过限流 ≠ 该开大字典。** 本节只回答“能不能继续试”。
> 实测对照：隔离出口下 5 个加固后台跑了 **12.7 万次，命中 0**；
> 同一时段 47 条短口令表跨实例横扫却新增 **5 套系统**。
> ⇒ 拿到稳定绕过时，**把它当成需要用户拍板的选项报上去**，并优先做短表横扫。

> ⚠️ **绕过节流 ≠ 就该无限爆破。** 用户环境里的硬约束是「弱口令测 10-20 个无果立即停」。
> 拿到稳定的节流绕过之后，**把它当成一个需要用户拍板的选项报告上去**，而不是自己开大字典。
> 本会话就停在这里并交给了用户。

---

## Response and Error-Page Discriminators

A final `200` is not evidence that the requested operation succeeded. Run the
first pass with redirects disabled and record the initial status and `Location`;
otherwise a protected `302 -> /login` becomes a misleading `200` login page.
For every candidate hit, compare final URL, content type, body length, and a
known-login negative control.

For scalar parameters on PHP/ThinkPHP endpoints, add one bounded type-shape
check: missing, empty, normal scalar, and array syntax (`field[]=x`). A
reproducible debug `500` can prove information disclosure when it exposes
internal paths, framework/version data, or configuration keys. It does not by
itself prove SQL injection or RCE. Preserve the raw response with restricted
permissions, redact secrets in reports, and rotate exposed credentials.

If a browser page presents a wallet payment or registration flow, inspect the
JavaScript transaction method and arguments read-only. Distinguish ERC-20
`approve`, `transfer`, and `transferFrom`; labels such as “authorize” are not
proof of the actual operation. Record destination and amount source, but never
sign or broadcast a transaction during reconnaissance. See
`references/response-and-payment-discriminators.md`.

## Pitfalls

1. **先证伪探针，再下结论。** 「0 命中」的第一假设是「我这边坏了」，不是「目标没有」。
2. **不许把 `000` 当空气**：它要么是 0 出站，要么是探针死了，两者都要求中止。
3. **“到达了”≠“命中了”。** 小写/编码能把请求送进应用层，但应用自己仍可能报错（如路由大小写不匹配）。
4. **大字典的「无命中」最不等于「不存在」**，只等于「这个字典没命中」。能拿源码路由表就拿。
5. **能读到源码就别猜版本**：看 `composer.lock` / lock 文件，不靠页面资源戳猜（资源戳只能给个粗下拉）。
6. **出口被目标封是常态**，扫描脚本默认要带出口切换能力，不要写死直连。
7. **探针自检必须与批量请求走同一条代码路径**（同 session / 同 proxy 参数 / 同异常语义）。壳层 curl 通了、Python 批量子请求全废，是最常见的自欺。
8. **代理配置是双刃**：作业机默认挂 Tor 时，忘记 `trust_env=False` / `--noproxy '*'` 会把整批流量导向慢出口甚至死出口——结果既慢又不准。
9. **「0 命中」要按字典维度自查，不只是条数**：少了扩展名维 / 目录维 / 派生名维，命中必然是 0。
   看到「webroot 干净」之前，先补扫 `/static/*.js|.css|.map` 并用已泄露路由反推文件名。
10. **长度 oracle 必须先固定 UA**：`curl/8.5.0` 看到 146B、Chrome UA 看到 548B 的**是同一个 404**（nginx `msie_padding`）。
    混用两种客户端会让「没变」的页面看起来「变了」，是本会话最贵的误判。
11. **被换页的 404 不许当「拦了」**：前置 nginx 把框架 404 替换成自己的默认页时，你看不到框架的 404 正文，
    也就**分不清「模块被拒」与「模块不存在」**。判据是**500 是否原样透出**：
    500 原样返回 ⇒ nginx 只换 404 ⇒ 那些 404 是框架自己产生的，不是 WAF 拦的。
    详见 `references/nginx-errorpage-masks-framework-404.md`。
12. **「全部 200」和「全部 404」一样值得怀疑**：SPA/Next catch-all 让敏感文件表整片回 200。
    先比 `Content-Type` 与 body md5，再往报告里写「泄露」。判据见 §C2。
13. **握手成功后的「0 字节」先当成「协议没走完」，不是「没有数据」（§G）**：
    WebSocket/socket.io/STOMP/MQTT 这类协议**不发协商帧就不推**，且不发帧时**不报错**，
    沉默得和空数据集一模一样。真「空集合」一般回结构完整的空壳（`{"payload":[]}`），
    **什么都不回**才可疑。只做被动接收就写的「空流/无数据」结论必须作废重测。
14. **一次性凭证（PoW/nonce/OTP）不许跨 attempt 复用（§H）** —— 复用会让第 2..N 条测试全回 400，
    把「探针坏了」伪装成「目标拒绝了这批载荷」。**每个 attempt 重新取 challenge。**
15. **必填字段的 400 会掩盖凭据判决（§H）** —— 形状校验先于 token/签名校验时，缺字段让真 token 与假 token
    回**同一个** 400；批量伪造测试**先凑齐必填字段**，再看 `invalid`/`unauthorized` 这种真判决。
16. **「空响应 / `000`」不等于「不存在」**（§I）：宝塔类 WAF 对高危特征**静默断连**，
    和被封出口/超时**长得一模一样**。每批「空响应」必须配一条**同通道、同客户端、同参数**的已知 200 对照；
    对照也空 = 通道废了，整批作废。**永远不许把「没试成」写成「试过且无效」。**
17. **`--resolve` 配 `socks5h` 无效**（主机名远端解析，本地覆盖被忽略）。要直连源站 IP 绕域名层 WAF，
    用 **裸 IP URL + `Host:` 头**（§I2），并先跑对照确认 vhost 能路由。
18. **算哈希/命名规则时先对齐目标语言的实际字符串化**：`md5(microtime(true))` 这类
    在 PHP 里受 `precision=14` 约束（当前时间戳只剩 4 位小数），拿 Python 17 位小数去算必然 0 命中。
    爆破前先本地 `php -r 'echo (string)microtime(true);'` 取真实格式。
19. **恒定墙钟超时（任何载荷都在 ~100s 被掐成 502）是超时边界，不是「链不可用」**：
    先跑「无载荷 / 换方法 / 换端点 / 换出口」对照齐射；同一墙钟全灭 = 环境阻塞。
    **「环境阻塞」与「洞不存在」是两个结论，不许混写**（§J）。慢站判读按三态分层（静态/PHP/DB），
    `favicon 200 + 应用端点 000` 是「半死站」，不许折成「站点死了」。
20. **「TCP 通」是传感侧假阳性源（§K）**：tarpit 下 SYN 可完成而 HTTP 数据全丢；「端口开」必须补 HTTP 层证据。`connect_ex` 的 `111`（RST=真没监听）与超时（多为被封/丢弃）不许合并——两者对应完全不同的行动（等窗口 vs 换出口）。

21. **「热命中」先过 cache-buster 再庆祝（§K2）**：公共代理会回放旧窗口的完整 200（`X-Cache: HIT` + `Date` 冻结在旧时刻），正文校验挡得住内容过滤页、**挡不住缓存**；跟一条 `?_<rand>`，buster 死 = 假活，只记日志。
22. **「无票 401」不是存在性证据（§L）**：全局鉴权中间件让**未知路径也回 401**；先拿真票带 `Authorization` 重刷，真 404 才判不存在。嵌套资源路径（`/user/userInfo/register/`）另需从 bundle 挖完整路径，词表翻不到。
23. **兄弟端口反代是会被忽视的门（§M）**：目标端口间歇关闭时，同机常开 nginx 端口的 `/admin-api` 反代可能一直活着——**502 = 路线已确认（上游没起）**，非 502 = 直插。把它挂进伏击（多路线 + 命中冷却 + 每轮重读代理池），别当「打不开」收手。

24. **非标端口「Empty reply / 静默」先换协议再下结论（2026-10 实测）**：自建栈常把 app 端口配成 **HTTPS-only**（实测 :8088 类）——http 探针得 `Empty reply from server`，与「端口被封 / 服务没起」外观一致，曾把整批探测误记成「全域被拉黑」。**同端口 `https://` 复测**（自签证书加 `-k`，必要时补 `Host:`）后才准判「沉默」。
25. **403 / 异常响应先过「头 + 编码」两关**：同一 URL 因缺**手机 UA + `X-Requested-With: XMLHttpRequest`** 回 403、补齐即 200（反爬**头**依赖 ≠ WAF 硬封）；抓到的 JS/文本先确认没被 gzip 包住——curl 不带 `--compressed` 落盘的是压缩体，grep 必然 0 命中，先 `gunzip` 或重抓再扫。

## 关联

| 技能 | 定位 |
|---|---|
| `recon-discriminators` | 侦察判读（**假阳性**侧：兎底页基线、停放页、同 IP 归组）—— 与本卡互为镜像，建议 adopt 后合并 |
| `ip-ban-bypass` | 出口被封的诊断与换路 |
| `egress-proxy-pool` | 住宅代理/代理链选型 |
| `agent-evidence-gate` | 证据闸：结论必须有可复现依据 |

## References

- `references/false-negative-cases.md` — 三类假阴性的完整实测记录 + PATH_INFO 前缀绕过完整请求/响应对照
- `references/silent-drop-and-channel-controls.md` — §I/§I2 实测：宝塔 WAF 静默断连 vs 错误页、`--resolve`+SOCKS 失效、直连 IP+Host 通道对照

