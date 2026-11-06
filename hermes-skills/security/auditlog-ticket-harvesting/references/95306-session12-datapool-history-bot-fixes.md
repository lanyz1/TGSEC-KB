# 95306 session12:数据池历史导入 + bot 修复(2026-08-29)

## 数据池历史全量导入(官方数据库近似)
- 源数据:项目表_13145.csv / 包件表_43870.csv / 08文件_615267条_全量补企业名.csv(19列:项目名称/编号/ID、包件ID/名称/编号、报名企业、审核状态/状态码、报名/审核时间、投标人ID、采购单位)/ 报名明细_277887.csv
- 导入脚本 `/opt/v6/import_history.py`:项目表→`/data_pool/<projId>/项目信息.json`;包件表→包件清单.json(pack_id 级);08文件→pack_map.json(企业→包件+审核状态)+ 企业档案目录(7,399 家)
- 产出:13,145 项目 / 43,870 包件 / 615,259 条报名 / 221,661 行 18列全量 CSV(81MB)
- **历史 index 会被 merger 覆盖** → merger 写 index 时**读旧 index 合并保留历史条目**,只覆盖 live 项目

## 8515 实时报名补导入(进行中项目)
- 8515.csv(proj_code/bidder_name/un_social_cr_code/buy_time)含进行中项目企业级报名(武汉局69次 113 条/18 家)
- 按 proj_code→projId 映射(index.json)合并进 pack_map.json,包件占位 `packId=PROJ_LEVEL`(项目级报名)
- **关键坑:merger 每轮用采集机数据重写 pack_map.json → 覆盖掉 8515 历史** → merger 改为**合并**(读旧 pack_map 保留 + 采集数据覆盖新增);index 的 enterpriseCount 也要从**合并后 pack_map** 读(`_enterprise_count()`),不能用采集机 enterprises

## collect_one.py 手动收集(数据池没有的项目)
- 用户 bot 里输入项目名 → SSH 上海采集机 `python3 collect_one.py '<kw>'`
- 流程:审计抓 ST → 搜项目 → 项目信息/公告包件清单(readNoticeInfo 解析)→ getBuyPackageList → 落盘 /tmp/targets/<projId>/ → merger 并入
- **搜索三坑**(武汉局69次实录):
  1. notTitle 搜"武汉局69次"=0 条(标题无连续子串)→ 需多关键词:原词 + `第N次` + `第N次废` + `N次`
  2. "第69次废钢铁"命中 9 条,第一个是西安局69次(选错项目!)→ **路局名+次数双条件精确定位**(`re.search(r'([\u4e00-\u9fa5]{2,8}局)', kw)` 且标题含 `第{N}次`)
  3. selectSelfSellList 翻 3 页不够(项目在 1000+ 深处)→ 公告搜索优先,列表翻 10 页兜底
- 武汉局69次(f1b40608):公告 13 包件(襄阳工务段废道岔 89.49吨 保证金20000 等)+ 18 家企业(8515);getBuyPackageList=0 正常(报名截止,ST 企业未报名)

## 加速器(30s/60s 切换)
- `/opt/v6/accel.py on|off`:SSH 4 台采集机切换 collect_daemon_fast.sh(sleep 30)/collect_daemon.sh(sleep 60)+ 主服 merge_daemon_fast.sh(sleep 120)/merge_daemon.sh(sleep 300)
- 状态文件 /opt/v6/accel.json;bot ⚙️设置→🚀加速器 一键切换
- merger 拉取改 ThreadPoolExecutor 并行(4 台 ~1 分钟,串行 4 分钟)

## bot v3 修复的 8 个 bug(通用)
1. **Markdown 注入**:项目名/企业名含 `_*[]` → send_msg 400 → 失败自动降级纯文本重发
2. **项目详情包件 0**:只读 包件清单.json,主服实际是 CSV → CSV 兜底读取
3. **8515 企业无 18 列文件** → generate_18col() 动态生成(pack_map→CSV,含 PROJ_LEVEL 行)
4. **pid[:20] 前缀匹配 2% 冲突** → 回调 data 用完整 36 位 pid(UUID 前 20 hex 重复概率 1/16^4,13K 项目≈2%)
5. **zip >50MB** → 压缩后检查大小,超限提示按项目下载
6. **collect/accel 同步阻塞 bot 40-90s** → threading.Thread 异步 + 完成通知
7. **数据池无分页** → pool:N 分页(每页 8 个 + ⬅️➡️)
8. 死代码清理

## SSH/运维通用坑(本会话踩到)
- **pkill -f 自杀**:`pkill -f 'collect_daemon'` 匹配 exec_command 自身命令行(含字面量)→ 分两条命令(先杀后启)或用 `[c]ollect_daemon` 正则技巧(方括号防自匹配,但命令里若含真实字面量 `collect_daemon.sh` 仍会自杀!)
- **双调度冲突**:crontab 每分钟 wrapper + nohup daemon 同时跑 → 请求翻倍 → 只保留一种调度
- **ST 过期 → 请求全超时(20s×N)→ 进程堆积**:超时降到 8s + 包件清单每项目只拉一次(已有跳过)
- **setsid nohup** 才不随 SSH 会话退出(纯 nohup 在 paramiko exec_command 下会死)
- **f-string 不能含反斜杠**(SyntaxError)→ 先赋值变量再 f-string
- **Python sockshandler 本地 DNS 解析被污染** → 用 curl socks5h(远程解析)或代理层
- **curl 终端中文 → GBK 编码错误**("strings must be encoded in UTF-8")→ 用 Python urllib 发 TG API
