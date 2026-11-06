# 8 台扩容 + v8 采集器(2026-09-01 实测)

场景:95306 监控管道 4 台→8 台扩容,一次性落地全部风控自保护机制。
所有"业务地址/口令/端口"已按凭据红线处理。

## 最终架构(8 台,同一份代码,SHARD 0-7 分片)

| SHARD | 机 | 说明 |
|---|---|---|
| 0-3 | 旧 4 台(沪/杭/穗/蓉) | 存量升级,SHARD 不变 |
| 4-7 | 新 4 台(沪2/蓉2/青/深) | 新增分片,一体化采集(同代码) |

- 项目分片:`_shard_ok(projId)`: `int(pid.replace("-",""),16) % SHARD_NUM == SHARD_ID`
- 票归一台:`_my_ticket(st)`: `int(md5(st.encode()).hexdigest(),16) % SHARD_NUM == SHARD_ID`
  —— **必须用 md5/稳定哈希,禁止内置 `hash()`(进程间随机化,分片会漂移)**
- 启动错峰:`time.sleep(SHARD_ID * 7.5)`(8 台审计翻页不打架)
- 主循环自适应:`sleep(max(30, 90 - elapsed))`(不再固定 60s)

## v8 六项增强(全部实测生效)

1. **节流器**:business 域(带 Authorization 的 `/business-proxy/business*`)同机请求间隔 ≥1.5s。
   模块级 `_BIZ_LAST` 时间戳 + `time.sleep(wait)`。数据平台域(findList 无鉴权)不节流。
2. **冷却状态机**:响应 `code==100` 或 msg 含"系统服务异常/请联系技术支持/操作频繁/访问过于频繁"
   → `_COOL_UNTIL = now + 15min`;**冷却期间 business 请求直接返回 `{success:False, code:100}`**(调用方走 retry),
   **审计通道(无鉴权域)继续跑**。冷却持久化到 state(`cooldown_until` 字段,重启不丢)。
3. **死票过滤**:user/info 返回 `401/403` → `dead_st` 列表标记(上限 500),**不再进 retry 队列**。
   注意区分:冷却期间的 code 100 不算死票(`_is_cool_resp(j) and not _in_cooldown()` 才标死)。
4. **票归一台**(见上,消除多台重复榨干同一张票;8 台 = 重复请求降 8 倍)。
5. **全局性任务 SHARD 0 独占**:notices_map 维护(30min)、8515 快照(6h)——避免 8 台重复拉同一批页面。
6. **buyed 矩阵扫描分票**:只扫 `_my_ticket(s0)` 的票,无票时兜底 `list(...)[:60]`。

## 部署顺序(从 0 到 8 台的完整流程)

1. 本机写好升级版代码 → `py_compile` 语法检查
2. 传主服(sftp put)→ 主服 `md5sum` + `stat` 大小确认
3. **新 4 台**:本机 paramiko 口令直连 → 检查环境 → 注入主服公钥 → sftp 写代码
   → systemd(`V6_SHARD=4/5/6/7`)→ enable --now → tail 日志
4. **旧 4 台**:本机直连超时 → 部署脚本上传主服执行(paramiko 口令连旧机,sftp 写码 + 重启)
5. **merger 采集机列表**:硬编码 COLLECTORS 数组加 4 台(名称/IP/口令),或 jumpers.json;
   改完**不用重启**(merger 是 cron `*/3 * * * *` 单次执行,下轮自动生效)
6. 验证:merger 日志出现 `上海2/青岛/成都2/深圳: tar 全量同步 N 文件` = 新机数据已进合并流
7. TTL 追踪 cron:挂一台新机(`17 */4 * * *` 每 4h 测最老 5 张票写 /tmp/ttl_probe.json)

## 关键坑(本会话实踩)

- **exec cat 截断**:paramiko `exec_command("cat /opt/v6/collector_v8.py")` 读出 41,609B
  (实际 46,057B),截断在合法语句边界 → py_compile 通过但代码缺块。
  后果:新机第一版部署写入截断代码。**传输一律 sftp,部署脚本三端 md5 校验**。
- **本机→旧机超时**:旧采集机只对主服开 SSH;新机可本机直连(口令)。
- **部署后 3/4 台同时触发风控冷却**:backlog 集中消化(重启后 retry/enroll/30min 票一起处理)
  导致请求密集 → 冷却状态机触发。这是**自保护生效**,不是故障;15min 后自动恢复,
  恢复后"目标项目数"回到 70-90 正常量级。
- **新机首轮 state 为空**:st_times/seen_st 未积累 → TTL probe 首跑 0 张票属正常,
  等 4h 后 cron 自跑即有数据。

## 请求预算参考(风控安全线)

- 实测:同 IP business 域 **0.5s 连发 12 个请求 → 第 3 个起全被拒**(2req/s 即触发);
  30s 间隔 ×6 全 OK;冷却期 10-40 分钟(40 分钟后全恢复,票没被打标)。
- 结论:**单 IP business 域间隔 ≥1.5s(0.67req/s)为安全线**,再叠加冷却状态机兜底。
- 数据平台域(无鉴权 findList)更宽松:单 IP 单日 9300 请求才封(8/24 实测)。
- ST 有效期实测下限:6.3h(丹阳江腾,30s×6 连测全过);"系统服务异常"= 网关限流不是票死。

## TTL 追踪脚本要点

- 选票:st_times 中最老 5 张且 ∈ seen_st(曾经成功);票间 sleep 5s(5 张共 25s,零压力)
- 输出:/tmp/ttl_probe.json `[{st[:8], first_seen, age_h, ok, code, msg, unit}]`,随 rsync 回主服
- 目的:票龄→存活率曲线,校准"抓到票后榨干的时间预算"
