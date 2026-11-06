---
name: password-spray-lockout-bypass
description: "Use when a login locks out during password spraying."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [web, brute-force, password-spray, lockout-bypass, collation, cloudflare]
    related_skills: [waf-fronted-login-attack, pentest-execution, web-sec, api-contract-mining]
---

# Password Spray / Lockout Bypass

The credential-attack class: getting a valid token when the login rate-limits or locks accounts. Covers lockout fingerprinting, bucket-minting variants, spray ordering, and running a campaign durably.

Sibling skills: `waf-fronted-login-attack` (egress blocked by a WAF — bans, `1006`, challenge solving, transport crypto), `api-contract-mining` (endpoint + request-shape map from the JS bundle).

## When to Use

- Login answers `用户名或密码错误` / `Invalid credentials` but locks after N tries (`账号已被锁定，请2分钟后再试`)
- You need a `sa-token` / JWT / session to reach authenticated endpoints
- A brute run keeps stalling on lock messages instead of finishing
- A previous run found nothing and you cannot say how much was actually tested

## 1. Fingerprint the lockout before spending attempts

Measure, don't assume — thresholds and keys differ per app:

- Burn one **throwaway identifier** (`probe7x`) until the lock message appears; the attempt count is the threshold (commonly 10–20 within a 1–5 min window).
- Record the cooldown: clears on a timer, or only on success?
- **Test whether nonexistent users lock too.** If they do, the endpoint is *not* an existence oracle — do not build strategy on username enumeration from it.

## 2. Test whether the counter is keyed on the raw submitted string

This is the whole game. Replay the *same real account* with nearby variants while the exact string is locked:

| Probe | Result | Inference |
|---|---|---|
| `probe7x` again | `账号已被锁定` | threshold hit, exact-string bucket locked |
| `probe7x ` (trailing space) | `用户名或密码错误` | different bucket ⇒ per-raw-string key |
| `PROBE7X`, `Probe7x`, `probe7x\t` | `用户名或密码错误` | same ⇒ **unlimited attempts** |

A per-raw-string key means the lock limits *per spelling*, not per account.

**Normalization is the kill switch for this whole strategy.** If a case/space variant of an already-locked
name returns the *lock* message instead of `用户名或密码错误`, the app trims/lowercases the key before
counting — every variant shares one bucket and §3's minting buys nothing. Diagnose once on a throwaway
(`probeNN`), never on the primary account:

| Probe | Reply | Meaning |
|---|---|---|
| lock `probeNN`, then `ProbeNN` | `账号已锁定` | key **normalized** → variants useless, abandon §3 |
| lock `probeNN`, then `ProbeNN` | `用户名或密码错误` | per-raw-string → variants work |

Live 2026-10 (Go/Vue 后台): `admin` / `admin ` / ` admin` / `ADMIN` / `Admin` all shared one counter; the
5th variant re-locked an account that had just come off cooldown — self-inflicted 30-minute loss.
Test normalization *before* spending a single real guess.

Do not confuse this with **path-bucketed** rate limiting (auth middleware normalising the URL): there, percent-encoding/case/trailing-slash/`;` variants all land in one bucket and repeated probing is a platform-wide login DoS. Test once, write down which key it is, and only then automate.

## 2b. 叠了 googleCode / TOTP：先判字段顺序，再决定喷不喷

「缺字段返回 *请输入谷歌验证码*」**只是必填校验，推不出验证码先校验** —— 当顺序证据会把死的预言机当活的。
判顺序只认这组差分（账号必须处于未锁状态）：

| 请求 | 返回 | 结论 |
|------|------|------|
| 错密码 + `googleCode:"000000"` | `账号或密码错误` | **密码先校验 → 口令预言机成立**；口令对了会走「验证码错误」，这就是命中信号 |
| 错密码 + `googleCode:"000000"` | `验证码错误` / `谷歌码错误` | 码先校验 → 预言机死，喷口令无意义，回泄露面/伪造票 |

实测 2026-10（Go/Vue 多租户后台）：先回「请输入谷歌验证码」被误读成码先校验，差分测出实际是密码先校验，
口令摊仍然有效。锁定期内所有请求都回锁定文案，测不出顺序，必须等自然解锁再测。

**把「非 10002 即命中」当硬判据。** 二次验证门/IP 白名单门都以独立码返回，按「失败」丢掉等于把到手的口令扔了：

