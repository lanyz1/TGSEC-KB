# 漏采追查 Playbook(公司/项目级)+ 采集出处溯源(2026-09-11 定稿)

## 触发
用户问"XX公司的报名包件漏采了/补采一直没采上,什么情况" 或 "这条是哪条ST抓出来的/详细找出来给我"

## 公司级漏采四步法(全在主服执行)
1. **名册定位**: /data_pool/plat_enroll_map.json → projs[code].企业[] 搜公司名 → 得项目code/公告日
2. **待补定位**: /data_pool/miss_current.json → proj_miss(阶段/pid/缺的企业清单) + miss_all(名→[项目名])
   (刷新方法=重跑 miss 复算,orch8b 同款: 名册企业 − pack_map 单位, _norm 归一)
3. **档案画像**:
   - /data_pool/企业档案/<单位>.json → 项目数/包件数/历史记录列表(2023前老数据迁移,"01三态+映射链")
   - /data_pool/供应商/<单位>.json → 信用代码/法人/联系人/手机号/注册日期(谈账号直登时给用户看)
   - /tmp/bk8_ctx.json → {miss_names, miss_map: 公司名→[pids]} 补漏工作器目标映射(证明系统"知道"它缺)
4. **票源实证(关键)**: 扫 TQ(tokenrailquery) 近 1~3 天整点窗(逐小时, pageSize 500), 行内搜 username/userid 关键词
   - TQ 行全字段: **username(企业显示名,如"翎博物资")**/userid/token/login_mode/user_type/login_time/return_url/id/login_media/ip/memo
   - 工器匹配 = miss_norm 归一 + v9.23 简名子串索引, 按行 username 命中→拉 getBuyPackageList
   - **0 命中 = 该公司无增强认证登录 = 补采无米下锅(双盲样本,非故障)**; 同时查审计类: audit_changed.json + gaps.json 采集机告警

## 结论框架(回复用户用)
- 名册有+池无+票源0 → "批量/直报+无增强认证"双盲样本; 收敛路径①竞价日进场(强制二次验证→TQ行→自动采) ②用户提供账号直登(秒采) ③特权会话线命中后批量回填
- 典型实证: 乌局72(OR002026083111104157) 15家报名/14已采/**仅陕西晨易阳1家待补**, 其 09-09~09-11 三日 TQ 全零

## 报名总表(bot 融合表, 用户最常看的视图)
- 位置: /data_pool/汇总/报名总表_<projCode前20>.csv (pix_bot_server.py 动态生成, 菜单📋projents 可见)
- 语义: **平台权威名册做基底 + 我方数据填充**; 未采企业留原位标 **⏳待补** / 已采标 ✅已采
- 列: 数据状态,报名时间,企业全称,**登录账号**,联系人,法人,手机号,包件编号,包件名称,竞卖保证金,审核状态,报价模式,物资条数
- 覆盖统计速法: csv 读入按"企业全称"聚合数据状态 → "N家已采/M家待补"

## 采集出处溯源("哪条ST抓的")
- pack_map 条目字段: 账号/用户/单位/**ST**/时间/**来源**/包件[](每条=某账号×某项目)
- 通道判定:
  - 来源=None 且带 ST → **采集机 collector 通道**(collector_v926b 写入,存完整32位ST)
  - 来源=backfill8(ST空) → **补漏 worker 通道**
  - 来源=01三态+映射链 → 历史迁移
- 上传落点: /data_raw/<机器名>/<pid>_pack_map.json; 事件级追: grep ST串 /tmp/bk_pool/<pid>/pack_map.json 与 /tmp/bk*.log
- 交付格式: 时间|单位|账号|完整ST + 通道判定(用户要"详细"就给全32位hex, 别截断)

## 用户词汇表(防误读, 2026-09-11 踩过)
- **"竞价室监控/竞价室详情监控" = 项目卡片里的 💰实时出价(bid_live.json) 那条**, 不是 stage 总览/场次统计!
- "报名包件" = 企业×包件(账号/保证金/审核状态)数据; "待补/漏采" = miss 集(名册有-采集无)
