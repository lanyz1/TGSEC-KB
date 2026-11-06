## 一、CSRF完整攻击面与威胁建模

### 1.1 敏感操作识别清单
| 操作类型 | 风险场景 | 攻击价值 |
|---------|---------|---------|
| 账户安全 | 修改密码/邮箱/手机号、绑定/解绑第三方账户、启用/禁用2FA、修改安全问题 | 高（直接接管前置） |
| 资金操作 | 转账、支付、充值、提现、购买、退款、改收款账户 | 极高（直接经济损失） |
| 权限变更 | 添加管理员、修改角色、授权API Key、邀请成员、改组织设置 | 极高（横向/垂直提权） |
| 数据操作 | 删除数据、修改内容、上传文件、发布内容、导出数据 | 高（完整性破坏+DoS） |
| 会话管理 | 注销（Logout CSRF）、登录（Login CSRF）、重置密码、会话固定 | 中-高（配合钓鱼/接管） |
| 配置变更 | Webhook、回调URL、重定向白名单、邮件转发规则、DNS/SPF记录 | 高（持久化+供应链） |
| 通知/社交 | 发送消息、评论、关注、邀请、点赞、关注攻击者账号 | 低-中（批量水军/钓鱼传播） |
| API操作 | GraphQL mutation、RESTful PUT/PATCH/DELETE、批量任务触发 | 中-高（取决于业务） |

### 1.2 请求类型与攻击难度矩阵
| 请求类型 | 攻击难度 | 典型Payload载体 | 现代浏览器注意点 |
|---------|---------|----------------|-----------------|
| GET | 低 | `<img>`/`<iframe>`/`<link>`/`meta refresh`/CSS背景 | Lax下顶级导航仍携带Cookie |
| POST urlencoded | 低 | 自动提交form | Lax下不携带Cookie（除非2分钟窗口） |
| POST multipart | 低 | form+`enctype=multipart/form-data` | 同上 |
| POST JSON | 中 | `enctype=text/plain`拼JSON、Flash、CORS | `application/json`触发预检，需特殊构造 |
| AJAX/Fetch（自定义Header） | 中-高 | CORS放行、Flash、SW劫持、DNS Rebinding | 预检拦截是主要障碍 |
| PUT/DELETE/PATCH | 中-高 | `_method`/`X-HTTP-Method-Override`、CORS | 方法覆盖是主要路径 |
| SOAP/XML | 中 | form+`text/plain`拼XML | 同JSON |
| WebSocket | 中-高 | `new WebSocket()`握手 | 握手GET无预检，SameSite决定Cookie |
| GraphQL | 中 | 见1.2请求类型 + mutation body | 通常JSON，同JSON CSRF |

### 1.3 CSRF攻击类型全景
- **常规CSRF**：以受害者身份执行任意操作
- **Login CSRF（登录CSRF）**：攻击者预置自己账户（已知密码），诱导受害者登录该账户，受害者在攻击者账户内输入的敏感信息（信用卡、身份证、收货地址）被攻击者掌握；或配合"登录后自动绑定"逻辑直接接管
- **Logout CSRF（注销CSRF）**：强制登出造成DoS，或配合钓鱼"重新登录"获取凭据；注意注销接口在Lax下GET导航可直接触发
- **OAuth授权码CSRF / 账户绑定CSRF**：state缺失/静态 → 受害者账户绑定攻击者第三方身份 → 攻击者反向登录受害者账户（账户劫持级，见第十章）
- **Flash/Silverlight CSRF**：跨域任意请求（含自定义Header与任意Content-Type），依赖`crossdomain.xml`错误配置
- **JSON CSRF**：绕过`application/json`的防护幻觉
- **CSRF+XSS**：XSS可读取Token、直接同源请求，使一切CSRF防护失效
- **CSRF+Open Redirect**：重定向使Referer显示同源
- **CSRF+CORS**：CORS错误配置→跨域读取Token→任意操作
- **CSRF+子域接管**：兄弟子域（sibling subdomain）接管→same-site上下文→绕过Strict/Lax
- **CSWSH（跨站WebSocket劫持）**：通过WebSocket信道执行状态改变
- **CSPT2CSRF（客户端路径穿越→CSRF）**：所有CSRF防护完备时仍可利用（见12.4节）
- **DoS via CSRF**：删除数据/改密/注销导致业务中断