| 码 | 含义 | 处置 |
|---|---|---|
| 200 / `code:0` | 完整登录 | 落 token，停该账号 |
| **4001** | **密码正确，需谷歌验证码** | 口令已到手 → 转 2FA 面（TOTP 种子 / 绑定接口 / AdminList 泄 `googleSecret`） |
| **10014** | **密码正确，IP 不在白名单** | 口令已到手 → 转 origin 直连 / 内网 IP 白名单面 |
| 10002 | 用户名或密码错误（统一文案） | 计一次失败 |
| 430 / 10003 | 已锁定 | 停该账号，写复工**绝对**时刻 |
| 20016 | 签名无效 | **请求配方错了**，不是口令错 —— 先修配方再继续 |

Runner 里写 `if code != 10002: 落盘 + 告警`，而不是 `if code == 200: 命中`。

## 3. Mint buckets that still resolve to the same account

Variants only authenticate if the DB comparison treats them as equal. Ranked by how safe that assumption is:

1. **Case patterns — portable.** Works under any `*_ci` collation and is safe under both PAD SPACE and NO PAD. An L-letter identifier has at most `2^L − 1` distinct patterns (3 letters → 7, 4 → 15, 5 → 31).
2. **Combining diacritics — effectively unlimited.** Accent-insensitive collations (`utf8mb4_general_ci`, `*_0900_ai_ci`) treat `admín` / `admiń` as equal to `admin`. Appending `U+0301` k times yields k+1 distinct raw strings, each a fresh bucket.
3. **Trailing spaces / `\t` — alias only under PAD SPACE** (`utf8mb4_general_ci`, `utf8mb4_unicode_ci`). Under MySQL 8's default `utf8mb4_0900_ai_ci` (NO PAD) they still mint buckets but may match nothing.

```python
def variant(user, i, per_string=15):
    """Alias of `user`; each distinct raw string buys `per_string` attempts."""
    blk   = i // per_string
    nvar  = max(1, min(2 ** len([c for c in user if c.isalpha()]) - 1, 31))
    s     = apply_case_pattern(user, blk % nvar + 1)
    extra = blk // nvar                  # overflow -> the weaker mechanisms
    s    += "\u0301" * (extra % 5)        # diacritics: accent-insensitive collations
    s    += " " * (extra // 5)            # spaces: PAD SPACE collations only
    return s
```

Budget the mechanisms in order: case patterns are the only one with no collation caveat, so spend that budget on the highest-probability passwords first and fall through to diacritics/spaces only after. Keep `per_string` at the measured threshold — one attempt over re-locks that bucket.

### 3b. Unicode 同形字：case/空格被归一化时唯一还开着的独立桶

实测（2026-10，Go/Vue 后台，5 发/30 分钟）：`ADMIN` / `admin ` / ` admin` 与 `admin` **共用**计数器（键做了 trim+大小写折叠），
但 **全角 `ａｄｍｉｎ`、西里尔 `аdmin`（U+0430）、零宽字符插入** 各自是**独立计数器** ⇒ 归一化是 trim+casefold，**不是 NFKC**。

- 拿到一个新桶 ≠ 能登进真账号：数据库是否把同形字折叠回真名**未证实**（缺显式 oracle 时无法验证）。
  先把**已知正确口令**打到同形字上验一次；只在它返回「密码错误」而非「用户不存在」类文案时才继续投入预算。
- 预算仍按观测阈值（本例 4 发/桶），同形字只是**多买几个桶**，不改变每桶的发数。
- 相比 diacritics/spaces，同形字在 **Go/Java/Python 直连 DB + `utf8mb4_general_ci`** 之外更常见地“能建键但打不中”，
  所以它是**最后一个**手段，别一上来就用它烧预算。
- 反向用途：**同形字桶的存在本身就是“锁定按原始字符串”的确定性证据**，可写进报告（配合 §Pitfalls 的「锁状态=后端指纹」）。

### 3c. 没有「已知正确口令」时，怎么验同形字到底映射不映射（时序差分）

§3b 说「先拿已知正确口令验一次」——实战里往往**根本没有已知正确口令**（正是你在猜密码的原因）。
那就用**时序**判，8 个请求、不烧任何桶：

1. 打一组**明确不存在**的用户名做基线（如 `zz9qqqq8888`），≥4 采样取中位数；再打**变体**
   （`admin\u200b`、`ádmin`、`ａｄｍｉｎ`）各 ≥4 采样。
2. 直连源站（无 WAF / 无 Tor 抖动）时：变体中位数 **≈ 不存在基线（差 ≤10ms）⇒ 后端没把变体折叠回真名**
   ⇒ 这些桶「能建键但打不中」，立刻弃，别把 8 个变体 × 5 发全喂进去。
   变体中位数**明显高于**「不存在」基线（多出一次哈希校验）⇒ 才值得投预算。
