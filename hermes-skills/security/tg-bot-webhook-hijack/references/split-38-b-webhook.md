## B 面: Webhook 后端攻击
- 签名缺失确认 → 伪造 update 执行命令;**伪造 admin from.id 提权**
- secret_token 缺失 = L1;伪造 update 执行命令 = L2;伪造 admin 提权 = L3;Stars 支付伪造白嫖 = L3
- 断原通知流操作(set-webhook 到自己 URL)**先问**或用测试 bot

