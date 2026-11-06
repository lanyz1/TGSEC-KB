# round12: v9.8 全方案修复落地(初次拦截/补漏闭环,2026-09-06)

用户需求链:初次拦截率仅 69%(总靠补漏)→ 问能否"缺口→翻登录日志→换票→ST 补采"做到 100% → 批准按全方案修复。
**注意:SKILL.md 主体 orch8b 小节与"数据流频率(30min/近14天)"已过时,以本文件为准(前台会话请 patch 主体)。**

## v9.8 部署清单(全部上线验证)

| 组件 | 改动 | 验证 |
|---|---|---|
| sync_plat_enroll | cron 30→10min + **分级防抖** | ✅ 手动首轮:6 个小回退保留上轮名单、零整轮重拉、851 项目稳定 |
| orch8b | ROUNDS 4→8 + TIMEOUT 50min + cron 10min(3,13,23,33,43,53) | ✅ |
| bk_worker | seen 只锁命中者 + found 8→20 + CHECK_LIMIT=400 | ✅(orch 分发自动生效) |
| gen_gap | cron 10min(8,18,28,38,48,58) | ✅ crontab 已装 |
| merger | 不动(daemon sleep 120,落库延迟非初次拦截瓶颈,CPU 已 64%) | — |

全链路:报名 → sync ≤10min → orch 翻票 ≤10min → 补采落库,**总延迟 ≤20-30min,余量 3.5h vs token TTL 4h**。

## sync 分级防抖(代码级逻辑,替代 round7 的"任何减少都整轮重拉")

```
上轮快照 prev_full(含名单,不再只存计数)
shrunk = 企业数比上轮少的项目
  delta>=3        → need_repull:30s 后整轮重拉 + 并集兜底(保留)
  delta 1-2       → plat_shrink.json 计数(持久化 /data_pool/plat_shrink.json):
                       第 1 轮 → keep_prev:该 code 用上轮名单覆盖本轮(防 25↔24 抖动)
                       连续 2 轮仍少 → accept:接受为本轮(真减少),清计数
```
- 动机:接口行级抖动常态化(每轮 7-15 项目少 1 家);10min 频率下整轮重拉成本 ×2 不可承受
- crontab 装载坑:`bad minute` = 文件头带注释/空行/BOM → **纯 3 行无注释**再 `crontab <file>`

## bk_worker seen 锁死根因(本会话最大发现)

旧版:seen = {token: 登录时间},查过即记,**6h 不重查** →
```
企业登录(拿 token)→ 被 worker 查过(当时它还没报该 miss 项目,未命中)
→ 30min 后报名(同 token)→ sync 发现 miss → orch 再查
→ token 已 seen(锁 6h)→ 永不重查 → 永久缺口(除非重新登录换新 token)
```
修复(seen 结构升级 {token: {"lt": 登录时间, "hit": 0/1}}):
- **hit=1(命中并写库)→ 永久跳过**;hit=0 → 登录龄 >45min 后可重查(`_recheck_ok`: `str(lt) <= _cut45` 才 True,**比较方向是坑**,写反会永远不重查)
- 旧格式(token->字符串)迁移保守视为 hit(避免突然全量重扫;6h 自然清)
- 候选排序:新 token(_fresh)优先,重查(_re)只占 CHECK_LIMIT 余量

## business 域限速预算(必做,否则平台冷却)

orch 10min×8 台×全量扫窗的 user/info 推算 **~90 万次/天** → user/info 走 business-proxy(有风控冷却!)→ 爆炸。
→ CHECK_LIMIT=400/台/轮:400×8×144轮≈46 万/天上限,实际 found≤20 break 远低;全窗 1600 候选分 4 轮(40min)扫完,仍在 TTL 4h 内。
→ 平台真实容忍度未知:观察 3-7 天冷却日志(403/429/告警),触发则降频或缩限速。

## 取证驱动的初次拦截三分法(案例=北京局13次 20 家)

1. 公告页报名跳转(redirectEnrollUrl)入口 → 100% 秒拦(enroll 票可提取,4/4)
2. 其它入口报名 + 后续有 cg 域活动 → 活动票兜住(16/20)
3. 其它入口报名 + 零活动(津铁 9/1、欧锦 8:39、德裕隆 9:29、恒铁 9:32)→ **审计零痕迹 = 物理边界**,只等竞价日登录补

审计通道硬限制(实测钉死,勿再试):按 operation_account like/eq = 0 命中;按企业名 = 0 命中;**只能按 operation_details like(noticeId/projId/URL 片段)**;审计行 projId= 出现 0 次,报名行只有 noticeId → 反查必须用 notices_map 的 noticeId(round10b v9.7 已修)。

## 遗留与可优化(观察后再动)

- TTL 实测(ttl_measure.py 沪4 后台,每 5min 记录):17-18min 龄票仍有效;精确死亡龄出结果后校准窗宽(若 TTL<2h 则 orch 频率需回调)
- orch ctx 按报名时间新→旧排序(现按企业名字母序,浪费窗口)
- miss 名单 norm 双向映射(空格/括号差异 → 下轮重复补同一家)
- business 域总请求看板(orch/collector 共享计数,近红线自动降频)
