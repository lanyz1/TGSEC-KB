## 第 5 步: 情报聚类与归属(恶意 bot)

- 同 token / 同 webhook URL / 同描述文本 / 同 chat_id → 同一运营者
- webhook 基础设施是 pivot:webhook.site / *.pipedream.net / *.trycloudflare.com / livegram.io = 一次性中继;自有域名 = 运营者基建
- bot 自曝:`getMyDescription`、menu web-app URL(→ Mini App 攻击面)、pinned message 常带广告或误泄 token
- 工具:matkap(0x6rss/matkap)——token 验证/Hunt 前转/IOC Discovery(ThreatFox/urlscan/ZoomEye)/统计面板

