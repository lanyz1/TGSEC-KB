# NightPlay GVA — 审计日志 sys_operation_records 明文口令收割

> 从 `sys_operation_records` 的 `body` 字段直接获取管理端明文口令

## 漏洞模式

GVA 的操作审计表 `sys_operation_records` **完整记录请求体 (`body` 字段)**。
当管理员创建代理/员工时，明文密码直接进入审计表：

```json
// POST /bizOrg/createAgent
{"loginUsername":"demo9999","loginPassword":"qwe123123"}

// POST /bizOrg/createEmployee
{"loginUsername":"ceshi","loginPassword":"123456"}
```

## 攻击链

```
1. 超管权限 (authorityId=888)
   ↓
2. 读 sys_operation_records 表 (5,184 条)
   → 方式A: sysExportTemplate 导出
   → 方式B: 业务接口分页拉
   ↓
3. 搜索 body 字段包含 "Password" 的记录
   ↓
4. 提取所有创建操作的明文口令
   → createAgent / createEmployee / register / resetPassword
   ↓
5. 横向登录其他账号（代理/员工体系）
```

## 数据规模

| 字段 | NightPlay 实例 |
|------|---------------|
| 审计记录总数 | 5,184 条 |
| 含明文口令 | createAgent + createEmployee 记录 |
| 操作来源 IP 分布 | 6+ 个不同 IP（运营方/攻击者/本机） |
| User-Agent | curl/8.7.1 (脚本化运维)、浏览器 |

## 审计日志的额外价值

除明文口令外，`sys_operation_records` 还可收割：

- **adminBuyBack** 操作 → 资金盘回购比例和金额
- **adjustBizUserBalance** → 人工调账记录（单次 1.11 亿）
- **IP 溯源** → 72.245.135.169 (2,844 次，非本人，疑运营方)
- **操作时间线** → 应急响应节奏

## 通用化

任何 GVA 二开站只要有超管权限，`sys_operation_records` 都是**低垂果实**：
- GVA 默认开启操作审计
- 默认记录完整 body (包括 POST 的 JSON)
- 默认无脱敏
- 有超管读权限即可导出

**检测方法**：拿到 GVA 超管后，`GET /sysSysOperationRecord/getSysSysOperationRecordList` 或导出 `sys_operation_records`，搜索 `Password` / `password` 关键字。
