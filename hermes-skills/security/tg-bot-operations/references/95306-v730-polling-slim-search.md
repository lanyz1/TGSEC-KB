# 95306 v7.3.0 轮询瘦身实施 + 菜单B 搜索 + 业务机制问答(2026-09-01 会话)

## 一、采集机轮询瘦身(5分30秒 → 2分20秒/轮,提速 55%)

### 耗时定位方法
- 看日志"轮询完成"时间戳间隔:部署前 4 台均 ~5分10-42秒/轮
- 逐一核对主循环各阶段代码,理论开销 ≈ 2-2.5 分钟(审计5页+discover 21页+候选15票+save),实测 4.5-5.5 分钟 → 差额找隐蔽循环

### 真正的大头(按收益排序)
1. **🔴 fetch_project_details 无清单项目每轮全量重试(最毒)**:
   - 对"包件清单.json 不存在/包件数=0"的项目,每轮走完整流程:2 页公告列表 + 按标题搜 + readNoticeInfo ≈ 3-4 请求/项目
   - 26 个 src=notice 项目(询价/线下类拉不到清单)→ 每轮 80-100 请求 ≈ 2 分钟白费!
   - **修复**:`_fetch_skip = {pid: 最后尝试时间戳}`,失败项目 **50 分钟退避**(3000s)内不重试;新公告 24h 内都会被补上,不丢数据
2. **坏票重试 5→2 次放弃**:`_bump_retry` 原来 5 次失败才 giveup,坏票 TTL 30 分钟内每轮占满 15 个候选名额,新票排队;改 2 次放弃 + 候选拆 `proc_new[:15] + proc_ret[:3]`(retry 票限速 3 个/轮)
3. **save_target 只写变化**:178 项目原来每轮全量重写 pack_map.json+项目信息.json;改 pack_map 仅 `pid in st_map` 时写、项目信息用 `_last_info_dump` 内容 hash 缓存(模块级 dict,≤178 键不膨胀)
4. **全量比对 30→15 项目/次**:每轮最多 1 个企业触发(24h 限),单次 ~27s → ~13s

### 链路其他环节
- **merger crontab 5min → */3**:采集机写盘变快后同步跟上(`crontab -l | sed 's|\\*/5|\\*/3|' | crontab -`)
- **bot index 缓存 30s → 5s**:load_index 的 `_idx_cache["t"]` 阈值;瓶颈不在 bot,锦上添花

### 端到端延迟(优化后)
企业报名/审核变化 → 采集机识别(≤2分20秒/轮)→ merger(≤3min)→ bot(≤5s)≈ **3-5 分钟**(原 10 分钟)

## 二、bot 部署多实例残留坑(⚠️ 新坑,本轮实测 4 实例!)

- **现象**:连续多轮部署后 `ps aux | grep '[p]ython3 pix_bot_server.py'` 有 4 个进程(含一个 8/31 的僵尸),多个实例同时 getUpdates → 抢消息/丢消息
- **根因**:kill 旧进程用默认 SIGTERM,旧 python 处理 getUpdates 阻塞中未立即退出;`sleep 2` 后启动新实例 → 新旧共存。deploy 脚本"新PID"列表混入未死透旧进程,误以为只有 1 个
- **修复(必须)**:
  1. 部署脚本 kill 后 `sleep 2`,**再查一次进程列表确认空**,空才启动
  2. 启动后**唯一实例校验**:`keep=$(ps aux|grep '[p]ython3 pix_bot_server.py'|awk '{print $2}'|tail -1); for p in ...; do [ "$p" = "$keep" ] || kill -9 $p; done`
  3. 巡检命令:`ps aux | grep '[p]ython3 pix_bot_server.py' | awk '{print $2, $9}'`(START 列看是不是当天)
- **systemd 服务名**:采集机是 `v6collector.service`(无连字符!`v6-collector`/`collector` 都报 inactive);`systemctl restart v6collector`
- **重启静默去重**:版本公告推送从"30 分钟窗口"改"**同版本永久去重**"(LAST_PUSH_FILE 存 v,`_lp.get("v") == VERSION` 即跳过)→ 重启永不重复推,只有版本升级才推

