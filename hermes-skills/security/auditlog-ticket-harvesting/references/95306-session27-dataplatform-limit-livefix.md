# 95306 Session 27 — 数据平台业务表全量限流 / 延迟补拉 / live判定 / patch陷阱

日期:2026-08-31(竞价日实战后续)

## 1. 数据平台业务表全量限流(重大环境变化)

**现象**:findList 通道对 `bid_xxx_business23` / `aggregation_*` 系列全部返回空
(`total=None, data=[]`),但 **auditlog(审计)/sysfunc(表地图)仍可用**。
8/28-30 还能拉(项目表 705/包件表 2185/公告表 2247/8515 快照),8/31 起全 0。

**判定方法(可复现)**:
1. `findList("sysfunc", params={"start_time":..., "end_time":...}, pageSize=5000)` 拉全量表地图(1,957 个 funcid)
2. 按关键词过滤候选表(pack/package/bidder/supplier/bfwz/scrap/报名/包件/竞价 → 372 个相关表)
3. 批量测候选表(params 时间窗 / None 两种都试;condition 通道也试)
4. 全部 0 → 平台侧限制,换跳板机/IP 无效,补拉无意义

**仍活的通道**:auditlog(主链路)、sysfunc、ES 公告接口
(`/proxy/portal/elasticSearch/scrapSuppliesQueryDataToEs`,无鉴权,totalCount≈19,961)、
bfwz 带 ST 接口(join/buyed/getBuyPackageList/公告全文)。

**影响**:8515 快照增量停用(采集机 fetch_8515_snapshot 已注释掉,省请求防 WAF);
"已结束项目包件表(aggregation_bfwz_bfwzpackage_a)"兜底通道失效;
已结束项目补全改走"竞价后企业登录 → 审计 ST → buyed → 包件"。
**主链路(审计 ST 拦截)不受影响**——报名期拦截 100% 完好。

## 2. 延迟补拉机制(报名提交不审计的时序缺口)

**问题**:报名跳转(redirectEnrollUrl)审计带 ST,但**报名提交(participateInProject)不审计**;
企业跳转后要选包件提交,提交动作无票可抓。若企业提交慢,跳转 ST 可能错过提交后状态。

**方案**:采集机加 `state["enroll_st"]` 队列:
- 识别到报名跳转 ST → 记入队列(带 st/账号/projId/时间/次数)
- 每轮循环处理:ST 未过期(30min TTL)且次数<3 → 重拉 getBuyPackageList(等企业提交完)
- 间隔约 5 分钟(和轮询周期一致),最多 3 次(5/10/15 分钟全覆盖)
- 落盘 state.json 持久化,失败累计,过期清理

**原理**:报名跳转 → 提交通常几秒-几分钟完成;ST TTL 30min 覆盖;3 次重拉 = 时序兜底。

## 3. live(实时项目)判定 — 时间窗,不能信 status

**bug**:merger index.json 里 `live` 字段曾硬编码 `True` → bot"实时项目"显示 142 个,
包含 2021-2023 历史老项目和当天已结束场次。

**正确判定**(_is_live):
```
bt = 归一化 bidStarttime(去 -: 空格 → 20260901092300)
max_end = 所有包件"竞价结束"最大值(从 包件清单.json 的 包件[].竞价结束/endTime)
if max_end:  return max_end > now      # 有包件时间:未结束 = live(竞价中/待竞价)
if bt:       return bt > now           # 无包件时间:还没开始 = live(报名中/待竞价)
return False                           # 无时间信息 = dead
```
**要点**:
- 不能用 status 字段兜底——历史导入项目 status 残留 19/22(报名中/竞价中),误导
- 时间归一化函数 `_fmt_ts`:str.replace("-","").replace(":","").replace(" ","") 再字符串比较
- 有包件清单才有可靠判定;无清单老项目一律 dead

## 4. patch 陷阱:函数插入位置导致死代码(本次最痛)

**事故**:在 merger.py 的 `merge_all()` 函数体中间(某循环后)patch 插入 `_fmt_ts`/`_is_live`
两个模块级函数定义——结果**后续的 index 更新段(几十行)被 Python 解释为 _is_live 函数体
的一部分(缩进 4 空格,在 `return False` 之后)→ 永不执行,index.json 不更新!**
现象:py_compile 通过、部署成功、手动跑 merger 日志"完成: None 个项目已更新"(merge_all
没有 return 语句了),但 live 数据纹丝不动。

**修复**:把被吞的 index 段拎成独立模块级函数 `build_index(projs)`,
merge_all 尾部 `build_index(projs); return len(projs)`。

**教训**:
1. patch 在函数体中间插 def 前,先确认插入点缩进上下文(模块级 vs 函数内)
2. 插完必须验证:py_compile 只是语法检查,**行为验证要看返回值/落盘结果**
3. 部署后手动跑一轮 + 检查输出文件(mtime/内容变化)再宣布成功
4. 日志出现 None 返回值 = 函数 return 丢失的强信号

## 5. bot 数据池新增提示(check_data_updates)

用户需求:新数据录入(新项目/新企业/新包件)bot 要有提示,但不想被频繁打扰。

**模式**(挂在 health_checker 5min 循环,tick%4=20min 执行一次):
- 读 index.json:now_pids 集合 + sum(packCount) + sum(enterpriseCount)(轻量,不遍历包件文件)
- 状态文件 /opt/v6/data_upd_state.json 存上次 {pids, pack, ent};首轮只记录不推
- 对比:新 pid 差集 / d_ent>0 / d_pack>0 → 有变化才 broadcast(新项目列名称+竞价时间前5个)
- 无变化完全静默

## 6. 报名期错过的项目(西安局69次/郑州13次/10次类)能力边界

- 报名期在采集机部署前 → 报名企业名单/精确 packId 全部缺失(8515 无/CSV 无/审计过期)
- 唯一活路:竞价前企业登录 bfwz 查审核 → 审计 ST → 拦截;竞价室 WebSocket 不审计
- 数据平台兜底表失效后无确定性补全 → 如实告知用户,给出观察窗(竞价当天早上)
- 二次挂网项目(如郑州10次废钢轨 8/28 二次公告,报名止 9/2)报名期仍在开 → 可完整拦截
