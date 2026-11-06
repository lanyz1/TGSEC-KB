# 共享数据文件 schema 契约 + 编排器静默失败(2026-09 95306 实证)

## 多写入方共享文件的 schema 契约(最大隐性坑)

多通道(采集机 collector / 补漏 backfill / 手动导入)写同一文件时,**后加入通道必须复用既有 schema,禁止自创字段结构**。消费端只认旧契约,新结构数据"在库但不可见"。

### 实证案例(95306 pack_map.json)
- 既有契约(collector/bot 生态):`enterprises{<登录账号>: {账号/单位/时间, 包件: [{packId, packCode, packName, 保证金, 报价模式, 物资条数, 审核状态, 审核码}]}}`
- bot 消费端只读 `包件`(list)+ `审核状态`:`check_status_summary` 审核统计、企业已报名包件展示(packCode 拼接)
- 补漏通道(orch8b)自创 `packs` dict(key=packId, 值含 "名称"/"审核"/"状态码")→ **45 项目 79 企业 536 包件全部静默不可见**:审核统计缺失、包件显示"项目级"而非 packCode。数据肉眼有内容但 bot 读不到,人工抽查才发现。

### 排查信号
- 消费端统计数字不含新通道数据;展示退化为"项目级"无包件编号
- pack_map 里同文件混存两种企业结构(merger key 归一化 `ev.get("账号") or ek` 只改 key 不转 schema)

### 修复要点
- 存量迁移:从同项目 18列 CSV 按 **packId** 回填 packCode/保证金/报价模式/物资条数(**包件属性与企业无关**,任意企业行可查;补漏通道独有的企业 CSV 无行则留空)
- 新通道首轮开发:复制一份既有样本结构做模板;worker 拉数据时就提取全字段,不事后补
- 写入语义:同 packId 覆盖更新(审核状态会变),新 packId 追加

## 远程批量启动(编排器)静默失败四坑

1. **pkill -f 在启动命令串内 = 自杀**:`pkill -f '[x]xx'; rm ...; setsid nohup python3 xxx.py ...` 中 bash -c 完整命令行含 "xxx.py" 字面量 → pkill 匹配分发 shell 自己 → rm/启动全没执行。编排器日志 started OK 无报错,但 worker 进程 0、结果文件 mtime 旧、收集到上一轮旧数据。`[x]` 括号技巧救不了(匹配文本在命令串后半段)。修复:分发命令**禁 pkill**。
2. **exec_command 不 read = 命令没发出**:fire-and-forget(exec 后 sleep 1 即 close)远端命令静默不执行。必须 read——PipeTimeout 异常吞掉(read 超时 = 命令已发出;不 read = sshd 没收到)。
3. **完成判定 grep 残留旧日志 = 假完成**:上轮 log 留 "DONE",下轮未清 log → 立即判全完成 → 收集旧结果(症状:16s 全 done、结果与上轮逐字节相同)。修复:分发时 rm 旧 log/结果;判定 = 远端进程计数=0 **且** log 含本轮 DONE。
4. **验证写盘别信中间输出**:worker 说 "DONE saved xxx.json" 但文件可能 = `{}`(前置逻辑 bug 或响应格式解析错)。主服收集后核对结果文件内容/mtime 再报写入条数。

### 编排验证链(任一环缺失先怀疑编排层,不怀疑 worker 逻辑)
ps 进程数 > 0 → log 出现本轮进度 → 结果文件 mtime 更新 → 消费端字段能读到

## 附带运维修复(同批实证)
- 增量 seen 文件:改 `{token: <REDACTED> dict + 加载时裁剪 >6h;旧纯 list 格式 = 过期池直接弃
- 串行分发改 ThreadPoolExecutor(4 并发):8 台 ~2min → ~30s;注意 BOXES 三元组配 enumerate 解包(lambda 取 4 项 IndexError)
- bot.log 轮转:apt install logrotate + /etc/logrotate.d/pixbot(daily/50M/**copytruncate**——进程持 fd 必须 copytruncate)
- 采集机 SSH 封禁会自动恢复:先 ssh 探测再让用户去控制台放行
