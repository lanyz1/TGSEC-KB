# 漏采/补采机制 —— 手搓版现役口径

2026-10-07 用「代码原文 + 主控 `crontab -l` + 现场日志」三方实证固定下来的口径。**回答用户「现在的漏采补采机制是什么样的」时照这份讲,不要照旧卡里的 `orch8b.py` 口径(那是老生产)。**

一句话:主控每 10 分钟算一次「该采但库里没有」的清单(**企业名级 + 账号级**两种),每 5 分钟把名册推到 12 台按 6h 窗逐台点名补齐;手动补采走 bot 按钮 → 队列 → 点名一台机 force 重拉。

```
① 判缺口  gapgen  [master/gapgen.py]
   遍历 /data_pool/<pid>/项目信息.json → 产物三件(原子写 tmp+os.replace):
     ① 在网项目里「有单位名、包件为空」的企业  → /opt/v6/gap_projects.json (人看)
     ② gaps.json「企业报名缺口」的账号          → /tmp/bk8_ctx.json (名册,下发采集机)
     ③ 已定稿的「账号×项目」                     → /opt/v6/cov.json (覆盖基线,免重拉)
   ★红线:本层只产清单,绝不写 pack_map(写入口只有 master/writer.py)
   ★在网判定 in_network = 阶段 ∈ gap.live_stages(默认 报名中,待竞价,竞价中,待发布)
   ★覆盖基线 coverage():进行中项目永不进基线;已结束 + (记录时间 ≥ 竞价开始 或 竞价开始已过 ended48_h=48h)
     且包件非 PROJ_LEVEL 占位 ⇒ 视为定稿,orch/bot 不再重拉
② 派活    两腿,都走主控 ssh 点名一台机 + 先推名册(cat > /tmp/bk8_ctx.json)
   orch      master/orch.py      2-59/5(每5分)  按项目补齐腿
                                 → 采集机 tools/gap_once.py <ctx> <shard>
                                 12 台 × window_min 30min = 6h 一圈;结果按 projId → writer.apply()
   backfill  master/backfill.py  */30 + timeout 900   票池深翻页腿
                                 → master/bk_worker.py（塞进 ctx 下发,worker 里零魔法数字）
                                 结果按【企业全名】索引 → writer.apply_named()
   ⚠️ 两腿输入形状不同(projId vs 企业名),混用 = 池里凭空多一批空目录
   ⚠️ 入口必须取【机器上的代码树根】[gap] remote_root(默认 /opt/v6/current)+ tool,写死扁平路径
      /opt/v6/tools/gap_once.py 会 12 台每轮 can't open file(2026-10-04 真机事故,腿静默瘫痪)
   ⚠️ 派发失败【不许回 started】——否则把「派发失败」记成「已触发」
③ 采集侧  collector/gapfill.py（必须在境内采集机出口打;主控 US IP 直连 403）
   先收割票(平台 ST 寿命 ~6h) → 匹配三条(缺一条就永久漏采):
     ① 全名 dwhz 归一后与名册 full 一致
     ② 简名唯一包含(包含在多个全称里 ⇒ 放弃,宁愿漏不错配)
     ③ uid 直命中 accts(dwhz 为空时不入库,防污染单位名)
   → 拉 getBuyPackageList → ★【包件真的拉到并写进 pack_map 之后】才把票标「已用/永久跳过」
     (探活命中 ≠ 采集成功;提前标死 = 该企业永久漏采,这是 v9.26 修复的核心)
```

## 两个触发口

- **自动**:cron → gapgen → orch / backfill(名册驱动,采集机不做任何判断 —— 缺口口径只有一个来源)。
- **手动(单项目粒度)**:bot 项目卡「🔄 补采包件」→ `bot/commands.repack_one` **只写请求文件**(原子写)→ `repackq`(cron `*/2`)消费 → 借 orch 的 ssh 通道点名一台机跑 `tools/repack_once.py`(**force=True 强拉该项目公告/包件清单**)→ 结果写 `done/<pid>.json`,bot 再点同一按钮就读它。请求/结果目录在**树外** `/opt/v6/repack_req`、`/opt/v6/repack_done` ⇒ 换树不丢。
  手动单跑:`v6m.py repackq --pid <36位pid>`;只看会下发谁:`--dry`。
  ★**架构红线**:bot 是只读消费者,真动作只在主控/采集机侧;`apply_enable=0` 时 bot 只回执零写。
  ★force 必须两处一起绕:`Targets.details` 对「已有包件清单」和失败退避**双重跳过**,只绕一处真机仍被退避挡住。

## 主控 cron 原文(2026-10-07 实测)

