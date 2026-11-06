# 单端点 RPC：方法表预言机 与 闸门顺序→可达性

适用形态：**整站只有一个 API 端点**（`/api.php`、`/api.html`、`/rpc`），业务动作全靠一个 `method=<名>` 参数分发，请求体常是「加密信封 + MD5 签名」（见 `encrypted-envelope-api-reversal.md`）。此时路径爆破、方法名字典爆破全部无效，攻击面的唯一开关就是**方法名**。

## 1) 方法表：词汇表喷服务端（覆盖面 > grep > 字典）
方法名在前端只是**字符串参数**，调用点常被加密包装吞掉 → `grep method:"..."` 拿不全。做法：
1. 从 bundle 抽全部小写标识符：`sorted(set(re.findall(r"[a-z][a-z0-9_]{2,}", src)))`（本例 11210 条）
2. 先打一个**假方法名**（`zzz_noexist`）校准「不存在」的响应形状
3. 逐条喷分发端点，按文案二分读数（8~16 并发；直连 0.03s/发）

预言机语义（实测）：
- `method 参数错误` → 后端无此方法（**与假方法名逐字相同**才是判据）
- `<name> 参数缺失或无效` → **真方法**，且直接吐出下一个必填参数名
- `操作太频繁` → 真方法且命中限速，换时序重试

实测数据：11210 候选 → **46 个真方法**；盲打字典 255 候选 **零命中**。本族 9 个隐藏方法（`walletoperat`/`updatetask`/`chekinjoin`/`usersign`/`msgup`/`msglistoff`/`getwallet`/`depositslist`/`setmyplayset`）全部由词汇表喷挖出。

## 2) 前端超前 = 假攻击面
`upflie`（上传）在前端有完整调用点（`FormData` + 加密 `data` 部件 + `h.append("image", file)`），后端回**与假方法逐字相同**的 `method 参数错误` ⇒ 前端版本 > 后端，后端根本没实现。
**任何「前端有调用点 = 该接口存在」的推断，必须先做假方法同形对照**，否则会把「后端未实现」误报成「无鉴权任意上传」。

## 3) 参数链矿工（一个循环挖干净写接口）
拿真方法后逐字段循环，服务端文案会给出**下一个缺失参数**：
- `postwithdrawal`（提现）→ `amount` → `withpassword` → 余额闸
- `walletoperat`（钱包操作/调账）→ `supplier`（`EVO` 为真供应商）→ `btype`（1/2 有效）→ 余额闸
- `receivetask`（领奖）→ `taskid` → `receivecode`（服务端真校验，空串不吃）
- `getgameurl`（游戏启动）→ `supplier`（`PG`/`CQ9` 等 10 家）→ 每次下发**全新** launch token
- `chekinjoin`（校验已加群）/ `ceakertaskqd`（校验 TG 个性签名）/ `updatetask`（提交任务）
- 负面结论同样要落纸：负数/零金额提现全被 `参数 amount 不完整` 拒（印钞路死）；提现密码一旦设置，再改**必须带旧密码**（曾疑的「任意会话重置提现密码」= 非漏洞）；`tid` 参数被服务端忽略（任意 tid 同响应）⇒ 不能靠改 tid 越权领奖。

## 4) 闸门顺序 → 可达性（判死前先证明可达）
`postwithdrawal` 的 `qrcode` 是**服务端可选拉取的 URL**（理论 SSRF / 打款运营端存储型 XSS）。实测：余额=0 时永远先回 `余额不足！`，**URL 处理排在余额闸之后** ⇒ 带外请求仓 0 命中、`http://10.255.255.1/` 与可达 URL 耗时一致（均 0.18s）。
结论写法：**「面存在、当前账户状态不可达」**，补足余额后复测；**不可达 ≠ 不存在**。任何「先闸后处理」的注入面都按这个句式写。

## 5) 带外验证：公共请求仓（SSRF/OOB 首选）
```
POST https://webhook.site/token                     -> {"uuid": "<uuid>"}
payload = https://webhook.site/<uuid>               # 注入待测 URL 参数
GET  https://webhook.site/token/<uuid>/requests?sorting=newest
```
命中即 **SSRF 实证**，且回包里的来源 IP = **服务端出口 IP**（顺带溯源）。零副作用、可重复。
无回显时先备**时序盲测**：同一参数依次注入 ①不可路由 `http://10.255.255.1/`（会撞连接超时）②已关闭端口 ③正常可达 URL，比响应耗时；三者一致 = 服务端没去取，别写「疑似 SSRF」。

## 6) multipart 指纹：requests 被吞、curl 能过
反直觉症状：同端点**不带文件**解析正常，**一挂文件部件**就报「`data` 参数缺失」（整段 multipart 被上游 WAF 丢掉）；`curl -F` 打同样字段完整送达。含文件类请求（上传/投稿/凭证照片）**一律先换 curl** 再下判定。
另：上传体里含 `.php` 等脚本后缀直接吃 `网站防火墙` 403（内容检测在业务逻辑之前）。

## 7) 用例：TG 钱包白标家族
`@tmqb` / `@okpay` / `@timi` / `@tmyx` / `@TiMiPGBot` 同一后端，品牌 Qzino；游戏站 `timi.nimingkj.com` 用「AES-CBC + MD5 签名」信封（密钥硬编码在包内 `[REDACTED]`）。同族新目标直接复用「词汇表 → 方法表 → 参数链」三步，再**比对方法清单差集**找新增面。
