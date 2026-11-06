# 95306 Session 11 — 手动收集项目 + merger 合并修复 + TG Bot v3 用户中心

日期:2026-08-29 | 环境:4 台国内采集机(上海/杭州/广州/成都)+ 海外主服(128.241.245.73:12971)+ TG bot

## 1. 手动收集项目(collect_one.py)— 数据池没有的项目一键采集

用户需求:数据池没有的项目,在 bot 里输入项目名 → 立即采集(公告包件+企业报名)→ 并入数据池。

流程:审计抓 ST → 搜索项目 → 项目信息/公告包件清单(readNoticeInfo 解析)→ getBuyPackageList → 落盘 /tmp/targets/<projId>/ → merger 下一轮并入。

**搜索定位是关键难点(踩坑 3 轮):**
- ❌ 只翻 selectSelfSellList 前 3 页(300 条):进行中项目在深处,找不到
- ❌ 公告搜索 notTitle=用户原词("武汉局69次"):公告标题无连续子串,0 条
- ❌ 关键词变体"第69次废钢铁"搜到 9 条,但取第一个匹配 → **选错项目(西安局69次)**
- ✅ 最终方案:**公告搜索 + 多关键词轮询(原词/第N次/第N次废/N次)+ 路局名+次数双条件精确匹配**:
```python
bureau = re.search(r'([\u4e00-\u9fa5]{2,8}局)', kw) or re.search(r'([\u4e00-\u9fa5]{2,12}公司)', kw)
num = re.search(r'(\d+)', kw)
# 公告结果里要求:标题同时含 路局名 且 第N次 → 才返回
```
- 兜底:selectSelfSellList 翻 10 页(1000 条)

**公告搜索参数**(queryBusinessNoticeList):`{"projType":"02","notTitle":kw,"noticeType":"01",...,"pageVo":{"pageNum":1,"pageSize":50},...}` — 注意 notTitle 是模糊子串匹配,但"武汉局69次"这种**跨词简称搜不到**(标题是"武汉局集团有限公司...第69次废钢铁")。

## 2. merger 覆盖历史数据的 bug(3 个修复)

**坑 A:merger 重写 pack_map.json 覆盖 8515 补导入的历史企业。**
修复:merger 合并时**保留旧 pack_map 的 enterprises,采集数据只覆盖新增**:
```python
old_ents = json.load(pack_map.json).get("enterprises", {})
merged = dict(old_ents); merged.update(新采集数据)
```

**坑 B:merger 重写 index.json 覆盖历史项目索引(13145→20)。**
修复:index 写入前先读旧 index,`idx["projects"] = old_projects`,再只更新实时项目条目(标记 live:True)。

**坑 C:index 企业数被 merger 统计覆盖为 0。**
修复:enterpriseCount 从**合并后的 pack_map.json** 读(`_enterprise_count(pid)`),不从采集机原始数据统计。

## 3. 8515 实时报名补导入(进行中项目企业级数据)

数据源:2026年8月报名全量_含进行中项目_8515条.csv(列:proj_name/proj_code/proj_business_type_name/bidder_name/un_social_cr_code/buy_time)。
- 按 proj_code 关联 index.json 的 projCode → projId
- 合并进 /data_pool/<projId>/pack_map.json(企业级,packId="PROJ_LEVEL" 占位标记"项目级报名")
- 武汉局69次:113 条/18 家企业(含信用代码)
- 重要:**8515 是"实时"数据源(含进行中项目),08文件(615,259 条)是"已结束"快照——两者互补**

## 4. 远程执行运维坑(通用)

- **pkill -f 自杀 bug**:`pkill -f pattern` 会匹配 exec_command 自己的命令行(命令串里含目标字面量,如 `nohup ./collect_daemon.sh`)。症状:旧进程没死+新进程没起+连接被强制关闭。修复:**杀和启动分两条 exec_command**;或 pkill 用 `[x]` 正则技巧(防 grep 自身,但防不了命令串里其他字面量)。
- **nohup 随 SSH 会话退出**:paramiko exec_command 结束后后台进程被收。修复:`setsid nohup python3 xxx.py > log 2>&1 < /dev/null &`(setsid 完全脱离会话)。
- **双调度冲突**:crontab(每分钟 wrapper.sh)+ nohup daemon(while 循环)同时存在 → 进程堆积(残留 10+ 个 collector)。部署新调度前先 `crontab -r` + pkill 全部旧调度。

## 5. TG Bot v3 用户中心模式

- /start → 用户中心:动态数据总览(项目/包件/企业/报名数/加速器状态/订阅数)+ 全功能按钮网格(双列)
- 用户昵称从 message.chat.first_name / callback message.chat.first_name 取
- 功能入口:数据池/竞价监控/项目搜索/企业查询/下载中心/数据统计/收集项目/加速器/订阅/设置/帮助
- ☰ 菜单按钮:`setMyCommands`(命令+中文描述,上限 100)+ `setChatMenuButton {"type":"commands"}` — 输入框左侧出现菜单按钮
- **加速器开关**:bot 设置里一键切换采集机(30s/60s 轮询 daemon)+ merger(2min/5min)节奏,accel.py 通过 SSH 切换 4 台采集机的 daemon 脚本(collect_daemon_fast.sh vs collect_daemon.sh)
- **收集项目交互**:回调 → PENDING_INPUT[cid]="collect" 状态机 → 下条文本当项目名 → SSH 采集机跑 collect_one.py → 结果回显

## 6. 数据池最终形态(与官方库几乎一致)

```
/data_pool/
├── index.json              13,165 项目(历史+live标记)
├── <projId>/(13,165 个)
│   ├── 项目信息.json / 包件清单.json / pack_map.json
│   └── 企业包件表_18列_<code>.csv / 包件清单_<code>.csv
├── 企业档案/(7,399 家,单位/项目数/包件数/记录)
└── 汇总/全量_历史_企业包件_18列.csv(221,661 行,81MB→zip 压缩后 <20MB 可 TG 发送)
```
- TG 文件限制 50MB:>45MB 自动 zip 压缩再 sendDocument
- 历史导入来源:项目表 13,145 / 包件表 43,870 / 08文件 615,259 条 / 报名明细 277,887 / 8515 实时 8,515 条

## 7. 实测数据验证

- 武汉局69次(f1b40608):包件 13(公告级)+ 企业 18(8515)→ index 显示"包件 13 | 企业 18"
- 手动收集"沈阳铁道"→ 沈阳铁道93次(9 包件)自动并入
- bot 全量搜索"南昌局"→ 10 个历史项目