```
8,18,28,38,48,58 * * * * cd /opt/v6 && flock -n /tmp/v6_gapgen.lock   python3 /opt/v6/v6m.py gapgen   > /tmp/gen_gap.log 2>&1 < /dev/null
2-59/5           * * * * cd /opt/v6 && flock -n /tmp/v6_orch.lock     python3 /opt/v6/v6m.py orch     > /tmp/orch8b_cron.log 2>&1 < /dev/null
*/30             * * * * cd /opt/v6 && flock -n /tmp/v6_backfill.lock timeout 900 python3 /opt/v6/v6m.py backfill >> /tmp/bk_multi_cron.log 2>&1
*/2              * * * * cd /opt/v6 && flock -n /tmp/v6_repackq.lock  python3 /opt/v6/v6m.py repackq  >> /tmp/v6_repackq.log 2>&1
```

角色分发 `deploy/master_launcher.py`:`gapgen→master.gapgen` / `orch→master.orch` / `repackq→master.repackq` / `backfill→master.backfill`。机队清单读 `paths.jumpers` = `/opt/v6/jumpers.json` 的 `collectors[]`(**不是 `boxes`**;两个键都认 collectors 优先,旧写法只看 boxes ⇒ 永远取空、静默什么都不做);逐台 ssh 必须带各自 port(宁波 25175)。

## 现行读数(答「现在有没有待补」)

```
/opt/v6/gap_projects.json  → 生成时间 / 项目总数 / 在网项目 / 缺口企业数 / 缺口账号数 /
                             覆盖基线_账号 / 覆盖基线_条目 / 缺企业[] / 缺账号{} / 项目[]
/tmp/bk8_ctx.json          → names[] + accts{}（空名册 ≈ 91 字节 = 无待补)
/opt/v6/master_state.json  → orch 每轮汇总（已触发/超时/命中/落库/验票）
/data_pool/gaps.json       → 五段:项目包件缺口 / 企业报名缺口 / 待确认缺口 / 疑似仅打开页面 / 采集机告警
```

2026-10-07 11:38 实测:项目总数 14379 / 在网 175 / **缺口企业 0、缺口账号 0**、名册 91 字节、覆盖基线 1702 账号 / 67073 条目;orch 11:38-11:39 逐台触发 shard0-5（窗口 30 分钟）;backfill 11:35 逐台回写;repackq 成功补 1 项目 `n_new=1 packs=5 秒=7 box=8.133.188.178`。

## ★为什么「名单有、库里没有」的历史真缺不会被自动补(必答点)

两条自动腿对它**都不成立,且不是故障**:

1. **在网腿**:`name_gaps()` 只遍历 `in_network` 项目(阶段 ∈ live_stages);项目 `stage=已结束` ⇒ 直接 skip。
2. **账号腿**:`enroll_gaps()` 只消费 `gaps.json` 的 `企业报名缺口` 段,而该段判据(`master/gaps.py::_enroll_one`)要求**审计里有真实提交证据**(`pid ∈ evid` 且 `unit ∈ evid_units`);没证据的只落 `疑似仅打开页面` —— **只记账不告警**(怕误报淹没真缺口)⇒ 条目数恒 0。
3. 另:平台报名名单 `plat_enroll_map.json` 报名期一结束该 projCode 键就消失 ⇒ 平台侧差异腿也填不上;`gaps_packs()` 的包件差集只对**有 `平台侧_8515.json` 且有 packId 差**的项目成立(且 `pack_ids` 只记 `miss[:10]`,别当全集)。

⇒ 结论口径:如实告诉用户「这类缺 = 无可用票 / 项目已出在网定义域」,**不给虚假希望**;要补只能走手动口 `v6m.py repackq --pid <pid>`(force 重拉)或按名单定向 `backfill`。

## 审计/巡检要点

- **缺口只认一个口径**:`gaps.json` 由 `merger::write_gaps`(`master/gaps.py` 五节)产,`gapgen` 只**消费**它的 `企业报名缺口`,不自己再算一遍 —— 两边各算一遍必然对不上账(老生产踩过)。
- 判活:`tail /tmp/orch8b_cron.log`(应有逐台「已触发 … 窗口 30 分钟」)/ `tail /tmp/bk_multi_cron.log`(「回写 …：企业 N / 新账号 N / 新增包件 N / 跳过 N」)/ `tail /tmp/v6_repackq.log`(「补采 <pid> … {"ok":true,…}」)。
- 名册是**主控唯一产物**:采集机上 `/tmp/bk8_ctx.json` 只是收到的副本;「采集机自己算缺口」= 反架构。
- 一切改动(闸门、口径、force 绕行)改完必须复跑结构闸+离线桩再谈发布;**发布/激活/重启是生产闸,须用户点头**。
