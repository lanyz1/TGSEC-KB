---
name: tiktok-data-collection
description: >-
  测绘引擎·采集 TikTok 账号数据(粉丝/作品)。SSR解析用户信息+CDP抓Cookie+页面fetch绕过签名。
owned: true
tier: ops
pack: survey-skill
---

# tiktok-data-collection（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/tiktok-data-collection/`

溯源（仅标记）：`hermes/software-development`

---

# TikTok 账号数据采集

<!-- split-index -->

## Section index

- [触发](references/split-01-section.md)
- [数据采集三通道(全部实测验证,2026-08)](references/split-02-2026-08.md)
- [★纯 HTTP 采集通道（2026-08-17 实测，推荐方向——绕开浏览器反爬）](references/split-03-http-2026-08-17.md)
- [★游客模式 vs 登录态模式（2026-08-19 实测，作品列表触发条件）](references/split-04-vs-2026-08-19.md)
- [★App 协议（api16 tiktokv.com + X-Gorgon）移植结论（2026-08-19 实测）](references/split-05-app-api16-tiktokv-com-x-gorgon-2026-08-1.md)
- [★Linux 服务器环境指纹硬伤（2026-08-19 实测，\"用户网页空白\"的服务器侧真相）](references/split-06-linux-2026-08-19.md)
- [★tiktok-signature 签名服务探索（2026-08-19，部分可行，未最终闭环）](references/split-07-tiktok-signature-2026-08-19.md)
- [★服务器采集终极结论（2026-08-19 全路线穷尽，别再投入服务器浏览器方案）](references/split-08-2026-08-19.md)
- [★客户端作品同步通道（2026-08-19 已上线 v1.3.2，作品采集最终方案）](references/split-09-2026-08-19-v1-3-2.md)
- [Next.js 14 集成 CDP（工程坑,2026-08 实测）](references/split-10-next-js-14-cdp-2026-08.md)
- [Pitfalls](references/split-11-pitfalls.md)
- [产品闭环（CK 主通道,2026-08 用户拍板）](references/split-12-ck-2026-08.md)
- [★每账号独立代理 IP(用户明确要求,2026-08 补)](references/split-13-ip-2026-08.md)
- [服务端部署(headless 采集浏览器)](references/split-14-headless.md)
- [★生产 .env 变更不生效 = pm2 环境快照坑(2026-08 实测,通用)](references/split-15-env-pm2-2026-08.md)
- [支付启用链路(USDT TRC20 主通道,2026-08 验证)](references/split-16-usdt-trc20-2026-08.md)
- [提现链路（USDT 收款地址,2026-08 完善）](references/split-17-usdt-2026-08.md)
- [上线前文案清理(用户偏好:正式感)](references/split-18-section.md)
- [域名 + HTTPS 上线(Caddy,2026-08 实测)](references/split-19-https-caddy-2026-08.md)
- [★前端弹窗 fixed 定位被 backdrop-filter 劫持(2026-08 实测,通用 React/Next 坑)](references/split-20-fixed-backdrop-filter-2026-08-react-next.md)
- [★Cookie 有效性验证 = 官方 tokenBeatWeb 协议(2026-08-16 实测,wukong 参考,最终方案)](references/split-21-cookie-tokenbeatweb-2026-08-16-wukong.md)
- [参考](references/split-22-section.md)
- [给用户看 dev 预览的技巧](references/split-23-dev.md)
