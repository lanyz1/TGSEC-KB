## 一、IDOR完整攻击面

### 1.1 对象引用类型（高级扩展）
| 引用类型 | 示例 | 测试方法 |
|---------|------|---------|
| 自增ID | `?user_id=123`、`/order/456` | 遍历ID递增/递减 |
| UUIDv4 | `?id=a1b2c3d4-...` | 需泄露源/密码学随机性验证（见第六章）|
| **UUIDv1** | `?id=xxxxxxxx-xxxx-1xxx-...` | **时间戳+MAC可预测，反推创建时间**（见6.2）|
| 顺序UUID/雪花ID | `?id=...` | 位结构分解，发现单调递增规律（见6.3）|
| 文件名 | `?file=report.pdf` | 路径遍历+枚举文件名 |
| 邮箱/手机号 | `?email=<EMAIL-REDACTED>` | 遍历/爆破邮箱 |
| 用户名 | `/profile/admin` | 用户名枚举 |
| 订单号/流水号 | `?order=202401010001` | 订单号规则猜测（日期+序号）|
| Hash ID | `?id=abc123xyz` | Hashids解码、salt爆破（见6.5）|
| Base64编码ID | `?id=MTIz` | 解码后修改再编码 |
| JWT Token中的ID | Token内含user_id | 修改JWT payload（见5.5）|
| 路径参数 | `/users/123/orders/456` | 修改路径段 |
| POST Body JSON | `{"user_id":123}` | 修改JSON字段 |
| HTTP Header | `X-User-Id: 123`、X-Tenant-ID | 修改Header（多租户）|
| Cookie字段 | Cookie中含user_id | 修改Cookie |
| 隐藏表单字段 | `<input type=hidden name=id>` | 修改隐藏字段 |
| **间接引用（Indirect Reference）** | 映射表ID/短码/分享码 | 爆破映射表ID、可预测短码（见3.9）|
| **对象关系引用** | order→user→profile | 通过关系链间接访问（见3.10）|
| **租户/工作区ID** | X-Workspace-ID、/orgs/{id} | 跨租户切换（见第七章）|
| **LLM/AI对象ID** | flow_id/thread_id/kb_id | AI平台对象越权（见第八章）|

### 1.2 IDOR类型（高级扩展）
- **水平越权（BOLA）**：同角色访问其他用户数据
- **垂直越权（BFLA）**：低权限访问高权限功能
- **对象属性越权（BOPLA）**：修改不应修改的字段（role=admin）
- **静态文件越权**：直接访问他人的上传/导出文件
- **ID枚举**：可遍历ID获取所有数据
- **参数污染越权（HPP）**：多参数/大小写变体取错值
- **批量分配**：额外字段is_admin=1创建管理员（+原型污染变体）
- **GraphQL IDOR**：未做对象级授权
- **多租户IDOR**：租户A的Token访问租户B数据（隔离失效）
- **关系链IDOR**：通过对象关联关系间接越权
- **间接引用绕过**：共享映射表/可预测引用码
- **LLM/AI平台IDOR**：flow/thread/credentials跨租户访问

