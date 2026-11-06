# 初次拦截取证修正 + v9.7 实施(2026-09-06 午后,接 round10 诊断)

## 取证推翻"报名无票"假设(审计逐条反查北京局13次, noticeId=abda9e7c-...)

1. **redirectEnrollUrl 行确实带 ST**:serviceTicket 不在请求 URL 而在 **detail 的"调用结果"返回跳转 URL 中** → collector 正则可提取 → enroll 票存在。走公告页跳转入口报名的企业 **4/4 被秒拦**(正亿 11:10 报名→11:10 采到;长藤 16:33→16:34)→ 该入口机制有效。
2. **审计行 URL 里 `projId=` 出现 0 次**、报名行只有 noticeId → 原定向反查(like projId[:8])确系死机制。noticeId 反查注意:整点"公告48h标记更新"系统任务行(detail 含几百个 noticeId, acct=None, 无 ST)会刷屏 → 过滤 acct 空即可;pageSize 5→50 才覆盖报名期多行。
3. **缺口的 4 家(津铁 9/1、欧锦 8:39、德裕隆 9:29、恒铁 9:32)= 走其它入口报名(前端项目列表/竞价系统内直接提交)→ 审计零痕迹 → 物理边界**,不是归属台故障。判定法:反查该 noticeId 全部历史行,缺口企业完全不在其中 → 其它入口报名+报名后零 cg 域活动 → 任何机制都拦不到,只能名册对照如实显示 + 竞价日登录补。

## 初次拦截率全景(北京局13次案例解剖)

```
公告页报名跳转入口 → 100% 秒拦(4/4,enroll 机制)
其它入口报名+后续有 cg 活动 → 活动票兜住(16/20)
其它入口报名+零活动(津铁/欧锦/德裕隆/恒铁) → 物理边界 ~20%
```

## v9.7 已实施(2026-09-06,8/8 台部署完成)

取证驱动的 4 处改动(collector_v9.py → 各台 /opt/v6/collector.py):
1. **enroll 票去 hash 分片**:主 proc 候选层 `if not t.get("enroll")` 才走 `hash(st)%8` 分片 → 8 台都处理报名票(幂等,量小);proc 排序 key 加 `0 if enroll else 1`(报名票最优先,时效强)
2. **定向反查双条件**:like projId[:8] + like noticeId[:8](gap 清单 meta 取 noticeId),pageSize 5→50
3. proc 上限 15→25(积压不饿死老票)
4. 审计翻页 5→10 页(1000 条窗口,截止高峰兜底)

## 部署方式铁律(采集机)

- 采集机 collector 由 **systemd 服务 v6collector** 管理:替换 /opt/v6/collector.py 后 `systemctl restart v6collector` 即重启(勿手动 pkill);V6_SHARD 在 service 文件里(查 `/proc/<pid>/environ` 可见)
- 日志 /tmp/v6_run.log,轮询 ~60s/轮;`审计 ST N, 新 M` 行看抓票密度;`过滤分布 [a,b,...]` 是 8 分片跳过计数
- 部署=主服中转 8 台(sftp put + systemctl restart);paramiko exec read 超时是假象(进程在跑),用轮询日志验证;本机直连仅 Ppikesi0001. 组(沪4/蓉5/青6/深7)可达,沪0-蓉3 须主服中转
- 验证:重启后日志出现新轮询行 + `systemctl is-active v6collector` = active

## 验证窗口

9/7 起沈阳铁道 97/98 次、9/9 北京局13次 19:00、9/10 漯阜A 10:00 竞价日 + 新公告报名高峰 → 对比缺口率是否收敛到物理边界值(~10-15%)。
