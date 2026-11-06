# 心跳告警时区判定 + SSH 入站封禁双通道评估 + 分片完成态(2026-09-02 实录)

场景:8 台采集机(旧4+新4,hash%8 分片)心跳告警连发(上海/杭州/成都 01:33,深圳/青岛 06:37-06:40),用户问"什么情况";同时 drain 验证遇"候选 0"谜团。以下为完整判定方法,同类告警直接套用。

## 一、时区差:告警时间戳先换算再定性

- **主服 = Etc/UTC,采集机 = CST(+08:00)**。health.json 的 `updated` 是主服时间、`ts` 是采集机时间,`gap_s` 用 epoch 算(跨时区依然正确)。
- 告警消息"最后心跳 2026-09-02 01:33:14"= 采集机 CST = 主服 UTC 17:33 = **昨天部署窗口的历史事件**;消息延迟 3.5h 送达,看起来像实时告警。
- **判定流程**:收到心跳告警 → ①看 health.json 当前 8 台 status(可能已恢复)②换算告警时间戳到主服时区 → ③对照当时在做什么(部署/调试/卡顿轮)→ ④查对应时段采集机日志。
- 主服 `date` 输出无时区标识,先 `timedatectl`/`date +%Z` 确认再下结论。

## 二、SSH 入站被封 ≠ 采集挂(双通道判定)

现象:主服→深圳/青岛/成都2 的 ssh 全部超时(ping 丢包/22 CLOSED),但 health.json 仍 ✅ 正常、心跳文件持续更新。

- **心跳文件 = 采集机出站主动推送落盘**(主服 `/data_raw/<机>/heartbeat.json`,merger */3 读取),**不受入站封禁影响**。
- 判定:
  1. 采集服务状态 = `stat -c %Y /data_raw/<机>/heartbeat.json` 新鲜度(<600s = 活)
  2. 管理通道 = 主服→采集机 22 端口(被封只影响看日志/改代码/验证,不影响数据链路)
- **触发源**:8 台全量高频部署 push + 诊断脚本轮询(05:00-06:00 多次 deploy)→ 腾讯云 SSH 爆破防护封主服 IP 入站。**对策:部署错峰、失败后不高频重试、停手等 15-60 分钟或云控制台安全组放行主服 IP。**
- 采集机心跳短暂中断(06:32-06:40,gap 334-444s)已自行恢复——单次事件,SSH 恢复前无法从主服侧深挖根因。

## 三、监控脚本:cron monitor_script 模式的稳定态设计

- monitor_script 输出哈希不变 = 静默,变化才触发 agent。**SSH 不可达但心跳新鲜 = 稳定异常态,必须输出稳定行(静默),只有心跳变陈旧才输出变化。**
- ssh 命令连接失败常以 **err 文本**返回(`timed out/refused/unreachable`)而非抛异常——按 err 内容分类,不能只依赖 except。
- 心跳新鲜度判定放宽时钟偏差:`-120 <= age < 600` 为 HB_OK。

## 四、分片"候选 0" = 完成态(非故障)

- 每台只处理 `hash(st)%8==SHARD_ID` 的新票;已处理票进 seen 不再算"新"。
- **加过滤分布日志**(candidates 构建处):
  ```python
  _skip_dist = [0]*8
  for t in new_t:
      if t["st"] in dead_set: continue
      if not _my_ticket(t["st"]):
          _skip_dist[int(hashlib.md5(t["st"].encode()).hexdigest(),16)%8] += 1
          continue
      candidates[t["st"]] = t
  log(f"  ↳ 候选 {len(candidates)} 过滤分布 {_skip_dist}")
  ```
- 判读:`候选 0(new_t 54) 过滤分布 [0,24,10,6,4,2,4,1]` = SHARD0 机分片 0 命中 0 = **本机分片票已全部处理完,窗口余票全属其他分片**;8 台各自分片=0 = 全系统处理完毕待命。**别用均匀概率直觉**(51 票 0 命中≈0.1% 会误判)——seen 过滤后是条件分布。
- 环境变量验证:pgrep 匹配**真实服务进程名**(`collector.py`,服务 ExecStart 指向),`pgrep -f collector_v9` 会抓到无关进程;读 `/proc/<pid>/environ | tr '\0' '\n' | grep V6_SHARD`。

## 五、drain 恒空 = acct/st 双分片错配

- 处理过滤用 `_my_ticket(t["st"])`,入队用 `_my_acct(t["acct"])`——**st 分片 ≠ acct 分片,同一票过得了处理关、永远过不了入队关** → seen 277 但 drain={}。
- 修复:入队条件去掉 `_my_acct`(处理成功已保证 st 归本机)。**教训:多分片 key 过滤必须统一同一个 key。**

## 六、SSH_DOWN 假警报:监控脚本 IP 过期(2026-09-07 实证)

- 症状:verify_drain_monitor.py 连续 5 天报 成都2/青岛/深圳 `SSH_DOWN|HB_OK`,误判为"腾讯云封禁延续"。
- 真相:三台机器早已换 IP(腾讯云新实例 iZ2vc3dzk5aunevnce7gmqZ/iZm5e9h0a1iicizpqiw6mmZ/iZwz9bgkg8790guzgp4mm5Z),merger COLLECTORS/jumpers.json 已更新,但**本地监控脚本 MACHINES 表还是旧 IP**(47.108.98.97/124.222.244.126/81.68.139.204 → 全 Connection timed out)。SSH_DOWN 是连错地址,不是被拦。
- **SSH 失联判据顺序**:①主服 merger 日志近 2 分钟是否 8/8 tar 同步(真源,merger 每轮都在连采集机)→ 全绿 = 机器可达,问题在监控脚本 IP 表;②核对 merger.py COLLECTORS/jumpers.json 现网 IP 与脚本 MACHINES 是否一致;③旧 IP ssh BatchMode 实测 timeout vs 新 IP 通。
- 心跳文件按机名落盘(/data_raw/<机>/heartbeat.json),与 IP 无关 → HB_OK 不能验证脚本 IP 正确性。
- 修复:verify_drain_monitor.py MACHINES 对齐 merger COLLECTORS(成都2=47.108.173.230/青岛=47.104.139.212/深圳=47.107.124.62),重跑实测 8/8 SSH_OK。教训:采集机换 IP 时监控/部署脚本 IP 表必须同批更新,以 merger COLLECTORS/jumpers.json 为单一真源。

## 七、try_fetch_bids 类尽力而为循环三件套

88 targets × initProjInfo × 4s 节流 ≈ 6 分钟/轮,单轮轮询 7.5 分钟,心跳 gap 冲高 → 告警。修复:
1. 降频:state 时间戳 `bid_fetch_ts` 1800s 间隔
2. 500 无权限项目记 `bid_skip` 跳过集(1h 有效,state 整体 json 保存,无需单独持久化)
3. **卡顿期间每 10 个请求写一次心跳**(try_fetch_bids 传入 state,循环内调 write_heartbeat)
