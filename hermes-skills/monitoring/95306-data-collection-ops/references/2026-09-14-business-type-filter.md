# 项目双类型(竞卖/竞买)与"只保留竞卖"过滤体系(2026-09-14 上线)

## 类型模型(平台原生字段)

- 名册行(bss/biddingandsellingsupplier)自带 `proj_business_type` / `proj_business_type_name`:
  - **竞卖 = 报废物资处置类**(铁路卖废料;报名方=回收企业) —— 例:大秦/西局废钢轨
  - **竞买 = 采购类**(铁路买物资/服务;报名方=供应商) —— 例:客车配件/机务项修
- 全史统计(90 个 roster 切片,1,000,575 行):**58,420 个项目打标 = 竞卖 16,319 / 竞买 42,102**(竞买项目多而每项报名少~8 行;竞卖项目少而每项几十家抢)。
- 近月:竞卖反超(9月=竞卖 223 项目/4,322 行 vs 竞买 133/801)。
- 判定铁证链:b580(business23)=**竞价阶段表**,9月切片对报名期企业 grep=0 → **报名期登记只在 bss/roster 曝光**(roster_fill 存在的理由);matrix=静态深档(含 USCC+包件级)。

## 用户决策(2026-09-14)

"只保留竞卖类的项目可以吗 竞买类的需求不是很大" → **只留竞卖**。范围=步1 类型地图+步2 bot 闸门+步3 补采过滤(含 bot 重启,用户已确认);步4(采集机停扫竞买)=未拍板。

## 三件套实现

### 1) 类型地图 `/data_pool/proj_types.json` (~2MB, {proj_code: "竞卖"|"竞买"})

- 一次性回填:`pt_backfill.py`——扫全部 `/data_raw/95306_full/roster_*.jsonl.gz` 增量合并、原子写;**幂等可重跑**。
- **sync v14**(`/opt/v6/sync_plat_enroll.py`):pull_all 加 `tmap` 参数顺带收集 → 尾部合并写 proj_types.json;日志行 `类型表: N 项目`。
- 覆盖:回填后当前窗口 762/762=100%;有报名记录即有类型(新公告无报名=未知,fail-open)。

### 2) bot 单点闸(pix_bot_server v9.17)

- `ENABLE_TYPE_FILTER = True`(一行回滚开关)+ `_ptypes()`(60s 缓存;文件缺失=空=全放行)。
- 闸门在 **`load_index()`**(数据唯一入口,reload 后过滤 `pt.get(projCode)=="竞买"`);菜单/搜索/项目列表/已结束/日报战报/`_intercept_stats`/mb_monitor 全部自动继承。
- **fail-open 语义:只滤"确认竞买",未知放行**(防误藏新公告)。
- 实测:RAW 22,011 → FILTERED 15,122;`GATED_KINDS {'竞卖': 15037, 'None': 85}`;竞买泄漏=0。
- 生效验证:
  `cd /opt/v6 && python3 -c "import pix_bot_server as b; ps=b.load_index(force=True)['projects']; print('N',len(ps))"`(应为过滤后数,启动日志同步显示 `数据池 N 个项目`)。

### 3) 补采过滤(roster_fill v2)

- 载入 proj_types.json → 循环内 `if pt.get(pc)=="竞买": continue`;竞买不再产生名册级补采。

## 部署纪律(md5 预检 + 备份换血,本次 3/3 零差错)

1. 本地改前 `md5sum` 三件 → 与主服同路径对账**相等才换**(杜绝补丁打错基座);
2. 上传 `*_v<ver>.py` → `cp -a` 原文件 `.bak913c` → `mv` 换血 → `py_compile`;
3. sync 换血后**手动实跑一次**:`OK: N 项目` + `类型表: N 项目` 双验证;
4. bot 重启=两段 exec(`pkill -f '[p]ix_bot_server'` → `setsid nohup … >> /opt/v6/pixbot.log`),日志确认 `[PixBot-v3] 启动`。

## 回滚

- 恢复两类:`ENABLE_TYPE_FILTER=False` + 重启 bot;补采恢复=删 roster_fill 跳过行。
- **数据未删**(竞买静默留池,列表不可见而已)。备份:sync `.bak913c` / bot `.bak913c` / roster_fill `.bak913`。

## 状态快照(09-14 08:59 BJT)

- 过滤后指标(竞卖口径):R1 99.3%(278/280,66项目) / R2 99.6%(937/941,87项目),miss 2。
- 观察项:成都/深圳/青岛 3 台工作环滞后 12-19min(心跳面正常;判据同 SKILL §13 载荷 ts)。

## 遗留

- sync 未存 USCC(名册行有 `un_social_cr_code`;增强可助消歧,未做)。
- 采集机层面仍扫两类(步4 未拍板;省配额选项在桌上)。
- ai_agent 简报若直读 index.json 则未受闸门影响(未核)。
