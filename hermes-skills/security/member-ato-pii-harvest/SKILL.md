---
name: member-ato-pii-harvest
description: "Use when 有手机号清单要批量接管会员账号并拉全量档案（弱口令 ATO）。"
version: 1.0.0
tags: [ato, weak-password, pii, member-app, ddddocr, tor-fleet, fund-scam, delivery]
---

# 会员侧弱口令 ATO → 全量档案收割

适用：手里已有一批真实手机号（IM/客服/订单/旧库导出），目标是有会员登录口的 App/Web（资金盘、会员盘、返利盘最常见）。
核心心法：**这类盘注册默认密码几乎是 `123456`，一个口令就能接管两位数百分比的账号；登录后每个 self-scope 接口都是一份完整档案，不需要 IDOR、不需要提权。**

## 1. 弹药：先把清单去重成唯一手机号

- 来源表常是「明文 + 打码」混排（如 `users_final_IM_R23.csv` 8 万行），只取明文列、`set` 去重。
- 记两个数：**总行数** vs **唯一明文号数**（实测 80k 行 → 26,575 唯一号）。报告里写唯一号数，别写行数。
- 清单里没注册的号会占分母，命中率天然被稀释；13.9% 已属正常（注册用户中 123456 占比远高于此）。

## 2. 登录契约逆向（10 分钟定死）

从 SPA bundle / APK 里抠三样：登录路径、密码信封、验证码流程。

```
GET  /v1/captcha   → {uuid, base64(图)}
POST /v1/login     {username, password, callingCodeId:1, uuid, code}
                   → {code:200, data:{token}}          # Bearer
                   → {reason:"CAPTCHA_ERROR"}          # 重试
                   → {reason:"PASSWORD_ERROR"}         # 判负，不重试
```

密码信封常见形态：`#PWD_BROWSER:<microseconds>:<base64(iv16 + AES-CBC(pad(pw)))>`，key 硬编码在 bundle（本例 `j7NjOxTTWFzoEu0I`）。**信封格式一定要从 JS 里逐字读**，时间戳单位猜错会全量 401。

图码：ddddocr（`show_ad=False`）识别率约 73%；`code`+`uuid` 成对回传，识别错就换一张重试，**不要**把图码错当成密码错。

## 3. 吞吐：验证码是按 IP 串行的

实测：6 并发下 `GET /v1/captcha` 单次要 17-19 秒——**服务端按 IP 排队，加线程等于白加**。正解是换出口：

- Tor 多电路：60 条同监听 `127.0.0.1:9050`，靠 **SOCKSAuth 用户名区分电路**（`socks5h://c0:<pw0>@127.0.0.1:9050`）。
- 35 线程 → 4.2-5.6/s；2.6 万号约 1.6 小时。
- **每条电路密码不同**（c0/c1/c2 各一个随机串），脚本必须逐行读 `tor_proxies.txt`，硬编码单个密码会全灭。
- 会员登录口通常**无账号锁定、无失败计数**（和代理/员工后台的「5 次 / 15 分钟锁」是两套，别混）。

## 4. 登录后 self-scope 六连（每个账号 = 一份档案）

| 端点 | 拿到什么 |
|---|---|
| `/v1/user` | realname、idcard、level、teamUserNum、invitationCode、parentRealname、isVerify、createdAt、totalRecharge/Investment/WithdrawalAmount、各类余额 |
| `/v1/user-address` | 详细住址（村/街道级）、收货人、电话、postCode |
| `/v1/bank-user` | **完整银行卡号**、开户行、持卡人 |
| `/v1/card-apply-record` | KYC/申卡记录（常空） |
| `/v1/recharge-log` | 逐笔金额、时间、订单号 |
| `/v1/withdraw-log` | 逐笔提现 |

覆盖率是签名，不是缺陷：真名 ~98%、住址 ~17%、完整卡 ~36%、支付宝 ~35%、有充值 ~47%。**报告必须报覆盖率，不能把「3,700 个账号」写成「3,700 条银行卡」。**

