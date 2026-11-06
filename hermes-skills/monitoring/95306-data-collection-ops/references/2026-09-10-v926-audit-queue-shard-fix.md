# v9.26/v9.26b:8515 审核刷新"吞噬缺陷"修复 + 全机切片队列化 (2026-09-10)

## 症状
- `audit_changed` 批"每批只吃前 8 个":今晨 40 项目批只处理 8 个后整批标 done,其余 32 个永久饿死。
- 实测上海队列 24 项 `0家拉取`:旧版"仅 SHARD 0 执行"实际覆盖率只有 ~1/12。

## 根因(三层)
1. **消费端**(collector.py `audit_refresh()`):`projs = sorted(...)[:8]` 只取前 8,处理完整批即写 `done.ts=ts` → 批内第 9+ 永不轮转;新批只吃自己前 8,老批剩余永久丢。
2. **生产端**(merger.py `audit_diff()`):`projects = allp[:40]` 封顶——超出项目 state 已推进(=不会再报)却不进清单 → 永久丢。
3. **覆盖面**:项目按 `int(pid_hex,16) % 12 == SHARD_ID` 分片;pack_map 各机只持有自己那份(实测同一项目可被多台机同时持有);"仅 SHARD 0 执行"→ 上海只能刷自己切片 ≈ 1/12。

## 修复(v9.26 → v9.26b)
- **消费端队列化**:批内全量入队 `/tmp/v6_audit_queue.json`(`queue`+`done_sig`);8 个/轮 drain;done_sig 防重放,check_time 变新可重入队;600 条保险上限;每轮日志 `审核刷新: 本轮N项目/X家拉取/Y家更新/队列剩M`(空转不刷屏)。
- **v9.26b 全机执行**:去掉 `SHARD_ID != 0` 门;入队过滤 `os.path.isfile(TARGETS_DIR/<pid>/pack_map.json)`(各机各刷本机切片;pack_map 出现后下一轮自动补入)。
- **生产端全量下发**:`projects = allp`(去 [:40] 封顶)。
- 结果写回本地 pack_map → rsync → merger merge_all 自动合并(幂等)。

## 部署记录(md5 链)
- collector: `ad6f89ad1827` → v926 `81b959ac3d0e` → v926b `bf579ce2ef8c`(12 台 `systemctl restart v6collector`;备份 `.bak_v926pre`/`.bak_v926bpre`)。
- merger: `de9484c1` → `cfabed1c9586`(免重启,daemon 下轮自加载;备份 `.bak_v926pre`)。
- 找回:今晨被吞批次 12 个可确认项目(种子)注入持有其 pack_map 的 7 台机队列(共 21 条)。
- 部署脚本:本地 `deploy_v926.py`/`deploy_v926b.py`(主服中转,逐台 上传→md5 校验→备份→install→restart→is-active 验证)。

## 关键坑(实测)
- **采集机"轮"很长**:单轮 1~16 分钟(平台风控冷却拖慢);`audit_refresh` 在**轮末**才调用 → 重启后几分钟内看不到审核刷新是正常,勿误判为故障。
- **换新要单波**:每次重启截断一个"在途轮";分两波部署 = 每台损失两轮。
- **多机重复消费正常**:同一项目 pack_map 可存在多台机,各机独立队列各刷一次,merge 幂等兜底。
- **主服侧诊断脚本连接对象坑**:driver 里 `cli`=主服连接、`s`=采集机连接;把"读机器 /tmp"的代码写进 `cli.exec_command` 会静默读成主服 /tmp(曾致"队列文件失踪"假警报)。
- 前 4 台(沪0/杭1/穗2/蓉3)仅主服可达:机器侧检查一律 本地→主服→采集机 中转。

## 排错路径
1. 机器: `journalctl -u v6collector | grep -a '审核刷新'` 看 drain;`cat /tmp/v6_audit_queue.json` 看 queue/done_sig。
2. 主服: `/data_pool/audit_changed.json`(ts/项目数) + `/tmp/v6_merge.log` 找 `audit_diff`。
3. 分片归属速算: `int(pid.replace('-',''),16) % 12`。
4. queue 文件在机器 /tmp(非主服);重启不丢(非 PID/namespace 敏感),但机器磁盘清理会重置——丢了下轮从当前批自动重建。
