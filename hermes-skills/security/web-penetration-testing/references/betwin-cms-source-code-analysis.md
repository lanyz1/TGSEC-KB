# BetWin CMS (贝盈API v4) 源码级分析参考

> 基于公开仓库 `lgz490541574/BetWin4` (C# .NET Core)
> ASP.NET Core 赌博游戏API聚合中间件

---

## 1. 与PHP博彩CMS的关键区别

| 维度 | PHP博彩CMS (biying/ThinkPHP) | BetWin CMS v4 |
|:-----|:-----------------------------|:---------------|
| 语言 | PHP | C# .NET Core |
| 架构 | 单体应用/一体化 | API聚合中间件（连接8个游戏平台） |
| 鉴权 | Session/Cookie | IP白名单 + Header密钥 |
| 部署 | Apache/nginx | Kestrel (自宿主) |
| 源码泄露 | 论坛/暗网 | **GitHub公开仓库** |
| 前端 | jQuery/Bootstrap | LayuiAdmin |
| 缓存 | File/Memcache | **Redis** |
| 核心功能 | 建站+会员管理 | 游戏API统一封装 |

## 2. 架构总览

```
┌──────────────────────────────────────────────────┐
│              BetWin CMS 部署拓扑                   │
├──────────────────────────────────────────────────┤
│                                                    │
│  商户外部系统 → BetWin API (:8000) → 第三方游戏API  │
│                    ↓                               │
│              管理后台API (:9000)                    │
│                    ↓                               │
│              MySQL + Redis                          │
└──────────────────────────────────────────────────┘
```

### 项目结构
```
API/
├── Web.API/       # 对外商户API — 端口通常 :8000
│   ├── Controller/AccountController.cs    # 注册/登录
│   ├── Controller/FundsController.cs      # 充值/提现/余额
│   ├── Controller/OrderController.cs      # 订单日志/明细
│   ├── Controller/LoginController.cs     # SESSION登录页
│   ├── Filters/APIFilter.cs              # API鉴权核心
│   └── Filters/APIExceptionMiddleware.cs # 异常处理
└── Web.System/    # 管理后台API — 端口通常 :9000
    ├── Controller/AdminController.cs     # 管理员登录/信息
    ├── Controller/ConfigController.cs    # 系统配置/菜单
    ├── Controller/GameController.cs      # 游戏开关/参数
    └── Controller/SiteController.cs      # 商户CRUD
Library/
├── BW.Common/     # 公共库 — 业务逻辑/实体/缓存
├── BW.Games/API/  # 第三方游戏协议实现 (8个)
    ├── AG.cs / AGLive.cs        # 亚游/AG视讯
    ├── BBIN.cs                  # 波音
    ├── Pinnacle.cs              # 平博体育
    ├── IM.cs / IMSport.cs       # IM体育
    ├── IMOne.cs                 # 电竞牛
    ├── AVIA.cs                  # 泛亚电竞
    ├── XJ188.cs                 # 小金188
    └── KY.cs                    # 开元棋牌
```

## 3. 硬编码凭证 (appsettings.json)

```json
{
  "ConnectionStrings": {
    "DbConnection": "server=db.bw4.com;uid=uBW4;pwd=<REDACTED>;database=BW4;",
    "RedisConnection": "redis.bw4.com:6379,password=<REDACTED>"
  }
}
```

**如果部署者未修改，可尝试：**
- MySQL: `uBW4 / HpTo4zqK2B7v6FQu @ db.bw4.com:3306`
- Redis: `redis.bw4.com:6379` 密码同上
- 替换 `db.bw4.com` / `redis.bw4.com` 为目标实际域名/IP

## 4. 商户API鉴权机制

### 鉴权流程 (APIFilter.cs)
```
请求 → [Guest]标记? → 是 → 放行
                    → 否 → 解析Authorization Header
                          → 格式: {SiteID}|{SecretKey} (Guid)
                          → 查询Redis获取该Site信息
                          → 对比SecretKey
                          → 检查IP白名单
                          → 检查商户状态
                          → 通过 → 放入HttpContext
```

### SecretKey
- `Guid.NewGuid()` 格式（32位十六进制）
- 理论上不可爆破
- 可从管理后台 `Site/SaveAPIInfo` 重新生成

### IP白名单
- 存储在Site表 `WhiteIP` 字段，逗号分隔
- 非白名单IP返回 `IP未授权 - {ip}`
- 可通过管理后台 `Site/SaveAPIInfo` 修改

### Guest接口（无需鉴权）
- `GET /login?id=xxx` — 获取登录SESSION页面
- 所有带 `[Guest]` 标签的方法

## 5. 管理后台认证机制

### 管理员登录
```
POST /Admin/Login
Body: userName=admin&password=123456
→ AdminAgent.Login() 验证用户名密码
→ 成功返回 Guid session（作为Token）
→ 后续请求 Header: token=<session_guid>
→ 从Redis查询session是否存在
```

### 弱点
- **无验证码** — 可暴力破解
- **Session无过期机制**（源码未实现）
- **Redis未授权** — 可窃取所有session
- **Guest接口** — `/Config/Init` 无需Token

## 6. API接口速查

### 商户API （路由: `/v1/[Controller]/[Action]`）

| 接口 | 方法 | 需要鉴权 | 关键参数 |
|:-----|:-----|:--------|:---------|
| 注册 | POST Account/Register | ✅ | UserName, Password |
| 登录 | POST Account/Login | ✅ | UserName, Game |
| 余额 | POST Funds/Balance | ✅ | UserName, Game |
| 充值 | POST Funds/Recharge | ✅ | UserName, Game, OrderID, Money |
| 提现 | POST Funds/Withdraw | ✅ | UserName, Game, OrderID, Money |
| 确认 | POST Funds/Check | ✅ | OrderID |
| 订单 | POST Order/Log | ✅ | Game, Time |
| 明细 | POST Order/Detail | ✅ | OrderID[] |
| 登录页 | GET /login?id=xxx | ❌ | id (session key) |

### 管理后台API （路由: `/[Controller]/[Action]`）

| 接口 | 需要鉴权 | 关键参数 |
|:-----|:--------|:---------|
| POST Admin/Login | ❌ | userName, password |
| POST Admin/Info | ✅ | — |
| POST Config/Init | ❌ | — (返回枚举字典) |
| POST Config/Menu | ✅ | — |
| POST Config/GetConfigList | ✅ | — |
| POST Config/SaveConfig | ✅ | type, value |
| POST Game/GetGameSetting | ✅ | type (GameType枚举) |
| POST Game/SaveGameInfo | ✅ | type, status, setting |
| POST Game/GetGameList | ✅ | — |
| POST Game/UpdateCache | ✅ | — |
| POST Site/CreateSite | ✅ | name, prefix, whiteIP |
| POST Site/GetSiteList | ✅ | — |
| POST Site/GetAPIInfo | ✅ | siteId |
| POST Site/SaveAPIInfo | ✅ | siteId, whiteIP, newSecretKey |
| POST Site/UpdateGameRate | ✅ | siteId, type, rate |
| POST Site/UpdateGameStatus | ✅ | siteId, type, status |

## 7. 第三方游戏协议详情

### AG (AGLive) — DES + MD5
- 加密: DES (8字节KEY, ASCII)
- 参数拼接: `key1=val1/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/key2=val2`
- 签名: `MD5(params + Md5Key)`
- 协议: XML over HTTP (doBusiness.do)
- 凭证: Agent + KEY + Md5Key + pidtoken

### BBIN — 动态MD5密钥
- 密钥格式: `GUID_A + MD5(WebSite + value + KEY + timestamp) + GUID_C`
- 不同操作使用不同KEY (KEYCreateMember, KEYLogin, KEYTransfer等)
- 美东时间时区 (UTC-12)

### Pinnacle — AES-CBC
- AES模式: CBC, PKCS7填充
- IV: **固定** `RandomInitVector`
- Token: `AES_Encrypt(AgentCode|timestamp|MD5(AgentCode+timestamp+AgentKey), SecretKey)`
- API: GET请求，参数见URL
- 注意: IV固定严重降低安全性

## 8. 数据库表结构推测

| 表 | 主要字段 |
|:---|:---------|
| Site | ID, Name, Prefix, Status, CreateAt, SecretKey(Guid), WhiteIP |
| Game | Type(GameType枚举), Status(GameStatus枚举), Setting(JSON) |
| SiteGame | SiteID, Type(GameType), Rate(decimal), Status |
| SystemConfig | Type(ConfigType枚举), Value(text) |
| SystemAdmin | ID, UserName, Password, ... |
| User | ID, UserName, Password, SiteID, ... |
| GameOrder | ID, SiteID, Type, OrderID, Game, UserName, BetMoney, Money, CreateAt, ... |

## 9. 渗透要点

### 入口
1. 硬编码数据库/Redis密码复用
2. 管理后台弱口令爆破（无验证码）
3. Redis未授权 → session劫持 → 管理权限
4. SecretKey泄露 → 商户API调用

### 商户API利用
- 获取SecretKey后可调用所有商户API
- 遍历SiteID可访问不同商户数据
- 资金操作（Recharge/Withdraw/Balance）
- 订单数据窃取（Order/Log）

### 横向
- 从管理后台提取所有第三方游戏API密钥
- 直接操作AG/BBIN/Pinnacle等游戏平台
- 修改赔率/费率/游戏开关

## 10. 指纹特征

- 路由模式: `/v1/[Controller]/[Action]`
- HTTP头: `Server: Kestrel`
- 管理后台: LayuiAdmin (可检查 `/version.js` 或 `layui` 相关资源)
- 开发环境: `*.es2.com`, `*.es3.com`
- CDN: `studio.aviacdn.com`
- Redis默认域名: `redis.bw4.com`
- 数据库默认域名: `db.bw4.com`
- 默认数据库用户: `uBW4`
