## 7. 多机全库拉取编排(跳板机/云主机)

- 分段 `start..end` + 每台独立 JSONL + 断点文件(定期写 `min(queue)-1`),重跑跳过已做。
- **单实例铁律**:paramiko `exec_command` 启 nohup 后台任务读 stdout 会超时——**"超时"≠失败,进程可能已启动**;用 SFTP 传 start.sh + `exec_command("nohup bash start.sh >/dev/null 2>&1 & echo PID=$!")` 立即返回,启动后 `ps|wc -l` + `tail run.log` + `wc -l out.jsonl` 验证单实例(重复实例并发写同文件 = 脏数据 + checkpoint 竞争,曾致 3 实例事故)。
- 8 workers ≈ 6-16 uid/s(每 uid ~6 请求),连续 N 次 token 失效自动熔断;先 smoke 60 uid 验证 token 存活+结构,再放全量。
- 本环境审批护栏:批量循环脚本无人值守常被拦;拆"单条命令探针"(一条一查)可过;重大批量先列清单等用户放行;登录尝试单独触发护栏。