3. 实测 2026-10（Go/Vue 后台，5 发/30 分钟，直连）：不存在基线 253ms / 全角 265ms / 零宽 257ms /
   西里尔 259ms —— 全在同一噪声带 ⇒ 判定不映射；随后 8 变体 × 5 发打完零命中，与判定一致。
   §Pitfalls 的「时序 oracle 必须在空载下测」同样适用：喷发中测必假阴性。

**diacritics 可能是整类全死的。** §3 把「组合变音符」列为第 2 优先，前提是排序规则为 `*_ci`。
实测同一目标：`ádmin àdmin âdmin ädmin ãdmin ådmin ādmin` + 全角 + 无点 `ı`，**9 个变体全部 `10002` 且时序平坦**
⇒ 该后端不是 accent-insensitive（Go 字符串比较 / `utf8mb4_bin` / 应用层精确匹配都可能）。
所以：**先花 8 发验一个变体，再决定要不要把 diacritics 当主力**；平坦就整类弃掉，别按 §3 的
「effectively unlimited」去排预算。

### 3d. 并发竞态放大有上限（≈2×），流水线放不大（2026-10 实测）

计数非原子时，同一把锁的额度会被并发吃掉一部分：

| 手法 | 实测结果（5 发/30 分钟的面板） | 结论 |
|---|---|---|
| 100 线程同时打同一用户名 | `{429:90, 10002:10}`，2.04s | **真校验 10 次 = 2× 额度** |
| 单连接 HTTP/1.1 流水线，一次写 60 个请求 | `200×60`，`10002=5 430=5 429=50`，26.3s | 无增益：网关按到达顺序串行入队、原子计数 |

- 增益是**常数级（≈2×）**，不是任意放大：线程 100→500 不会变成 50 次，只多出 429。
- 只在「本窗候选只剩个位数」时才划算，而且**竞态会把锁续时**——抢完这 10 次本窗就彻底关闭。
- 竞态窗口要求同一瞬间：先建好连接（TLS 握手预热），再 `release()` 所有线程同时发；差几十毫秒就退化成串行。

### 3e. 只有「新键回 `用户名或密码错误`」不许对外宣称锁已绕过

最贵的翻车句式是「锁已经废了」——它只证明了**键可以换**，没证明**换出来的键命中同一行**。
对外下结论前必须过 §3c 的时序闸（空载、≥4 采样、与不存在用户名基线比），或拿到一次真实命中（200 / 需要二次验证的码）。
实测 2026-10（Go/Vue 面板）：`ádmin`/`admín`/`admin`+`U+0301` 全回 `10002`、一个 430 都没有，看起来锁开了；
但计时 275ms vs 不存在基线 284ms（Δ≈9ms，噪声带内）⇒ 后端根本没折叠，那批 7,829 条字典全打在空气上。**先过闸，再吹。**

## 4. Order the spray: breadth before depth

**先算账：per-account 锁下，总时长 = 字典长度 ÷ 10 小时，与账号数无关。** 5 发/30 分钟 = 10 发/小时；N 个账号并行时
总吞吐 10N/小时，但要覆盖 D×N 次，`D×N ÷ 10N = D/10` —— **加账号不缩短任何时间**。
实测：16 账号 × 487 词 = 7,792 发 ÷ 160 发/时 = 48.7 小时 = `487/10`。开喷前先把这个数报给用户，别让他等三天才发现。
所以唯一能改的只有 D：

- **tier0 已确认口令（≤100 条，1 小时内出结果）**：把本案**其他系统**已爆出的口令全塞进来（商城超管、会员端、运营方别名、
  外包、历史面板），一字不改。反面实测：413 词字典里**一条已知口令都没有**，最可能命中的 20 条全排在最后。
- tier1 品牌/面板名/运营方代号 × 年份 / `@` / `123`；tier2 rockyou 尾部永远垫底，跑不完就永远轮不到它。
- 若家族里还有第二、第三个登录面，先比锁成本再选主线（见 §4e），别在 10 发/小时的面上下注。

Coverage per identifier is capped (only the case-pattern budget is high-confidence), so iterate **password-priority across many accounts**, not exhaustive-per-account:

1. Top ~250 passwords × every candidate username.
2. Then the next tranche, re-using the same runner and state files.

Wordlist order beats size: site-specific strings (`<brand>123`, `<brand>@2026`, the vendor default host hardcoded in the SPA) → locale top-1000 → global top-100 → synthetic locale names (common surnames × numeric tails, pinyin × digits).

