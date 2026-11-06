---
name: api-param-name-discovery
description: "未知 API 参数发现：错误驱动探测（参数名反推）+ JS chunk 挖掘（bundle 参数名/类型提取）。触发：API 参数未知/文档缺失/需要逆向参数结构。"
tags: [参数未知, 乱试, 报错, 参数名, 字段名, 参数反推]
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]

---
# API 参数名逆向: 报错驱动爆破 + 前端 chunk 挖参

## 触发场景
- 接口报 `xxx.notBlank` / "Can Not Be Blank" / "Invalid parameter format", 但不知道正确字段名
- 前端表单构造代码在未下载的弹窗/页面 chunk 里, 已有 chunks/ 目录 grep 不到
- 已知端点(从 entry.js 的 API 清单拿到)但参数名反直觉, 瞎猜浪费时间

## 核心技术 1: 报错驱动参数名爆破(核心教训)
服务端对 DTO 的校验错误消息**泄露字段名语义**, 但有两个坑:

1. **主/确认字段都缺失时, 错误消息随机返回**(同一请求两种缺失, 返回哪个看 Map 迭代序)。
 实测: 单发 `{code:X}` → `confirm.notBlank`; 单发 `{newCode:X}` → "Withdrawal Code Can Not Be Blank" — 单发探测结果全是误导, 无法判断主字段是否绑定。
2. **正确姿势(两阶段)**:
 - 阶段A 探确认字段: 逐个候选名单发, 看哪个触发 `confirm` 类错误(说明主字段已绑定、只差确认字段)或先试常见名 `confirm`。
 - 阶段B 固定确认字段, 只换主字段候选名, 每次带两个值:
 - `{"<candidate>": "Test1234", "confirm": "123456"}` → 报 "Password Format Error" / 格式错 = **绑定成功**
 - `{"<candidate>": "Test1234", "confirm": "99999999"}` → 报 "mismatch" = **绑定成功**
 - 报 "Can Not Be Blank" = 没绑上, 换下一个候选
3. 候选词表: `code, newCode, withdrawalCode, newWithdrawalCode, withdrawCode, password, newPassword, verifyCode, authCode, oldCode, confirmCode, <field>Password, <field>Code...` — 命中的往往是最反直觉的那个(如 msg389 提现密码 = `newWithdrawalCode` + `confirm`)。
4. 本库无 Hermes `scripts/param_probe.py`。按本卡候选名用 curl 逐个 POST；授权 API 也可走 `authz-probe`。

## 核心技术 2: 前端 chunk 补抓(已有 chunks/ 不全时)
- Nuxt/Vite 应用: entry.js 路由段直接给出页面→chunk 映射:
 `name:"profile-wallet-add-wallet", path:"/profile/wallet/add-wallet", component:()=>p(()=>import("./chunks/index-index-CHMAGC40.js")...)`
 → 直接 `curl https://<site>/_nuxt/chunks/index-index-CHMAGC40.js` 补抓, 不用整站爬。
- 表单构造代码特征: `new FormData` + `Object.keys(t).map(s=>(s!==void 0&&r.append(s,t[s])))` 的 API 包装 = **multipart 端点**;直接传对象 = JSON 端点。
- **minified 单行 JS 陷阱**: search_files/ripgrep 默认行模式对超长行会 0 命中或截断 → 用 `rg -o '.{0,80}<pattern>.{0,200}' file` 提取上下文;python `re.finditer` 也一样可靠。
- 找 API 方法调用方: 先 grep entry.js 里的方法定义(如 `addWallet(t,n={})`), 再 `rg -o '.{0,100}\.addWallet\(.{0,200}' chunks/*.js` 找调用点拿实参;调用方可能在未下载 chunk, 回到补抓。

## 辅助技巧
- 令牌失效/账号被锁(登录错 15/20 次): 白标博彩一般注册即返回 token, 直接注册新号, 不必过登录滑块。
- 枚举/配置端点(`*-enum/get`, `chain-type/get`, `bank/get{currency}`, `kyc-config/*`)能拿到字段枚举值(int/字符串)、必填项和字段名, 先拉再猜。
- 绑定/设置的"内容字段名"以 `*-user-info/get` 返回的 content dict 为准, 比猜表单快。
- KYC/绑定类端点常是 multipart(含文件字段), 用 `multipart/form-data` 而非 JSON, 否则报 "Missing Servlet Request Parameter" / Type Mismatch。

## 实战记录
- msg389.com(dingyi 白标)提现密码/钱包绑定/KYC 参数全记录: 个案附件未入库（原 references/msg389-wallet-kyc-params.md）

## 交付
- 参数模板 + 每个接口的成功/失败响应贴进战报;证据落 `evidence/<date>-<target>/`。

## 真源

- 手法：`docs/playbooks/业务API未授权与越权手法.md`
- 工具：`python3 tools/ops/api_dispatcher_enum.py --help`

## 2026-10 情报批增量（Dev 常用参数名四表 · @n0aziXss）

