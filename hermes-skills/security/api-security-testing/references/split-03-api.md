## 二、API发现与枚举

### 2.1 API端点发现
```
路径枚举：
/api/
/api/v1/ /api/v2/ /v1/ /v2/
/swagger/ /swagger-ui.html /v2/api-docs /v3/api-docs /openapi.json
/graphql /graphiql /playground /explorer /altair /apollo
/healthz /actuator /debug /console
/.well-known/ /openapi.yaml /swagger.json /docs /redoc /api-docs.json

BFF/网关专属路径（重点）：
/bff/ /mfe/ /edge/ /gateway/ /api-gateway/ /aggregator/
/__api/ /_next/data/ /ssr-api/ /webapp/ /mobile-api/

常用路径Fuzz：
ffuf -w api-wordlist.txt -u https://target.com/FUZZ -fc 404,400
kiterunner scan https://target.com -w routes.kite

# 从JS/SourceMap中提取隐藏API（jsfinder/SecretFinder/LinkFinder）
```

### 2.2 OpenAPI/Swagger深度利用
```
# 除标准端点外，注意：
# - Swagger JSON 中的 deprecated:true 接口（老代码，漏洞多）
# - 生产与测试环境共享swagger（staging.api.com/swagger）
# - 从OpenAPI文档批量生成可测试客户端
npx @redocly/cli build-docs openapi.json -o docs.html
# Swagger-Codegen / Bruno / Postman 批量导入测试
# 对比 v1/v2/v3 api-docs 差异：旧版本缺失的授权参数即BFLA线索
```

### 2.3 GraphQL发现
```
# 常见端点 + 持久化查询端点（Persisted Query）
/persisted/ /persist-query/ /graphql/persist /api/graphql/persist
# 持久化查询绕过：若仅允许哈希引用，可尝试通过内省先dump再重放
# 检测：POST {"query":"query{__typename}"} 返回正常即存在
```

### 2.4 HTTP方法探测
```http
GET     /api/users     → 列出用户
POST    /api/users     → 创建用户
PUT     /api/users/1   → 替换用户
PATCH   /api/users/1   → 部分更新
DELETE  /api/users/1   → 删除用户
HEAD    /api/users/1   → 只返回头部
OPTIONS /api/users     → 返回允许的方法
TRACE   /api/users     → 回显请求（XST）
CONNECT /api/users     → 隧道
LINK/UNLINK           → WebDAV方法

# 方法混淆攻击（BFLA核心）：
POST /api/users/1/delete        # 资源动作直传
POST /api/users/1 HTTP/1.1
X-HTTP-Method-Override: DELETE  # 方法覆盖
_method=DELETE
# 网关允许GET但后端服务端路由到POST等
```

