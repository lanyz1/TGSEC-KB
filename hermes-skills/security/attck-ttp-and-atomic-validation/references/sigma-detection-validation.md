# 检测规则验证闭环（Sigma / 日志 / 覆盖矩阵）

## 闭环六步

```text
① 定靶：选 T-ID（优先"有行为但无告警"的阶段）
② 备检测：确认日志已采集（Sysmon/auditd/云审计）+ SIEM 规则已加载
③ 执行：atomicredteam 单个原子（或手工等价动作），记录起止时间戳
④ 判定：查遥测（是否产生日志）→ 查告警（规则是否命中）
    遥测无 = 采集缺口（要改配置）
    遥测有、告警无 = 规则缺口（要写规则）
    告警有 = 通过，记录规则 ID
⑤ 补规则 → 回归：同一条原子再跑一次，确认这次响
⑥ 回填矩阵：战术 × T-ID × 遥测 × 告警 × 规则路径
```

## 覆盖矩阵（报告就用这个表）

| T-ID | 战术 | 遥测 | 告警 | 规则来源 | 备注 |
|------|------|------|------|----------|------|
| T1059.001 | 执行 | 有 | 无 | 待补 | PS 命令行未入 SIEM |
| T1003.001 | 凭据访问 | 有 | 有 | EDR 内置 | LSASS 句柄访问 |
| T1505.003 | 持久化 | 有 | 无 | 待补 | 上传目录无文件监控 |

## Sigma 使用要点

```bash
# 写规则：logsource(product/category/service) + detection(selection/condition)
# 转换：sigma convert -t splunk|elasticsearch|lucene -p <pipeline> rule.yml
# 批量：sigma convert -t <backend> -p <pipeline> rules/ -o out.txt
```

- 字段映射是最大坑：Windows 事件字段在 Splunk/ES 里名字不同 → 必须用 pipeline 映射。
- 规则里的 `condition` 别只写 `selection`：加过滤（白名单进程/路径）否则告警风暴。
- 版本兼容：新 pySigma 与老 sigmac 语法不同，老规则要迁移。

## 其他日志源

| 场景 | 看什么 |
|------|--------|
| Linux | auditd（execve/文件写/ptrace）、`/var/log/auth.log`、journal、bash history（不可信） |
| Web | access log（配合 `attacker-tracing-and-counterstrike` 的日志探针）、应用审计日志 |
| Windows | Security 4688/4624/4672、Sysmon 1/3/11/13、PS 4104 脚本块 |
| 云 | CloudTrail/操作审计（凭据使用、角色扮演、快照导出） |
| 容器/K8s | audit 日志、API Server 审计、Pod 创建/exec 事件 |

## 常见坑

- 只跑原子不看日志 = 白跑；**没有遥测本身就是结论**。
- 告警命中但无规则路径 = 无法回归，等于没验证。
- 时间不同步（多地时区）导致关联失败：先对时（本库：主服 UTC、平台 +8）。
- 把"文件被删了"当清理完成：日志里的执行痕迹已产生，报告要写清楚。