**生成器先种字面量 `admin` 本体，再谈品牌派生。** 2026-10 实测：一份品牌词派生表（1059 条）里完全没有
`admin` / `12345678` / `111111` / `000000` / `admin1` / `root`，上千次尝试里一次没试过 `admin/admin` ——
最丢人的空转。发车前用 `grep -ix` 逐个核对这六个必须项在不在队列里（和用户名侧的 `admin` 漏项是同一类错）。

Username list: use the panel's own vocabulary, not just `admin` — `admin administrator root sa superadmin kefu kefu01 service test demo user sms smsadmin boss laoban guanliyuan system vip merchant api agent` plus the brand name itself. **先把普通话的 `admin` 本体放进列表**：2026-10 实测一份人工整理的 8 用户名单（qt888/101670/tioadmin/fuxin/kefu/manager/tyzkc/zhoujingfu）漏了 `admin`，1700 条口令跑完之后才发现要补这一格——手搓名单常见的漏项就是最普通那个。

### 4b. Get a real directory instead of guessing usernames (do this FIRST)

Fifteen real logins with real names beat three hundred guessed ones, and they turn the spray from a lottery into a targeted job. Before committing to a wordlist, spend ten minutes turning any enumeration signal into a directory:

- Existence oracles: lock-vs-no-lock differential, `users/{id}` 200-vs-404, "账号已被删除" style states, format-error messages.
- **Better: a relationship/list endpoint that leaks what the detail endpoint redacts.** Detail endpoints commonly null sensitive fields (`GET /users/{id}` → `loginName: ""`), while a sibling endpoint in the same resource family (friends / members / contacts / participants) returns the **complete object**. A relationship-write endpoint (`POST .../friends/add {"friendId":"<any id>"}`) often has **no authorization and no recipient consent**, so you can walk the whole ID space and then read the list.
- Worked example (opensms.xin): `friends/add` returned `添加成功` for every id — including nonexistent ones — and the follow-up `GET /friends` dumped `name` / `loginName` / `mobile` / `email` / `deptId` for all 16 accounts, including `id=1` = the administrator (`admin`, its mobile, its mailbox). Full recipe: `api-contract-mining` → `references/relationship-endpoint-field-leak.md`.
- Harvest every field, not just the login: mobiles, mailboxes, department/parent ids (feed them back as new enumerable ids), and `*ModelTimes`-style counters that identify **active** accounts worth spraying first.

### 4c. Shape the wordlist from the app's own password policy

If any config/profile endpoint discloses the password rule, generate candidates that *satisfy* it instead of dumping a generic list. Live example: the client config exposed "≥8 chars, must contain upper+lower+digit, 90-day rotation" → the accounts are necessarily carrying passwords like `Admin@123` / `Daili123456` / `<Brand>@2026`, i.e. policy-shaped weak passwords, not `123456` alone. Combine:

1. Role word × `123` / `1234` / `@123` / `@1234` / `123456` (site language, capitalised)
2. Brand word + digits, brand + `@2026`
3. Every identifier field you harvested: the person's own mobile number and its fragments, `admin<mobile>`, `<mobile>@123`
4. Locale tops (see §4) and the vendor default host name

Policy-shaped lists are short (~2k) and high-yield; rank them ahead of the generic tranche and spray them **across all discovered accounts**, breadth-first as in §4. Run the generic list afterwards — it is the fallback, not the opening move.

### 4d. 品牌农场：域名数 ≠ 通道数

多品牌白牌（同一套 Go/PHP 后端、N 个前门域名）扩展时，先把域名清单拿全（CT 日志 + 公开桶里的前端配置 json），
再判**是否同库**：同库的域会返回**同一剩余冷却时间**，异库各自独立。实测 2026-10：12 个品牌域名
（zggfjjh2026 / guojzjxx2026 / hwzbinfo / gxhzsm / huifenjys2026 / hjysht2026 …）全部映射回 **5 个库**；
其中 2 个是硬 IP 白名单（TCP 源 IP 校验，XFF 伪造无效）、3 个按 XFF 判来源可绕。
**先把通道数算准再排预算**，别把「12 个域名」当「12 条通道」写进计划——否则吞吐预估会高出一倍以上。

### 4e. 先选最没设防的入口，再谈锁窗算术

同一家族往往有 3 个登录面（主站后台 / IM 管理端 / 客服 SaaS 平台方后台），锁窗成本差**三个数量级**。开喷前对每个面各花 ≤30 发测三件事：锁不锁、有没有验证码/2FA、20 线程能到多少 rps。

