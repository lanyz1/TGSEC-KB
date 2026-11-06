# v9 缺口驱动补拉闭环 + 配置下发(2026-09-01 实测)

场景:8 台采集机跑通后,把"完整度 100%"做成自动化闭环:主服检测缺口 → 下发清单 → 采集机定向补拉/反查 → 差集跳过死数据。所有业务地址/口令按凭据红线处理。

## 一、主服→采集机配置下发模式(通用可复用)

**主服生成"指挥文件" → sftp 推 8 台 → 采集机定时重读生效**,无需改代码/重启:

- 主服脚本 `gen_gap_projects.py`(cron `*/30 * * * *`):
  1. 读 `/data_pool/gaps.json` + `index.json` + `notices_map.json`
  2. 过滤出**进行中**缺口 → 写 `/opt/v6/gap_projects.json`
  3. 每 6h 额外生成 `ent_coverage.json`(差集基线,单独 state 文件记录 `cov_ts`)
  4. `paramiko sftp.put` 推 8 台 `/opt/v6/` 同名文件
- 推送连接:先 `key_filename=~/.ssh/id_ed25519`(主服已注入采集机 authorized_keys),失败回退密码;采集机列表读 `jumpers.json`(bot 新增/更换跳板机自动生效,硬编码 COLLECTORS 仅兜底)
- 采集机侧:模块级缓存 + **60s 重读**函数(`load_gap_projects(force=False)`),文件更新即生效,零重启
- 采集机新清单生效 = 下一轮轮询(≤90s),验证别急

## 二、缺口判定数据格式速查(95306 实测)

| 数据 | 结构要点 |
|---|---|
| `gaps.json`(merger 产物) | keys: `time/项目包件缺口(proj_id,缺,pack_ids)/企业报名缺口/待确认缺口(notice_id,账号,时间)/疑似仅打开页面/采集机告警/new`;`new`=签名变化标记,bot 变化才推 |
| `index.json` | `projects[pid] = {projName, projCode, bidStarttime(YYYY-MM-DD HH:MM[:SS]), status(14=已结束/19=进行中), stage, enterpriseCount, packCount, live}`;stage 枚举: 报名中/待竞价/竞价中/待发布/已结束/历史 |
| `notices_map.json` | **方向 {noticeId: projId}**;noticeId 查不到 = 待确认缺口(映射失败),只能做**账号级**补拉,不能做项目级 |
| `pack_map.json` | `{targetProj, enterprises{单位名: {单位,账号,信用代码,包件[],时间,来源,记录[]}}}`;**账号可能为空**(8515 项目级来源) |
| **PROJ_LEVEL 占位** | 包件 `[{"packId":"PROJ_LEVEL","packName":"项目级报名(未到包件级)"}]` = 8515 项目级占位,**不是真实覆盖**;差集跳过必须排除,否则永久漏真实包件 |

- 进行中判定(采集端补拉只推进行中):`stage in (报名中,待竞价,竞价中,待发布)` **或** `live==True` **或** `bidStarttime >= now`。注意:merger 的 `live` 字段**不含待发布**(live=False),但用户视角待发布=可拦截,判定要单独放宽。

## 三、采集机端三个新机制(v9)

### 1. 缺口票识别 + 强制补拉(审计行匹配)
审计行 `operation_details` 里正则抓 `projId=([0-9a-f-]{36})` / `noticeId=...` / `serviceTicket=([0-9a-f]{32})`,与下发的 gap_projects 匹配:
- projId 命中 → 该票标记 gap,处理时**对该 projId 强制 getBuyPackageList**(即使不在 targets/buyed)
- noticeId 命中 → 在 gap_projects.projects 里反查 projId(清单带 noticeId 映射)
- 账号命中(`accounts[acct]`)→ 票标 gap 优先处理(账号级补拉靠 drain 队列全量榨干兜底,不需定向)
- gap 票进 `proc` 时插队:`key=lambda t: (0 if t.get("gap") else 1, time)`,且反查命中直接 `proc.insert(0, ...)`

