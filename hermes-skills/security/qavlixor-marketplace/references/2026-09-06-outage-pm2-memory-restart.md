# 2026-09-06 线上告警排查：PM2 max_memory_restart 重启循环（根因链完整版）

## 告警形态
monitor-production.mjs（每 5 分钟 cron → /var/log/tiktok-monitor.log）报：
"网站无法访问（TypeError: fetch failed）+ 应用未在线（waiting restart）"
（告警时刻 09-05 16:45 UTC；monitor 日志同一分钟：`http: None | pm2: waiting restart`——完全吻合）

## 排查顺序（实例验证，按序执行）
1. **当前探针** curl -w '%{http_code} %{time_total}'（区分已自愈 vs 还在挂）
2. `pm2 list`（uptime/↺）+ `pm2 jlist`：`restart_time` **累积不清零**（1173 是历史值勿当近期）；`unstable_restarts=0` ⇒ **不是崩溃重启**（是 max_memory_restart 或手动）
3. `pm2 describe` → **`max memory restart 1677721600`（1600MB/实例）**——内存涨破即自动 kill+重启
4. **`/root/.pm2/pm2.log` 守护日志直接写原因**：`Process N restarted because it exceeds --max-memory-restart value (current_memory=1714311168 max_memory_limit=1677721600)`；`App exited with code [0] via signal [SIGINT]` = 正常 kill 流程
5. **monitor 日志 = 时间线金矿**：`grep '2026-09-05T1[67]:' /var/log/tiktok-monitor.log` 逐条还原告警前后（http 状态/pm2 status/restartTime）
6. **根因层**（为什么内存涨破）：nginx access.log 看 UA/IP 分布——**SEO 爬虫潮**（AhrefsBot 单 IP 107 次/天 + PetalBot/Applebot/Googlebot/curl 高频 SSR 商品页）顶破 1.6GB → 每 15-30 分钟一台重启，重启窗口（kill→冷启动 10-60s）内无响应
7. **噪音项**：`pm2 logs --err` 刷 `[machine-translator] API 请求失败: 402 balance is insufficient` = SiliconFlow 余额耗尽；**不影响主功能**；err 日志文件跨重启累积（1352 条 ≠ 实时速率）

## 关键认知
- 机器内存充足（16GB 9.5GB free）≠ 无重启：这是 **PM2 主动阈值**（每实例 1.6GB），不是系统 OOM——dmesg/journalctl 查不到
- restart×2 是 deploy.py 部署正常行为（凌晨 02:18-02:52 批量创建时间 = 部署痕迹）
- 系统 cron（run-scheduled-tasks 每 10 分钟 + monitor 每 5 分钟）日志全 ok ⇒ 排除定时任务因素
- 站点"活着但 4-6s 慢" = 爬虫潮 + 实例频繁冷启动的常态

## 应对方向（已与用户确认，待执行）
1. PM2 max_memory_restart 1.6GB → 2.5GB/实例（16GB 机器：4×2.5=10GB 可承受）→ 重启频率大降
2. nginx 爬虫 UA 限速 + 商品页缓存头（治本）
3. machine-translator 402 熔断（失败冷却 10 分钟不再重试，防日志刷屏）
4. SiliconFlow 充值（最低 $5）或暂停翻译（用户拍板二选一）

## 附：SSH 访问方式变更（重要）
- 2026-08-12 起生产 SSH 密码登录已禁用，改 **ed25519 密钥 `~/.ssh/qavlixor_prod`**
- deploy.py 已内置 pkey 优先 + 密码回退
- 注意：user-owned skill `qavlixor-prod-ops` 的"密码见 %LOCALAPPDATA%\Temp\_run_q_*.py 明文;勿禁 root 密码"段落**已过时**（密码已禁），该 skill 待 adopt 后修正
