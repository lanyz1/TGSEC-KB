---
name: web-error-oracles
description: "框架/登录错误信息泄露做参数逆向与账号枚举"
version: 1.0.0
tags: [web, api-recon, auth-enum, thinkphp, error-oracle, lockout, captcha]
---

# Web 错误信息 Oracle（API 逆向 / 认证枚举）

利用框架与应用返回的**差异化错误信息**做渗透——逆向 API 参数、枚举账号、判断锁定边界。核心原则：同一接口对"缺参/错参/错账号/错密码/锁平台"返回不同 message，每个差异都是一个 oracle。先记 message + code + file/line，再下结论；错误信息本身就是最大的信息源。

## Always-on 规则

- **不要假阳性漏洞**：组件/CVE/版本命中 ≠ 可利用漏洞。只有 exploit 真能跑通拿权限/拖数据才算 VALIDATED；理论漏洞（反序列化无 session/cookie 入口、文件包含无 lang 参数、SQL 注入参数化、越权改 role_id 需 admin）标 REJECTED，不进高危报告。用户只要能打的路径，不要"理论上存在"的漏洞清单。
- 每个错误差异先记 message + code + file/line，再析响应；别凭记忆判参数字段名。

## 框架缺参报错 = 免费参数链逆向

- **ThinkPHP 6 debug 开启**：未传参数报 `Undefined index: <field>` + `file`(绝对路径) + `line` + `exception`。逐个补齐字段即可逆向完整 API 参数（一次实战从 type→user_id→order_amount→…→order_remarks 逆向出 14 个参数）。报错里的绝对路径还泄露框架路径与版本。
- **FastAPI Pydantic 422**：空 `{}` 或错类型字段触发 422，泄露字段名/类型/约束/嵌套（同一类技术）。
- **Java/Spring Bean Validation 缺参报错**：提交空 `{}` 或只填部分字段，后端返回 `{字段路径_约束}` 形式的 i18n 消息 key——`{}` 包裹的字符串本身就是 Bean 字段路径 + 约束后缀，一次请求逆向出完整嵌套结构。如支付商户后台登录返回 `{merchant.user.password_require}`、`{merchant.User.AccountNo_Not_blank}`、`{merchant.merchantId.require}`，直接读出字段 `merchant.user.password`、`merchant.User.AccountNo`、`merchant.merchantId` 与约束（`require`=@NotNull、`Not_blank`=@NotBlank）。**路径大小写是字段真实大小写**（`user` vs `User` 并存），补字段时照抄不归一化。填满必填字段后错误才从「缺参」切换到业务错误（如统一 `"Please check"`）。
- **Spring Boot `@RequestParam` 缺参报错**：必填参数缺失时返回 `{"status":400,"error":"Bad Request","message":"Required Integer parameter 'usdtType' is not present","path":"/api/addCashAccount"}`——**逐个暴露参数名 + 类型**（Integer/String）。补一个参数就报下一个缺的（`usdtType`→`cashPassword`→`type`→`verifyCode`…），一轮循环逆向出完整参数链，无需前端 JS。报错里的 `path` 字段同时确认端点真实存在（不存在的端点返回 403/520，而非这种 Spring 缺参报错），所以 400 缺参本身 = 端点存在 + 参数名 + 类型三重 oracle。
- **参数化 vs 可注入的判别**：单引号 `'` 若被当作普通字符（返回业务错误而非 SQL 错误）→ 参数化查询，放弃注入，转其他攻击面。

## 登录错误三态枚举 oracle

登录接口对三种状态返回不同错误，精确枚举账号：
- `用户不存在` → 账号不存在
- `密码不正确` / `密码错误` → 账号存在，密码错
- `账户与平台不匹配` → 账号存在但属于另一平台/租户（多后端账号体系隔离）
- **单码反枚举（退化态）**：接口不区分「账号不存在/密码错误」时统一返一个业务码（如 `"Please check"`），三态枚举失效、账号存在性不可判，但缺参报错仍可逆向 schema（见上节 Bean Validation）。2FA 字段（googleCode/TOTP 6 位码）通常在账号密码校验**之后**才校验——空值 vs 任意 6 位数字响应无差异，证明先验账号密码；别在 2FA 绕过上浪费时间，除非先拿到正确账号密码。