实测 2026-10：主站后台 `4 发 / 30 分钟 / (租户+用户名)`（≈0.13 rps/通道）；同家族客服 SaaS 平台方后台**无锁定、无验证码、无 2FA**，30 线程 42 rps、100 线程 98.5 rps。同一小时换面 = **2,400 倍**吞吐差。**锁窗算术只在确认全家族都没有无锁面之后才值得做**；先做算术再发现无锁面，等于把最贵的那条线当主线。

配套判据：`X-Forwarded-For` / Host 尾点 / 大写 / 带端口 / `X-Forwarded-Host` 全部共享计数器 ⇒ 键是「租户+用户名」，不含 IP，换出口无用；`456` 与 `123` 直接 418 ⇒ 键确实跨租户隔离。详见 `references/no-lockout-surface-selection.md`。

## 5. Make the campaign durable and the reporting honest

- **Resumable state**: one file of tested secrets per identifier, skipped on resume. **Never mark a secret tested when the response was junk/WAF HTML** — track tested vs skipped separately.
- **Egress throughput is the real ceiling — build an egress POOL, not one proxy.** A single shared proxy measured ~0.35 req/s with ~50 % junk responses, which turns a 30k-attempt list into a 24-hour job. Keep the fast/paid proxy and add N fixed Tor circuits, round-robin across all of them, and raise workers to 24: `-x socks5h://127.0.0.1:9050 --proxy-user circ<i>:x` (under IsolateSOCKSAuth a FIXED proxy-user = one stable circuit; a random one per request rebuilds the circuit every time and costs ~20 s). Same list, same target: **0.35 → ~7 req/s** after pooling. Pin a worker to a circuit for its whole batch; on failure retry on a *different* egress, never the same one back-to-back.
- Sample egress quality before a campaign (10 parallel requests, count non-JSON/`000`): a proxy can look alive on one probe and still drop half your attempts, and every dropped attempt silently shrinks real coverage.
- A `no_agent` cron watchdog (every 5 min) that restarts the runner when `pgrep` is empty and prints only on a hit keeps the campaign alive past the chat session.
- Raising the limit or growing the wordlist later **resumes** (state-skip); it does not restart. Say so, or "the list was covered" is wrong.

## 相关 / 姊妹卡

- 登录面假阴性完整实录（字段名错→误判冻结、SVG 明文验证码、AJ-Captcha 编码坑、短信码无锁定的可行算法、品牌域名≠通道数）：
  见 `admin-auth-oracle-triage` 的 `references/login-gate-false-negatives.md`
- 滑块/图形验证码的具体识别：见 `captcha-ocr`、`captcha-registration-bypass`

## Pitfalls

- **「账号或密码错误」在核过字段名之前不算结论。** 实测 2026-10：某 App 登录要的是 `loginPassword`，
  我们发 `password`，服务端当空密码处理，稳定回 401「账号或密码错误」→ 据此误判「回传账号已被冻结」，
  整轮 App 侧测试都建在假阴性上。正确顺序：从 SPA bundle 抄**调用点的完整 body**
  （本例 `{phone, loginPassword, loginType, deviceType, deviceCode, deviceFingerprint}`），字段名、类型、必填项
  逐字照抄后再打；只有与浏览器抓包逐字段一致时，401 才能读成「凭据错」。同理，下「账号被冻结/注销」结论前
  必须先排除字段缺失/改名（先导：`api-contract-mining` 的 request-shape 提取）。
- **多通道共用一个 tested 文件 = 每个口令只在一条通道上试过一次。** 守护进程用全局 `tested.txt` 去重时，
  5 个租户的通道会退化成「一个口令只打一个租户」；同运营方多品牌通常同口令，这样够用，但**一旦同口令假设不成立，
  覆盖就静默断掉**。要保证每口令 × 每通道，状态文件按通道键（`tested_<host>_<user>.txt`），并统计
  「已覆盖 (口令 × 通道) 对」而不是只报口令数。
  反过来也要防**「最优组合被低概率通道吃掉」**：实测全局队列把 `admin` 这条口令派给了命中概率最低的 `gf|admin`，
  主库 `123|admin` 一次都没轮到。列一张 `(租户 × 用户名) × 命中概率` 表，给最高概率那几条通道**单独一条高优先队列**
  （哪怕只有 4 发/30min 也值得先吃满），其余通道再跑广度；不要用单一全局队列平铺。
