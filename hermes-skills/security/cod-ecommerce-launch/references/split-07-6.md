## 6. 营销配套

- **斗篷风控**(11 规则引擎/回流页/HMAC 管理员放行/测试方法): 见 `references/cloak-risk-control.md`
  - **坑: 管理员放行检查必须在黑名单检查之后且 `return []`(不是 return $hits)**——放行优先级最高, 否则被自动拉黑的 IP 登录后台后访问落地页仍被拦(修复: `if (cloak_back_ok()) return [];`)
- **Meta Pixel + CAPI 回传**(Graph API v20/SHA256 哈希/多像素/测试事件): 见 `references/cloak-risk-control.md` 第二节
  - **CAPI token 配置与实测**(用户提供 Pixel ID + token 后): ① 后台 pixel save API 写入 → ② 商品页 `grep -c <new_id>` 应 >0 且旧 ID 残留 0——**旧 ID 残留位置在 SKU JSON 的 `fbpixel` 字段**(商品自带兜底), 需同步 `UPDATE dr_pro SET fbpixel='["<new_id>"]'` → ③ `graph.facebook.com/v22.0/debug_token?input_token=<t>&access_token=<t>` 验证 token: SYSTEM USER + `read_ads_dataset_quality` scope 也能发 events(实测 HTTP 200 `events_received:1`)——**Dataset Quality 只读 token 足够 CAPI 发事件**, 不需要 ads_management; ④ events 端点 v20.0 在 2026-08 仍可用, 不必急着升 API 版本
- **Telegram 订单通知**(后台配置 + getUpdates 自动 chat_id + 下单挂钩): 见 `references/tg-order-notify.md`
- 品牌改名: 全站 grep 目标词 → 批量替换源码文件 + 删除 curl 测试残留 html → 同步服务器 → 服务器 grep 残留=0 验证。

