## 九、云资产发现

### 9.1 对象存储（S3/OSS/COS/Blob/GCS）
```bash
# Bucket 命名规律（红队生成式枚举）
# target-prod / target-dev / target-backup / target-upload / target-images
# target-数据 / target-备份 / 拼音/英文名+环境

# 工具
- S3Scanner（批量检测）
- bucket-stream
- grayhatwarfare.com（公共桶搜索）
- 空间引擎：FOFA "target.com" 关联存储域名

# 权限验证（无签名直接列举）
aws s3 ls s3://target-prod --no-sign-request
aws s3api get-bucket-acl --bucket target-prod --no-sign-request
# 阿里云：ossutil ls oss://bucket --no-sign-request
# 腾讯云：cosbrowser / coscmd 无签名列举
# 错误语义：AccessDenied(存在但拒绝) / NoSuchBucket(不存在) / AllAccessDisabled
```

### 9.2 云函数与 Serverless 资产
```bash
# 云函数 API 网关：/api/v1/xxx、/prod/xxx 形态，常暴露内网调用接口
# 微信云开发/腾讯云开发环境指纹
curl -i "https://xxx.app.tcloudbase.com/_/cloudbaserun"
# 响应头 X-TCB-Source 暴露云环境存在
# 阿里云 FC / AWS Lambda API 网关 / GCP Cloud Run

# 云函数常见问题：未授权调用（无鉴权）、调试日志泄露、环境变量注入
# 空间引擎语法：FOFA "app.tcloudbase.com" && 目标关键词
```

### 9.3 未绑定域名与影子资产
```
# 已注册但未接入 DNS/未部署服务的域名（NS 指向无效）
# 方法：CT 日志中找到的域名 → 无法解析 → 可注册或接管（见第五章）
# 已解绑的 CDN/存储域名 → 悬空 CNAME → 接管

# 影子资产画像（红队甜点区）
# - 开发者自建测试站（VPS 上跑 Jupyter/phpMyAdmin/Grafana）
# - 员工个人 GitHub Pages/网盘/云主机绑定目标域名
# - 未纳入采购的云资源（AWS 账号/新租户）
# 发现渠道：空间引擎按公司名/邮箱/证书关联、员工社交主页、招聘 JD 中的技术栈
```

### 9.4 容器与编排（K8s/Docker）
```bash
# 暴露面
# 2375/2376 Docker API（未授权 = 直接 RCE）
# 6443 Kubernetes API、10250 kubelet（未授权 pod 管理）
# 9090 Prometheus / 3000 Grafana / 8080 Harbor Registry
# 空间引擎：FOFA "protocol=docker" && 目标IP段 / "kubelet" "10250"
nmap -sV -p 2375,2376,6443,10250,9090,3000 target.com
```

