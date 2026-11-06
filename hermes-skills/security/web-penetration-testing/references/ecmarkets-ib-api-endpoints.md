# EC Markets IB Portal API 端点手册

> 基于 EC Markets IB 系统（ib.ecmarkets.com.au）真实逆向分析
> 更新日期: 2026-07-25

## 认证方式

```bash
# 自定义 token header（非 Bearer）
token: <JWT>
platform: IB          # 必须
x-api-version: 2.44.0 # 必须
lang: zh-CN           # 建议
browserfingerprint: <userId>  # 部分API需要
```

> ⚠️ 所有 API 调用必须使用 `api.ecmarkets.com.au` 域名。  \
> `ib.ecmarkets.com.au` 是前端反向代理，POST 请求会返回 405。\
> 浏览器中 fetch 请求走的是 `ib.ecmarkets.com.au` → 返回 405，\
> 但 curl 直接调 `api.ecmarkets.com.au` 可正常工作。

## Token 获取

```javascript
// 从 cookie 获取 JWT（在用户浏览器控制台运行）
var token = <REDACTED>;]+)/)[1];

// 或用 browser_navigate 登录后直接用 API（需credentials）

// Browser自动化登录步骤（中文版更稳定）:
//   1. browser_navigate("https://ib.ecmarkets.com.au/zh-CN/userSign/login")
//   2. browser_type(ref=e14, text="邮箱账号")
//   3. browser_type(ref=e16, text="密码")
//   4. browser_click(ref=e10)  // "登 录"按钮
//   5. 成功后自动跳转到Dashboard，cookie自动设置
//   6. 之后可直接导航到各菜单页面
//     注意：SPA在headless浏览器中可能渲染失败，但API调用不受影响

// login URL: https://ib.ecmarkets.com.au/zh-CN/userSign/login → 有服务端渲染的登录表单
// 中文版比英文版更稳定（英文版 SPA 在 headless 浏览器中容易渲染失败）
// 填 email + password → 点 Login → cookie自动设置 → 可调API
```

### 已知有效登录凭证

```
邮箱: <EMAIL-REDACTED>
密码: jqka1234
用户: 刘东 (CN29331658, userId=1073981)
```

## 菜单布局对照

中文版（推荐用于 headless 浏览器）:

