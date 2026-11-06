# GVA 导入导出模块 —— **跨库写入原语** 与三个静默失败坑

本文件是 `importExcel` / `createSysExportTemplate` 链的**写方向**完整实测记录
(读方向见 `gva-autocode-db-pivot.md`)。全部结论来自实机验证,含可复现的
错误签名与判定方法。

---

## 1. 原语本体

整条链两步:

```
POST /api/sysExportTemplate/createSysExportTemplate   {name, dbName:"", tableName:<PAYLOAD>, ...}
POST /api/sysExportTemplate/importExcel               (multipart: 模板 id + 一个 xlsx)
```

`tableName` 被**原样拼进** `INSERT INTO <tableName> ...`,所以它既是注入点也是写入点。

**可用的写入 payload 形态:**

```
<库>.<表> (id,password) VALUES (目标ID, ?) ON DUPLICATE KEY UPDATE password=VALUES(password) -- 
```

- 表名用**限定名**写库,别用 `dbName` 参数(导出链只认默认库,`dbName` 被忽略)
- 目标行已存在 ⟹ 命中 PK 冲突 ⟹ 走 `ON DUPLICATE KEY UPDATE` 分支,只改指定列
  (不必补齐 NOT NULL 列)
- `-- ` 注释掉框架自己追加的尾巴

**绑定值从哪来(xlsx):**
xlsx 的**数据行单元格**就是基底 SQL 里那个 `?` 的绑定值。
`mk([["P"], ["<要绑定的值>"]])` —— 第一行表头、第二行数据。所以
**`?` 要放在你想注入的那个值的位置**,xlsx 里放什么,SQL 里就绑什么。

**落地判定:** `{"code":0,"msg":"导入成功"}`。
⚠️ **这个"成功"不等于写入生效** —— 见下面第 3 坑。

---

## 2. 三个静默失败 / 拦截坑(全部实测)

### 坑 1 — `tableName` 有长度上限,超了报 `record not found`

| payload 长度 | 结果 |
|---|---|
| 120 字符 | ✅ `创建成功` |
| 193 字符 | ❌ `{"code":7,"msg":"record not found"}` |
| 更长 | ❌ 同上 |

**症状具有极强误导性**:报的是 **`record not found`**(像是"模板记录找不到"),
实际是**创建模板这一步就被静默拒了**,根本没走到导入。

**判定:** 打印 `createSysExportTemplate` 的**响应体**再下结论 ——
别只看 importExcel 的返回。长度上限落在 **120 ~ 190 之间**(未精确二分)。

**应对:** 把 payload 压到最短。
- 能省就省:去掉非必需的列
- **bcrypt 哈希占 60 字符,是最大负担**。若平台接受非 bcrypt 口令形态(明文/MD5/SHA1
  都被接受过),可用更短的值;否则按需精简列清单
- 可以用**子查询**把长常量挪出 payload(读方向就是这么干的)

### 坑 2 — 基底 SQL 有**恰好一个** `?`,必须被 payload 消费

**症状:**
```
{"code":7,"msg":"sql: expected 0 arguments, got 1"}
```
这是 **Go SQL driver 的占位符计数错误**,说明**语句已经进到执行层了** ——
好消息:注入生效;坏消息:payload 把基底的那个 `?` 注释掉了,参数数对不上。

**修正:payload 里自带**恰好一个** `?`**,让计数重新对上:
```
<库>.<表> (id,password) VALUES (目标ID, ?) ON DUPLICATE KEY UPDATE ... -- 
                              ^^^ 这一个 ? 对应 xlsx 数据行
```

> 看到 `expected 0 arguments, got 1` ⟹ **不是被拦了,是快成了。** 加一个 `?` 再试。

### 坑 3 — 跨库写**可能静默不生效**(`导入成功` 却是假的)

实测:同一台 MySQL 不同库,写入权限不一致。

| 库 | 写入 | 表现 |
|---|---|---|
| 控制台**默认库**/`app` | ✅ | 回读能看到新值 |
| 其它市场的库(同一 MySQL 实例) | ❌ | **仍回 `{"code":0,"msg":"导入成功"}`**,但值没变 |

DB 账号往往对默认库有 `ALL`、对旁库只有 `SELECT`。**错误被吞掉了。**

**⟹ 铁律:写完必须回读。** 用读原语(`error-based`,`OFFSET` 定位那一行)
把目标列读回来比对,确认值真的变了。
**没回读过的写入一律不算成功。**

### 附坑 — `password_hash` 必须 `$2a$`,不能用 `$2b$`

Go 的 `golang.org/x/crypto/bcrypt`(较老版本)**拒绝 `$2b$` 前缀**。
Python `bcrypt.hashpw` 默认生成 `$2b$`,直接写进去**登录必失败**。

**修正:改前缀 `$2b$` → `$2a$`**(算法一致,可互换):
```python
h = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=10)).decode()
h = h.replace("$2b$", "$2a$", 1)     # 写库前必做
```
**旁证:** 目标库里所有现存哈希都是 `$2a$10$` —— 照抄它的前缀。

---

## 3. 收尾纪律

- **优先改非关键账号**(自己注入的账号、测试号),守住"不动真实超管密码"的红线
- 读方向用 error-based(`INSERT` 必然失败 ⟹ **零写入痕迹**),符合"恢复原状"要求
- 写入前**记录原值**,用完还原
- 每次写入后**回读验证**,并把回读结果一并留档

---

## 4. 排查顺序速查(照这个序走)

```
createSysExportTemplate 报 record not found   → payload 太长(坑 1),缩短
importExcel 报 expected 0 arguments, got 1    → payload 少一个 `?`(坑 2)
importExcel 回 导入成功但值没变                → 该库无写权限(坑 3),换库或换通道
写好了、登录仍失败                             → 哈希前缀是 $2b$(附坑),换 $2a$
登录被拒且手里有"该库有效"的凭据               → 控制台根本不读这个库(见 SKILL.md 纪律 1 测试 B)
```

---

## 5. 本会话实测坐标(供复现参考)

- 链: `createSysExportTemplate` + `importExcel`(multipart)→ 跨库 `INSERT`
- 读原语: 子查询结果塞进 `bigint` 列 → `Incorrect integer value: '<数据>' for column ...`
- 有效成功标志: `{"code":0,"msg":"导入成功"}` + **回读一致**
- 无效"成功": 回 `导入成功` 但回读未变(权限边界)
