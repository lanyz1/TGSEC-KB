# 95306 v7.26 — 部署验证实录 + 告警链架构(2026-08-30)

本会话:merger 部署覆盖验证、bot 真身发现、采集机告警链上线。配套 SKILL.md 第 7 节。

## 部署验证的假警报与真验证

- **上传后 ls 大小不符 = 假警报**:本地 t95306_v6_merger.py 23,738B,主服显示 26,623B——一度怀疑覆盖失败,写 ssh_check_merger.py 验证。真相:CRLF/编码差异导致字节数不同,**内容正确**。
- **真验证方法**:`py_compile` + grep 关键函数计数(`merge_8515_snap`/`check_gaps` 出现 2 次 = 定义+调用)即确认生效。**永远不要以文件大小判断上传结果**。
- **密码认证失败 → 私钥**:ssh_check_merger.py 首版用 password=口令 认证失败(Authentication failed),改 `paramiko.Ed25519Key.from_private_key_file(r"C:\Users\Administrator\.ssh\v6_master_key")` 成功——主服只认私钥。
- **sftp 读返回 bytes**:`s.open(p, "r").read()` 是 bytes,直接字符串 replace 报类型错误 → `.decode("utf-8", "replace")`。

## CRLF 匹配坑(patch 远程文件)

主服 pix_bot_server.py 是 **CRLF 行尾**(早期从 Windows 上传的历史)。本地写的 old_string 用 `\n` 匹配不到 → patch 静默不生效。
修复:读入后 `code = code.replace("\r\n", "\n")` 统一行尾再替换,写回统一 `\n`(python 不在乎行尾)。

## bot 真身 = pix_bot_server.py(不是 pix_bot_v3.py)

- 本机副本名 `pix_bot_v3.py`,但主服实际运行 `pix_bot_server.py`(142,976B,比本地 125,719B **更新**)。
- 整体上传 pix_bot_v3.py = 白传 + 主服出现两个文件混淆。
- **热更运行中 bot 的正确姿势**:`ps aux | grep python` 确认真身 → 读主服真身文件 → 内存字符串替换增量补丁 → 写回 → 主服 py_compile → `pkill -f '[p]ix_bot_server'` 分两条 exec_command 重启 → setsid nohup 启动 → ps 验证新 PID。
- 教训:**先 ps 确认真身再部署,别信本机文件名**。

## merger 是 cron 周期任务

- `crontab -l`:`*/5 * * * * python3 /opt/v6/merger.py`(每 5 分钟),**不是常驻进程**。
- pgrep 看到的 merger PID 是 cron 刚启的;上传后等下一轮 cron 自动生效,或手动 `python3 /opt/v6/merger.py` 立即验证。
- 单实例锁防并发;手动跑与 cron 撞车时以日志为准。

## rsync 根级文件特判

merger 的 rsync 循环原本只按 `/tmp/targets/<pid>/` 子目录拉取,**根级协作文件永远不会被拉回**。
修复:循环里特判 `if not pid.endswith(...)` → 根级文件(`_enroll_ops.json`/`_alerts.json`/`_ent_full_*.json`)直接 get,否则按子目录拉。
症状识别:主服 /data_raw/<机>/ 下永远没有下划线开头的文件。

## 告警链架构(本轮新增)

```
采集机每轮落盘:
  /tmp/targets/_alerts.json   {"giveup": [ST放弃(≥5次失败)], "overflow": 审计5页全满时间}
  /tmp/targets/_enroll_ops.json  {"projId": {"账号": 时间}}  报名操作记录
  /tmp/targets/_ent_full_*.json {"企业","账号","ST","时间","项目":[{projId,projCode,projName,包件:[...]}]}
  → rsync 根级特判拉回主服 /data_raw/<机>/
merger:
  merge_ent_full(): 扫描 _ent_full_*.json → 数据池没有的 projId 自动建目录+index 条目(live=True,来源=企业全量)+ 包件合并进 pack_map(按 packId 去重)
  check_gaps(): 项目包件缺口(8515快照 vs pack_map) + 企业报名缺口(enroll_ops vs pack_map) + 采集机告警(_alerts.json) → /data_pool/gaps.json
bot:
  check_gaps_alert() 在 health_checker(5min)里:三路签名(sig/ent_sig/alert_sig)对比 /opt/v6/gaps_alert.json,变化才推
```

- **签名对比法**:cur/old 各拼 `json.dumps(缺口列表)` 比较,`new` 标记变化——避免每轮重复推送存量缺口。
- 首次推送 = 存量缺口一次性告知(26 项目/0 企业),之后只推增量。
- bot 补丁注意:主服真身文件里 `sig/ent_sig` 已有,增量补丁加 `alert_sig` 第三路——三处同步改(签名计算、判等、写入)。

## 企业全量拉取(采集机侧)

- 触发:每次处理新 ST,`getSupplierPackageList?statusGroup=buyed&bidType=02&pageNum=1&pageSize=50` → 该企业**全部已报名项目** → 逐项目 `getBuyPackageList?projId=` 拉包件,写 `_ent_full_*.json`。
- **限频**:state 里 `full_times` 滚动窗口,每台每小时 ≤4 次(防 WAF)。
- 价值:**审计 60s 窗口外的报名项目也能被发现**(企业只要登录一次,名下全量补全)——治"报名早于采集部署、之后不登录 → packId 缺失"类问题。