| 中文菜单 | 英文菜单 | 对应API路径 |
|---------|---------|------------|
| 首页 | Home | dashboard |
| 推广链接 | Referral Link | popularize/link |
| 客户 | Clients | user/manages |
| 销售机会 | Leads | saleChance |
| 交易管理 | Trades Mgmt | trades |
| **佣金数据** | Commission Data | rebate/* |
| ├ 详情 | Details | rebate/rebateDetail |
| ├ 规则 | Rules | rebate/rebateRule |
| ├ **IB/代理绩效** | IB/Agent Performance | rebate/getAgentPerformanceStatistics |
| └ 报表 | Report | rebate/report |
| **关系树** | Commission Chain | user/relationship/page |
| 推广素材 | Materials | popularize/material |

## 已验证的 API 端点

### 用户信息

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/ib/user/current/info` | GET | 无 | 当前用户完整信息（含 parentAgentUserId=null, isAgent, invitationCode, agentAuthority） |
| `/api/ib/user/current/info?offset=0` | GET | offset | 同上（带分页偏移量） |
| `/api/ib/user/current/detail` | GET | 无 | 404 —不存在 |
| `/api/ib/user/check/account` | GET | 无 | 账户安全检查（登录后首次加载时调用） |

### Dashboard（仪表盘）

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/ib/dashboard/basic/info` | GET | 无 | 统计数据（cusTotalCount, rebateBalance, deposit/withdraw等） |
| `/api/ib/dashboard/count` | POST | `{"duration":{"startTime":...,"endTime":...}}` | 客户分类计数（需时间范围：startTime="不能为空"） |
| `/api/ib/global/counter` | GET | 无 | 全局计数器 |
| `/api/ib/heartbeat/recording/ping` | POST | content-length:0 | 心跳（用于维持session） |
| `/api/ib/page/baseInfo` | GET | 无 | 页面基础信息（返回footer/header HTML片段） |
| `/api/ib/internalMsg/countPerUserInternalMsgApp` | GET | 无 | 未读内部消息数 |
| `/api/ib/exportDownload/ibGetDownloadAmount` | GET | 无 | 可下载资料数量 |
| `/api/ib/voip/account/currentUser` | GET | 无 | VoIP/通话账号信息 |
| `/api/ib/dashboard/transactionRebate` | - | 404 | |
| `/api/ib/dashboard/header` | - | 404 | |
| `/api/ib/dashboard/list` | - | 404 | |
| `/api/ib/dashboard/page` | - | 404 | |

### 客户管理

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/ib/user/manages/ordinary/type` | POST | `{"pageNum":1,"pageSize":10}` | 普通客户列表（含 agentUserId 字段显示所属代理） |
| `/api/ib/user/manages/ordinary/total` | POST | `{}` | 普通客户汇总 |
| `/api/ib/user/manages/proxy/type` | POST | `{"pageNum":1,"pageSize":10,"queryType":?}` | 代理页客户列表（需正确 queryType 值） |

### 用户关系

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/ib/user/relationship/page` | GET | `userId=...&pageNum=1&pageSize=10` | **佣金链页面** — 返回UID/Email/姓名/Relation树。Relation列含父级链。 |
| `/api/ib/user/manages/agent/type` | POST | `{"pageNum":1,"pageSize":10}` | **下级代理列表** — 返回31个代理。含agentUserId字段。 |
| `/api/ib/user/manages/agent/total` | POST | `{}` | 下级代理汇总统计 |
| `/api/ib/user/manages/ibAgentButtonShow/{userId}/false` | GET | 无 | IB代理按钮显示开关（返回boolean） |
| `/api/ib/user/agentSearch/field` | GET | `field={uid/email/name}` | 代理搜索（只能搜已有用户，invite code搜不到） |
| `/api/ib/childAccount/listChildAccountInIB` | GET | 无 | 当前用户的IB子账户列表（返回 roleId=2） |

### 返佣/业绩

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/ib/rebate/getAgentPerformanceStatistics` | POST | `{"direct":1,"type":4,"pageNum":1,"pageSize":10,"duration":{"startTime":...,"endTime":...}}` | 下级代理业绩（type=4=代理, total=13个代理） |
| `/api/ib/commission/rule` | - | 404 | |
| `/api/ib/user/commission/rule` | - | 404 | |

### 推广链接

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/ib/popularize/link/page` | GET | `pageNum=1&pageSize=10` | 推广链接列表（含 invitationCode, link, remark, mt4配置） |

### 配置

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ib/dataListCustomization/dataListCustomization?code=ib.customer.xx` | GET | 页面列配置（code=ordinaryCustomer/proxy等） |
| `/api/ib/commonConfig` | GET | 通用配置（withdrawalRate, livechatKey, serverOffset） |

## 已知限制

1. **parentAgentUserId 永远为 null** — IB API 不暴露上级关系（即使返佣关系存在，如刘东的上级邀请码U17FZ的属主无法查询）
2. **关系树(Commission Chain)只显示下级** — Relation列只显示用户自身一个层级，不显示上级链
3. **邀请码无法反查属主** — 80+ API 路径测试后确认无此接口；通过邀请链接 `i.ecmarkets.sc/api/client/pm/2/{code}` 也无法获取属主
4. **agentSearch 不能搜 invite code** — 只能搜 UID/邮箱/姓名
5. **下级列表 pagination 限制** — 即使 total=166，API 也只返回固定10条（通过 pageNum 翻页可获取全部）
6. **返佣规则可查，但规则创建者不可查** — 只能看到返佣费率，看不到谁设的
7. **ibAgentButtonShow/{userId}/false 返回 true** — 表明该功能启用但不暴露数据
8. **admin.ecmarkets.co.uk 为 IIS ASP.NET 后台** — 当前返回503（服务不可用），是可能的突破口
9. **backend.ecmarkets.co.uk 为 Spring Boot** — `/actuator/health` 泄露两个PostgreSQL数据库（ec1DataSource + traderEvolutionDataSource），其他端点需认证(401)
10. **数据库(AWS RDS PostgreSQL)** — AWS安全组阻止外部连接

## 非API前端路由（页面路径）

从 Umi.js 路由推断：

| 页面 | 路由路径 | JS Chunk |
|------|---------|----------|
| 普通客户 | `/customer/ordinary-customer` | `p__Customer__OrdinaryCustomer__index.*.async.js` |
| KYC/入金 | `/customer/kyc-and-in-money` | `p__Customer__KycAndInMoney__index.*.async.js` |
| 代理管理 | `/customer/proxy` | (用到 dataListCustomization?code=ib.customer.proxy) |

## 关系树(Commission Chain)行为

- 页面路由: `/api/ib/user/relationship/page` (GET, 带pageNum/pageSize)
- Relation列显示树形导航: `listitem [level=1]` (用户头像图标) + `listitem [level=1]` (用户名)
- **只显示用户自身一个层级** — 不上查父级
- 默认筛选"直属"(Direct)，可改为其他筛选条件
- "我的数据"(My Data)按钮：刷新显示当前用户数据
- 数据字段: UID, 邮箱/手机, 姓名/昵称, 关系(树形导航)
- 每条数据有 row clickable 事件 → 可点击展开下级详情

## 佣金数据(Commission Data)子页面

| 子菜单 | 功能 | 已知API |
|-------|------|---------|
| 详情(Details) | 佣金明细 | (需进一步探索，页面基本空白) |
| 规则(Rules) | 佣金费率配置 | rebate/rebateRule (前端路由, 显示全局费率表: Forex/Index/Metal/Energy/Stock/Crypto各产品线费率) |
| IB/代理绩效(IB/Agent Performance) | 代理绩效统计 | rebate/getAgentPerformanceStatistics (POST, 需duration+direct+type参数) |
| 报表(Report) | 佣金报表 | (需进一步探索) |

## dataListCustomization 列配置

前端通过 `dataListCustomization?code=ib.customer.{type}` 获取页面列配置：

| code | 页面 | 关键字段 |
|------|------|---------|
| `ib.customer.ordinaryCustomer` | 普通客户 | UID, 邮箱/手机, 姓名, 总资产, 返佣钱包等 |
| `ib.customer.proxy` | 代理管理 | UID, Relation(关系), subAgent(子代理), maintainer(维护人) |
| `ib.customer.kycAndDeposit` | KYC/入金 | UID, KYC状态, 入金金额等 |

### `/api/ib/user/current/info` 返回的 agentAuthority（权限列表）

```
ibRelationTree, ibRelationTreeDetail        # 关系树
commission, commission.deposit, commission.rule  # 返佣
user, user.allCustomer, user.subAgent       # 用户管理
user.ordinary, user.kycAndDeposit           # 客户分类
user.subAgent.addAgent                      # 添加子代理
popularize.link, popularize.link.edit       # 推广链接
subAccount, subAccount.list                 # 子账户
saleChance                                  # 销售机会
tsManager                                   # TS管理
userInfo, userInfo.agentInformation         # 用户信息
```

### 客户列表字段（来自 ordinary/type 响应）

| 字段 | 示例 | 说明 |
|------|------|------|
| userId | 1126115 | 内部ID |
| uid | CN30270070 | 公开UID |
| agentUserId | 1073981 | **上级代理ID** |
| agentLoginName | <EMAIL-REDACTED> | 上级代理邮箱 |
| agentFirstname | 东 | 上级代理名 |
| agentLastname | 刘 | 上级代理姓 |
| kycStatus | 3 | KYC状态(3=通过) |
| isAgent | 0 | 是否代理 |
| registerType | 2 | 注册类型 |

### 直接API调用测试备忘

```bash
# 获取下级代理列表
curl -sk -X POST "https://api.ecmarkets.com.au/api/ib/user/manages/agent/type" \
  -H "token: $TOKEN" -H "platform: IB" -H "x-api-version: 2.44.0" \
  -H "Content-Type: application/json" \
  -d '{"pageNum":1,"pageSize":10}'

# 获取关系树
curl -sk "https://api.ecmarkets.com.au/api/ib/user/relationship/page?pageNum=1&pageSize=10" \
  -H "token: $TOKEN" -H "platform: IB" -H "x-api-version: 2.44.0"

# 下级代理业绩
curl -sk -X POST "https://api.ecmarkets.com.au/api/ib/rebate/getAgentPerformanceStatistics" \
  -H "token: $TOKEN" -H "platform: IB" -H "x-api-version: 2.44.0" \
  -H "Content-Type: application/json" \
  -d '{"direct":1,"type":4,"pageNum":1,"pageSize":10,"duration":{"startTime":1782421200000,"endTime":1785013199999}}'

# WebSocket心跳
curl -sk -X POST "https://api.ecmarkets.com.au/api/ib/heartbeat/recording/ping" \
  -H "token: $TOKEN" -H "platform: IB" -H "x-api-version: 2.44.0" \
  -H "Content-Length: 0"
```
