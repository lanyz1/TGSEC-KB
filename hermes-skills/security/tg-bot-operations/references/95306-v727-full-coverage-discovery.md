# 95306 v7.27 全量在网项目发现 + 管道健壮性(2026-08-30 实战)

背景:用户反馈"实时项目缺发布中/报名期项目"——采集机只翻 3 页+只收 48h 内竞价的项目,发布中项目被已结束项目淹没。

## 1. selectSelfSellList 全量发现(status 过滤是唯一可靠法)

- 接口:POST `/business-proxy/business/bidProject/selectSelfSellList`(需 ST,bidType=02)
- **默认排序会把已结束项目排前面——不按 status 过滤翻 15 页(1500 条)也找不到发布中的项目**
- 必须按 status 参数过滤分页拉取(实测 2026-08-30 分布):
  - `13`=竞价中(1 个,多为测试) | `19`=发布中/未开始(**169**) | `22`=待竞价/报名中(**468**)
  - `30`=已结束(965) | `31`=已结束/流拍(128) | `14`=成交(1118)
  - **只监控 13/19/22 = 637 个在网未结束项目**
- 过滤测试项目:projName 含 "测试"/"test"(2029 测试集团、2021 南宁测试等会混入)
- 按 projName 搜索参数可定位具体项目(如 projName="26081507" 命中二次项目 OF002026081916151982,status=19)
- 返回字段:id(projId)/projCode/projName/bidStarttime/status/bidEndtime
- **getProjInfo?projId= 无包件清单字段**;猜 `/bidPackage/getXxx` 等接口名全 500——别走猜名路线(低效)
- 包件清单:只靠 getBuyPackageList(需企业已报名)或历史导入(包件表_43870.csv);企业 0 的项目包件要等报名后捕获

## 2. 分片部署(V6_SHARD)

- 637 目标 × 多 ST × 包件请求会爆炸 → 4 台采集机分片:`int(proj_id.replace("-",""),16) % 4 == SHARD_ID`
- systemd 注入环境变量:`sed -i '/^\[Service\]/a Environment=V6_SHARD=n' /etc/systemd/system/v6collector.service` + `systemctl daemon-reload` + restart
- 实测目标数:上海 173 / 杭州 94 / 广州 146 / 成都 148

## 3. 请求优化(关键省请求)

- 每个 ST 先拉 `getSupplierPackageList?statusGroup=buyed&bidType=02&pageNum=1&pageSize=50` = 该企业**全部已报名项目**列表
- 只对"企业已报名的目标项目 + force 目标"拉 getBuyPackageList → 每 ST 从 160 请求降到 2-5
- 该列表同时复用为企业全量记录(_ent_full_ 文件),不重复请求
- 附带价值:审计外的新项目(该企业报了但我们没发现的)也通过此列表发现

## 4. paramiko sftp rsync 陷阱(主服无 rsync/sshpass)

- 主服没有 rsync/sshpass 命令 → 只能 paramiko sftp
- **sftp.get 无超时**:某台响应慢就整轮挂死(手动跑 merger 200s timeout 被杀,raw 目录 3 分钟只 +8 文件)
- 修复三件套:
  1. **mtime 增量**:`sftp.listdir_attr(rdir)` 比较 `|本地 mtime - 远程 st_mtime| < 2` 跳过相同文件
  2. **每台时间预算**:循环内 `if time.time()-t0 > 110: break`
  3. **线程超时**:`f.result(timeout=125)` 包 try/except,超时跳过该台下轮续拉
- 首次全量(560 目录 × 3 文件/台)慢属正常;增量后每轮几十文件
- 锁是进程级,挂死线程随主进程退出被杀,锁自动释放

## 5. 审计滚动日志语义(溢出检测别用页满)

- auditlog 500 条(5 页 × 100)覆盖约 1.5 天(页1 15:25 → 页5 前日 21:52)
- **5 页全满是常态,不是溢出!** 误用"页满=溢出"会 4 台全量永久误报
- 正确检测:统计页1 内 `operation_time >= now-60s` 的条数,≥100 才算真溢出

## 6. merger 单实例锁

- `fcntl.flock(_lk, LOCK_EX|LOCK_NB)` + except → `sys.exit(0)`
- **必须 import sys**——否则锁被占用时 NameError 崩溃,cron 每 5 分钟循环崩溃且无正常日志

## 7. bot 主服补丁模式(增量,绝不整体覆盖)

- 主服真身 = `/opt/v6/pix_bot_server.py`(**不是本机 pix_bot_v3.py**),且主服文件比本地副本新(多 17K+)
- 增量补丁:sftp 读主服文件 → `.replace("\r\n","\n")` 统一行尾 → 字符串替换(old/new 片段)→ 写回 → `python3 -m py_compile` → `grep -c` 验证
- 重启:分两条 exec_command(`pkill -f pix_bot_server.py` → `cd /opt/v6 && setsid nohup python3 pix_bot_server.py > /tmp/pix_bot.log 2>&1 < /dev/null &`)防自杀,ps+tail 验证
- 版本公告:只推本次变更;重启静默

## 8. 数据平台表全部停更(2026-08-27 16:57 后)

- `bid_project_business23`(8月窗口 705 条,含 id/bidStarttime)、`bid_package_business23`(2185,含 **pack_id+proj_id+pack_code+pack_name+outbid_date**)、`bid_notice_business23`(2247,not_title 结果公告)
- 全部无鉴权 findList,但 **8/27 后停更 → 只能作历史源,实时唯一依赖审计 ST 链路**
- 8515 历史全量拉法:`bid_package_bidder_business23` 分月窗口(2025-01~2026-08,每月 pageSize=1000 × 最多 6 页)= **12 万条 / 5,231 项目 / 17,607 包件**(buy_time 2021-11→2026-08-24)
- 8515 企业字段(dwcode/phone/person/address)全 null(历史+增量都是)→ 仅"项目包件覆盖"核对源,不能做企业粒度

## 9. 其他部署事实

- 本机直连采集机 IP 超时(网络全走主服跳板)→ 一切采集机操作通过主服 SSH 执行(密钥 v6_master_key)
- 杭州采集机日志文件不更新但 systemd journal 有输出(标准输出去向差异),功能正常别误判停机
- 上传后主服文件大小与本地不符(CRLF/编码)是常态——**以 grep 关键函数计数验证内容,别信文件大小**
