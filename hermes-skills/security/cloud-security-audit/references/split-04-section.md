## 三、云存储安全深度审计

### 3.1 AWS S3 Bucket 攻击

**未授权访问检测与策略审计：**
```bash
aws s3 ls s3://target-bucket --no-sign-request
aws s3api get-bucket-policy --bucket target-bucket
aws s3api get-bucket-acl --bucket target-bucket
aws s3api get-bucket-versioning --bucket target-bucket
aws s3api get-bucket-website --bucket target-bucket

# 常见误配置矩阵
# - s3:GetObject 公开 → 数据泄露
# - s3:PutObject 公开 → 数据篡改/钓鱼托管
# - s3:ListBucket 公开 → 文件枚举
# - s3:PutBucketPolicy → 策略篡改（给自己开权限）
# - 版本控制未开启 → 无法恢复被删数据
# - Bucket未删除 → Dangling DNS劫持
```

**Bucket 命名接管（Dangling DNS / Subdomain Takeover）：**
```
1. 域名 CNAME 指向已删除的 S3 Bucket（或未创建）
2. 在目标区域创建同名 Bucket 接管
3. 实现钓鱼/内容注入/证书签发
```

**预签名URL与STS滥用：**
```
1. 泄露的预签名URL在有效期（最长7天）内可重复使用 → 收集分析日志中的签名URL
2. 预签名URL Policy过于宽松（允许上传任意key）→ 覆盖关键对象
3. 前端生成的STS临时凭据权限过大 → 直接越权访问其他桶
4. 参数篡改：?acl / ?uploads / ?tagging / ?versioning / ?logging 测试越权
```

### 3.2 阿里云 OSS 攻击

```bash
# 公开访问检测
curl "https://bucket.oss-cn-hangzhou.aliyuncs.com/?list-type=2"

# 前端AKSK硬编码（长期凭据，最常见）
# AK: LTAI 开头；SK: 40位字符串
# 泄露源：前端JS、小程序、配置文件、GitHub、heapdump

# RAM策略注入（用户输入未过滤直接拼入策略JSON时）
# 输入: aaa"]},{"effect":"allow","action":[""],"resource":["qcs::oss:","qcs::ecs:*
# 结果: 策略被闭合注入，允许访问所有资源

# 签名绕过与越权
# - 预签名URL key参数覆盖（替换为其他对象路径）
# - STS临时凭据权限过大
# - CDN回源误配置（回源请求未过滤，阿里云OSS 2024年曾公开案例）
# - CORS配置过宽（Access-Control-Allow-Origin: *）→ 浏览器端跨域读取桶数据

# 桶策略/ACL测试
ossutil64 ls oss://bucket-name
ossutil64 stat oss://bucket-name/object
```

### 3.3 Azure Blob / GCP Cloud Storage
```bash
# Azure 公开容器枚举
curl "https://account.blob.core.windows.net/container?restype=container&comp=list"
# SAS Token 泄露利用（sv= 开头的URL参数）
az storage blob list --container-name container --sas-token "sv=...&sig=..."

# GCP 公开桶
gsutil ls gs://bucket-name
# 桶策略
gsutil iam get gs://bucket-name
# 版本化对象恢复/删除
gsutil versioning get gs://bucket-name
```

### 3.4 私有/自建对象存储（MinIO 等）
- **MinIO CVE-2025-31489**：任意覆盖写桶文件（绕过签名校验），可篡改/投毒其中的 AI 模型文件、数据集，实现"存储→模型供应链投毒"（加载模型即执行恶意代码）
- S3 兼容服务（MinIO/Ceph/RGW）常暴露在公网且使用默认/弱凭据，注意识别 `9000` 端口（MinIO Console）
- 检查桶内 AI 相关资产：模型权重（.pt/.safetensors）、向量库备份、RAG语料——**AI/ML管道资产是高权限凭据的常见藏身处**（8分钟攻击事件即从公开S3桶中的RAG凭据入手）

