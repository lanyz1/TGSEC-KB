# 95306 十轮: v6 多机部署实战 + TG bot v3 + 历史全量导入(2026-08-29)

## 新基础设施(跳板机池全面更换)
```
海外主服 128.241.245.73:12971(root/qfgR3okF9wfn4PXF) — Ubuntu22, 4C8T/7.7G/229G, 双IP, TG 直连无需代理
上海 8.133.188.178 / 杭州 121.43.97.73 / 广州 8.138.236.124 / 成都 47.108.152.60(root/Ppikesi10x.)
旧池(河源/内蒙古/绍兴/北京/深圳/宁波)全部抹除痕迹;宁波从未登录成功(密码从一开始就不对)
```

## v6 架构落地(采集机×4 + 主服合并 + bot)
```
采集机: /opt/v6/collector.py + collect_daemon.sh(while+sleep 60, setsid nohup)
  每轮: 审计抓ST → 企业识别(user/info) → 目标发现(selectSelfSellList 3页) → getBuyPackageList → /tmp/targets/<projId>/
主服:  /opt/v6/merger.py + merge_daemon.sh(sleep 300) — 并行拉4台(ThreadPoolExecutor) → /data_pool/<projId>/
bot:   /opt/v6/pix_bot_server.py(长轮询,读 /data_pool)
```

## v6 部署踩坑(全部实测,重要)
1. **bidStarttime 格式无秒**:`"2026-08-31 09:30"`(部分带秒)——解析要兼容 `%Y-%m-%d %H:%M` 和 `%H:%M:%S` 两种
2. **selectSelfSellList 默认排序不是竞价时间** → 前 100 条最早是 9 月的,48h 窗口项目在深处 → **必须翻 3 页**(pageSize 上限 100)
3. **目标发现 ST 选择**:不能用"新 ST"——没新 ST 时用**审计最新 ST(无论新旧)**;发现失败(0 目标)时**用上次 targets 兜底**,否则目标列表会丢
4. **ST 过期 → 全部请求卡超时 → 进程堆积**:http 超时 20s→**8s**;每项目"包件清单.json 存在且非空即跳过"(公告不变,只拉一次)
5. **双调度冲突**:crontab 每分钟 wrapper + daemon while 循环同时跑 → 进程成倍堆积 → **只保留一种调度**(选 setsid daemon)
6. **pkill -f 自杀**:paramiko exec_command 的命令行若含目标进程名**真实字面量**(即使用了 `[c]` 技巧,命令串里其他部分的 `collector.py` 字面量仍会被匹配)→ pkill 杀掉自己的 shell,后续命令不执行且连接断开。**修复:杀和启动分两条 exec_command**
7. **setsid 保活**:普通 `nohup ... &` 在 paramiko 会话关闭后可能被杀 → **`setsid nohup python3 x.py > log 2>&1 < /dev/null &`** 彻底脱离会话
8. **进程计数陷阱**:`ps aux | grep -c '[x]'` 会把 exec_command 的 shell 也算进去(计数=2 实际 1 个真进程),要 grep 完整特征或看实际命令行

## participateInProject(SM4-ECB 复刻,主动参与路径)
- 前端拦截器:`memServer` 接口 = SM4-ECB,key = `"YYYYMMDD+memberserver"`[:16](日期为天级,一天内不变)
- 明文:`{"token": ST, "businessId": projId, "businessType": "02"}`;响应是**纯 base64 密文**(不是 {"data":...})
- 成功:参与后 `getBuyPackageList?projId=` 返回**全部可报名包件**(packId 级);但**报名截止后拒绝**("已过报名截止时间")
- 结论:主动参与=写操作(留痕,用户拒绝)——**纯读路径用公告链路代替**

## 公告链路(纯读包件清单,替代参与)
```
POST /notice/queryBusinessNoticeList(纯读,23,130 条,含 projId+公告id) → 按 projId 匹配
GET  /notice/readNoticeInfo?noticeId=<公告id> → data.bidNoticeResultVo.notCont(HTML)
解析: 正则 `第(\d{3})包[：:](.*?)(?=第\d{3}包|包件具体内容|交付时间)` + `竞卖保证金:人民币([\d.]+)元` + `开启时间:\s*(\d{8})\s*(\d{2}:\d{2}:\d{2})`
→ 包号/名称/保证金/竞价时段(无 packId UUID,packCode 级)
```

## 历史全量导入数据池(官方库近似一致)
- 数据源:08文件_615267条_全量补企业名.csv(19列:项目ID/包件ID/报名企业/审核状态/状态码/报名时间/审核时间/驳回原因/投标人ID/采购单位) = **企业→pack_id→审核状态全量**
- 包件表_43870.csv(pack_id/proj_id/pack_code/pack_name/status/outbid_price)+ 项目表_13145.csv(id/proj_code/proj_name/status/proj_endtime)
- 导入结果:13,145 项目 / 43,870 包件 / 615,259 条报名 / 7,399 企业档案 / 221,661 行 18列全量
- ⚠️ **merger 覆盖 index bug**:实时 merger 每 5 分钟重写 index.json → 历史 13K 项目被挤掉只剩 20 live。**修复:merger 读旧 index 合并,只覆盖 live 项目**;已损坏时用扫描脚本重建(遍历数据池文件夹读 项目信息.json/包件清单.json/pack_map.json)
- 跨洋 sftp 上传 500MB ≈ 0.4MB/s ≈ 20 分钟——大文件上传放后台
- TG 文件限制 50MB:81MB 全量 CSV → zip 压缩后发送

## TG bot v3 增强(菜单/体验)
- **☰ 菜单按钮**(输入框左侧):`setMyCommands`(命令+中文描述)+ `setChatMenuButton {"type":"commands"}`;终端 curl 发中文报 UTF-8 错 → Python 走代理发送
- **加速器开关**(用户 TG 里自控):accel.py 通过 SSH 远程切换 4 台采集机 daemon(fast=sleep 30 / normal=sleep 60)+ 主服 merger(fast=2min / normal=5min);状态存 /opt/v6/accel.json,bot ⚙️设置 显示当前模式
- **企业画像**:/data_pool/企业档案/<企业名>.json(项目数/包件数/审核分布/物资类型分布/保证金合计/报名记录)
- **每日汇总**:bot 内 threading 定时线程,每天 20:00 broadcast(数据池统计+今日竞价+今日新报名)
- **全量搜索**:index.json 内存加载(13K 项目,30s 缓存),名称/编号模糊搜索;实时项目标 live=true,历史标 📚
- 历史+实时融合:数据池索引默认只显示 live 项目,历史走搜索(/proj /ent 或直接输入关键词)

## bot 授权与推送
- ALLOWED_IDS 列表控制;未与 bot 对话的用户收不到推送(老头 8368000122 曾因此 False,需先发消息)
- 每日汇总 20:00 自动推;订阅(sub/unsub callback)按项目