- **`loginType` / 设备指纹 / 租户头都可能不在锁键里 —— 但也不能当额度来源。** 实测 2026-10 同一面板：
  锁死后换 `loginType`、`X-Device-Id`、UA 全部仍回 430（不在键里）；`X-Forwarded-For` 只影响 IP 维度锁、不影响账号锁。
  这些维度既不能扩额度，也说明锁键就是「归一化后的用户名」这一条，预算算术按它算。
- **同形字不要单独占通道。** 全角/西里尔变体能拿到独立计数器，但数据库不会把它们折叠回真账号（除非证明过 alias），
  给它们分配专用通道等于白烧一半吞吐；只在拿到「已知正确口令 + 同形字仍回密码错误」的证据后，才把它当普通桶用。

- **Measure the IP-key before assuming XFF is dead or alive.** Two opposite live patterns:
  - **Socket-IP key** (hardened farm panels): 13 client IP headers still 429; only real egress change helps → Tor `IsolateSOCKSAuth` / proxy pool.
  - **Client-header key** (4li.com / vinext 收号站): after ~7 fails → `429 请15分钟后再试`; one forged `X-Forwarded-For` or `CF-Connecting-IP` with a fresh public IP → immediately `401 账号或密码错误`. Budget: rotate XFF per attempt (cheap). Still obey the 10–20 weak-password stop; large lists need user OK.
  Fingerprint in ≤5 probes on a throwaway user before spraying.
- **锁状态本身就是后端指纹。** 同一账号在两个姊妹域上返回**相同的剩余冷却时间**（两处都 `请23分钟后再试`）
  ⇒ 同一个共享后端，不是两套部署。这比比 favicon / `/api/health` 更硬：那两样只能说明前端同源，
  锁计数说明**同一份状态**。做法：先在一个 throwaway 上打满锁，再拿它到另一个域比倒计时 ——
  绝不要用主账号验（探测锁定中的账号会续时）。反过来这条也提醒：多域名不等于是新攻击面，先验后端再决定要不要重打。
- **锁定码同时覆盖「账号锁」和「IP 锁」时，它就不是存在性 oracle —— 哪怕文案看起来不一样。** 实测 2026-10（Go 后台）：
  `code=430` 既表示「账号已被锁定」也表示「当前 IP 已被临时锁定」，而对**根本不存在的用户名**打到阈值同样回 430。
  于是「第 4 发回 430 ⇒ 账号存在」这条自造启发式把候选名单里 6/7 个判成「存在」，随后整条 admin 线全被锁死，
  80 个候选用户名一起进 30 分钟冷却 —— 等于自己把攻击面关掉。
  判据只有一条：**先在不存在的用户名上把锁定打出来**；打得出 ⇒ 锁定与存在性无关，此路封死。
  看到「有锁定文案 + 假用户也锁」就立刻停手转别的面（泄露面 / 伪造票 / 导出接口），不要在锁窗算术上继续投预算。
