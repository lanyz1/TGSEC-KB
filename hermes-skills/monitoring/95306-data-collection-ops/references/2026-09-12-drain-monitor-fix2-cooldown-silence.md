# 2026-09-12 fix2: drain 监控判读修正 + 冷却静默 ≠ stall

## 现象
cron `v6-drain验证监控`(e93ac7f7b11a,*/10min)在 20:34 / 20:40 两轮里,青岛 sh6 的 tail 一直是
`20:29:50 轮询完成 ... 识别 1`,看着像 11 分钟没动静(疑似卡死/被 SSH 封)。

## 实证(经主服 128.241.245.73:12971 跳转,只读)
```
host=iZm5e9h0a1iicizpqiw6mmZ date=2026-09-12 20:44:57
-- unit: active / Sat 2026-09-12 06:07:01 CST
1113706  14:37:56  /usr/bin/python3 /opt/v6/collector.py      # pid 未变、无重启
journal 20:30:18 审计 ST 45, 新 0
        20:43:51   ↳ 候选 0(new_t 0) → proc 0 (新0/重试0)     # 复活
        20:44:44   ↳ 风控响应 [/user/info]: code=100 msg=系统服务异常，请联系技术支持！
        20:44:44 🧊 触发风控冷却 15min(business 域暂停,审计继续)
        20:44:44   ↳ user/info 冷却(...) → 退避30min复活
        20:44:44 🧊 冷却升级(w<PHONE-REDACTED> 当日第12次): 冻结到次日 09-14 00:10(北京)
```
→ 20:29:50→20:43:51 的"静默"是 15min 风控冷却(退避),**不是 stall**。

## 根因(脚本盲区)
`verify_drain_monitor.py` 的远端 grep 只匹配 `候选|入队|榨干|gap|识别到|识别 N|轮询完成`,
`风控/冷却/冻结/退避/审计 ST` 全被滤掉 → 冷却期自然"无日志";
且收尾截断是 `body[:1600]`(**丢最新、留最旧**),长行机器会把最近行切掉。

## 修法(已落地)
```python
j=$(journalctl -u v6collector --no-pager -n 300 2>/dev/null | grep -aE '候选|入队|榨干|gap|识别到|识别 [1-9]|轮询完成|风控|冷却|冻结|退避|审计 ST' | tail -12)
...
parts=[x.strip()[:190] for x in raw.splitlines() if x.strip()]
body=" / ".join(parts)
if len(body)>1600: body="…"+body[-1599:]     # 丢最旧、留最新(含末尾 DRAIN/SEEN 行)
```
验证:py_compile 通过;按新 grep 手工经主服复扫 sh6/sh7/sh10,风控/冷却/审计行全部可见,新4台(sh8-11)走 `/opt/v6/v6_run.log` 分支正常。

## 判读顺序(定论)
1. 看有无 `风控/冷却/冻结`(有 → 上游账号冻结,非管道);
2. 看 SEEN 是否推进(不推进 = 同批票重生 churn);
3. 看 drain 入队/榨干 + DRAIN 总量(09-12 全天稳定 241 条 = 无票被搁死,#8 修复无回退);
4. 都正常才怀疑管道;某台 tail 陈旧先用原机 grep 复扫再下结论。

## 本轮(20:23–20:46)机队状态
- 12/12 SSH_OK,心跳 17–29s,无 ERROR/SSH_DOWN;
- 无 `drain 入队`/`📦 榨干`,DRAIN 合计 241 不变;
- 候选>0 仅 sh10 乌兰(sh10 20:35–20:45 候选 2→proc 2 连续 8+ 轮,识别 0;伴随
  `冷却升级(liujie00777 第161次 / whsentie 第165次 / xgxhadmin 第26次)`→ 冻结到 09-14 00:10);
- sh6 20:29:50 识别 1、sh11 20:34:46 识别 1(均上一轮已报);
- 审计 ST 45 稳定(20:29 深圳 502 抖动已自愈)。

## 21:03 复扫(cron 轮次):全队静默 + sh10 候选 2 + UNFIN 挂起
- **投递截断坑**:cron 投递的 monitor 输出只到 sh5 就被截断(其余靠 `… [output truncated]`),
  判读前必须重跑 `python scripts/verify_drain_monitor.py`(或读 `scripts/_drainmon_*.txt`)拿全 12 台,
  否则会把 sh6-11 的候选/冷却/失联全看漏。
- 12/12 SSH_OK,心跳 30–67s,无 ERROR/SSH_DOWN(21:03 无 SSH 封禁迹象,无需提腾讯云安全组)。
- 本轮窗口 20:53–21:03:全队 0 入队 / 0 榨干 / 0 识别;唯一非零候选 = 乌兰 sh10
  `21:02:12 审计 ST 43, 新 2` → `候选 2(new_t 2) → proc 2 (新2/重试0)`(21:03:25 复现),识别 0
  —— 因该机池账号持续冻结(whsentie 第179/180 次、liujie00777 第176 次,冻结到 09-14 00:10 北京)。
- **#8 指纹复核**(`scripts/_drain_fix_verify_2105.py`,只读:md5sum + `_my_acct` 计数 + state drain UNFIN):
  12/12 `collector.py` MD5=`15cb51226b8dffe82e5ddd8eb9ccf547`,mtime 09-11 22:33–22:36,`_my_acct`=2
  → 去二次分片版本在位、未被回滚。
- DRAIN 分布(sh0→sh11):16 / 23 / 24 / 15 / 22 / 16 / 17 / 24 / 25 / 18 / 24 / 16 = **241**,
  UNFIN=0 除 **sh10 UNFIN=2**(GK8685, ZZ<PHONE-REDACTED>,已挂 >1.5h,随账号冻结;解冻后仍不消化才算 drain 卡件)。
  13:31 合计 511 → 21:03 241,队列在正常消化。
- 判读纪律:窗口内出现「候选>0」就按机制生效证据上报(即使识别 0);纯 0 才静默一行。

