# 盲测集（2026-10-22，12 条，**已烧**）

用途：验证「调过的 eval_core 是不是自我感觉良好」。这 12 条在补词前从没进过任何评测集，跑法：

```bash
cd /root/.hermes/arsenal
SKILL_FIND_NOLOG=1 python3 skill_find.py "<query>" --top 3 --fast
```

| # | 现场说法 | 期望 TOP1 | 首轮实测 |
|---|---|---|---|
| 1 | 扫出来一个 8080 上面是 druid 监控台 没密码 | `druid-console-unauth` | ✓ |
| 2 | 登录以后 cookie 里有个 jwt 想改 alg 试一下 | `jwt-bypass-pentest` / `jwt-attacks` 家族 | ✓（`jwt-oauth-token-attacks`） |
| 3 | 客户给了个 apk 让我看看有没有硬编码的 key | `apk-recon` / `mobile-hardcoded-key-decrypt` | ✓（`apk-recon`） |
| 4 | thinkphp 5.0 老站有 rce 但被宝塔 waf 拦了 | `thinkphp5-rce-and-bt-waf-bypass` | ✓ 正中 |
| 5 | 支付回调 signature 能伪造吗 | `payment-callback-forgery` / `callback-signature-forgery` | ✗ `new-postures-2026-q3` 抢位 → 修后 ✓ |
| 6 | 小程序抓包发现走 uni-app 后端在哪 | `apk-backend-pentest` / `mobile-app-pentest` | ✓ |
| 7 | k8s 里 pod 能不能逃出去 | `k8s-container-escape` | ✓ |
| 8 | 目标只开了 443 想找源站 | `cf-hidden-origin-tracing` / `cloudflare-bypass` | ✓ |
| 9 | 后台是若依 想从定时任务打 rce | `ruoyi-quartz-whitelist-bypass-el-rce` | ✓ 正中 |
| 10 | tg bot token 泄露了 怎么接管 webhook | `tg-bot-token-webhook-fullchain` | ✓ 正中 |
| 11 | redis 未授权 怎么拿 shell | `redis-attack` / `redis-restore-rce-cve-2026-66373` | ✓ |
| 12 | grafana 默认口令进去以后能干嘛 | `monitoring-plane-unauth-recon` | ✗ `auth-brute` 抢位 → 修后 ✓ |

首轮 **TOP1 10/12、TOP3 12/12**；修完单字权重 + 两张空 tags 卡后 12/12。

**这 12 条已经用来修 bug，不能再当验证集**（再跑 12/12 是循环论证）。留作回归集：以后动打分/加词，跑它确认没把这两条修好的又打回 rank2。新验证必须另写 fresh 题。
