# v738 — 菜单B 23↔21 抖动根治 + AI 待补截断修复(2026-09-03)

## 症状

bot 反复推送「📊 菜单B 数据变化 • 审核通过 23 → 21 → 23 → 21」,且每轮都差同样的 2 个包件。
同源还出现 `[菜单B监控异常] too many values to unpack (expected 2)` 每 3 分钟一次。

## 根因 1:非原子写 pack_map.json(假抖动)

- orch8b(cron 5/35 分,8 台并行补漏)+ merger 直写 `open(path,"w")` → **先 truncate 再分块写入**(json.dump indent=1 使窗口可见)。
- bot `mb_monitor_loop`(3 分钟轮询)读 pack_map.json 数审核通过/拒绝;**读中半写文件 → json.load 抛错 → 整个项目计为 0**(该项目 2 个已通过包件消失)→ 推「23→21」;文件写完 → 下轮恢复 → 推「21→23」。循环往复,按 orch8b 写轮次节奏横跳。
- 注意:真实审核变化(如十堰车务段 4→6)叠加在写竞态上时,会表现为先掉后涨,**别把真实推送当抖动**——原子化 + 明细推送(见下)可区分。

## 修复 1:全部写点原子化

orch8b.py + merger.py 所有 pack_map.json 写点改为 `tmp 文件 + os.replace`(读者永远看到完整旧文件或完整新文件)。
修复后同一轮的真实变化(十堰 4→6)推送一次即稳定,不再横跳。

## 根因 2:detail 推送 tuple 解包 bug

pix_bot_server.py ~3925:`for pid, (op0, cu0) in diffs[:4]:` 错误(元素实际是 3 元)。
真实审核状态变化(未审批→通过)触发 detail 生成时崩溃 → 推送失败且状态不落盘 → 下轮重算再崩。
修:`for pid, op0, cu0 in diffs[:4]:`。

**定位残留炸点的方法**:静态审查穷尽后,给 except 打 traceback:
`except Exception as e: import traceback; _tb=traceback.format_exc().splitlines(); print(f"[菜单B监控异常] {str(e)[:60]} @ {_tb[-2][:150]}", flush=True)`
重启等自曝行号。本次验证:修复后异常数 0(此前误判"还在炸"是观察器问题,见下)。

## 根因 3(后续):AI 查询工具静默截断 pending

用户问「哪18家」,AI 答平台 18 = 采集 6 + 待补 10——6+10≠18,差 2 家。
- 数据侧完全正确:plat_enroll_map.projs[projCode] 企业列表 18 家、pack_map 采集 6 家、真实待补 **12 家**。
- ai_query.py `project_enterprises` 返回 `"pending": pending[:10]` **硬截断前 10 条**;缺的是名单尾部两家四川企业(成都收荒匠、四川和记鑫城),LLM 看不到就顺着报「待补10家」,还无法察觉算术矛盾。
- 修复:`pending[:10]` → `pending[:limit]`(默认 50 全量),**加 `pending_total` 字段**让 LLM 永远知道总数;顺手把 ents 按 `_norm(单位)` 去重(pack_map 有账号键+中文单位键双条目 → 重复计数 8 条→6 条)。
- 验证:直接 python3 调函数,pending_total=12/pending 12 条全量/ents=6;再重启 bot 生效(ai_query 被 bot import,必须重启)。

**类级规则**:函数调用工具返回任何截断列表,必须同时返回 `*_total`;截断跟随 limit 参数而非写死;模型推理工具结果的算术一致性靠字段齐全保证。

## 补丁与验证纪律(本周期反复踩)

1. **文本替换 patch 毁缩进**:patch_atomic_* 用字符串替换保留行首空白不当 → merger.py 双 try/错位缩进、with=20/dump=20/os.replace=16 空格错位、orch8b `_tmp` 16 空格(应为 8)。修复用整块正则(显式捕获空白)或**精确按行重写缩进**;每次改完必须 py_compile。
2. **远程脚本传运**:SSH 命令串内嵌 python 引号嵌套必炸 → 本地写文件 SFTP 上传 + 远端执行;或 base64 通道:
   `echo <b64> | base64 -d > /tmp/x.py && python3 /tmp/x.py`(REMOTE_PY 用普通三引号,勿 raw)。
3. **转义链路吃字面 `\n`**:JSON 参数 → 本地文件 → 本地 python 解析 → base64 → 远程 python 解析,多层转义后 `\\n` 可能以**字面反斜杠-n** 写进被改文件 → SyntaxError: unexpected character after line continuation。反修构造:`BS = chr(92) + "n"`,用 `src.replace('...'+BS+'...', '...真换行...')`。
4. **START exec 读超时是假象**:setsid 后台进程持有 channel → exec_command read 超时;kill 后分两个 exec(先 kill 验证 0 残留,再 start),用独立 ps(`ps -eo pid,lstart,cmd | grep '[p]ix_bot_server.py'`)确认单实例 + 启动时间。
5. **日志观察器骗局**:grep 窗口只匹配「菜单B监控/异常/启动」关键词时,用户操作日志不匹配 → 每次 check 输出**同一批历史行**(行号略移),误判「重启后还在炸」。对账三件事:进程 lstart 是否晚于部署、异常/推送行是否在重启时间戳之后、小日志文件(6KB 级)直接全量拉而不用 grep 窗口。本次最后确认:06:40:09 重启后异常 0 次、06:41 后 4+ 轮零推送,抖动根治;观察器反复显示的异常全是 06:22 前旧进程历史。
6. **ai_query/ai_agent 改动重启 bot 生效**(无独立 ai_agent 进程,函数调用在 pix_bot_server 进程内)。
