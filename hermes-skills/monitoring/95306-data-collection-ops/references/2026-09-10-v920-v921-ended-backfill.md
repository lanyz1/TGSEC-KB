# 95306 v9.20 / v9.21: /q 日期修复 + 已结束项目补全(2026-09-10)

## v9.20 — /q 日期静默放行修复(bot pix_bot_server.py)
- 根因: match_query 日期分支 `bt`(=bidStarttime‖projEndtime)解析失败 `except→return True` 静默放行 → 8161 个空日期已结束项目混入所有「状态+时间」查询(「已结束+今天」虚大 8132,真实仅 9)。
- 修复: 空/无效日期 `return False`(多格式容忍解析 std16/date10);`now` 由 `datetime.now()`(master UTC)切平台时间系 `_bj_now_dt()`(既有惯例;「近30天」参照 UTC/北京实测差 20 vs 10)。
- 实测: 已结束+今天 8132→9 · 已结束+近30天 8143→10 · 进行中+近30天=275 · 武汉+进行中=11(回归);三状态桶与直读计数逐项相等,空日期混入=0。
- 部署: md5 7d478018→87bcb1a0,bak_v920pre,重启 bot(kill/start 分 exec,~30s);probe 先证格式普查:空 8161/标准 13775/异形 0。
- 测试 harness 坑: 抽取线上 `_bj_now_dt`+`match_query` 源码 exec 时,ns 必须传 datetime **类**+timedelta(传模块则 datetime.now() 崩)。
- 脚本: Temp/{probe_bt, deploy_q_v920, test_q_v920, run_test_v920, restart_bot_v920, verify_bot_v920}.py

## v9.21 — 已结束项目"自动补全"(orch8b.py)
- 用户报: 已结束项目采集不完全,结束后不自动补全。
- 根因链(三层): ①orch8b 补漏目标只含 报名中/待竞价/竞价中(当天26h),已结束 continue → 项目结束=补漏停摆;②collector/gen_gap_projects 同口径(仅进行中),ent_coverage 只"已覆盖跳过"不"未覆盖重试";③残余缺口=双盲批量用户类(审计流无痕),唯一通道=登录流 token(bk_worker),通道随结束关闭。
- 量化(Temp/q2_quant.py,近30天已结束 497 个): 101 项目缺 741 家;24 项目 enterpriseCount=0 但名册有人;9 项目 pack_map 冻结。样本: 广铁30次 名册41/采1;西铁72次 缺40。
- 修复: orch8b 目标过滤增加 `elif stg == "已结束"` + bidStarttime≤30 天窗(与 plat_enroll 名册窗对齐);bk_worker/collector 零改动。原则:「结束后任何登录=补采窗口」(v9.10 竞价中逻辑的自然延伸)。
- 效果(部署后实测): 目标 208(进行中107+已结束101),miss 名集 131→481,涉及项目 105→209,已结束 pid 入 ctx。
- 部署: md5 b133cc7e→e64029ea,bak_v921pre;**cron 每5分钟自动加载新代码,无需重启**(部署后 ≤5min 生效,验证 = /tmp/bk8_ctx.json 名集数量 + 已结束 pid 出现)。
- 边界: 永不登录的企业补不了(物理极限);30 天窗外不再补。命中后经 getBuyPackageList 回填,观测指标 = orch log `企业N 项目写入N` / 预算看板 hits。
- 干跑脚本 Temp/q2_dry.py(复刻目标过滤,不派 worker)。
