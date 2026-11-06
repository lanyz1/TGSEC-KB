## 八、托管数据库与云服务独特漏洞

### 8.1 托管数据库未授权/配置缺陷

| 平台 | 服务 | 常见缺陷 |
|------|------|---------|
| AWS | RDS/Aurora | 公开可访问（PubliclyAccessible=true）、弱口令、快照公开共享、删除保护关闭 |
| AWS | DynamoDB | 表级策略过宽（未授权Scan）、DAX端点暴露 |
| AWS | OpenSearch/ES | 公网开放+无认证（IAM policy缺失）、Kibana未授权 |
| AWS | Redshift | 公网端口5439暴露、凭据泄露 |
| Azure | SQL DB/Cosmos | 防火墙规则0.0.0.0/0、SAS key泄露、连接串硬编码 |
| GCP | Cloud SQL | 公网IP+无SSL强制+弱口令、Cloud SQL Auth Proxy未启用 |
| GCP | BigQuery | 数据集/表IAM过宽（allUsers可查询） |
| 阿里云 | RDS | 白名单0.0.0.0/0、弱口令、内外网地址混淆（私网地址被当作公网开放） |
| 通用 | 托管Redis/Memcached | 公网+无认证 → 写SSH key/反弹Shell |

```bash
# 探测公开托管数据库（Shodan/FOFA语法）
# AWS RDS: port:"3306" ssl:"Amazon RDS" / "rds.amazonaws.com"
# Azure: "database.windows.net"
# 阿里云RDS: port:"3306" "aliyuncs.com"
mysql -h <rds-endpoint> -u admin -p
# 无认证Redis写SSH key链
redis-cli -h <host> -p 6379
# config set dir /root/.ssh → set authorized_keys
```

### 8.2 数据库凭据链与快照攻击

```
1. 数据库连接串泄露（代码/配置/环境变量/heapdump）→ 直连托管数据库
2. 快照共享/导出：RDS/EBS/Cloud SQL 快照共享给攻击者账号 → 离线恢复读取全库
3. 跨账号RDS快照共享：modify-db-snapshot-attribute 添加攻击者账号ID
4. 数据库恢复后从系统表中提取其他凭据（mysql.user、pg_shadow等）继续横向
5. 备份文件公开：S3/OSS桶中的.sql/.bak备份未加密且桶公开
6. 托管数据库自带"导入导出"通道：Data Pipeline、DMS复制任务→指向攻击者库
7. 内存数据库（ElastiCache/Redis）无认证 + 弱口令 → 数据窃取/RCE
```

### 8.3 其他云服务独特漏洞与滥用

```
1. CloudFormation/Cloud Development Kit（IaC）：模板中硬编码密钥；ChangeSet/Stack策略
   → 结合 PassRole 执行任意IAM操作（UNC6426 提权环节）
2. SSM（Systems Manager）：
   - Parameter Store 明文参数（/prod/db_password 明文）
   - RunCommand 对托管实例执行命令（若持有ssm:SendCommand）
   - SSM Agent 端口的本地利用（未认证HTTP 127.0.0.1:9999+）
3. Service Quota / GetServiceQuota：侦察时摸清配额上限，规划挖矿/资源滥用规模（10分钟挖矿案例）
4. 备份服务滥用：云备份/Veeam等（2025年威胁报告显示备份系统成为首要目标）→ 删库/勒索先删备份
5. 事件桥/编排滥用：EventBridge、Step Functions 编排中的越权
6. 云密钥管理：KMS 密钥策略过宽（其他账号可加密/解密）、CMK自动轮换缺失
7. 静态网站/CDN：CloudFront/OSS静态托管 + 桶策略过宽 → 钓鱼基础设施
8. 消息队列：SQS/SNS/MNS 未授权订阅/消费 → 数据流窃听
```

