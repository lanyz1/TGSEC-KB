## 一、攻击面驱动的审计方法论

### 1.1 为什么必须从攻击面出发

传统 SAST 是 **sink-first**（从危险函数反推路径），能发现"可能危险"但无法回答"攻击者能否真的触达"。2026 年主流 AI 审计框架（如 Capital One VulnHunter）已反转思路：**从真实攻击入口点正向追踪**，沿攻击者实际路径经过认证、授权、校验等安全关卡，只有整条路径可行才上报。审计者必须以"攻击者视角"绘制入口点到敏感操作的地图。

### 1.2 入口点枚举（Entry Point 清单）

```
# HTTP 类
- 路由注册表（Spring @RequestMapping / Flask @app.route / Express app.get / Gin 路由组）
- 中间件/过滤器/拦截器（全局鉴权是否被跳过）
- 文件上传、下载接口
- 回调接口（Webhook、OAuth redirect_uri、支付回调——最容易绕过鉴权）
- GraphQL / gRPC / WebSocket 端点

# 非 HTTP 类
- 消息队列消费者（Kafka/RabbitMQ/SQS 监听器）
- 定时任务/批处理入口
- 反序列化入口（RMI/AMF/XML/JSON/YAML）
- 外部 API 集成点（第三方 SDK 回调）
- CLI / 运维命令入口

# 隐藏入口
- 未版本控制的接口（/admin、/debug、/actuator）
- 测试接口（测试代码误上生产）
- 调试开关（--debug、Env 变量切换的隐藏路由）
```

### 1.3 三步法：入口点 → 数据流 → 敏感操作

```
第一步 枚举入口点：全局搜索路由注册、消息监听、回调注册
第二步 追踪数据流：从入口参数出发，追踪其流向（请求体→DTO→Service→DAO）
第三步 定位敏感操作：标记沿路径上的危险 Sink（SQL/命令/文件/反序列化/SSRF/越权点）
产出物：入口点×Sink 的可达矩阵，作为审计优先级依据
```

**实战命令（快速定位入口点）：**
```bash
# Java Spring：路由注解
grep -rn "RequestMapping\|GetMapping\|PostMapping\|RestController" --include="*.java" src/ | head -50

# Python Flask/Django
grep -rn "@app.route\|urlpatterns\|path(" --include="*.py" . | head -50

# Node.js Express
grep -rn "app\.\(get\|post\|put\|delete\|use\)\|router\.\(get\|post\)" --include="*.js" . | head -50

# Go
grep -rn "r\.Handle\|mux\.Handle\|gin\.Default" --include="*.go" . | head -50

# PHP
grep -rn "route\|match\|dispatch" --include="*.php" app/ public/ | head -50
```

### 1.4 审计优先级矩阵

| 优先级 | 条件 | 动作 |
|-------|------|------|
| P0 | 未鉴权入口 + 直接到达命令/SQL/反序列化 Sink | 立即深挖，构造 PoC |
| P1 | 鉴权后入口 + 敏感操作 + 用户可控数据 | 深度数据流追踪 |
| P2 | 鉴权后入口 + 敏感操作 + 数据受限 | 抽查 + 逻辑审计 |
| P3 | 内部工具代码、无外部输入 | 依赖与配置审计为主 |

**排序因子：** 资产价值（数据敏感度）× 暴露程度（是否公网可达）× 可利用性（前置条件数量）× 影响（RCE>文件读写>信息泄露）。

### 1.4b 十维攻击面（审计入口清单）

逐维扫输入与数据流，未验证可达只标嫌疑：

1. 用户输入（参数 / header / cookie / 上传）
2. 文件读写（路径拼接、include、上传回显）
3. 数据库（SQL/NoSQL 拼接、ORM 危险用法）
4. 命令执行（exec/system、模板、反序列化）
5. 认证授权（校验位置、默认证、可绕过）
6. 会话与令牌（JWT、随机数、cookie 属性）
7. 序列化点（unserialize / pickle / yaml）
8. 外部交互（SSRF、回调、URL 拼装）
9. 竞态与并发（共享状态、TOCTOU）
10. 配置与部署（调试开关、密钥硬编码、暴露接口）

### 1.4c 假设驱动挖掘循环

1. 静态 grep / 污点追踪生成候选  
2. 对每个候选提出可证伪假设（「该 sink 是否受不受信任输入控制？」）  
3. 最小 PoC 验可控性、可达性、影响  
4. 记录通过/失败，淘汰不可证者  
5. 交叉验证（多 payload、正负对照）后才进 `confirmed/`

### 1.5 五阶段标准流程

```
阶段1 侦察（Recon）：摸清技术栈、框架版本、依赖清单、认证模型
阶段2 映射（Map）：绘制攻击面与入口点清单
阶段3 深挖（Deep Dive）：对 P0/P1 目标做数据流追踪与模式匹配
阶段4 验证（Verify）：构造 PoC 验证可利用性（仅限授权环境）
阶段5 报告（Report）：证据链闭环（见第十三章）
```

