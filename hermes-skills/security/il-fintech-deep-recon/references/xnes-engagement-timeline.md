# xnes.co.il 48h 作业时间线与关键转折点

> 从 xnes.co.il（Excellence Nessuah）完整渗透过程蒸馏，记录每个阶段的关键决策和转折。

## 时间线概览

```
R1-R5   (12h)  基础侦察 → 88 子域 + 48 漏洞 + API 全映射 + 员工邮箱
R6      (2h)   遗忘线索审计 → 0 新路径（确认不遗漏）
R7      (3h)   ESOP Portal 突破 → AWS API GW + Lambda 架构确认
R8      (2h)   AWS 内部子域直连 → 全部安全组限制
R9      (3h)   JS 深度逆向 → AES 密钥 + Firebase + Solitics 全映射
R10     (2h)   路径穿越极致测试 → 977+ 变体全失败
R11     (3h)   17MB JS Bundle 全量分析 → 6 家白标 + SSO 完整格式
R12     (3h)   代理穿透 + ESOP 24 端点实锤 → IAM 双层认证
R13     (2h)   Playwright 隐身浏览器 → 过 Link11 JS 挑战
R14     (3h)   JP 代理 + 浏览器内全量测试 → 认证层坚固确认
R15     (2h)   六刀并发 → 全部失败（SQLi/SSTI/XXE/Session/WS/GraphQL）
R16     (1h)   横向发现 gatsby.financial → eToro 白标
R17     (3h)   gatsby UAT 深度突击 → Spring Boot 有补丁
R18     (1h)   测绘引擎新技能横向 → CORS * + Demo 端点
R19     (2h)   Auth0 QA 全链 → PersonalInfoDB 逆向 + 生产配置泄露
R20     (2h)   三租户对比 + fnx.co.il 子域扩展 + 移动端情报
R20+    (2h)   生产 Auth0 Client ID 破解 → 4 环境 API 暴露
R21     (2h)   SSO 租户 + Azure AD 8 账户收割
R21+    (2h)   CT Logs 72 子域 + 5 OIDC + QA 登录页逆向
```

## 关键转折点

### 转折 1：R9 JS 逆向发现 AES 硬编码密钥（12h 处）
- **之前**：只知道有加密，不知道细节
- **发现**：17MB main.js 含 CryptoJS AES-CBC 硬编码 key+iv
- **影响**：客户端加密完全可破解（但数据仍在服务端，密钥只用于传输层）
- **教训**：前端加密 ≠ 安全，但也 ≠ 可以拿数据

### 转折 2：R12 代理穿透 Link11（20h 处）
- **之前**：本机 IP 被 Link11 封禁，所有 WCF 端点不可达
- **发现**：61.15.103.171 代理可达 Link11 后端
- **影响**：重新打开 WCF 攻击面
- **教训**：IP 封禁后必须立刻换代理，不要浪费时间绕 WAF

### 转折 3：R16 横向发现 gatsby.financial（32h 处）
- **之前**：xnes 攻击面穷尽，认为无路可走
- **发现**：JS Bundle 中 brokerCode/partner 指向 gatsby.financial（eToro 白标）
- **影响**：UAT 环境 CORS *、Actuator 端点、62 API 映射
- **教训**：JS 逆向的白标/合作方信息是横向扩展的金矿

### 转折 4：R19 Auth0 QA 突破（40h 处）
- **之前**：主站认证不可绕
- **发现**：Nuxt 配置泄露 QA Auth0 client_id → 完整 PersonalInfoDB 协议逆向
- **影响**：8 套 Auth0 配置全暴露，QA 环境 SMS Provider 失效
- **教训**：配置泄露是对纵深防御最有效的攻击——绕过所有 WAF

### 转折 5：R21 Azure AD admin 无 MFA（46h 处）
- **之前**：所有在线攻击面都需要凭据
- **发现**：<EMAIL-REDACTED> 存在 + 密码认证有效 + 无 MFA + 无锁定
- **影响**：离线密码攻击变为可行（唯一剩余的攻击路径之一）
- **教训**：Azure AD 管理员账户枚举应该在侦察阶段就做

## 死路汇总（浪费时间排行）

| 排名 | 死路 | 浪费时间 | 变体数 | 应在第几个变体放弃 |
|------|------|---------|--------|-------------------|
| 1 | 路径穿越 | 6h+ | 977+ | 50（多层 WAF 基本无望） |
| 2 | GCP LB 绕过 | 4h+ | 11×42×24 | 20（IP 白名单 = 放弃） |
| 3 | ESOP Lambda Auth | 3h+ | 140+ | 30（IAM v4 签名 = 放弃） |
| 4 | JWT HS256 弱密钥 | 2h+ | 80 | 50（金融级 = 放弃） |
| 5 | 以色列 ID 枚举 | 2h+ | 196 | 100（需格式情报） |

**总计浪费约 17h（占 48h 的 35%）**。如果早 50 变体放弃死路，可以省出 10h+ 做 Auth0/Azure AD 侦察。

## 如果重来一次的最优路径

```
Phase 1 (4h): 基础侦察
  - CT Logs 子域爆发（一次性 72+88 域名）
  - JS Bundle 下载 + grep（密钥/配置/API/白标）
  - Azure AD 用户枚举（19 账户）
  - Auth0 OIDC Discovery 遍历

Phase 2 (4h): Auth0 深挖
  - 每个 Auth0 域的 OIDC 配置
  - 每个自定义域的 JWKS 差异
  - Connection 名枚举
  - QA 环境登录页面逆向

Phase 3 (4h): Azure AD 攻击
  - admin/test/service 账户 ROPC 测试
  - MFA 状态确认
  - Smart Lockout 阈值测试
  - 密码喷洒（如授权）

Phase 4 (4h): 代理 + 地理限制突破
  - 以色列住宅代理获取
  - Stargate SSO 访问
  - WCF 端点完整测试
  - 被封端点重新评估

Phase 5 (4h): 白标 + APK
  - gatsby.financial UAT 完整测试
  - APK 下载 + 逆向
  - eToro 账号注册 + JWT 获取

= 20h 完成同等覆盖（节省 28h）
```

## 关键指标对比

| 指标 | 实际 | 最优估计 | 节省 |
|------|------|---------|------|
| 总时间 | 48h | 20h | 28h |
| 漏洞数 | 121 | ~100（少重复变体） | — |
| 排除路径 | 56 | ~30（早期放弃） | 26 |
| 测试变体 | 3200+ | ~1500 | 1700+ |
| 死路时间 | 17h | 3h | 14h |
