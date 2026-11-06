## 十一、API网关与微服务攻击面（高级）

### 11.1 API网关绕过
```
# 网关路径归一化 vs 后端不一致（参数走私）
/api/../admin
/api/%2e%2e/admin
/api/v1/..;/admin
# 网关解码差异：%25xx、双编码
# 网关校验Header，后端信任Header（X-User-Role: admin 直传后端）

# 网关身份信任：
X-User-Id / X-Forwarded-User / X-Auth-Header
# 若网关放行内部请求特征头 → 直接伪造内部身份头绕过鉴权
X-Forwarded-For: 127.0.0.1
X-Real-IP: 127.0.0.1
X-Envoy-Internal: true
X-Amz-Cf-Id: 本地地址判定

# 网关限流/授权在网关层，后端服务无防护 → 直连后端端口
# 端口扫描内网服务：服务网格/注册中心（consul/nacos/eureka）泄露服务列表
```

### 11.2 BFF（Backend for Frontend）攻击
```
# BFF聚合层把多个内部API拼装给前端，常缺少内部权限细分
# 篡改BFF传入字段 → 内部服务信任BFF的字段
# BFF未做BOLA → 直接改内部对象ID
# 移动端/Web端BFF鉴权不一致（mobile BFF宽松）
# /bff/ 端点枚举与SSRF：BFF常会代理外部URL
```

### 11.3 服务间信任与JWT传播
```
# 服务间用JWT/service account通信，信任传播链
# A服务校验后生成的内部Token，B服务不再校验claim → 横向
# 内部服务地址可直连（service.internal:8080）
# 获取服务账号Token（K8s SA token / 环境变量）后调用管理API
# gRPC mTLS：SPIFFE ID伪造（若信任校验宽松）
```

### 11.4 聚合/批量API
```
POST /api/batch {"operations":[{"method":"GET","path":"/users/1"},...]}
# 批量API常绕过单对象授权检查
# 递归/嵌套批量 → 越权+DoS
# GraphQL批量查询同理
```

