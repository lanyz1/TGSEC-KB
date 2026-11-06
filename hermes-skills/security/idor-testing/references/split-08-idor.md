## 七、多租户与跨租户IDOR（新增·重点）

### 7.1 租户隔离机制识别
```
# 常见租户标识位置：
# - Header：X-Tenant-ID / X-Org-ID / X-Account-ID / X-Workspace-ID
# - 路径：/orgs/{id}/... /workspaces/{id}/... /tenants/{id}/...
# - 子域：tenantA.target.com → tenantB.target.com
# - JWT/Claim：org_id / tenant_id in token
# - Body字段：{"tenant_id":"a"}

# 隔离失效模式：
# 1. 租户参数可切换（改header/路径即跨租户）
# 2. 租户参数与Token不校验（Token的租户≠请求租户）
# 3. 全局对象（如公共配置/模板）泄露租户数据
# 4. 搜索结果跨租户（多租户共享索引）
# 5. 缓存键不含租户维度（A租户缓存命中B租户数据）
# 6. 文件存储共享桶（目录隔离被路径遍历绕过）
```

### 7.2 跨租户攻击手法
```http
# 切换租户头
X-Tenant-ID: 1 → 2
X-Org-ID: acme → globex
X-Workspace-ID: ws1 → ws2

# 子域切换
a.target.com → b.target.com（cookie可能不隔离）

# JWT claim篡改（配合签名绕过）
{"sub":"<EMAIL-REDACTED>","tenant":"competitor"}

# 搜索/导出跨租户
GET /api/search?q=*&tenant_id=other
GET /api/export?scope=all_tenants

# 批量接口跨租户
POST /api/batch {"tenant_id":"other","ops":[...]}

# 关联对象跨租户
GET /api/orders/1001 → 订单属于租户B但租户A可读
```

### 7.3 SaaS多租户案例（情报参考）
```
# 案例1：Langflow（AI平台）CVE-2026-55255
# - 跨租户IDOR：租户A可访问/执行租户B的workflow
# - 危害升级：恶意执行他人flow → 窃取内嵌的LLM API Key/云凭证
# - 根因：flow对象缺少租户级授权校验（BOLA）
# 测试路径：GET /api/v1/flows/{id} 用其他租户Token

# 案例2：Chainlit CVE-2025-68492（AI对话平台）
# - thread/chat对象跨用户IDOR：可读他人对话历史
# 测试路径：GET /api/v1/threads/{id}

# 通用规律：SaaS平台"共享数据平面+租户隔离"架构，隔离层一旦漏检即全租户沦陷
# 重点测试：公共配置/模板/AdminAPI/管理后台端点是否忽略租户维度
```

