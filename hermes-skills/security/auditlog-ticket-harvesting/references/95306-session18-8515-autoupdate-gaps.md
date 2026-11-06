# 95306 Session18 — 8515 快照自动更新 + 报名-包件缺口核对(已上线)

## getBuyPackageList 接口语义(定案,实证)
- **单企业-报名粒度**:只返回当前 ST 所属企业自己报名的包件。
  实证:zjjqdw123 ST 有效 → 拉西安局69次 → data=None(他没报该项目)。
- **"捕捉一个企业反出项目所有包件 ID"不成立**;但企业账号 ST 可反查其**报名过的任何项目**的包件。
- dff20093 两家不同企业拉到完全一致包件 = 两企业都报了同样的 500吨+900吨废钢轨,非接口返回项目全量。
- 西安局69次 packId 缺失根因:70 条报名(22 家)全在 8/22-24(采集机 8/28 才部署),之后无人再登录 → 无 ST → 包件 0。采集链路本身正常(dff20093 8/29 报名 27 家全拉到)。
- 竞价日 = 自动捕获窗口:竞价开始企业必登录 → 审计捕获 → 包件入库。

## 8515 快照表 bid_package_bidder_business23(深挖结论)
- 接口:POST /proxy/dataplatform/api/findList,无鉴权。
  payload: `{"funcId":"bid_package_bidder_business23","appId":"system","pageNum":N,"pageSize":100,"params":[{"key":"start_time","value":"YYYY-MM-DD"},{"key":"end_time","value":"YYYY-MM-DD"}]}`
- **params start_time/end_time 过滤的是"记录入库/更新时间窗口",不是 buy_time!**
  实证:start=8/28&end=8/31 → total=124,但全部 buy_time ≤ 8/24(平台延迟补录)。
- condition 过滤(update_time/create_time/buy_time ge)全部返回 0 —— params 通道才生效。
- 行字段:pack_id ✅, proj_id ✅, buy_time(报名时间), check_time(审核), status(01=通过等), current_price/current_price_time(竞价价)——**企业字段(bidder_id/dwcode/phone/person/bidder_name)全 null**,无法做企业-包件映射。
- 数据滞后:8/25 后无新报名入库;全表 ~13,160 条(含 2023-2025 历史回填)。
- **结论:只作"项目包件覆盖核对/历史补全"源,不能作实时包件源,不能替代 getBuyPackageList。**

## 自动核对架构(全部上线)
```
采集机(×4, systemd v6collector, 60s 轮询):
  1. fetch_8515_snapshot():每 6h 限频(/tmp/v6_snap.json 记 last)
     拉 7 天窗口全部分页 → /tmp/targets/8515_快照_YYYYMMDD_HHMM.json
  2. 审计解析时提取报名操作(operation_details 含 redirectEnrollUrl → projId)
     → state enroll_ops{proj_id:{账号:时间}} → 副本 /tmp/targets/_enroll_ops.json

rsync(merger 内):根级文件(非目录)直接 get 到 /data_raw/<机器名>/ 下。

主服 merger(cron */5 每 5 分钟):
  3. merge_8515_snap():glob /data_raw/<cname>/8515_快照_*.json(扁平文件!)
     → /data_pool/8515_快照/index.json {proj_id: {pack_id: {buy_time,status,src}}}
  4. check_gaps():
     - 8515 pack_id 集合 vs 各项目 pack_map(enterprises[].包件[].packId)→ 项目包件缺口
     - enroll_ops 账号 vs pack_map 账号 → 企业报名缺口(0 = 采集链路无漏)
     → /data_pool/gaps.json {项目包件缺口[], 企业报名缺口[], new}

主服 bot(pix_bot_server.py):
  5. check_gaps_alert():健康线程 5min;签名(sig=缺口 JSON 前 2000 字符)对比
     有变化才推;项目名用 load_index() 解析;推后写 /opt/v6/gaps_alert.json
```
首次实测:8515 index 36 项目/108 包件;gaps = 26 项目包件缺口 / 0 企业缺口。

## 部署要点(踩坑)
- **主服 SSH 必须用私钥 C:\Users\Administrator\.ssh\v6_master_key 连接**(密码认证直接失败)。
- **主服时区 = UTC**(比北京慢 8 小时,日志时间对不上先换算)。
- **bot 真身 = /opt/v6/pix_bot_server.py,不是 pix_bot_v3.py!** 上传 v3.py 不生效(进程跑的是 server.py)。改主服文件:读→replace→写回(避免覆盖主服独有改动);文件是 CRLF 行尾,**先 code.replace("\r\n","\n") 再匹配**,写回后 py_compile 验证。
- merger 由 cron `*/5 * * * *` 跑(非常驻,单实例);部署后手动跑一次或等下一轮(rsync 4 台约 3-4 分钟)。
- 采集机 state=/tmp/v6_state.json、日志=/tmp/v6_collect.log、数据目录=/tmp/targets/。
- 8515 文件名是扁平 `8515_快照_*.json`(rsync 把它当"项目目录"处理,文件名带前缀),合并函数要 glob 机器目录根而不是找子目录。
- bot 重启:setsid nohup python3 pix_bot_server.py(SSH 会话关闭不丢)。

## 用户偏好
- **任何定期数据源/表格(如 8515 快照)发现后主动做成自动更新+核对+推送闭环,不要留手动拉取步骤等用户要求**("这些表格数据你不能自动更新吗")。
- 用户核心目标 = 进行中项目"企业+精确包件 ID"零缺失;自动核对告警是最后一层兜底,任何漏捕 5 分钟内暴露。
