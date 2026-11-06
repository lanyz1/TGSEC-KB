# 2026-09 Round3: 状态流转修复 / 假波动 / 菜单合并 记录

## 1. pack_map 冗余键 → 审核计数假波动(十堰 ✅9↔7 "逆向波动")

- 症状:bot 推 "审核通过 33→31;十堰 ✅9→7"(审核数倒退,用户质疑)
- 根因:pack_map.enterprises 存在**账号键(规范,10 个)与历史中文单位键(冗余,3 个)并存**;check_status_summary 遍历全部键 → 同一批企业数两遍(9=7账号通过+2冗余通过)。写入者(补采/合并)重写时冗余键时有时无 → 计数 9↔7 抖,监控当"审核变化"推
- 修复:pix_bot_server check_status_summary 改为先 `merge_ents_by_unit(enterprises)`(同单位合并,包件按 packId 去重、账号键优先)再计数。菜单列表(L~1257)与 3min 监控(L~4054)共用此函数,一处修复全局生效
- 铁律:**任何 pack_map 企业/审核统计不得直接遍历 enterprises 键**;先按单位合并(或按"账号字段非空"过滤冗余键)
- 验证:十堰去重后 = 通过7/未审批3(10 家),稳定

## 2. 报名截止时间推导体系(bot 不等平台切状态)

背景:平台对部分项目 status 19(发布中/报名中)滞后数小时不切 22(实测合肥报名截止 2h 后平台仍 19、sellEnddate 空)。菜单B 分组因此不流转。三处配套改动:

- **bot 渲染层时间推导**(blockable_projects):stage=报名中 且 regEndtime/sellEnddate(regEndtime 格式 `yyyymmddHHMM`)已过 → 直接归 🟡 报名结束未竞价,不等平台
- **采集完成(✅)硬门槛**(collect_complete_projects):regEndtime/sellEnddate **未到 → 绝不算"采集完成"**(名单还会涨),无论 stage 因何进入 pb
- **merger._stage_of 保守化**:无 sell(平台接口无 + 公告解析失败)时**不得直接落"待竞价"**(会把报名中项目提前切→提前标完成)。修复:无 sell 且 status=19 → "报名中";**status=22 不特判**(教训:历史导入项目残留 status=22,曾把 2021-2025 老项目全标待竞价 → pb 飙 703 事件;22 分支去掉后回落)
- **时区**:平台时间系=北京时间 UTC+8,主服/采集机=UTC。一切时间推导用 `_bj_now_dt() = datetime.utcnow() + timedelta(hours=8)` 统一;regEndtime 解析 `_deadline_dt()` 支持 yyyymmddHHMM / YYYY-MM-DD HH:MM[:SS]
- **DEPLOY_DAY(2026-08-31)过滤 = 用户业务规则,不得放开**:菜单B 只收部署后公告项目(部署前公告=报名真空期,数据不可信)。放开曾致 8/24-26 老项目全涌进菜单(用户纠正)。合肥(8/28 公告)即使流转正确也被正确挡在菜单B 外,数据采集不受影响(采集机按平台状态全量维护,与公告日无关;AI 查数据池全量也无此过滤)
- bot 周期 subprocess 调 merger.py(L~3535,~2.5min/轮)更新 index.json(updated 时间戳为证);改 merger 无需重启 daemon,重启 bot 即可

## 3. 点按钮"没反应"= send_msg 超长静默失败(沈阳99次报名总表)

- 症状:项目详情点"📋 报名总表"无任何消息,连点多次无效;bot 其他功能正常
- 排查:日志 CB 时间线(用户多次点 projents:pid)→ 独立进程 import pix_bot_server 实测渲染函数 → 正常 1.8s;txt len=4688 > **TG 单条 4096 上限** → sendMessage 400 被静默吞(函数无长度处理)
- 触发场景:18 包长描述名项目(每行 45+ 字符)
- 修复:send_msg 通用超长保护:text>4000 按行切段(每段 ≤3800)分多条发,键盘只挂最后一段;edit 模式不分段
- 排查套路:**回调"没反应"先查"消息太长/渲染异常被吞",独立进程实测渲染函数排除逻辑问题**

## 4. 项目名截断放宽(推送显示不全)

- 数据池更新(新增企业记录 [:28]/新增项目 [:30])、缺口告警 [:30]、菜单B 审核变化推送 [:22]、报名动态企业名 [:18/22] 全部截断长项目名(用户报"好多项目名称显示不全")
- 统一放宽:项目名 → [:80](TG 4096 内安全),CSV 导出行去截断(全名)
- 菜单列表 render_mb 本来就全名;检查截断点用 grep `projName.*\[:` / `\[:\d+\]` 扫推送路径

## 5. 菜单 A/B 合并(用户产品决策)

- 用户要求:主界面 = 菜单B(项目总览),菜单A 的 7 个功能按钮(数据池/竞价监控/搜索/企业查询/实时面板/下载中心/收集项目)隐藏,功能代码保留(slash 命令 /pool /download /live /mine 仍可达)
- 实现:mode 机制停用(/start、main 回调、"/菜单/首页"一律 menu_b);user_center 精简为"设置中心"(仅 设置/最近浏览/企业监控/订阅/授权),入口=/menu_a 或"设置中心";menu_b 底部旧按钮"🅰️ 返回完整菜单"(指向 main)改"⚙️ 设置中心"(menu_a 新回调)——**合并时漏改此按钮 = main 死循环 bug,用户报"不对,有bug"**
- 菜单B 改名:"🅱️ 简化菜单" → "📋 项目总览"(输入"简化菜单"保留为命令别名)
- 教训:改导航结构时必须全量 grep 旧入口的 callback_data 反向引用,防死循环/断链;用户明确"菜单B保持不动"时,只能改指向 B 的导航按钮本身

## 6. 竞价室实时监控侦察(未完成,半成品状态)

- 竞价室接口 `business-proxy/business/bidRoom/initProjInfo?projId=` 对**非报名企业 ST 返回 HTTP 500**(权限墙,实测 5 个项目全 500;collector try_fetch_bids 因此从未成功落地,数据池 0 个 bid_live 样本)
- 竞价系统真实域:**bid.95306.cn/api/execute-server/**(审计 URL 暴露 skipJoinPage 等;cg.95306.cn/business-proxy 只是报名/业务代理)
- 可行通道假设(未验证):竞价时段报名企业必然登录出价 → 审计流抓其活跃 ST → 用投标人权限拉竞价室数据;监控器须 setsid 部署到采集机独立跑(防 SSH 长连接断)+ 轮询日志
- 侦察注意:9daec874 类 projId 可能根本不在数据池/非进行中;先查平台侧真实状态再设计监控

## 7. 部署/验证方法论增量

- 远程代码修改最稳链路:**本地 write_file 纯 Python 源码 → SFTP put → 远程 py_compile + 执行**;勿在 ssh 命令串嵌 python(多层引号/\\n 嵌套转义必炸;base64 也翻车过)
- 验证脚本 import pix_bot_server 需 `sys.path.insert(0, "/opt/v6")`;跑在 /tmp 下
- import 后首次操作慢的卡点定位:norm_ent_name 无索引线性扫 36.9 万供应商名单(上亿次比较)→ 已加 `_sup_key_index()`(norm-key → 全称 dict,600s 缓存);sup_profile 的 os.listdir(369K 文件目录)实测仅 0.14s(SSD),不是卡点
- setsid 后台重定向到文件:print 必须 flush=True(或等进程退出),否则轮询文件为空误判"卡死"