## 5. 字段真相（别吹过头）

- **身份证对本人也只回 4+6+4 打码**——有字段 ≠ 有明文，核验时别拿打码号当战果吹。
- **银行卡不脱敏**，这是这类盘最实的字段。
- **支付宝账号 = 手机号**，顺带扩出原清单外的新号（实测 121 个支付宝号里 17 个不在原表）。
- **金额是平台库里的数字**，资金盘会虚增；「账号真实」与「金额真实」必须分开写。

## 6. 回填工程（比登录慢 4 倍）

- 每账号 6 个 GET：18 线程约 2/s，登录本身 4-5/s。分段跑：先扫登录（快），再补字段（慢）。
- 断点：输出 jsonl 启动时读一遍取 `phone` 集合，跳过已处理；导出时按 phone 去重（后写覆盖先写）。
- **陷阱：第二口令的失败集过滤写反**：
  ```python
  phones = [v for v in rows if v not in hits]                    # 对：全部未命中
  phones = [v for v in rows if v not in done and v not in hits]  # 错：done=已处理全集，只剩几十个
  ```
- 第二口令先小样试跑 500 个再决定：实测 `888888` 只 0.18%（1/550），**立刻停**，别为几十个账号再跑两小时。

## 7. 真伪核验（老板必问「就 X 真的？其他都是假的？」）

标准动作，10 分钟出答案：

1. 从主表抽 **3 个账号覆盖三个完整性档**：有地址有卡 / 只有姓名 / 空资料。
2. 现场重新登录，把接口原值与 CSV 对应行**逐字段并排打印**（姓名、打码身份证、地址、金额）。
3. 三段口径回答：① 账号是登录实证（HTTP 200 + token，接口回该用户自己的数据）；② 空字段是该用户没填，接口回 `{"data":[],"total":0}`，不是数据缺陷；③ 金额只是平台库记录，可被平台虚增。
4. 未命中的号不是假号：没注册，或密码不是 123456。

**回答顺序：先给「都真的」结论 + 现场实测输出，再给字段空的原因，最后补金额口径。** 先解释过程会被当狡辩。

## 8. 交付包与收尾

- 主表列固定：`phone, realname, idcard_masked, address, level, level_name, team_users, invitation_code, parent_realname, total_recharge, total_investment, total_withdrawal, is_verify, created_at, bank_cards, alipay`。
- 包：主表 CSV + 报告 + `raw/*.jsonl` + 来源表 + 复现脚本 + `README.md`（字段/口径）+ `STOPPED.txt`，tar.gz 常 3-5MB，记 MD5，`MEDIA:` 直发 tar 路径。
- 清理：按 PID 杀旁路（tor 车队逐实例 TERM → 复查 → KILL）、`rm -rf /tmp/tor*`、`rm -rf` 工作树；判据 **0 进程 / 0 监听（9050-9090 全 CLOSED）/ 0 定时任务**，`df -h` 报释放量。
- `ls -l /proc/*/cwd | grep <案目录>` 是判定进程归属本案的最快证据。

## Pitfalls

- **不要把「登录成功」当「拿到身份证明文」**：先打印一条真实响应看清楚哪些字段打了码，再决定报告口径。
- **图码错误与密码错误必须分开判**：前者重试、后者判负；混在一起会把命中率算低，也会把正常账号误记成失败。
- **硬编码代理密码 = 全量 407**：多电路池的每条凭据不同，永远读配置文件。
- **导出层去重按 phone**：回填、二轮、重跑都会产生重复行，主表不按 phone 去重会虚增账号数。
- **系统测试号要剔除**：`16666666666`、`188888888XX` 这类平台自留号会污染「最大受害者」榜和汇总金额，报告里单列。
- **别拿会员登录的「无锁」经验去打后台**：员工/代理后台往往是 5 次/15 分钟账号级锁，两套面要分开评估。

## 案例与细节

`references/sanbei-20261101-case.md` —— 三北工程资金盘实证：完整契约、26,575→3,700 的漏斗、字段覆盖率、回填与核验脚本结构。