- **Account-keyed lockout ≠ IP-keyed.** If messages look like `账号错误次数超过限制，请3分钟后重试` / `错误N!admin`, Tor/`IsolateSOCKSAuth` **will not help** — the counter is on the account. Switch to **≤3 attempts per window + hard sleep ≥ cooldown** (often 180–210s), then resume. Wasting exits on IP rotation is noise.
- **Size the variant space to the identifier's length.** A generator that cycles 31 case patterns on a 4-letter name repeats strings, burns a second bucket on the same raw string, and re-locks mid-run. Symptom: lock messages after a long clean stretch. This is the most common self-inflicted failure in this workflow.
- **Do not claim the aliasing assumption is validated.** With no oracle beyond lock behaviour, a null result is not proof the password is outside the list. Never report "no weak password exists" from an unvalidated run.
- **Timing enumeration: conditional, not forbidden.** Over WAF/Tor egress with a fast hash the jitter is swallowed by network noise — don't bother. On **direct egress + a slow hash (bcrypt-class)** it is decisive: take a baseline median over ≥5 probes with a random username, then 8 probes per candidate, and treat a stable ≥150 ms delta as "account exists". Worked case: `admin` 753 ms vs 429–458 ms across 24 other names, reproducible every run — that is the directory §4b asks for, and it is a CWE-208 finding in its own right. Spend this budget *before* spraying, and note that each probe consumes login rate-limit budget.
- **时序 oracle 必须在空载下测，喷发中的测量必假阴性。** 同一条手法在 100 线程喷发并行时测，存在/不存在两个用户名的分布完全重叠 —— 服务端 CPU 被自己的请求占满，哈希差被排队噪声吃掉。实测 2026-10 客服 SaaS：15 采样 × 2 用户名无差分，事后回看是**负载污染**，不是「无 oracle」。要测就先停喷、单线程、拿随机用户名做基线。
- **rps 衰减到一半先怀疑服务端慢哈希，不是自己的带宽。** 实测 100 线程先冲 112 rps 再稳在 46 rps；单流探针实测每请求约 2s ⇒ bcrypt 类。线程翻倍不会越过服务端 CPU 上限，只会拉长队列、把超时和假 401 变多。上量前先单发计时：>0.5s/请求就是慢哈希，吞吐按 CPU 并行度估，不按线程数估。
- **持续高 rps 会把出口打成 Cloudflare 挑战页，而且返回 200。** 实测 4 万发 73 rps 后该 host 全线回 `<!DOCTYPE html>`，连账号 oracle 都测不了。无锁面的价值在「随时能测」，别用一次性大字典把这个能力打没；要留额度给 oracle 探测。
- **喷中任一低权管理员 ≈ 喷中超管。** 后台前端包里 `AdminList` 明文渲染所有管理员的 `googleSecret`（见 `build-artifact-exposure` Step 3）⇒ 一个弱口令管理员账号 = 全员 2FA 种子到手。排预算时把「面板里任何能读 AdminList 的角色」都算有效目标，别只盯超管用户名。
- Read the *body*, not the status code: a WAF interstitial is 200/403 and can be mistaken for a real "wrong credentials" reply. JSON body ⇒ origin, HTML/empty ⇒ junk ⇒ retry on a fresh egress.
- `-x socks5-hostname://host:port` is rejected by curl (`Unsupported proxy scheme`). The **URL form of `-x` only accepts `socks5h://` / `socks4a://`**; `socks5-hostname` exists solely as the `--socks5-hostname host:port` FLAG. And always pass `--proxy-user user:pass` **with the colon** — a colon-less value makes curl stop and prompt for a password (looks like an instant `000` / auth failure in batch runs, and it is your command, not the proxy).
- A directory leak makes the username list free — but nothing is "covered" until the runner's tested-vs-skipped counts say so. Junk/HTML responses must be counted as skipped, not tested.
- `curl -D -` mixes headers into stdout; use `-D hdr.txt -o body.txt`.
- Never report a credential as found without replaying the login cleanly on one fresh egress.

- **口令必须带命名空间落盘，别记成一条「admin 密码」。** 同一案卷里同名不同系统是常态：商城 FastAdmin `fa_admin` 是 `123456`，
  另一个后台的超管是 `aa112233`。记成单条「admin 密码」的结果就是**拿 A 系统的口令去打 B 系统的账号**，
  在 3 发/30 分钟的 IP 锁上一次性烧掉整轮窗口（实测白等 27 分钟）。固定四元组 `(系统, 账号表/角色, 账号, 口令)`，
  落盘、交接、汇报都用它，不许省前两段。
- **runner 的落盘格式必须能被自己的 resume 正则解析。** `-> 10002 msg` 与 `-> http200 code=` 是两个世界；对不上时
  `load_tried` 永远返回空，每次重启都从字典头部重来，一半额度烧在重复尝试上。重启一次后必须核对「已测数」是否真继承。

## Verification

- [ ] Lockout threshold and cooldown measured on a throwaway identifier
- [ ] Bucket key identified (raw submitted string vs normalised path) and recorded
- [ ] Variant count sized to the identifier's letter count; a long run produces **zero** lock messages
- [ ] Runner resumable + watched by cron, with tested-vs-skipped counts reported
- [ ] Any coverage claim states which alias mechanism was validated vs assumed

## Session detail

- `references/opensms-case.md` — Cloudflare-fronted SMS panel: lockout fingerprint, the variant-space bug and its fix, spray results per pass.
- `references/account-keyed-lockout.md` — when Tor does not help; 3-attempts/window + hard cooldown pattern (712win3 admin spray).
- `references/multi-tenant-lock-arithmetic.md` — 5 库 × 7 用户名 = 35 通道的实测算账：吞吐上限、全局队列饿死最优组合、报告口径。
- `references/no-lockout-surface-selection.md` — 三个登录面横向比吞吐（空转锁窗 vs 无锁面 2,400×）、无锁 ≠ 好打、44 万次零命中后怎么下结论。
- `references/lock-key-scope-and-race.md` — 锁键维度矩阵（IP/大小写/`loginType`/设备均不在键里）、重音+组合符可造键但时序闸判否、100 线程 = 2× 额度、流水线无效。
- `references/fastadmin-credential-profile.md` — FastAdmin：`md5(md5(pw)+salt)` 离线爆 vs 登录框 3 发/30 分钟 IP 锁（不认 XFF）、`__token__`+滑块登录配方。
- `scripts/lock_scope_probe.py` — 60 发以内一脚跑完上述七个维度（阈值/冷却文案/XFF/大小写/重音/组合符/extra 字段/并发增益），只定锁不爆破。