## 三、菜单B 搜索功能模式(精确 + 空格分词模糊)

### 交互模式(复用现有状态机,零新机制)
- 入口按钮 `mb:5`(全库)/`mb:6`(已结束)/`mb:7`(可拦截) → `PENDING_INPUT[cid] = {"m": "mbsearch"/"mbsearch_end"/"mbsearch_blk", "t": time.time()}`
- handle_text 对应分支:先处理 `/cancel`/`取消`,然后 `do_mb_search(cid, t, scope=...)`;10 分钟超时自动清除(现有 PENDING_INPUT 超时机制)
- 搜索中不能再用 PENDING_INPUT 的其它 pend 值(pend 是单值,`if pend == "mbsearch"` 链式判断)

### do_mb_search(scope 参数化)
```python
kws = [k for k in text.split() if k]              # 空格分词
all(k in projName for k in kws)                   # AND 模糊匹配(精确=整串包含)
# scope: all=全库 / finished=finished_projects() 三类的 pid 集合 / blockable=blockable_projects() 并集
# 排序: 可拦截(报名中/待竞价/竞价中) pri=0 < 待发布 1 < 已结束 2;同级按公告时间倒序
```
- 复用 `render_mb(cid, title, hits, show_status=True, page=0, per=10, back="mb")`:分页 10/页、数字按钮直达详情、审核状态统计全都有
- **性能**:21,603 项目内存遍历子串匹配 ≈ 毫秒级,无压力(index 已在内存,load_index 5s 缓存)
- **实测**:「郑州 13次」→ 10 命中(待竞价置顶);「成都 废钢轨」→ 124(报名中置顶);「乌鲁木齐 第70次」→ 2

### 菜单B 结构演进(用户驱动)
- 功能1(可拦截分类)与功能3(纯名单)**渲染完全相同**(show_status 都是 False,同 render_mb),只有标题不同 → 用户问"是不是重复了" → 用户拍板"保留2" → **删 1 和 3,只留功能2(可拦截+审核状态)和功能4(已结束比对)**
- 教训:用户原始需求"1.分类划分好 / 3.分类不带审核状态"本身重叠,实现时应先合并同类项再交付,别照单全收
- 最终菜单B:🏷️可拦截项目+审核状态 / 🏁已结束项目(比对) / 🔍搜索项目(全库) + 各分类页内嵌聚焦搜索

## 四、95306 业务机制问答(用户答疑实锤)

### 可拦截项目 39 个的数据来源
- 8/31 部署后采集机**公告流接口(queryBusinessNoticeList)**发现 8/31 新发布 46 个公告 → 全部入池
- 46 个里 39 个 stage=报名中(bidType=02 网上竞价销售)→ 可拦截;7 个归"历史"(询价/单一来源/谈判/线下销售,不在 selectSelfSellList 竞价销售列表,排除正确)
- 39 = 36 未开始(enterpriseCount=0)+ 3 已开始(已有企业报名)

### "已结束项目是竞价结束后才归入吗" → 两阶段归入
```python
def _stage_of(pid, info):   # merger.py 判定(实锤)
    1. 报名中: now <= sellEnddate
    2. 已结束: status == "14"          # ← 平台终态/结果公示
    3. 待发布: now >= 包件最大结束时间   # ← 竞价室关闭,等审核员发布结果
    4. 竞价中: now >= bidStarttime 且 < max_end
    5. 待竞价: 有 bt 且未到
    6. 历史: 无任何时间信息 / 无清单老项目
```
- **归入"已结束"触发 = 平台置 status=14(结果公示)**,不是竞价刚结束;竞价结束→公示之间先"待发布"(641 个)
- 12,797 完整拦截 = 监控期间走完生命周期自然归入(status=14);7,922 历史索引 = 8515 快照导入时已终态,**导入即归入**(非竞价后归入)
- 生命周期:报名中 → 待竞价 → 竞价中 → 待发布 → 已结束(公示)
