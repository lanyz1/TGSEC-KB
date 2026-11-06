# 凭证票源通道边界实证(2026-09-07 后半段)

承接 references/2026-09-07-bidding-day-battle.md(状态机漏洞/饥饿/前半段)。后半段聚焦一个问题:**orch 翻 tokenrailquery 换票对"自动化批量报名企业"是否物理无效**——最终四窗全查实锤,并摸清接口结构。

## 四窗全查:排除跨天会话假说

用户追问"抓登录 token 换 ST 也不行吗" → 补验跨天会话假说(企业昨天登录、会话今天持续、报名不产生新行):

| 窗 | 活票03 全查数 | 目标企业命中 |
|---|---|---|
| 9/7 08:00-09:00 | 1904 | 0 |
| 9/7 09:00-10:40 | 1767 | 0 |
| 9/7 10:40-11:40 | 1588 | 0 |
| 9/6 21:00-22:00 | 361 | 0 |
| **合计** | **5620** | **0** |

目标企业=当日名册有报名动作的崇锐/益鑫/金纪源/名可名/鑫地/天昊/金迈盛。结论:自动化报名企业会话**任何时段都不在 tokenrailquery**——不是票龄(TTL)问题、不是时段问题、不是 seen 锁问题。

## 自动化批量报名特征(识别方法)

- 同企业 09:47-09:50 连报南昌 3 项目 + 11:05-11:09 连报乌鲁木齐 4 项目,项目间间隔 1-5 秒
- 名册接口(biddingandsellingsupplier)行对同一动作**重复返回多行**(30 天窗不去重)——本地必须 set 去重;这也是 sync 名单 dedupe 的原因
- 判定口径:间隔秒级 + 跨局连报 = 脚本/代报工具(如崇锐 91410311MAD3W90R38)

## 接口结构实证

**名册行(biddingandsellingsupplier)字段**:bidder_name / buy_time / proj_code / proj_name / bulletin_reldate / un_social_cr_code(信用代码=唯一身份锚点)。**无账号字段**。参数 startDate/endDate 语义 = bulletin_reldate(公告日)窗,不是 buy_time;不能按 projCode 过滤(返回 0)。

**tokenrailquery 行字段**:token / userid / **username** / ip / login_mode(随机码|手机号|证书) / login_device / login_media / user_type / user_type_name / login_status / login_time / return_url。行里有账号但 findList 无按账号过滤参数 → 只能全窗拉 + 本地筛。

**user_type 分布**(1h 窗 3500 行):
- **03 供应商 = 2080(主力,orch 筛 03 正确)**
- 02 集团公司 = 1298(量大但无 token 换 ST 权限,勿浪费请求)
- 00 游客 86 / 09 运营·商城(证书登录)3 / 05 2 / None 31

**login_status 分布**:1(活)=3217 / **0(登出)=283**。

## ⚠️ login_status=0 盲区(未完结,下次接手先验)

orch worker 与 debug 全查都只筛 `login_status==1`(活票)。每窗 ~283 行 status=0(登出/失效票据)**从未被查过**。自动工具"登录→操作→登出"正会留下 status=0 的票——若 5620 结论有漏洞,就在这里。

待验脚本(已传沪4 /tmp/dbg_s0.py):拉 09:30-11:30 窗**不过滤 status**,type=03 行逐个 user/info 找目标企业:
- 命中 → orch 筛错(候选应含 status=0,或对 0 票也试 user/info)
- 仍 0 → 通道边界终局坐实(business 域直调无 cg 票),放弃此路

## 三入口可观测性矩阵

| 报名入口 | cg 审计 | tokenrailquery | 我们能否补 |
|---|---|---|---|
| ①公告页/列表跳转报名(redirectEnrollUrl) | ✅ 可见 | ✅ 有行 | ✅ collector 秒拦 100% |
| ②站内业务系统报名 | ❌ 不可见(域隔离) | ⚠️ 登录走 cg SSO 则有 | 理论可补 |
| ③客户端/接口直调批量报名 | ❌ | ❌(5620 票实证) | ❌ 报名期无票,等竞价日(cg 入口进场)或永缺(僵尸⚠️) |

## 域探测结论(B 探测)

- **execute-server 域有 dataplatform 面板**:`bid.95306.cn/api/execute-server/dataplatform/api/findList` 返回 code:1001"请先登录!!"→ 需登录态(非无鉴权)。有有效 ST 后可探其 funcId 表 = 潜在竞价域票源(待办)
- cg 域 dataplatform funcId 是**注册制**:盲猜词表(sysloginlog/loginlog/tokenlog/ssolog/bizloginlog/logintrace/sessionlog)全部返回"不存在的功能" → 只能从页面/JS/已见接口反推功能码,不浪费盲猜
- business-proxy 下无 dataplatform 路由(404);business.95306.cn 域名不存在;bid.95306.cn/proxy/dataplatform=404

## 拦截率口径修正(预测教训)

- 对用户承诺前必须分口径:笼统"85-90%"错误。正确两口径:
  - **报名期即时拦截率**(g1):受通道边界限制(cg 入口可见企业才可即时补;③类企业报名期无票),今天实测 ~57%
  - **竞价日终局完整度**(g3/🏁):项目竞价日进场(cg 入口)→ orch 补 → 90%+ 可达,剩 2-5% 弃权僵尸 ⚠️
- 每窗候选用全查(不采样)判定"无命中"才是实锤;采样/前 N 个只能说"未发现"