用"密码不正确"作为账号存在性判据，枚举账号名（含中文名/数字/拼音/平台名变体，如 qixinpay 的 admin 账号 `qixin`）。**账号锁定态也是存在性 oracle：** 当接口不区分「账号不存在」和「密码错误」（统一返同一码，如 EIMS 门户 402），但区分「账号锁定」（603）时，用锁定态枚举——先发随机账号确认「不存在」基线（402），再枚举账号名，返回锁定码（603）的即账号存在。注意锁定码也可能被参数异常触发（timestamp 负数/0、sign 空/数组），枚举必须用正确签名格式，否则误判。

## 零鉴权写接口的唯一性校验 = 读不到的数据集也能枚举

一个本该「写」的接口若对某字段做**唯一性校验**（已存在就报错），它同时就是一个**存在性 oracle** —— 即使该接口零鉴权，也能拿来枚举你读不到的真实数据。

- **实测形态**：某零鉴权 `POST /user/info/edit`（真写库），`name=<值>` 返回 `编辑成功`（=库里没有）或 `真实姓名已注册`（=库里有）⇒ 用一个写接口枚举出全平台已绑定的真实姓名。同类还有 `/user/bank/delete?id=N` 这类零鉴权写接口。
- **两个信号一起用**：① 成功/失败文案成对，且失败侧语义指向「已存在」；② **响应耗时差异**（实测 0.3s 写成功 vs 0.02s 唯一键冲突早退）—— **时序是第二个 oracle**，文案被统一时改看时序。
- **枚举前先摸「校验顺序」**：多字段接口按固定顺序短路校验，**前面的检查不过就永远看不到后面的 oracle**（实测：用户名格式校验先于邀请码校验，用户名太短时恒返格式错误 ⇒ 会把「没命中」误判成「码不存在」）。**先用合法最小输入把前置条件喂饱、看到目标文案，再开跑枚举**。
- **语义差异就是判据，别只看 code**：`该邀请码不存在` = 无效，**其它任何文案 = 命中**。开跑前先把「无效基线和命中基线」各打一次固化下来。
- **报错回显输入 = 免费 oracle**：错误里带上你的请求值（如 `非法的请求IP:<你的IP>`）时，**别人工读，让脚本按「回显是否等于预期」自动判**，横扫几百种 header/参数变体（实测靠这个一次排掉 80 种 IP 头）。
- **碰到这类 oracle 先冷静看配额**：枚举值空间大（手机号/真实姓名）且目标有 CC/WAF 时，**几百次就可能封 IP**；先估「值空间 ÷ 实测可靠速率」再决定要不要跑，别拿自己的出口 IP 烤（拿不到可靠速率就别开）。

## 账号级 vs IP 级锁定（XFF 绕过的边界）

- **IP 级锁定**（"IP is locked"）：key 在源 IP → `X-Forwarded-For`/`X-Real-IP` 随机换头即可绕过，无限爆破。**但锁定的 key 头不一定是 XFF/X-Real-IP：** 逐个试 `CF-Connecting-IP`（Cloudflare 回源头）、`True-Client-IP`、`X-Client-IP`、`X-Originating-IP`。实测 EIMS 门户锁定只信任 `CF-Connecting-IP`（XFF/X-Real-IP/True-Client-IP/X-Client-IP 全无效仍 480，仅 CF-Connecting-IP 生效 480→402）。**真实 IP 轮换（动态旋转代理池）是独立的一层**，与 header 伪造叠加双保险：header 伪造绕过「服务端读错 IP」，代理池绕过「真实源 IP 被锁」。
- **账号级锁定**（"密码错误次数过多，请1小时后再试"）：key 在账号 → XFF 无效，只能等解锁或换账号。
- 先测锁定类型再定爆破策略：账号级锁定时，一次只投 3-4 个高价值密码，避免 5 次错误触发 1 小时锁定。

## 验证码 token 一次性

登录验证码 token 用一次就失效（复用返回"图形验证码已失效"）。爆破必须每轮重新拉验证码 + OCR，不能缓存 token。OCR/验证码失败不计入密码错误次数（只有"密码不正确"才累计锁定），所以验证码错可以安全重试。