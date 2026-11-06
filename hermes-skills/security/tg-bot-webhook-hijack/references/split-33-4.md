## 第 4 步: 客户端/恶意样本逆向

| 产物类型 | 打法 |
|---|---|
| PyInstaller bot/RAT | pyinstxtractor 解包 → 反编译 .pyc → grep token/chat_id/命令处理(案例:NursultanClient) |
| 前端 JS(drainer/stealer) | 先搜 api.telegram.org/token/chat_id 字符串锚点 → 沿调用回推;重度混淆用 de4js/AST 还原;注意假私钥诱饵 |
| APK(混合 bot 客户端) | jadx 解包 → token/后端 URL;后端在服务端则转 web 渗透 |
| 开源 bot 源码 | pip-audit / npm audit 审计依赖(aiogram<3.22 WebApp 签名 `==` 时序洞、pyTelegramBotAPI→aiohttp CVE-2024-23334 等) |