### 2. auditlog 定向反查滚雪球(findList 无鉴权通道)
- 每轮对缺口项目清单滑窗取 ≤5 个,`findList(funcId=auditlog, appId=system, condition={"operation_details":{"like":"%projId前8位%"}})`,pageSize=5
- 命中新 ST → 注入候选 + `st_times` + 强制本轮处理;进度持久化 `state["rev_idx"]`(滑窗指针)
- **注意变量作用域**:反查块必须放在 `candidates`/`dead_set` 定义**之后**(否则 UnboundLocalError),审计提取块只做 gap_tickets 标记

### 3. 榨干队列 drain(历史全量补强,去 15 上限)
取代"24h 一次全量 projs[:15]":
- `state["drain"][acct] = {st, tm, ent, all:[projId...], done:[...], full_ts, last}`
- 入队:该票 buyed 全部项目 + `_my_acct(acct)` 企业分片(hash(acct)%8==SHARD_ID 才做全量,消除多台重复)
- 执行:每轮 pending 排序(tm 新→旧)取 ≤3 票,每票 ≤10 项目,**拉过的项目无论有无包件都记 done**(防重复请求);有包件写 `_ent_full_<ts>_<acct8>.json` 给 merger merge_ent_full
- 清理:all 空/ST 死票 → 移除;done 满 → 记 full_ts,满 24h 移除(下次登录重新入队);队列 >200 条按 tm 截断
- 差集:`_cov_skip(acct, projId)` 读 ent_coverage,已结束+已覆盖的项目跳过(**活数据永不跳过**)

## 四、死数据差集基线 ent_coverage.json(完整度 100% 后启用)

主服每 6h 生成,`{acct: {projId: {cov: 记录时间, end: true}}}`。**end=True 必须同时满足**:
1. 项目已结束(`stage=="已结束"` 或 `status=="14"` 或 `bidStarttime < now`)
2. 该企业有**真实包件**(packId 非空且 ≠ "PROJ_LEVEL")
3. 记录时间 ≥ 竞价开始(报名截止)→ 报名期后抓的完整数据;无时间或早于截止 → 保守不跳过(报名期数据可能不全)

进行中项目**永不进基线**——违反"活数据永不跳过"铁律即错。

## 五、TTL 追踪回传修正

v8 版本输出 `/tmp/ttl_probe.json` 需单独 rsync 通道;v9 直接写 **`/tmp/targets/_ttl_probe.json`** 随主目录 rsync 自动回主服(merger 按根级 `.json` 文件拉取),零额外通道。死票判定:success 但 `dwhz` 为 ?/空 = 死票特征,计无效。

## 六、节奏优化

- `discover_targets`(目标发现 3 状态×多页)降频 **600s**:`state["discover_ts"]` 时间窗,未到期用 `state["targets"]` 兜底;fetch_project_details 保持每轮(已有清单跳过+50min 退避,开销小)
- 审计拉票(核心信号源)保持 90s 高频,不受降频影响

## 部署顺序(本次实测)

1. 本地写 collector_v9.py → py_compile → 传主服 → 主服 sftp 推 8 台 + md5 校验 → systemd 重启 → tail 日志
2. gen_gap_projects.py 传主服 → 试跑(看"缺口清单 N 项目/N 账号/N notice"输出)→ 挂 cron
3. ttl_probe.py 改输出路径 → 推沪-新机覆盖
4. 验证:gap_projects.json 到达 8 台(ls 检查)、采集机日志出现"缺口补拉/榨干队列/定向反查"、cron 二跑文件更新

## 坑(本会话实踩)

- **gaps.json 字段名不能猜**:企业报名缺口当前可能为空、项目包件缺口 proj_id 可能不在 index.json(查 {});先 dump 结构再写解析,别按记忆写字段
- **notices_map 方向别猜反**:{noticeId: projId};待确认缺口 = 映射失败,别试图从它拿 projId
- **删除旧逻辑时连带删了变量定义**:删旧"企业全量"段时把 `acct_key = str(t["acct"])` 一起删了,drain 入队直接 UnboundLocalError;删代码段先 grep 段内变量是否被后文引用
- **ent_coverage 首跑 0 企业不是错**:扫描 51935 条但全不满足 end 条件(占位记录/记录早于竞价开始),保守即正确;放宽条件要按第四节三条逐个验证
