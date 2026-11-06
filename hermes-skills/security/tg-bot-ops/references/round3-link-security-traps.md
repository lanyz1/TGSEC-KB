# 第三轮审查:链路/安全层陷阱(95306 bot v5.x 会话实录)

补充 SKILL.md 交互陷阱清单的第三轮发现(链路/安全层,2026-08-29 实测):

## 1. 动态配置代替硬编码(最隐蔽)
- 症状:bot 里新增跳板机显示成功,但 merger 根本不拉新机数据、加速器不切新机、health 不显示新机——全部"白加"。
- 根因:merger.py/accel.py 的 COLLECTORS 是代码硬编码常量,bot 写 jumpers.json 消费方不知道。
- 修复:`get_collectors()` 读 jumpers.json(跳过 disabled),失败回退内置列表;SSH connect 要带 port。
- 验证:`merger 采集机: [('上海', 22), ...]` 打印确认读到动态配置。

## 2. 命令注入(远程脚本 f-string)
- 症状:新增跳板机口令含引号/换行 → 内嵌脚本 Python 语法错误 → 崩溃。
- 修复:cfg = json.dumps({...}); script 里 `cfg = json.loads({cfg!r})`,所有用户输入走 cfg 字典。

## 3. 输入状态机超时
- 症状:用户点"收集项目"后忘记取消,下一条消息(可能是项目查询)被当作收集关键词执行。
- 修复:PENDING_INPUT[cid] = {"m": "collect", "t": time.time()};handle_text 里 >600s 自动 pop。
- 兼容:jumpswap:{old_name} 模式存进 "m" 字段,startswith 匹配。

## 4. 原子写 JSON
- 症状:偶发显示"企业 0"——merger json.dump 写 pack_map.json 进行中,bot 读到半写文件解析失败。
- 修复:写 tmp 文件 + os.replace(原子 rename)。

## 5. 更换资源要清场
- 症状:更换跳板机后旧机 daemon 继续跑(继续请求目标站,白耗配额/可能触发风控)。
- 修复:更换流程 = 部署新机 + 旧机标记 disabled + SSH 远程 pkill 旧 daemon。
- 杀 daemon 命令:`pkill -9 -f '[c]ollect_daemon' || true; pkill -9 -f 'collector.py' || true`(注意 [x] 技巧+分步)。

## 6. 新增节点闭环验证
- 加机器后必须验证全链路:jumpers.json 写入 → merger 下一轮 get_collectors() 读到 → 拉取新机数据 → 心跳上报 health.json。
- 只验证 SSH 通 = 假成功。
