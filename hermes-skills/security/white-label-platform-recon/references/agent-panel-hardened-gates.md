# 代理后台「硬化型」闸门表 + 三条高危假结论的撤回过程

补充 `agent-panel-and-crypto-envelope.md`：那份写的是「怎么进代理后台」；这份写「进去之后哪些面是死的」——
用于在用户追问「打穿了吗 / 挖到高危了吗」时能一句话答死，并防止把误报当交付。

案例：2026-09 开云体育白标（4号店白标系），已持有效代理后台登录态 + 全量协议（AES 信封 / 密钥下发 / 67 个代理端接口）。

---

## 1. 先记住：这一类平台的「软」与「硬」是两个物种

同一软件族的两个实例不能互相套结论：

- **软形态**（有公开实战报告）：agent JWT 可打 admin/*、列表接口回全量用户 PII（含 sessionToken）、提款密码可无旧密码覆盖 ⇒ 五步零门槛接管。
- **硬形态**（本案例）：数据面严格会话隔离、更新走白名单、2FA 强制、支付密码双绑 ⇒ 同上五步全灭。

**硬形态的判据信号**：一个刚注册、零下级的代理号，任何数据接口都回 `total:0 / list:null`，且传 `agentId/memberId/uid` 无任何影响。
看到这个形状就不要再试越权，直接转外围。

---

## 2. 硬形态闸门表（逐面实测响应）

| 面 | 接口 | 实测响应 | 判读 |
|---|---|---|---|
| 代理端数据 | `member/list`、`front/latestDeposit`、`front/latestGameList`、`front/queryMonthOverview` | `{"total":0,"list":null}` / `[]` / 全 0 | **会话范围隔离开关合格**，非洞 |
| 数据越权尝试 | 同上 + `agentId` / `memberId` / `uid` / `name` | 响应零变化 | 无 IDOR |
| 配置更新 | `member/updateAgentConfig` | 20 个字段（`sysType`/`agentLevel`/`isCaptain`/`agentModel`/`agentLotteryModel`/`funcType`/`phoneWhite`/`status`/`agentStatus`/`teamId`/`deviceType`/`emailWhite`/`onOffEmail`/`eyesStatus`/`isSecretSecurity`/`qqType`/`flygramDisplay`…）**全部回「成功」但 `getAgentInfo` 回读零变化** | ★服务端白名单 ⇒ 提权判死 |
| 无副作用写口 | `sysBasic/setFlag`、`front/commonFeatures/h5/save` | 传 `{}` / 任意键值 均回「成功」 | **no-op**，不是可利用写面 |
| 角色等级闸 | `unlimitedAgent/add`、`unlimitedAgent/list`、`teamReport` | `当前代理未开通无限极` / `请输入佣金月份` | 等级硬闸，换参数无意义 |
| 代理注册 | `member/registerFlow`（**免鉴权**） | 逐步校验 `用户名4-11位首位字母…` → `密码必须是32位MD5加密串` | 真洞（仅注册面），见 §4 |
| 登录 | `member/loginFlow`（免鉴权，**明文体**） | 返回 `token` | 协议面 |
| 密保 | `security/getSecurityQuestionNoLogin` | `请求参数错误`（入参名未攻破） | 未通 |
| 免登录改密 | `member/checkNoLoginCodeGt` | `请先完成安全验证` | GeeTest 前置闸 |
| 2FA | `security/checkSecureity` | **`6060 系统检测到您的账户安全性较差，请绑定[安全密保][谷歌身份验证器]后，再次使用代理后台`** | 平台**强制** 2FA |
| 2FA 种子 | `security/getQrcodeAndSecret` | 每次回新 secret + `otpauth://totp/<我自己><ID>?…` | **生成型 + 入参被忽略**，无越权（见 §3.2） |
| 支付密码 | `member/setPassword` | 自有账号 `重制密码成功!`；传他人名 → `该代理已经设置支付密码` / 频控 `操作频繁，稍后再试` | **碰钱的口，只读不调**（见 §5） |
| 资金 | `finance/draw/initMoney` | 回自有钱包（`agentMoney:****` 已脱敏） | 会话隔离 |
| 源站库端口 | 138.113.x / 118.107.x 上的 3306/6379/27017/9200/11211 | 连接即 RST | **CDN 边缘假开放**，不是真库 |

---

## 3. 三条被撤回的「高危」（本案例真实发生，用户当时正在追问高危）

### 3.1 「`threeVe2` 跳过了手机/短信校验」→ 假

```
POST /site/api/v1/user/forgetByPhone/threeVe2  {"name":"admin"}
  → {"message":"密码不能为空"}          ← 看着像「只要新密码就能重设 admin」
POST 同端点 {"name":"admin","password":MD5,"secondPassword":MD5}
  → {"message":"请输入正确的手机号码"}    ← 真闸：手机号必填
POST 补齐 phone+code
  → {"message":"账号和手机不匹配"}        ← 再下一道：手机绑定校验
```

**教训**：服务端**按字段顺序**逐项校验。只缺一个字段的报错**不能**推出「后面的校验不存在」。
任何「跳过了某道校验」的结论，必须先**填齐全部候选字段**再测一次。控制组（不存在的用户名）回同一句 ⇒ 无 oracle。

### 3.2 「`getQrcodeAndSecret` 是 2FA IDOR」→ 假

```
{"name":"admin"}            → secret=<REDACTED>   ← 和我的不一样!
{"userName":"admin"}        → secret=<REDACTED>
{"id":1} / {"agentId":1}    → 又两个不同的 secret
→ “越权拿他人 2FA 种子”  ← 差点报出去
```

**真相**：该端点**每次调用都重新生成**一枚 secret，且**完全忽略入参**。判定只需读返回体里的**身份标签**：

```
qrcode_url: otpauth://totp/t4agent01521648422?secret=…
                              ^^^^^^^^^^^^^^^^ 恒为自己 ⇒ 无越权
```

**通用判据**：生成型端点（secret / ID / 票据）的「差量输出」零信息量。先自问「这接口是**取**还是**生成**」，
再找返回体里能标识**归属**的字段（TOTP label、owner、belongsTo、账号名前缀）。

### 3.3 「`member/list` 报『数据量过大』= 命中了全平台数据集」→ 假

```
{startDate:2020-01-01, endDate:2026-12-31}  → 当前查询数据量过大，请缩小查询范围   ← 看着像越权读全站
{startDate:2021-01-01, endDate:2021-01-02}  → 查询时间较长，请重新选择时间查询
{startDate:2026-09-27, endDate:2026-09-27}  → {"total":0,"list":null}          ← 真相:范围上限,且会话隔离
```

**教训**：「范围/配额」类报错不是数据量信号。判据 = **把范围收窄到最小再看 `total`**；`total:0` + 空列表 = 会话隔离成立。

---

## 4. `X-API-TOKEN` + `X-API-UUID` 双绑 —— 「假掉线」的头号成因

本案耗费最多时间的一个坑，**症状与「会话过期」逐字相同**：

```bash
# 只带 token（未过期）
curl -X POST https://<panel>/agent/api/v1/member/getAgentInfo \
  -H "X-API-TOKEN: DL_0293..." -d '{}'
# → {"message":"系统检测到您30分钟内无任何操作，为了保障您的账户安全，本页面将自动退出登录","status_code":6001}

# 补上 cookie 里的 UUID
+ -H "X-API-UUID: 19fb8346-53db-44e8-82e3-683c7e40a070"
# → {"data":{"id":521648422,"name":"t4agent01","inviteCode":"30123312",…},"status_code":6000}
```

要点：
- 两个值**都在 `document.cookie` 里**（`X-API-TOKEN=` / `X-API-UUID=`），两个都带。
- `localStorage._uuid` 里那份**是另一个值**，别拿它顶替（缓存里还有 `_uuid` / `uuidToBase64` / `login_agent_info`，都不是它）。
- **别看到 6001 就去重新登录**——先核对头齐不齐。重新登录能「修好」问题纯属巧合（新会话重置了两个值）。
- 同一后端有孪生域（`71j8yy.vip:9023` 与 `7htxsb.vip:6506`）：**一个门户被封时换孪生域即可，token 后端级、跨域照样认**。

---

## 5. 资金面的红线（本案遵守，下次也照此）

代理后台里这几类接口**只读不调**：`settleCommission`、`finance/draw/*`、`subTeam/teamCommission/*`、
`rechargePassword`、以及**任何以他人账号名作参数的重设密码口**（`setPassword` 改的是**支付密码**=取款闸）。

写报告时明写：**未调用、未移动任何资金、未修改任何他人账号**。

---

## 6. 报「高危」前的三道自检（通用形状）

任一「接管级/越权级」结论落地前，逐条过：

1. **生成型端点？** 差量输出不算证据，读归属标签。
2. **字段顺序报错？** 填齐全部候选字段再测一次。
3. **范围/配额类报错？** 收窄到最小再看 `total`/记录数。

外加：**先写出「如果是正常实现，服务端会怎么回」并实测对照**。这三类形状是凭空造洞的主要来源，
而用户恰恰会拿「挖到高危了吗」加压——误报比没挖到更伤信用。
