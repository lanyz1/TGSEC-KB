# 实战档案：ThinkPHP6 + sqlsrv（712win3 / brmt777 / 777club）

## 目标事实（已验证，可直接当地图）
| 项 | 值 |
|---|---|
| DB | **MSSQL**，PDO `sqlsrv:`，`Database=OM_MasterDB`，`Server=18.231.63.236,1433`（凭据 [REDACTED]） |
| 框架 | ThinkPHP 6，**debug 开启**（异常页回显 SQL/`$_SERVER`/中间件源码/RunTime） |
| 注入面 | `POST https://gameapi.brmt777.com/channelapi/verify`，参数取 **`Origin:` 请求头** → 当 `channel_url` |
| 生成 SQL | `... WHERE [a].[channel_url] = 'https://channel.brmt777.com:443'`（方括号标识符+单引号拼接） |
| 被查表 | `T_PackageUrl`；每包 DB 连接存 `T_PackageConfig` |
| 拦点 | `app/channelapi/middleware/BasicMiddleware.php:32` 引号校验 → 返回 `请求来源错误` |
| 过中间件后 | 先按 channel 找 `T_PackageConfig` 再连库 → `SQLSTATE[HYT00] Login timeout expired`（SQL 执行前就死） |
| 其它面 | `getPackages` **免认证可达**，响应含 `ROW_NUMBER()` → 后端拼 MSSQL 窗口函数 |

## 关键技术：用「标记法」证明参数进了 SQL（比时序/长度可靠得多）
1. 给每个候选参数发**唯一良性标记**：`Origin: https://ORDERMARK123.x`、`packageId=987654321`、`order=MARKCOL`。
2. 拉 debug 页（TP6 异常/调试输出），**在回显的 SQL 里搜标记**：
   - 标记原文出现在 SQL 且未被参数绑定 → 注入面成立 → 上 `'`/`;`/`WAITFOR` payload；
   - 标记不出现（被白名单/丢弃）→ 该参数不进 SQL，**立即排除，别浪费时间**。
3. 同时看 `RunTime`：既当"SQL 是否真执行"的判据，又当**生产健康度监测口**。

## 引号校验（BasicMiddleware）绕过思路
- **先读它**：debug 页连中间件源码片段一起回显 → 确认它到底查 `strpos/正则` 还是 URL 合法性，再针对性构造（读源码 5 分钟，胜过盲试 500 次）。
- **优先找免引号面**：数值参数（`packageId`/`roleId`/`TOP n`）若能直接进 SQL，`1;WAITFOR DELAY '0:0:5'--`、`1 AND 1=(SELECT @@version)` 无需 `'` → 天然绕过。
- 备选：宽字节/非 UTF-8 截断（`%bf%27`、`%c0%27`，前提是字节级过滤与解码不一致）、`CHAR(39)`/hex 形式、排序列名面（`order=`/`field=` 走函数报错注入，不需要引号）。
- **请求头运载**：payload 放 `Origin`/`Referer`/`X-Forwarded-*`（WAF/中间件常只查 body/query）。

## 已判死路径（别重跑）
- `/adminapi/verify` 13 payload → 响应全同（参数化）。
- 4 个免认证白名单路由（`getPackages`/`getProjectNote`/`verify`/`groupLogin`）× 26 参数 × 16 payload ≈ **1,700 次 → 响应恒 468B**（参数未进 SQL）。
- `channel_url` 引号 payload → 被 `BasicMiddleware.php:32` 挡回 `请求来源错误`。
- 时间盲注 → **假阳性**（端点本身 4–7s 慢）。
- channel_url 全量 23,566 条 → 0 命中；UG admin 88,742 条 → 0 命中。
- MSSQL 用户名枚举 → 无 oracle（存在/不存在同回 `18456`）。

## DB 直连面结论
- 1433 后是**真 SQL Server + 前置连接代理/审计网关**（pymssql 得真 `18456`；手搓 PRELOGIN 收到代理错误文本+GUID）。
- 唯一成功信号 = 登录成功；爆破 8,400/102,133 组合无命中后因**生产被拖慢**主动停止。
- 库故障期现象：应用任意请求抛 `PDOException(SQLSTATE[HYT00] Login timeout)`；**此时任何"报错注入命中"都是假阳性**——先确认基线健康。

## 教训
- **TDS 40 线程爆破 → 应用 `0.001s→1.9s→HYT00`，我方 TDS 退化为 `EOF`（TCP 仍 0.02s）**：前置代理是共享瓶颈。并发 ≤2 + 同步监测应用耗时 + 停后 240s 静默观察。
- 判定器会退化：库挂后 debug 页只剩 `PDOException`，不再回显 CONNECT/RunTime → 需另找信号（如基线健康度先决）。
