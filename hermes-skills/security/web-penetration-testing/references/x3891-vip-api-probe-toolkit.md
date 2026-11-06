# 新葡京娱乐城 — API 探针工具包

## 目标信息
| 项目 | 内容 |
|------|------|
| 站点名 | 新葡京娱乐城 |
| 品牌 | 新葡京 (Xinpujing Entertainment) |
| 域名 | `3frpf3wtokt7l5bd7booe7v.74euptem8...x3891.vip:9016` |
| 技术栈 | Vue 3 + Vite + Element Plus + Pinia + OpenResty + PHP |
| server: openresty | 确认 — 405 HTML 响应含 `<hr><center>openresty</center>` |
| CDN | jkydns (x-cache: BYPASS) |
| CAPTCHA | Geetest 极验 (capchaType: 7) |
| siteId | 100038 |
| sitePath | F376 |
| apiPrefix | fag |
| isGuestMode | 1 (启用) |

## API 网关模式

**所有真实 API 通过 POST `/tools/_ajax/<Action>` 访问**

前端在 services-*.js 中定义:
```javascript
let h = "/tools/_ajax/" + e.Action  // API URL 拼接
```

请求格式:
```json
POST /tools/_ajax/<Action>
Content-Type: application/json
Body: {"Action": "<ActionName>", "Requirement": {...}}
```

## 方法测试一览

### HTTP 方法 + 路径矩阵
| 路径 | GET | POST | PUT | PATCH | OPTIONS | DELETE |
|------|-----|------|-----|-------|---------|--------|
| `/api/register` | 200 (SPA) | 405 | 405 | 405 | 405 | 405 |
| `/` | 200 (SPA) | 405 | 405 | 405 | 405 | 405 |
| `/tools/_ajax/<Action>` | 405 | ✅ JSON | — | — | — | — |

### 内容类型测试 (POST /api/register)
| Content-Type | 结果 |
|-------------|------|
| application/json | 405 (OpenResty) |
| application/x-www-form-urlencoded | 405 |
| multipart/form-data | 405 |
| application/xml | 405 |

## 已验证的 Action

### 成功 (`code: "success"`)
| Action | 响应 | 说明 |
|--------|------|------|
| `getSiteInitData` | 完整站点配置 (siteId, lottery列表, VIP等级, 排行榜等) | **信息泄露** |
| `cache/MobileCache` | 移动端配置 + App 下载链接 | **信息泄露** |

### 部分成功 (有响应但受阻)
| Action | 响应 | 原因 |
|--------|------|------|
| `guestRegister` | `"错误站点"` | 需要传 sitePath/siteId 参数 |
| `login` | 403 Forbidden | IP 区域限制 / 缺 AES / 缺 CAPTCHA |
| `getSiteInitData` (无 Requirment) | 成功 | 未加密访问可行 |
| `walletTransfer/register` | `"nologin"` | 需要登录 token |

### 失败
| Action | 响应 | 原因 |
|--------|------|------|
| `register` | 404 HTML | Action 名可能与前端不一致 |
| `walletTransfer/index` | 404 HTML | 不存在 |
| `third/loginCp` | 404 HTML | 不存在 |

## AES 加密机制

### 白名单 (不需要 AES)
从services-*.js提取:
```javascript
ji = [
  "addNewEbankPayOrder",
  "getServerTimeMillisecond",
  "internalWallet/buy",
  "gameChart/*",
  "gameSgChart/*"
]
```

### 跳过 AES 的条件
```javascript
function Zi(e, t) {
  return e.noAes === true || Qi(e.Action) || v0().__no_aes
    ? JSON.stringify(t)     // 不加密
    : zi(t)                  // AES 加密
}
```

### AES 参数 (从已有参考)
- 模式: ECB
- 填充: Pkcs7
- Key: MD5(alias) 的 hex 字符串 → UTF-8 编码
- 双层 Base64

