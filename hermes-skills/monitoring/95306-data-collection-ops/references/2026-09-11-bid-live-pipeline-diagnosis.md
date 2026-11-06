# 2026-09-11 竞价室详情监控(bid_live / 卡片"💰实时出价")诊断 — 从未产出, 修复未实施

## 功能定位(先分清两个"竞价监控", 用户问的易混)
- 菜单B「🔥 竞价监控」(bidwatch / bidday:时间范围) = **列出**竞价项目 —— 这条正常。
- 「竞价室详情」= **单个项目**的实时出价详情: bot `fmt_proj_card`(pix_bot_server.py ~452) 读 `/data_pool/<pid>/bid_live.json`,
  有 `data` 才显示"💰 实时出价: 抓取于 <时间>", 否则"暂未抓到出价数据"。
  - 用户原话"那个具体看某个竞价室详情监控那个" = 指这条; 问"竞价室监控"时先确认是列表还是详情。

## 现状取证(2026-09-11 晚, 全环节实测)
- `/data_pool` bid_live.json = **0**; 采集机本地 `/tmp/targets/*/bid_live.json` = **0**; 日志"出价数据已抓" = **0**
- SHARD0 机器 `/tmp/v6_cstats.json` → `bid_req` = 4987/日, 产出 0（持续空转）

## 链路与三处断点(collector写 → rsync上传 → merger并入池 → bot读)
1. **抓取侧(根因)**: `collector_v926b_stage.py` `try_fetch_bids(any_st, targets, state)`（调用点 ~1524; 仅 SHARD_ID%4==0 三台执行, 30min 节流）:
   用**"任意一张 ST"**打 `/bidRoom/initProjInfo?projId=<pid>`, 而平台校验**该场次参与方会话**(或内部账号) →
   全被拒 → 记 skip 1h → 换一张票继续失败, 永久空转; 端点实测 401/被拒。
2. **静默失败**: 抓取异常 `except: pass`、无权限仅记 skip 不记原因 → 坏了很久无任何告警(可观测盲区)。
3. **搬运侧**: `merger.py` 无 bid_live 搬运规则（对照: bid_status 有 v9.25 专门并入池补丁, merger.py ~423）→
   **即使抓到也到不了池**, bot 卡片永远"暂未抓到出价数据"。

## 修复计划(3 补丁 — 待用户 GO; 尚未实施/未验证, 勿当已完成)
1. `try_fetch_bids` 按房间挑票: 从该项目报名企业 ST / 竞价日进场票中挑**该房间参与者**的会话; 无票不空转
2. merger 仿 v9.25 bid_status 增加 `<pid>_bid_live.json` → 池 搬运
3. 抓取失败打日志+计数（可观测）

## 验证时机
- 任一竞价开始后的房间（SHARD%4 的三台在窗口内尝试; 下一场: 09-12 09:00 乌局72次）
- 补丁前可先用**已关闭房间**验证搬运链(手工放一个 bid_live.json 走 merger)
- 相关: 「竞价室关闭即并入已结束」v9.18; bid_status 链正常(参考文献 2026-09-10-v925-audit-status-pipeline); `/bidRoom/*` 端点全表见 2026-09-11-priv-token-loop-and-blindspot-solution.md
