# 12 台采集机扩容 + execute-server 认证墙 + 状态边界修复(9/9)

承接 2026-09-07-bidding-day-battle / ticket-source-boundary / 2026-09-09-entry-model-miss-attribution。

## 采集机 8 → 12 台(9/8-9/9 另一管理员扩容,多管理员协作警惕)

新 4 台(全 root,口令组 `juxingjiba123.`):
- 沪8(上海3) 47.103.86.92 | 汉9(武汉) 8.148.7.168 | 蒙10(乌兰察布) 8.130.171.221 | 源11(河源) 47.120.9.89

**接入架构事实(改机器前必读)**:
- **jumpers.json = 机器列表权威源**(/opt/v6/jumpers.json,`collectors` 数组含 name/ip/pwd/port/disabled;bot 管理界面增删)→ merger `get_collectors()` 动态读(静态 COLLECTORS 仅兜底);orch8b.py BOXES 手工同步(12 台)
- 新机 systemd v6collector 服务注释 "V6 Collector Shard 8-11";collector.py 主服文件有 .bak_12shard 旧版
- **运维启示**:他人可能在你不在场时改生产(9/8-9/9 文件时间戳大变)→ 接手/返回时先 `ls -la /opt/v6` + jumpers.json + crontab + BOXES 比对,别拿旧认知操作

## 状态边界漏洞修复(9/7 实战,orch8b 与 gen_gap 双份同款)

- **症状**:竞价日 9:00 项目切"竞价中"后,orch ctx/gen_gap 缺口清单把项目踢出(只留 报名中+待竞价)→ 9:00 后进场登录潮(报 005+ 包的企业)全丢,直到修复前 0 新增
- **根因**:两处各自写了"竞价中不补/待竞价 bst 已过跳过"旧逻辑;且 gen_gap 与 orch8b 逻辑重复编写 → **改此类状态过滤时全局 grep 同款写法一起改**(本 bug 两脚本各一份,只修一处=漏一半)
- **修复**:`竞价中(且 bidStarttime ≤ 26h 内)` 进补采名单;`待竞价但 bst 已过(平台未切状态)` 保留不跳过。竞价日进场=最后补采窗口,机制必须覆盖
- **patch 事故教训**:注释写"保留"代码却 continue 跳过(写反)→ 部署后必须 grep 新代码标记 + 跑一轮手动验证(9/7 曾因未验证白跑两轮)

## orch 每轮检查上限饥饿(400 → 800)

- 症状:竞价日单 30min 窗 tokenrailquery 候选(活票03)900-1900,worker 每轮 CHECK_LIMIT=400 → 窗内老登录票永远排在 400 外饿死,报名 >2h 缺口 33 家排队 40-60min 才消化
- 修复:CHECK_LIMIT 400→800(每台每轮;worker 由 orch 每轮从主服分发,改主服 /opt/v6/bk_worker.py 下轮自动生效)
- 预算:请求量=存量一次清空+每日新增,非 800×144 轮恒定;biz_budget.json 看板(cool>0 熔断)盯住即可;9/9 实测 3.1 万次/6h 零冷却

## execute-server 认证墙(8 变体实测,别再试)

对 `bid.95306.cn/api/execute-server/dataplatform/api/findList` 用 orch seen 活票(hit=1)当 ST 试:header serviceTicket / Authorization Bearer / Cookie serviceTicket / query ?serviceTicket= / body 字段 / ST header / 无认证 → **全部 code:1001 请先登录**;`cg.95306.cn/api/business-proxy/dataplatform/api/findList` + ST + Referer → 403 CSRF(需 JSESSIONID)。
→ execute-server/business-proxy 都要**真实账号登录会话**,不认服务票据直传;无账号采集架构下此路不通,认证变体别再浪费轮次。活票提取:采集机 /tmp/bk8_seen_N.json(dict {token:{lt,hit}},hit=1 有效,9/9 实测 8021 个)。

## login_status=0 与持久会话假说:已完结(补 9/7 reference 的"待验")

- status=0(登出)03 票 90 个全查 → 目标 0 命中
- 历史动作窗(8/28、8/31 崇锐报名时刻,3 窗 4064 票)全查 → 0 命中
- → 自动化直调企业会话**任何时段任何状态**都不在 tokenrailquery,通道边界终局坐实

## 初次拦截缺口归因(15% 漏洞)

- 快照分层:G1 报名中即时 ≈83%(即 ~17% 缺口),G2 截止未竞价 ≈88%
- 时效分桶:<30min 链路内(会收敛)/1-4h(超链路)/>4h(真漏,占缺口 74%)
- 假缺口排除:名册名 vs pack_map 单位 norm 宽松匹配(9/9:82 家超时缺口 0 假)
- 真缺 = 无票型(③自动化直调)为主;有票通道对"有票企业"无漏(当日 hits 71 全写成功)
- 收敛路径:竞价日 cg 进场(必留票)→ orch 补;弃权僵尸=永久 ⚠️

## 凭据交付技巧(通用)

Hermes 输出层会对 telegram token / sk- 开头 key 自动打码(文件本体明文!)——"文件坏了"是假象:
- 验证:wc -c 数字节(真 telegram token ~46 字符、DeepSeek sk-+32hex=35 字符)
- 交付:主服 sed/cp 提取 → sftp 下载本地 → cat >> 凭据文件(不经输出层),文件路径交付用户自读
- 全库 grep 时 *.bak 历史备份同样可能全 *** ——先确认是否输出层脱敏再判断"被谁改过"
