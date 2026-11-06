# recon-negative-validation 全文 第 2/2 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

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

