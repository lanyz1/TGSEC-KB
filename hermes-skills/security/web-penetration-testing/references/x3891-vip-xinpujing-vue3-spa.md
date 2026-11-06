# 新葡京娱乐城 — Vue 3 SPA 赌博平台分析

## 基本信息

| 项目 | 内容 |
|------|------|
| 站点名 | 新葡京娱乐城 |
| 品牌名称 | 新葡京娱乐城 (New Lisbon Entertainment) |
| 目标URL | `https://3frpf3wtokt7l5bd7booe7v.74euptem8ixruhxhoqc1r76.oa5ie22bnet8b1wdqcx1qa7.x3891.vip:9016/lottery/K3/SG31K3` |
| 游戏 | SG31K3（新加坡快三/国际快三）, 1分钟1期, 自主彩种 (isSelfGame:true) |
| 技术栈 | Vue 3 + Vite + Element Plus + PHP 后端 |
| 状态管理 | Pinia |
| 打包产物 | `assets/index-*.js`, `assets/services-*.js`, `assets/vendor-vue-*.js` |
| CDN | jkydns806.com（自定义 CDN） |
| DNS链 | `*.x3891.vip:9016` → `gd66218.cdn.jkydns806.com` → `333cdn.dk.jkydns806.com` |
| 源站IP | 67.211.68.209, 67.211.70.202, 45.126.181.133, 43.229.5.217 |
| 端口 | 9016 (HTTPS) |
| siteId | 100038 |
| mobile URL | s0.vip |
| 二维码 | `https://cr50s4.2idtekqgnucg.online/uploads/images/F376/5aee749c-4f38-408a-b0ac-b1834e4bc006.png` |

## 架构

```
Vue 3 SPA（浏览器端）
  ↓ Pinia stores: site, user, lottery, common, thirdCp, meeline, home, bankCard, extGame
  ↓
POST /tools/_ajax/{Action}  (Content-Type: application/json)
Body: {"Action": "ActionName", "Requirement": {...}}
Authorization: <token> (从 localStorage.getItem('token') 获取)
  ↓
PHP 后端 API
  ↓
数据库 + 游戏引擎
```

## API 调用格式

所有 API 调用统一格式：

**请求**：
```
POST https://domain:9016/tools/_ajax/{ActionName}
Content-Type: application/json
Body: {"Action": "ActionName", "Requirement": {...}}
Authorization: <token> (登录后)
```

**响应**：
```json
{"code": "success|fail|nologin|error", "data": {...}, "msg": "..."}
```

## 发现的所有 API Action

从 services-*.js 文件枚举：

### 公开API（无需登录）
| Action | 说明 |
|--------|------|
| `getNewestBonusList` | 中奖列表 |
| `getBetBoardList` | 投注面板 |
| `getAbstractType` | 财务摘要类型 |
| `cache/MobileCache` | 移动端配置 (含siteId: 100038, 二维码链接) |
| `cache/lotterySetting` | 彩票设置 (空数据) |

### 需登录API
| Action | 说明 |
|--------|------|
| `cache/lotteryOpenCache` | 开奖缓存 (对自主彩种返回"服务器内部错误") |
| `getLotteryOpen` | 开奖号码 (不支持自主彩种) |
| `getLotteryOpenNewestGame` | 需要正确gameId (所有常见值无效) |
| `cache/PersonalInfoCache` | 个人信息 |
| `getBetting` | 投注记录 |
| `getChaseBetting` | 追号记录 |
| `cancelBet` | 撤单 |
| `chat/getToken` | 聊天室Token |
| `checkHasChatRoom` | 聊天室检查 |
| `getNotReadMsgNum` | 未读消息数 |

### 注册/登录API
| Action | 说明 |
|--------|------|
| `register1` | 注册第一步 (返回Geetest v3 CAPTCHA) |
| `login` | 会员登录 (IP限制: 某些地区返回403) |
| `guestRegister` | 游客注册 |

## 自主彩种限制

SG31K3 配置 (`localStorage.getItem('site.lotteryList')` 中的 `SG31K3` 条目):
```json
{
  "lotteryCode": "SG31K3",
  "lotteryType": "K3", 
  "lotteryName": "幸运快三",
  "lotteryIntro": "1分钟1期",
  "isSelfGame": true,
  "gameType": "GPCP",
  "betType": 1,
  "sortId": 5,
  "templateId": 1004902,
  "conSortId": 251,
  "isLeopardKill": false,
  "isChangLongAide": true,
  "stopIssueList": ""
}
```

`isSelfGame: true` 导致:
- `getLotteryOpen` 返回 "开奖号码不支援自主彩种和官彩号码查询"
- `cache/lotteryOpenCache` 返回 "服务器内部错误"
- 开奖号码由管理员后台预生成，API层无接口暴露未来结果

## 认证流程

1. **注册**: 调用 `register1` → 返回 Geetest v3 CAPTCHA (gt, challenge, codePhotoKey) → 需滑块验证
2. **登录**: 调用 `login` API → 返回 token (可能IP限制403)
3. **最佳路径**: 用户在浏览器手动登录 → CDP读取localStorage token

