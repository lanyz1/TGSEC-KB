# 2026-09 审核假波动/状态机规则/UI合并 修复记录(后段)

## 1. "审核通过 9→7" 逆向波动 — pack_map 冗余键重复计数(区别于原子写抖动)

- 症状:十堰项目推送 "✅9→7"(审核数倒退),数分钟后又回 9 → 不是真实审核回退
- 根因:pack_map enterprises 里**账号键(现行)与中文单位键(历史导入遗留)并存**(13 键=10账号+3单位冗余,同一批企业)。`check_status_summary` 遍历全部键 → 重复计数(9=7账号通过+2冗余通过)。不同写入者重写时冗余键时有时无 → 计数在 7/9 间抖
- 修复:check_status_summary 统计前 `merge_ents_by_unit(pm["enterprises"])`(同单位多键合并、包件 packId 去重、账号键优先)→ 菜单列表(L1257)与 3min 监控推送(L4054)共用此函数,一处修全局生效
- 验证:十堰去重后 = 通过7/未审批3(10家真实企业),稳定
- 通用教训:**对 pack_map 做任何计数前先按单位合并**;冗余单位键本身可留(展示层已 merge),统计层必须去重

## 2. 菜单B 范围业务规则(DEPLOY_DAY,用户强制,勿自改)

- 菜单B"可拦截项目"**只收公告日 ≥ 2026-08-31(部署日)项目**;部署前公告=报名真空期,数据不完整,不进菜单B——用户明确纠正过"部署日过滤依旧要筛选,不能放开"
- 放开过滤的后果:8/24-26 公告老项目 82+ 涌进 🟡(用户问"怎么突然多了这么多")
- 中间地带(8/31前公告但报名截止在8/31后,如合肥 8/28公告9/3截止)已被挡在菜单B外;若用户要纳入,规则应为"公告日≥DEPLOY_DAY **或** 报名截止≥DEPLOY_DAY"(纯真空项目仍排除)——**待用户拍板,不要自作主张**
- 恢复过滤后 🟡=0 属正常:部署后公告项目最早 9/5 才截止(报名截止分布决定 🟡 增长节奏)

## 3. merger._stage_of 推导缺陷 + 703 事故(改 stage 判定的教训)

- merger(由 bot subprocess 每 ~2.5min 调,index.json updated 实时更新)全量重算 stage;`_stage_of` 纯时间推导(status 仅 14 判已结束)
- **原缺陷**:报名截止(sellEnddate/公告解析 regEndtime)缺失时直接落 "待竞价"(有 bidStarttime 即猜)→ 报名中项目被提前切 → 进 🟡 候选 → 采集齐即被误标"采集完成"(成都项目提前进✅的根因)
- **1b 补丁事故**:补丁写 `if not sell and st in ("19","22"): 22→待竞价` → **历史导入项目残留大量 status=22 → 2021-2025 老项目全被标待竞价 → pb 飙到 703**
- 正确修复:只认 `st == "19" → 报名中`(保守);22 是"待竞价/报名中混合"语义,**不可作"报名已结束"特判**
- 修完手动触发 `python3 merger.py` 重算(注意与 bot 周期调用并发,原子写兜底)→ pb 回落 703→88

## 4. 采集完成判定硬门槛

- collect_complete_projects(✅组):无论 stage 因何进入 🟡,**regEndtime/sellEnddate 未到(北京时间)一律不算完成**(归 open_,截止后才可能 ✅)
- 验证:构造 reg=2099 但 stage=待竞价 → done=0 open=1 正确拦截

## 5. 平台状态滞后实测 + 时区铁律

- 报名截止 2h 后 selectSelfSellList 仍返回 status=19(发布中)、sellEnddate=None → 平台状态流转滞后是常态,**时间推导(regEndtime 已过→归 🟡)是必要兜底,不能等平台**
- 时区:平台时间为北京时间(UTC+8),主服 datetime.now()=UTC → 比较前必须 `datetime.utcnow()+timedelta(hours=8)`(bot 内 `_bj_now_dt()`;merger/orch8b 同)

## 6. TG send_msg >4096 字符静默失败(用户"点按钮没反应")

- 症状:点"📋 报名总表"无任何消息,日志只有 CB 行;bot 其他功能正常
- 诊断路径:①日志看 CB 到达 ②本地 import 实测渲染函数(正常,1.8s 出 4688 字符文本)③**len>4096 → tg_api 400 被吞**
- 修复:send_msg 开头加超长分支——按行切段(每段≤3800,行边界切防断 Markdown),键盘只挂最后一段,递归发送
- 通用:TG 消息上限 4096;任何长列表渲染都要过这段

## 7. 菜单 A/B 合并的导航一致性检查清单

- main 回调/start 改指 menu_b 后,**必须全库查残留导航**:menu_b 底部"🅰️ 返回完整菜单"(main)成自循环 → 改为"⚙️ 设置中心"(新回调 menu_a → user_center 精简版);"🔙 返回用户中心"按钮(3处)→"返回项目总览";main_menu() 是死代码
- TG 左下角命令菜单(setMyCommands,不在代码里):用 bot token 调 getMyCommands 查旧配置 → setMyCommands 换新(删除无处理的死命令如 /today /status,补 /ai /q /live /watch);TG 客户端缓存,重开聊天生效
- 推送落款/更新公告/搜索引导/help 文案同步("菜单B"→"项目总览","报名明细"→"报名总览","查看用户中心"→"打开 📋 项目总览")

## 8. 性能:norm_ent_name 线性扫 36.9 万供应商名单

- norm_ent_name 原实现每次全量 for _sup_names()(369,412 条)比较 → collect_complete 91 项目 × N 企业 → 数亿次比较卡死
- 修复:模块级 `_sup_key_index()`(norm-key→全称 dict,10min 缓存,首建 ~秒级)替代线性扫;二次"包含匹配"保留低频兜底
- 注意:listdir 369K 文件目录实测仅 0.14s(SSD readdir 快),**不要误判 listdir 为卡点**
- import pix_bot_server 慢/卡时:先查是否 norm/索引类全量扫描,别急着下"import 慢"结论

## 9. 竞价室侦察结论(实时竞价监控前置验证)

- `bidRoom/initProjInfo?projId=` 非报名企业 ST = HTTP 500 无权限;initProjInfo 仅报名企业可看
- 竞价真实域:审计 URL 暴露 `bid.95306.cn/api/execute-server/...`(skipJoinPage 等;cg.95306.cn/business-proxy 只是报名/业务代理)
- 监控思路(未完整验证):采集机盯审计流 → 抓目标项目报名企业活跃 ST → 以其权限拉竞价室数据;等待竞价窗口实测