## 注册验证规则 (从 JS ut 对象提取)
```javascript
UserName:  /^[a-zA-Z1-9][a-zA-Z0-9]{3,15}$/
             // 4-16字符, 字母或1-9开头, 不含下划线
Password:  /^[a-zA-Z0-9]{6,14}$/
             // 6-14字符, 纯字母数字
Promotion: /^[a-zA-Z0-9]{6,10}?$/
             // 可选, 6-10字符邀请码
Mobile:    /^1[0-9]{10}$/
             // 中国手机号
```

## GraphQL 测试
| 端点 | 结果 |
|------|------|
| `/graphql` | 200 (SPA CAPTCHA 页) |
| `/api/graphql` | 200 (SPA CAPTCHA 页) |
| `/graphiql` | 200 (SPA CAPTCHA 页) |
| `/tools/_ajax/graphql` | 404 |
| `/tools/_ajax/api/graphql` | 404 |

结论: ❌ 无 GraphQL 端点

## JSONP 测试
| 端点 | 结果 |
|------|------|
| `/api/register?callback=test` | 200 (SPA) |
| `/api/register?jsonp=test` | 200 (SPA) |
| `/api/register?jsoncallback=test` | 200 (SPA) |
| `/api/config?callback=test` | 200 (SPA) |
| `/api/version?callback=test` | 200 (SPA) |

结论: ❌ 无 JSONP 绕过可能

## 弱口令测试
所有 `POST /tools/_ajax/login` 返回 403:
- admin/admin123, admin/admin, admin/123456
- test/test123, admin/password

403 = 请求到达应用层但被拒绝 (非 OpenResty 405)

## SPA 技术细节

### Vue 3 打包产物
| 文件 | 大小 | 用途 |
|------|------|------|
| `assets/index-D67on5fr.js` | ~147KB | 主应用 (Header, Footer, 路由) |
| `assets/services-k0yFuL9w.js` | ~430KB | **API 定义 + 状态管理** |
| `assets/vendor-DNhkrRvw.js` | 大 | 第三方依赖 |
| `assets/vendor-vue-NUOJVDj6.js` | Vue 核心 |
| `assets/vendor-element-plus-BaE7MAaH.js` | Element Plus UI |
| `assets/register-BZWXErK8.js` | 注册页面 |
| `assets/login-B9mTvhPS.js` | 登录页面 |

### 关键 JS 变量 (从 services 提取)
- `h = "/tools/_ajax/" + e.Action` — API 路径
- `w({Action: "...", Requirement: {...}})` — 通用 API 调用
- `Zi(e,t)` — AES 加密判断
- `Qi(e.Action)` — 检查是否在白名单
- `v0().__no_aes` — 全局跳过加密标志
- `isGuestMode: 1` — 允许游客访问
- `capchaType: 7` — Geetest 行为验证

### 从中提取的 API 操作
```
cache/MobileCache, cache/PersonalInfoCache, cache/lotterySetting
getSiteInitData, getServerTimeMillisecond, getNewestBonusList
getBetBoardList, getAbstractType
guestRegister, register, login
walletTransfer/register
getLotteryOpen, getLotteryOpenNewestGame
getBetting, getChaseBetting, cancelBet
chat/getToken, checkHasChatRoom, getNotReadMsgNum
getMemberRegisterList, checkRegisterBonusRecord, getRegisterBonus
```

## OpenResty 诊断
```bash
# 405 = OpenResty 拦截
curl -sk -X POST "https://target:9016/" -w "%{http_code}"
# → 405 <hr><center>openresty</center>

# 200 JSON = 后端可达
curl -sk -X POST -H "Content-Type: application/json" \
  -d '{"Action":"getSiteInitData","Requirement":{}}' \
  "https://target:9016/tools/_ajax/getSiteInitData" -w "\nHTTP %{http_code}"
# → JSON + 200

# 403 = 应用层拒绝
curl -sk -X POST -H "Content-Type: application/json" \
  -d '{"Action":"login","Requirement":{"username":"admin","password":"admin123"}}' \
  "https://target:9016/tools/_ajax/login" -w "\nHTTP %{http_code}"
# → 403 Forbidden (无 body 或短消息)
```