## Pinia Store 数据提取

### LotteryResults — 开奖数据核心（200期数据提取）

```javascript
var pinia = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia;
var results = pinia.state.value.lottery.LotteryResults;

// 结构:
// {
//   "SG31K3": {
//     "time": "2026-07-20T18:43:33.653Z",
//     "results": [
//       {
//         "gameId": "SG31K3",
//         "gameName": "一分快3-3",
//         "issueNo": "20260721163",        // 期号 (11位数字，格式: yyyyMMdd + 3位流水)
//         "lotteryOpen": "3,3,4",           // 开奖号码 (逗号分隔)
//         "count": 10,                      // 和值
//         "daxiao": "xiao",                 // "da"=大, "xiao"=小
//         "danshuang": "shuang",            // "dan"=单, "shuang"=双
//         "awardStatus": null,
//         "resultDate": "1784572983396",    // 时间戳(毫秒)
//         "openTime": "02:43:03"            // 开奖时间
//       }
//     ],                                    // 共200条，按时间倒序
//     "total": 200
//   }
// }
```

**提取到JSON文件的Python模式**:
```python
import json
# 通过CDP或浏览器控制台获取后保存
with open('lottery_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

### User Store
```javascript
var user = pinia.state.value.user;
// loginName: "a<PHONE-REDACTED>"          - 用户名
// accountId: 1022285613              - 用户ID
// money: "0.3"                       - 余额
// type: "0"                          - 用户类型 (0=普通会员)
// parentId: 1019940048               - 上级代理ID
// userGrade: "VIP2"                  - VIP等级
// userTitle: "白银"                  - 头衔
// userStatus: "0"                    - 状态
// bettingStatus: "0"                 - 投注状态
// freezeStatus: "0"                  - 冻结状态
// blackStatus: "0"                   - 黑名单状态
// chatroom: "true"                   - 聊天室权限
```

### 从 localStorage 获取关键数据

**token**: `localStorage.getItem('token')` → JWT格式，用于API认证

**其他key**（全部可从 `localStorage` 枚举）:

| Key | 值类型 | 说明 |
|-----|--------|------|
| `token` | JWT string | API认证令牌 |
| `user.loginName` | string | 用户名 |
| `user.Balance` | JSON string | 余额 |
| `user.accountId` | string | 账号ID |
| `user.ImgPath` | string | 头像路径 |
| `user.type` | string | 用户类型 |
| `user.Id` | string | 用户ID |
| `user.Status` | string | 状态 |
| `user.userTitle` | string | 头衔 |
| `user.userGrade` | string | VIP等级 |
| `user.pwdEncodeType` | string | 密码编码类型 |
| `user.chatroom` | string | 聊天室权限 |
| `user.testAccountType` | string | 测试账号类型 |
| `user.agentRebates` | JSON string | 代理返点配置 |
| `user.extLoginName` | string | 外部登录名 |
| `site.lotteryList` | JSON string (object) | **所有彩票配置**，key为游戏代码 |
| `site.config` | JSON string | 站点配置 |
| `site.lotteryConfig` | JSON string | 彩票配置 |
| `site.optionStates` | JSON string | 功能开关 |
| `site.cacheData` | JSON string | 缓存数据 |
| `site.noticeData` | JSON string | 通知数据 |
| `site.bannerList` | JSON string | Banner列表 |
| `site.gradeList` | JSON string | VIP等级配置 |
| `site.rankingList` | JSON string | 排行榜 |
| `site.recommendLotteryCache` | JSON string | 推荐彩票缓存 |
| `__uuid` | string | 设备UUID |
| `version` | string | 版本号 |
| `abcdefg` | JSON string | 登录配置（含loginSave） |
| `meeline` | string | 聊天相关 |
| `RebateSG31K3` | string | 游戏返点配置 |
| `lotteryPlanCTGSK3` | ... | 彩票计划缓存 |
| `site.lotteryList` 中的 `Rebate*` keys | string | 各游戏返点率 |

**`site.lotteryList` 结构**：对象形式，key为游戏代码（如 `SG31K3`, `SG1K3`, `DF1K3` 等），value为配置对象。

**所有彩票游戏代码**（从站点提取）:
SG1K3, SG1CT1PK10, DF1K3, CTOG15PK10, SG13PK10, CTGXK3, CTOG5K3, SG23K3, CTOG3BSC, SG21PK10, CTOG5BSC, SG31K3, SG3K3, CTOG10K3, CTAHK3, SG25K3, XGLHC, CTHUBK3, NXYFT, CTSHK3, JLK3, CTHEBK3, TWBINGO, CTGSK3, GZK3, CTGZK3, CTBJPK10, SHK3, CTOG15FT, HUBK3, CTCQSSC, HEBK3, CTBJK3, GXK3, GSK3, CTJLK3, BJK3, CTJSK3, AHK3, CTOG10FFC, CTOG10PK10, K3MMC, FCKL8, CTXJSSC, FCLK28, SGCT1FFC, CTOG1BSC, OG10FFC, OG10PK10, HJBJPK, HJHLSX, CQSSC, FC3D, XJSSC, JSK3, JX11X5, GD11X5, JS11X5, SD11X5, BJPK10, SH11X5, BSCMMC, SSQCP, KK30RG, KK1RG, KK3RG, KK5RG, KK10RG, SG5FFC, SG1FFC, SG3FFC, SG11LHC, SG15LHC, SG11ANL, SG115ANL, SG13ANL, SG15ANL, SG11LK28, SG113D, SG133D, SG153D, PL3CP, SG10K3, SG11PK10, LHCMMC, SG45K3

## Vue 3 SPA 路由结构

共132条路由，全部是用户/会员功能，**无Admin后台路由**。会员中心路由包括:

### 会员中心 (`/memberCenter/`)
- `betRecord` — 投注记录
- `seekOrder` / `seekOrder/detail` — 追号记录
- `betDetail` — 注单详情
- `letter` / `letterDetail/:messageId` — 站内信
- `notice` / `noticeDetail` — 公告
- `personalInfo` — 个人信息
- `personalLevel` — 会员等级
- `manageBankcard` — 银行卡管理
- `manageAlipay` — 支付宝管理
- `manageYun` — 云支付管理
- `manageWeChatPay` — 微信支付管理
- `manageFxshuo` — 纷享钱包管理
- `manageUSDT` — 数字钱包管理
- `billRecord` — 交易记录
- `creditTransfer` — 额度转换
- `extRecord` — 第三方记录
- `qzBetRecord` — 棋牌记录
- `yuebao/*` — 余额宝相关 (review, transferIn, transferOut, service)

### 代理中心 (`/memberCenter/`) (agent: true)
- `agentIntro` — 代理说明
- `agentReport` — 代理报表（含filter: 今日/昨日/七日/上周/本月/上月/自定义）
- `commission` / `commission/myPromotion` / `commissionSearch` / `commissionDescrip` / `commissionDetail` — 无限代佣金系统
- `lowerReport` — 下级报表
- `manageInvite` — 下级开户
- `promotionInvite` — 邀请码管理
- `agentMember` — 会员管理
- `agentBetRecord` — 彩票明细
- `qzAgentBetRecord` — 棋牌明细
- `agentBillRecord` — 交易明细

### 其他路由
- `/lobby` — 购彩大厅
- `/lottery/:type/:code` — 彩票游戏页
- `/login` — 登录
- `/register` — 注册
- `/home` — 首页
- `/third/loginCp` — 第三方跳转
- `/memberCenter` — 会员中心入口
- `/howToPlay/:paramPlayId` — 玩法说明
- `/maintain` — 系统维护
- `/ipError` — IP错误
- `/chat/` — 聊天室
- `/notfound` — 404
- `/*` → redirect `/home` — 兜底

### 页面元信息
```javascript
meta: { title: "页面标题", user: true|false, agent: true|false }
```
- `user: true` = 需要登录才能访问
- `agent: true` = 需要代理权限

## 管理后台

- **该域名不承载管理后台** — 所有132条路由均为用户/代理/会员功能
- 后台在独立系统，地址未知
- 开奖管理（预生成结果）不在前端系统

## Chrome 标准浏览器启动 + CDP

```python
import subprocess, time, urllib.request, json, websocket

# 1. 杀所有现有Chrome进程（避免端口冲突）
# 2. 启动带 debugging 端口的 Chrome
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_dir = r"C:\Users\Administrator\Desktop\chrome_debug"
cmd = [
    chrome_path,
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",   # 必须！否则websocket连接被403
    f"--user-data-dir={user_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "https://target-url"
]
subprocess.Popen(cmd)
time.sleep(5)

# 3. 连接CDP
tab_ws = "ws://127.0.0.1:9222/devtools/page/<tab_id>"
ws = websocket.create_connection(tab_ws, timeout=30)

# 4. 执行JS提取数据
def cdp(method, params=None):
    msg = {"id": 1, "method": method}
    if params: msg["params"] = params
    ws.send(json.dumps(msg))
    time.sleep(0.5)
    return json.loads(ws.recv())

# 获取token和彩票数据
result = cdp("Runtime.evaluate", {
    "expression": "localStorage.getItem('token')",
    "returnByValue": True
})
token = result["result"]["result"]["value"]

# 获取Pinia数据
result2 = cdp("Runtime.evaluate", {
    "expression": """
    JSON.stringify(
        document.querySelector('#app').__vue_app__
            .config.globalProperties.$pinia
            .state.value.lottery.LotteryResults
    )
    """,
    "returnByValue": True
})
```

## 数据采集脚本模式

当页面已登录，可通过CDP持续采集历史数据。200期开奖数据存储在Pinia `lottery.LotteryResults[gameCode].results` 中，可一次性提取。
