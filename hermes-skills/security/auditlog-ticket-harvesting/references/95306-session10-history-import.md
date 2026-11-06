# 95306 Session 10 — 历史全量导入数据池 + TG Bot 完整版 + 多机部署陷阱

日期:2026-08-29 | 关联:auditlog-ticket-harvesting(活票管道 → 数据池 → bot 交付)

## 一、数据池结构(海外主服 /data_pool/)

```
/data_pool/
├── index.json                  全局索引(项目/包件数/企业数/更新时间)
├── <projId>/                   每项目独立文件夹
│   ├── 项目信息.json           名称/编号/状态/竞价时间(实时+历史)
│   ├── 包件清单.json           公告级包件(含 pack_id,历史导入)
│   ├── pack_map.json           企业→包件+审核状态(核心)
│   ├── 企业包件表_18列_<code>.csv
│   └── 包件清单_<code>.csv     公告级
├── 企业档案/<企业名>.json       企业画像(项目数/包件数/审核分布/类型分布/记录)
└── 汇总/全量_企业包件_18列.csv  全部项目合并
```

## 二、历史数据导入(官方库 → 数据池)

关键 CSV 表头(导入脚本按这些字段解析):
- **08文件_615267条_全量补企业名.csv**(19列):项目名称/编号/ID、包件ID/名称/编号、报名企业、审核状态/状态码、报名/审核时间、审核人、驳回原因、投标人ID、记录ID、采购单位 → **企业→pack_id→审核状态 全量**
- 项目表_13145.csv: id/proj_code/proj_name/status/proj_endtime/pur_id
- 包件表_43870.csv: pack_id/proj_id/pack_code/pack_name/pack_desc/status/outbid_price/end_time
- 报名明细_277887.csv: 企业级报名(无包件)

导入流程:项目表→项目信息;包件表→包件清单;08文件→pack_map+企业档案+18列;全量写 index.json。60 万条流式读取(csv.DictReader),8 核主服几分钟完成。

**跨洋上传慢(0.4MB/s)**:500MB 需 20+ 分钟,必须后台跑(sftp.put 逐文件);先传小文件可提前开始导入。

## 三、TG Bot 完整菜单(纯 HTTP 长轮询,零依赖)

- 主菜单 inline_keyboard:`/start` → [📁数据池索引][🔥竞价监控][🏢企业查询][📥下载中心][⏱实时状态][⚙️设置]
- 回调(callback_data 前缀路由):pool/proj:/bidday:/bidwatch/entquery/entlatest/downloads/dlall/status/bidlive/settings/mysubs/sub:/unsub:/file:/packfile:/help
- 文本命令:/proj <关键词> /ent <企业> /today /status;**直接输入企业名自动企业画像**
- 文件发送:multipart/form-data 手工构造(boundary),sendDocument
- 每日汇总:threading 定时线程,每天 20:00 broadcast(先判断 hour==20 且日期未发过)
- 企业画像聚合:全量 pack_map 反向索引 → 单位/账号/项目数/包件总数/保证金合计/审核分布/物资类型分布(关键词归类:废钢轨/废道岔/废闸瓦/废有色金属/报废汽车...)/最近报名/记录列表

## 四、多机部署陷阱集(全部实测踩过)

1. **pkill -f 自杀**:`exec_command("pkill -f xxx; ...")` 中 shell 命令行本身含 "xxx" 字符串 → pkill 匹配并杀死自己的 exec shell(连接断、进程没杀)。**用 `[x]` 正则技巧**:`pkill -9 -f '[c]ollector.py'`(方括号使自身命令行不匹配)。
2. **后台进程随 SSH 会话退出**:nohup 不够(exec_command 通道关闭时进程被杀)。**用 `setsid nohup python3 xxx.py > log 2>&1 < /dev/null &`** 完全脱离会话;验证:关连接后再查进程。
3. **双调度冲突**:crontab `* * * * *` + daemon while 循环同时跑 → 进程堆积(每分钟 2 个 collector)。**只保留一种调度**;排查:`ps aux | grep wrapper` 看是否有 `/bin/sh -c ...wrapper.sh` 进程。
4. **ST 过期 → 请求全卡超时 → 进程堆积**:每轮 fetch 请求数 × 超时时间 = 轮时长;ST 过期时 19 项目 × 3 请求 × 20s ≈ 19 分钟,daemon 60s 又起新进程。修复:**请求超时降到 8s + 包件清单只拉一次(存在跳过)+ 目标发现失败用上次状态兜底**。
5. **ps 计数假象**:`ps aux | grep -c '[c]ollect_daemon'` = 2 时实际可能是 1 个真 daemon + 1 个 exec shell(命令串含关键字)。用 `ps aux | grep '[c]ollect'` 看明细确认。
6. **TG 网络**:海外主服直连 api.telegram.org;国内机器必须走代理(本机 v2rayN socks5h://127.0.0.1:10808,curl 子进程远程解析 DNS——Python sockshandler 本地解析会 SSL EOF)。
7. **bidStarttime 无秒**:`"%Y-%m-%d %H:%M"` 和 `"%Y-%m-%d %H:%M:%S"` 都要 try;selectSelfSellList 排序非时间序,48h 扫描翻 3 页。
8. **用户偏好**:不留痕(写操作先问)、先汇报进度再继续、失败修复后立即复测验证、交付要"和官方几乎一致"的全量数据池。

## 五、现状(2026-08-29)

- 4 台采集机(上海/杭州/广州/成都):v6 collector 每 60s(错峰 0/10/20/30s)→ /tmp/targets/
- 海外主服 128.241.245.73:merger 每 5 分钟拉 4 台 → /data_pool/;bot pix_bot_server.py setsid 常驻;merge_daemon.sh while 循环
- 授权推送:8002394686(本人)/7548633061(VOKE);**未对话用户(如老头 8368000122)推送失败,需先主动发消息**