- 状态/权限：`debug=true` `test=1` `admin=1` `isAdmin=true` `isPremium=true` `superuser=1` `role=user→admin` `uid=42` `userid=42` `account=42` `profile=42` `ref=partner→internal` `partnerId=1`
- 环境/开关：`stage=dev` `draft=1` `mode=live→test` `settings=default→debug` `config=prod→dev` `preview=true` `env=production→staging` `reportId=999` `documentId=999`
- 缓存/格式：`beta=1` `roleId=1` `rank=1` `step=1` `origin=trusted` `nocache=1` `source=external→internal` `cache=0` `format=json→xml/yaml/php` `output=pdf→json/txt`
- 跳转：`affiliate=evil` `redirect=/dashboard` `redir=/home` `url=evil.com` `next=/secret` `returnUrl=evil.com` `callback=attacker.com` `continue=/admin` `dest=evil.com`
- （2026-02 系列；收口：XSS `inurl:q=|s=|search=`、SQLi `inurl:id=|pid=|category=|action=`）


---

## 外部库增量（2026-10-11 分享包）

## 核心技术 3: 门禁前置型接口的绑定层 oracle(免过门禁探参数)

很多接口在业务逻辑前挂了门禁(图形验证码 / 一次性 token / 未登录校验)。**门禁不改变绑定层的位置**:
Go-Gin `ShouldBindJSON`、Java `@Valid`、NestJS class-validator 都在 handler 之前跑 ⇒
**绑定层错误不用过门禁就能看到**,据此零成本反推字段名/类型/必填。

按出现时机把响应文案分三层(靠文案分类,不靠猜):

| 文案 | 层 | 说明 |
|---|---|---|
| `xxx.notBlank` / 格式错 / `请认真填写` | 绑定层 | 字段名/类型/必填不符 → **未过门禁也能探** |
| `验证码错误` / `token 无效` / 未登录 | 门禁层 | 结构已对、被门禁挡 → 字段名猜对了 |
| `已领取` / `暂未开放` / 业务限制 | 业务层 | **已过墙**,是业务结论 |

判据(同一 client、同一端点连发,别混 UA/会话):
- **字段名**: 候选名逐个换,只有「绑定层报错 ↔ 门禁层报错」的**切换**才算命中(如 `account` 对 / `username` 错)。
- **类型**: 同一字段发 `101`(整型) 与 `"101"`(字符串) → 类型不符会落到绑定层。
- **必填**: 逐个删字段,收集触发绑定错的最小集合。

**假阳性防线**(写报告前必查):
- 空值被「必填」拒 = 绑定层在工作,**不是**空值绕过;只有进业务层才算绕过。
- 门禁文案先取基线: `验证码不存在`/`验证码已失效` 与 `验证码错误` 若可区分,那是 **id 空间 oracle**(可枚举/可预测),不是「字段名对了」。
- 分类器顺序敏感: 同一响应同时含门禁词与格式词时按最具体的一条判,别用「含关键词即命中」的粗暴写法。
  参考实现 + 单测: `tools/ops/ginvue_admin_probe.py::classify_reward_response` · `tests/unit/test_ginvue_captcha_wall.py`。

工具: `python3 tools/ops/ginvue_admin_probe.py captcha-probe --base <URL> --case <案卷>` 自动出 `binder_before_captcha` 判据。

## 核心技术 4: 传输载体必须先定 —— 载体错 = 恒定假阴性(能骗过整轮探测)

字段「读没读到」由**载体**决定,与字段名无关。**任何字段名/存在性探测之前,先从调用点确认载体**:
- vue-resource `$http.post(url, body, {emulateJSON:true})` ⇒ **form-urlencoded**(不是 JSON);无该选项 ⇒ JSON(vue-resource 默认 JSON)。
- axios 默认 JSON;传 `URLSearchParams`/`qs.stringify` ⇒ form;原生 fetch 传 `URLSearchParams` ⇒ form。
- jQuery `$.post(url, obj)` ⇒ form;`$.ajax({contentType:"application/json"})` ⇒ JSON。

**实测教训(2026-09 xcoin/PF 白标 `/pfv3/resetLoginPwd`)**:用 JSON 发,则**每个载荷**——正确用户名、类型错(数字/数组/对象)、缺字段、换参名——**全部恒回同一句 `username_not_exist`**。连续 4 个脚本据此写下「该字段非登录用户名、存在性 oracle 不可用、IDOR 阴性」的错误结论。
改用 form-urlencoded 后同名立刻回 `otp_wrong` ⇒ 用户真实存在、oracle 成立、前 4 轮结论全部撤回。

⇒ 铁律:**同一端点先用 form / json / query 三种载体各发一次**;响应有差异才进入字段级探测,响应完全相同则先怀疑载体。
⇒ 反证信号:「所有载荷文案完全一致」不是「服务端不读该字段」的证据,而是**载体/参数位置不对**的第一嫌疑。
⇒ 同族坑:multipart 端点用 JSON 发 ⇒ 报 `Missing Servlet Request Parameter` / Type Mismatch(见下「辅助技巧」末条)。
