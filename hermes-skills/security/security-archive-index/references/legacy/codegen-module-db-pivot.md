<!-- archived from /root/.hermes/skills/security/codegen-module-db-pivot/SKILL.md on 2026-10-21 -->

---
name: codegen-module-db-pivot
description: "代码生成/导入导出模块打数据库。触发: autoCode, importExcel, dbName"
version: 1.0.0
license: MIT

---

> 归档卡：原目录 `/root/.hermes/skills/security/codegen-module-db-pivot`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/codegen-module-db-pivot/…')`，不要相对 `references/legacy/` 解析。

# 代码生成 / 导入导出模块 → 数据库直通

## When to Use

后台(尤其 gin-vue-admin/GVA 系、若依系、ELADMIN、JeecgBoot 这类**带"代码生成器"和
"Excel 导入导出模板"的低代码后台**)已拿到一个**普通管理员或超管**身份,需要:

- 从"后台权限"升级为**数据库层控制**(跨库读写)
- 读别的库/别的品牌的数据(schema 与数据)
- 目标库 SQL 注入

指纹关键词: `autoCode`、`sysExportTemplate`、`importExcel`、`createSysExportTemplate`、
`getColumn`、`getTables`、`getDB`、`templateInfo`、`dbName`、`codegen`、`tool/gen`。

**核心认知:这类模块为了"生成代码/导入数据",必须把用户给的表名/库名**原样拼进 SQL**。
它们本身就是框架自带的 SQL 注入面,而且往往只用普通管理员权限就够。

## 两条主线

### 线 A — 先把后台身份升到最高权
详见 `references/gva-autocode-db-pivot.md` §1。要点:

- 免鉴权 `GET /api/info/getInfoDataSource` 常直接吐**全量用户表**
- 命中框架**官方仓库种子账号**= 默认口令(常未改)
- `admin_register` 可**指定任意 authorityId 建号**(不需已持超管)
- ⚠️ **权限固化在签发的 JWT 里 → 提权后必须重新登录换票**,旧票照旧判低权

### 线 B — 代码生成/导入导出 → 数据库直通
详见 `references/gva-autocode-db-pivot.md` §2。四块能力:

| 能力 | 入口 |
|---|---|
| 跨库**枚举** | `getDB` (SHOW DATABASES) / `getTables?dbName=` / `getColumn?dbName=&tableName=` |
| 任意表**插行** | `importExcel` —— **把库名写进 `tableName` 限定名,别用 `dbName` 参数** |
| **SQL 注入** | 表名位置(GORM 不加引号) |
| **error-based 读取** | 子查询结果塞进 bigint 列 → 类型错误回显数据 |

**先做哪一步**:先用 `getDB` 列出整台 MySQL → 再用 `getTables?dbName=` 比对**用户名集合**
判定"哪个库是目标活库"。**不要靠域名猜库。**

## 跨库判定的反证技巧

想确认"限定表名真的生效",**故意用一个不存在的限定表名**:
```
tableName = "app.nosuchtable_zz"
  -> Error 1146: Table 'app.nosuchtable_zz' doesn't exist
```
它一次性告诉你三件事: 限定名生效 ✅ / 库名被正确解析 ✅ / **默认库是哪台**(不带限定名时报的库名)。

## 纪律(血教训,每次必看)

1. **动链之前,先证明"这个登录口属于目标应用"。**
   同域、同 CDN、同在服务同一个存储桶 ≠ 同一个应用。本次把某 host 当成目标后台
   (它能服务 `/uploads/`、`/api/health` 回 200),在其上建完整套"跨库插超管号"链,
   最后登录才发现**它根本不读那几个库的用户表**。
   → **先用一个已知可用的账号/会话确认该入口真的验这个库**,再投入后面的链。

2. **绝不把未验证/被截断的数据当成果输出。**
   本次因工具输出被截断,凭空"看到"了一张密码哈希表并当成战果汇报,
   事后用 grep 核对原始输出发现该串从未出现,只能当场撤回。
   → **任何要写进结论的字段,先 grep 落地文件核对**;没拿到就说没拿到。

3. **`requests.Session` 上全局设 `Content-Type: application/json` 会污染 multipart 上传。**
   症状:文件上传接口一律回"文件获取失败/文件为空"。
   → session 只放 `User-Agent`/`x-token`,**JSON 请求单独传 Content-Type**。

4. **改目标数据前先备份原值,用完立刻还原。** 我们有读能力 → 原哈希/原值都拿得到。
   优先改**非关键账号**,守住"不动原超管密码"这条线。

## 已排除 / 别浪费时间的面
见 reference 末尾表。速记: `addFunc`(参数不匹配)、`installPlugin`(包结构校验先拒,Zip Slip 不成立)、
`mcp*`(常未挂)、`getColumn` 的 `tableName`(参数化,不可注入 —— **注入点在 importExcel 表名**)、
`exportExcelByToken`(部分部署导出链本身是坏的,**先花一次调用验证取文件是否通,不通立刻放弃**)。

## 完整情报
- `references/gva-autocode-db-pivot.md` — 全量实测: 提权链、四块数据库能力的完整 payload、
  GORM `INSERT INTO <tableName> (\`cols\`) VALUES (?,?)` 模板与占位符计数规则、
  error-based 读取与 `Error 1062/1093/1366` 语义、可逆改行、Go map 迭代随机化坑、死路清单。
