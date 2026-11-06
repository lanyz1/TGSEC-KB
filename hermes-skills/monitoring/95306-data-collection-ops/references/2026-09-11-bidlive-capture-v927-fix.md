# 2026-09-11 竞价室 bid_live(💰实时出价) 从"从未产出"到 v9.27 修复

## 症状与取证(修复前)
- /data_pool 与 12 台机器本地 bid_live.json 均 = 0;机器日志 "出价数据已抓" = 0;SHARD0 当日 bid_req=4987 全空转;`except: pass` 全静默。

## 根因(三处)
1. **选票错**: try_fetch_bids 用单张 any_st(审计流最新票/上轮票)打每间房 `/bidRoom/initProjInfo` — 非"该场参与方"→ 平台 100/401 → 全灭。
2. **静默**: 抓取异常 except-pass、失败只记 1h 跳过集无原因 → 坏而不觉。
3. **搬运缺**: merger 无 bid_live 规则;且【重要教训】扫描器只认 `<pid>_pack_map.json`/`<pid>_项目信息.json` 固定后缀白名单,`<pid>_bid_live.json` 不进 projs 遍历,per-pid 复制块永不触达 → 必须放**全局 sweep**(直扫 RAW 下 `*_bid_live.json`)。

## 修复 v9.27(已部署)
- **collector**(`collector_v927_stage.py`, md5 `15cb51226b8dffe82e5ddd8eb9ccf547`, 12/12 `bak_v927pre`):
  - 选票链: 本轮票据(按 `ticket["proj"]` 匹配)> state `bid_tickets` 滚存(近6h, 每轮从 tickets 维护)> st_map[pid] 参与企业 ST > any_st 兜底;每室 ≤5 票。
  - 失败分类日志(`出价未获 <pid>: 试N票 末因[code]`)+ 轮总结(`出价抓取轮: 尝试N 成功M 无票K`)。
  - 部署器 `deploy_v927_fleet.py`(jumpers.json 遍历, key优先密码兜底, md5 校验+备份+restart+is-active)。
- **merger**(两处, `bak_v927pre`/`bak_v927bpre`): per-pid 块 + **merge_all 尾部全局 sweep**(日志 `bid_live 搬运: N 个项目`)。
- 验证: 搬运实弹(合成 `<pid>_bid_live.json` → 150s 内入池 → 已清场);抓取首轮日志正常输出(当时无活票,成功0 属预期)。

## 待验与下一迭代
- **09-12 09:00 乌局72次(pid f9f4e392-4aeb-45f1-a704-f289451267fc)**: 一次性哨兵已挂(10:42 报)。
- 若日志仍 `试1票 末因[100]` 全灭 → 竞价室"进场票"未进审计 tickets:下一迭代 = 竞价室进场票源挖掘(审计 detail 是否有 room ST / TQ 进场票如何按房间匹配)。
- 相关: 8515 快照(current_price 字段实测空)不能替代 bid_live。
