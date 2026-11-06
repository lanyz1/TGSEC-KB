# m9600 客服系统独立 API 攻破配方(2026-08-07 实战)

白标平台(MM99/m9600.com)的客服系统是**独立应用**(与主站 WS 协议无关),有自己的前端、API 服务器、鉴权。攻破客户视角 API 后能查聊天记录;客服工作台(/service)存在但 401 需凭证、无登录入口。

## 资产定位

1. **主站 REST 泄露客服链接**: `GET https://m9600.com/api/customer_info` → `{"code":"0","data":{"liveVivai_customer":"https://www.qesdeegs.icu/#/GcPOYpIVCcP6IQPEgD33YQGc6Egie5yE"}}`
   - 链接带 **hash token**(会话/商家标识),无 token 访问首页只显示 "Invalid Link"
2. **客服前端**: `https://www.qesdeegs.icu/`(标题 MM99,欢迎语 "Welcome to the work platform user service center")
3. **客服 API 服务器**: 从前端 JS(assets/index-e412f1fa.js)提取 `ci="https://apic.dwlmjmcw.xyz"` + AES 参数(密钥 DfoieDOsdkfmfkwofxoDMytduexwJkmN / IV IfklajiocsowmJsk — 但实际请求体是明文 JSON,加密密钥另有用途)

## 客户 API 格式(已攻破)

```
POST https://apic.dwlmjmcw.xyz/customer-service/v1/customer/history
Headers:
  Content-Type: application/json
  merchant-id: 12                  ← 商家 ID(枚举 1-15,只有 12 有效)
  X-Timestamp: <加密值,密钥未知,但页面 fetch 可不带>
Body: {"cid":"Nd6acLZsJ5Cd5sLoCl8gzUSl3bfd647e"}   ← 会话 ID(hash token 之外另有 cid)
```

**响应是明文 JSON**: `{"code":200,"message":"Success","data":[{"id":"18166592","send_by":"1","type":"text","content":"<AES加密base64>","created_at":"1786118828"}]}`

关键观察:
- content 字段再加密(与主站 STORAGE_PASSPHRASE 密钥不同,本会话未解出)
- 错误码: 433 = key error(缺 merchant-id/cid)、422 = cid error/merchant error、404 = 页面未找到
- **cid 校验严格**: 随机/全A/末位±1 全部 422 cid error → 不可枚举他人会话
- **merchant-id 枚举**: 只有 12 有效 → 确认唯一商家

## 端点清单

| 端点 | 方法 | 说明 |
|------|------|------|
| /customer-service/v1/customer/history | POST | 聊天历史(data[].content 加密) |
| /customer-service/v1/customer/config | POST | 需 key(带 cid+merchant-id 仍 433 key error) |
| /customer-service/v1/customer/m | POST | 消息(空 data) |
| /customer-service/v1/customer/send2 | POST | 发送消息(422 error,可能需更多字段) |
| /customer-service/v1/customer/typing | POST | 输入状态 |
| /customer-service/v1/service | GET | **客服工作台 API,401 invalid credentials** |
| /customer-service/v1/service/history | GET | 同上 401 |
| /customer-service/v1/ | GET | 401 |

## 客服工作台侦察结论

- `/service/*` 存在但 401(需要客服凭证)—— 证明有服务端 API,但**无登录接口**(/service/login /auth /token 全 404)
- 前端只有路由 `/` 和 `/:mid`,无管理端页面
- 子域(admin.qesdeegs.icu 等)不存在
- 结论: 客服工作台入口不暴露,爆破无目标,及时收手

## 工程要点

1. **Python 直连被 CF bot 检测**: body 请求返回 403(CF 1010 bot 检测)。用**页面内 fetch**(CDP Runtime.evaluate + awaitPromise:true)可绕过 — 页面有真实浏览器指纹
2. **CDP 抓 API 格式**: Network.requestWillBeSent 抓 request.headers/postData,能看到完整鉴权格式
3. **页面 fetch 相对路径被 SPA 拦截**: 必须用完整 URL `https://apic.dwlmjmcw.xyz/...`
4. **hook fetch 在页面重载后被清除**: 用 addScriptToEvaluateOnNewDocument 或直接页面内 fetch(带 awaitPromise)
