# 报名三入口模型 + 初次拦截缺口归因(9/9 实证定稿)

## 报名三入口(每类的可观测性不同 → 决定用什么通道补)

| 入口 | 行为特征 | cg 审计(auditlog) | tokenrailquery | 我们的通道 |
|---|---|---|---|---|
| ①公告页/列表跳转 redirectEnrollUrl | 从 cg 公告点报名,URL 带 serviceTicket | ✅ 可见(detail 含 ST) | 登录有行 | collector 秒拦 ~100%(9/4 实证 4/4) |
| ②站内业务系统报名 | 登录后业务菜单直报 | ❌ 域隔离不可见 | 登录有行 → orch 可翻 | orch 补 |
| ③自动化/代报/接口直调 | 同企业同分钟连续报多项目(间隔1-5s);部分深夜(00:53/03:25/05:56) | ❌ 零痕迹 | ❌ **全时段 0 行**(实证:今/昨/历史动作窗 1.2万+ 票 user/info 全查 0 命中) | **无票物理边界** → 等竞价日 cg 进场或弃权 |

崇锐类特征样本:河南崇锐贸易(7项目两段密集)、天津市益鑫物资回收(40min 6项)、江西名可名贸易(凌晨 03:25)、新疆双龙聚/中科凯瑞/南宁明华(2-4分钟多项=秒级)。
注意:**白天批量≠自动化**(人工代报/熟练业务员也批量),只有"深夜动作"与"同秒重复行(接口重试特征,如 11:06:45 ×5)"是铁证。

## 实测关键结论

- 竞价日进场(从 cg 入口进竞价室)= 必留 tokenrailquery 票 → orch 10min 内补(9/7 西安 38→54 实证);所以缺口企业在**各自项目竞价日**自动收敛,无需人工
- "今日新报名即时拦截率 ~57%"与"竞价日终局 90%+"是**两个口径**,不能混用;bot 战报已分两层显示

## 初次拦截缺口归因方法(把"15%漏洞"切成可解释块)

1. **量化定位**:G1 报名中(报名期即时)≈83%,G2 截止未竞价 ≈88%;缺口时效分桶:
   `<30min 链路内(会收敛)/ 30-60min / 1-4h(超链路,可疑)/ >4h(真漏,占74%)`
2. **排除假缺口**:名册名 vs pack_map 单位做 norm 宽松匹配(去空格/全角/括号/非中文数字)——9/9 实测 82 家超时缺口 0 假,全真缺
3. **剩余真缺 = 无票型(③)为主**:有票通道(collector/orch)对"有票企业"实测无漏(当日 hits 71 家全写成功),缺的都是无票的

## tokenrailquery 接口速查(debug 用)

- 正确参数:`findList {funcId: "tokenrailquery", appId: "system", pageNum, pageSize:500, params:[{key:startDate,value},{key:endDate,value}]}`,返回 `j["data"]`(不是 rows!)
- 行字段:token/user_type/user_type_name/username(个人账号,非企业名)/login_status/userid/login_time/login_mode_name(随机码/手机号/证书)/ip/login_device
- user_type 分布(1h 窗 3500 行):03 供应商 2080 / 02 集团公司 1298 / 00 游客 86 / 09 运营 3;03 的 mode:证书 67%/手机 16%/随机码 16%
- 拉窗 6 页=3000 行封顶,高峰窗可能截断(30min 窗 03 活票可达 900-1900)
- 查询按 user_type 过滤 03 + login_status=1(orch worker 同款)

## 验证纪律(本次调查踩过的坑,防再犯)

1. **"0 命中/0 行"先验证自己的查询参数**——曾用 query{login_time_start} 参数拉 tokenrailquery 得 0 行(正确=params startDate/endDate + 读 j["data"]),差点误判"该时段无登录"
2. **时段全覆盖**:只查 8:00-9:00 和 10:40-11:40 漏了中段 9:00-10:40(目标企业 11:06 报名,登录若在 10:3x 就在漏掉的窗)
3. **状态全覆盖**:除 login_status=1 活票还要查 status=0 死票(自动工具"登录→操作→登出"留死票);user_type 分布先摸底再筛
4. 判断"企业全天无票"前,至少覆盖:今日全域 + 历史报名动作时刻窗(持久会话假说:票在 8/28-8/31)→ 全 0 才算实锤

## 相关接口探测结论(后续课题)

- bid.95306.cn/api/execute-server/dataplatform/api/findList 存在但需登录态(code 1001 请先登录)——有有效 ST 后可探其功能表
- cg 域 findList 盲猜 funcId(loginlog/sysloginlog 等)全部"不存在的功能"(注册制词表);错误响应 viewModel 键(sysfunc/sysmeta)值全 null 无注册表可挖
- business.95306.cn 域名不存在;bid.95306.cn/proxy/... 404;cg.95306.cn/business-proxy/dataplatform 404

## bot 展示口径(勿回归)

- 推送/卡片"企业 N/M":N 必须 merge_ents_by_unit 去重(pack_map 键含账号键+中文键冗余,50键→真实44家;未去重会虚高误导)
- 战报三层行:🎯漏采收敛 / 📈报名期即时+竞价前拦截率 / 🏁今日已结束 ✅完整/⚠️部分(弃权边界);每日存 /opt/v6/miss_snap.json 供次日收敛对比
