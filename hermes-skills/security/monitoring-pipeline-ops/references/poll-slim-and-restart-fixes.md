# 轮询瘦身 + 服务重启坑(2026-09-01 实录)

## 轮询耗时瘦身:单轮 5分30秒 → 2分20秒(4 台采集机全部生效)

### 方法(按序)
1. **量化基线**:日志"轮询完成"时间戳间隔,部署前后对比,别凭感觉。
2. **逐段估算请求数**:审计 N 页 + discover 翻页(3 status × 8 页 + join 3 + 公告流 5)+ fetch 每项目 + 候选 15 + save + 比对。请求数 × 0.8-1.5s(国内直连)≈ 真实耗时。
3. **找"每轮重复的无用请求"**——差距几乎都在这里。

### 三大毒点与修复
| 毒点 | 现象 | 修复 |
|---|---|---|
| 无清单项目每轮全量重试 | 26 个拉不到包件清单的项目(询价/线下/单一来源公告),每轮每个 3-4 请求(公告列表 2 页 + 标题搜 + readNoticeInfo)≈ 80-100 请求 ≈ 2 分钟 | 失败退避:内存 dict `_fetch_skip[pid] = ts`,50 分钟内不重试(新公告 24h 内仍会被补上) |
| 坏票重试占满候选名额 | 识别失败票默认 5 次重试,TTL 30 分钟内每轮都进候选,15 个名额被占满、新票排队 | 失败 2 次即放弃 + retry 票每轮限速 ≤3 个且排在新票之后(`proc = proc_new + proc_ret[:3]`) |
| 全量重写浪费 IO | 178 个项目每轮全量 json.dump | 项目信息 hash 去重(内容不变不写,全局 `_last_info_dump`);pack_map 仅 st_map 命中的项目重写 |

附带:全量比对(24h 一次)30 → 15 项目上限,sleep 0.4 → 0.3。

### 端到端实时链路(配合 bot)
采集机单轮 2-3 分钟 + merger crontab */3 + bot index 缓存 5s → 企业报名/审核变化 ≈ 3-5 分钟在 bot 可见。

## 服务重启部署坑
1. **systemd 服务名无连字符**:`v6collector.service` ≠ 猜的 `v6-collector.service`。先 `systemctl list-units --type=service --all | grep -i v6` 查真实名。
2. **pkill -f 自杀**:`pkill -f pix_bot_server.py` 整行匹配到执行命令的 shell 自身 → 服务没起来。安全:`ps aux | grep '[p]ix_bot_server.py' | awk '{print $2}'` 拿 pid 再 kill;杀启分离。
3. **setsid nohup + 彻底重定向**:`setsid nohup python3 x.py >> /tmp/x.log 2>&1 < /dev/null &`。否则 nohup 持有 SSH channel,exec_command read 阻塞超时(exit 124/read 挂住),误导为失败(实际已启动)。
4. **启动后 sleep 5-8s 再 ps 验证**;若出现双进程(第一次 nohup 实际成功 + 第二次 setsid),kill 多余只留一套(注意先确认哪个是哪个)。
5. **本机私钥陷阱**:`id_ed25519` 存在但不是目标服务器密钥 → paramiko 认证失败;强制指定专用密钥(`v6_master_key`),不要用"存在即用"的回退逻辑。
6. 远端脚本执行顺序:先上传代码(备份 .bak_vXXX)→ py_compile 验证 → 再 restart;restart 用两个独立 exec_command(杀、启分开),避免 channel 挂住。

## 数据口径答疑模式(用户问"N 个是什么"时)
- 必须给实据:抽样项目(名称/编号/年份)+ 构成分布(status/年份/来源)+ 与相邻数字的关系(12,797 + 7,922 = 20,719 = 已结束总数)。
- 典型口径:可拦截项目 = 部署后公告发布时间 ≥ 部署日 + stage∈{报名中/待竞价/竞价中};8/31 发布 46 公告 → 39 报名中(可拦截)+ 7 历史(询价/单一来源/谈判/线下类,非 bidType=02,merger 自动归历史,排除正确)。
- 菜单分类判定统一:`blockable_projects()` 返回 (未开始, 已开始) 元组列表,每项 (pid, info);finished_projects() 三类:有包件清单(完整)/ 有 pack_map(部分)/ 无目录(历史索引占位)。
