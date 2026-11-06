# 多机分段大拉取(Multi-server segmented pull)——跳板机并行遍历 uid/ID 段

场景:目标为自增数字资源(uid/order_id),数据量几十万级,用户提供多台跳板机要求不走本机 IP。把区间切成 N 段,每台跑一段,后台长跑,最后合并。

## 编排要点(2026-09 doumvips 69 万 uid 实测)

- 分片:uid 1→693400 按跳板台数均分(3 台 × ~23.1 万);每台独立输出 JSONL + `.done` checkpoint + run.log。
- 遍历器(urllib 零依赖,见 spa-api-discovery scripts/fetch_range.py):8 workers 线程池;每 uid 拉 6 个接口;每 5k 写 checkpoint(断点续跑:启动读 .done 跳过已处理段);**连续 >30 次 token 失效熔断退出**(token 被封不空跑)。
- 速率参考:8 workers/台 ≈ 6-14 uid/s;23 万段 6-11 小时;每台请求并发 = workers×每uid请求数。
- 先每台 smoke 60 uid(验证 token 存活 + 返回结构 + tokfail=0)再放全量。
- 合并:回传后按 uid 去重(保留字段最全记录),再出 Excel/报告。

## 关键坑(全部实测)

1. **paramiko exec "FAIL/超时" ≠ 没启动**:`exec_command("setsid python3 ... & echo $!")` 后 read() 阻塞报 TimeoutError,但进程已拉起。据此重试启动 → 每台 3 实例并发写同一文件,checkpoint 互踩,行数对不上。正解:
   - 启动命令收尾用 `nohup bash start.sh > /dev/null 2>&1 & echo PID=$!`(start.sh 内含 rm 旧输出 + exec python3 ... > run.log 2>&1),不依赖 read() 收尾;
   - **任何重启前先 `ps aux | grep -v grep | grep <name> | wc -l`**;>1 时先 `pkill -9 -f <name>`(与启动分两条 exec)再确认 0,清输出文件,启动单实例;
   - 启动后 5-8s 三连验证:ps=1 + tail run.log + wc -l out.jsonl(在涨)。
2. 目标机房 IP 拦截:主域老系统(ThinkPHP /toupiao /douxingbang)常对数据中心 IP 返回 403/111,而 api 子域放行——先 curl 主域根判网关,别把"跳板不通"误判成目标下线。
3. token 是共享资源:69 万请求共用一个 token,风控封号前会先 tokfail 连续报错 → 熔断器必须基于 tokfail 计数,不是 HTTP 错误。
4. 数据分层交付:明文 PII(手机/微信)只在子集数据面,全库字段面(资金/绑定/层级)可全量——报告分开写,Excel 分 sheet。