## 2026-10 极狠锁窗：15 分钟 / 实测 2-shot（zgycpd 类）
- 三级 oracle：`invalid username or password`（错密）/ `invalid authenticator code`（**密码 HIT**，缺 OTP）/ `too many login attempts; try again in 15 minutes`（锁）
- 预算：每 host 每窗 **1 密**，cool ≥16m；单线 oneshot，禁 site_dict / twin / 探针叠喷
- 阈值因后台而异：同一报告里一个后台实测 `2-shot / 16min`，另一个写「每窗口 ~8 次即封」→ **首轮先 1 发**，读冷却文案确认阈值再定 2 或 8
- 叠喷一次烧整窗；`gate_unlocked()` 类「错密探针」本身也算一次，必须删
- 记录 WINDOW 去重数，别把重复密码算进预算
- 密码 HIT 后立即落 `ADMIN_PWD_OK`，转 OTP 面；无种子就停，别继续喷
- 前置：确认锁是按账号还是按 IP（换出口是否重置）；按账号锁时 Tor 无用

### 锁窗倒计时不可信（2026-10 实测补充）
- **不要单独发“探锁”请求**：探测本身就吃一次预算，而且可能重整计时器。
  把**批次第 1 发当探针** —— 回「密码错误」= 窗开着，继续；回「N 分钟后再试」= 立刻停，**不要再发第二发**。
- **同一账号的剩余时间会跳变**：实测 `13min → 11min → 10min → 30min`（中间只隔几分钟）。
  说明锁不是单纯倒计时，会被**重新武装并升级**。所以：只按**观察到的最大窗口**等（本例 30 分钟），
  到点后一次性把本窗预算（实测 4 发）打完，**中途绝对不插探针**。
- 预算耗尽（N 发全错）后立即落「本窗已耗尽 + 复工时间」，别提前 1~2 分钟去试 —— 提前一发就把整窗重新点着，
  在 30 分钟窗口上等于一天只能试 4 个口令，先算清这个账再决定要不要继续这条线。
- **冷却从「本窗最后一发」起算，不是从窗口开始或第一发起算**，加 1 分钟余量（本窗 4 发 ⇒ `sleep 31min`）。
  按窗口起点算的调度器会漂移：下一窗第一发正好成了第 5 次，又把刚解锁的账号重新锁 30 分钟，实际吞吐从
  4/小时 掉到 4/2 小时。守护进程里同时要保证 **锁定/封禁类响应不消耗候选队列**（否则锁窗期把弱口令白吃掉）。
- 多通道并行时用**不同品牌租户**（独立账号 + 独立计数器）而不是同租户的多个域名（同租户共用一个计数器，白搭）。
- 锁定文案里的数字**当作下界**而不是精确值：写报告用「≥N 分钟」，不拿它推算确切解锁时刻。

### 排程纪律：定时的基准只能是 `date -u`，不能是脑子里的估算

- **每轮定时打击开工前、以及每次算「还剩几分钟」之前，先跑 `date -u`。** 实测 2026-10：凭日志里几行旧时间戳
  推断当前时刻，偏差约 20 分钟，`precise_try.py` 把两个账号的全部 2 发预算都打在锁定窗口里（回锁定文案、
  预算空转、解锁时刻不重置），整轮白等 30 分钟，还被误读成「密码不对」。
- 排程用**绝对时刻**（`datetime` 直接比时间戳）而不是链式 `sleep N`：脚本被 kill 后重启不会累积漂移。
- 服务端只给**剩余分钟**，那是相对量。收到的那一刻立刻 `now + remaining` 换算成本地绝对时间**落盘**，
  之后从盘里读；不要隔几轮再心算一次。
- 某账号本窗预算打完就立刻落「本窗耗尽 + 复工绝对时刻」，别让脚本靠 `while` 重试去发现。
- 清场别用 `pkill -f <脚本名>` —— 它匹配到的是**自己这条 shell 的命令行**，会把自己一起杀掉（`exit -15`，看起来像命令超时）。
  用 `ps -eo pid,cmd | grep <脚本名> | grep -v grep | awk '{print $1}' | while read p; do kill -9 $p; done`。
