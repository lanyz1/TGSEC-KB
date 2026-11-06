# TG 机器人/小程序博彩站渗透 — 实战案例(2026-08-08 周氏PG/c7)

> 完整方法论见 `tg-bot-backend-pentest` 技能;本文件为实战侦察链记录。

## 侦察链: TG bot → 推广站 → 真实平台

目标 `@zhoushipgbot`(周氏PG电子),完整链路:

1. **TG 频道识别**: `t.me/aipg` → og:description 泄露业务(USDT/okpay/kkpay 上下分)+ 交流群 + 客服 @kefuzhou
2. **下注机器人**: `telegram.me/zhoushipgbot` → 确认周氏PG电子 bot
3. **品牌反查**: DDG 搜"周氏电子/周氏PG" → `zhou-shi.com`(c7 站)
4. **JS 资源泄露品牌**: `/skin/cover/zhoushicom/*.webp` → 实锤运营主体,跳转 `wlw-zgqjfww.com`(爱游戏 AYX)+ `wwgpr.com`(c7)
5. **结论**: 周氏PG = **c7/爱游戏体育(AYX)平台代理**,bot 是引流工具,真实平台是 c7

## c7 平台指纹

- 服务器群 `186.240.59.68-71`(宝塔/Nginx 多站点 Host 路由;直连 IP HTTPS 返回"没有找到站点" = 宝塔空站)
- 域名矩阵: wwgpr.com / zhou-shi.com / wlw-zgqjfww.com / ky1.ac
- SEO 壳站: `/go?url=join-now` JS 跳转 → `tz.js` iframe src = `/ldy/index.html`

## TUN 假象下真实端口扫描(必用)

- TUN 开时全端口假 OPEN(连关闭端口 33333 也 OK)
- **破法**: 系统代理 127.0.0.1:10808 发真实 HTTP(`http.client.HTTPConnection("127.0.0.1", 10808)` + 绝对 URL `http://<ip>:<port>/`)
- 状态码判真伪: 200/400 = 真开放,超时 = 关,503 = 网关/代理响应
- 实测: 只有 80(200)/443(400) 真实开放 → 攻击面收窄到 Web 层
