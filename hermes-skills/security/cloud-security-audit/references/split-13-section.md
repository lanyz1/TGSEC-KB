## 十二、云取证与对抗

### 12.1 云日志体系（审计与取证基线）

| 平台 | 审计日志 | 数据事件 | 网络流 |
|------|---------|---------|--------|
| AWS | CloudTrail（管理事件/数据事件） | S3 Access Logs | VPC Flow Logs |
| Azure | Activity Log | Diagnostic Logs | NSG Flow Logs |
| GCP | Cloud Audit Logs（Admin/Data Access） | Storage Logs | VPC Flow Logs |
| 阿里云 | ActionTrail | OSS访问日志 | VPC流日志 |

```bash
# 取证视角：快速定位异常
# CloudTrail 中找提权动作
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AttachUserPolicy --max-results 50
# 找 AssumeRole 横跳
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole --max-results 100
# 找新凭据创建
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=CreateAccessKey
# 找日志自身被操作（攻击信号！）
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=StopLogging
```

### 12.2 检测规避（攻击者视角对抗）

```
1. 日志禁用/删除（T1562.008 Disable or Modify Cloud Logs——ATT&CK云矩阵最高保真检测点）：
   - AWS: StopLogging / DeleteTrail / UpdateTrail / PutBucketLifecycle(短过期自动删日志桶)
   - Azure: Diagnostic settings 删除 / Activity Log retention缩短
   - GCP: Cloud Audit Logs sink 删除 / exclusion filter
   - 阿里云: ActionTrail 停用 / 日志库删除
2. 时间线破坏：修改资源创建时间戳、快照删除
3. LOTC（Living-off-the-cloud）：纯API操作 + 合法云服务中继（S3/云盘/Slack API）做C2与数据外带
4. 身份拟态：伪造可信role-session-name（如CI/CD管道名）、借用服务角色执行
5. 隐蔽凭据：创建拟态命名的AK（backup-svc-2026）替代轮换
6. 小批量慢速外传：规避批量下载检测规则与数据量告警阈值
7. 跨区域操作：在日志未启用的区域执行关键操作
```

### 12.3 云取证要点（对抗中的证据保全）

```
1. 先保全再响应：CloudTrail/S3日志桶开启版本控制+对象锁定（Object Lock/WORM）
2. 快照优先：EC2/RDS/EBS 先打快照再隔离，防止攻击者删数据
3. 日志外置：CloudTrail日志多副本到不可变存储（S3 Object Lock / 第三方SIEM）
4. 时间线构建：以 GetCallerIdentity → 首次异常操作 → 提权 → 外传 建立时间线
5. 注意 CloudTrail Lake 已于2026.05.31停止新客户开通——取证方案需迁移
6. 身份侧取证：SSO登录日志、MFA事件、令牌使用地（IP/UA）
7. 对抗前提：攻击者大概率已删部分日志——以"日志缺失本身"作为攻击证据
```

### 12.4 红队对抗作战要点
```
1. 行动前记录目标日志配置（哪家审计开没开、保留多久）→ 决定规避策略
2. 首选管理账号/根凭据的获取路径往往能顺带获得日志权限
3. 使用独立IP/代理池 + 合理时区操作，模拟正常业务行为
4. 明确"触警预期"：已知检测规则的动作（StopLogging等）留到收尾或改用替代手法
5. 每步操作同步记录CloudTrail事件名，便于报告阶段给客户做检测验证
```

