<!-- archived from /root/.hermes/skills/security/admin-export-template-sqli/SKILL.md on 2026-10-21 -->

---
name: admin-export-template-sqli
description: "导出模板注入(读+任意写)时使用。触发: sysExportTemplate, importExcel。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, sqli, gva, gin-vue-admin, lowcode, export-template, arbitrary-insert, read-write]
    related_skills: [cn-admin-framework-pentest, goframe-api-pentest, lowcode-admin-data-exfil, lowcode-admin-rce-primitives, sqlmap-chinese-guide]
    category: security
---

> 归档卡：原目录 `/root/.hermes/skills/security/admin-export-template-sqli`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/admin-export-template-sqli/…')`，不要相对 `references/legacy/` 解析。

# 后台「导出/导入模板」注入:读 + 任意写

低代码/国产后台框架几乎都有**导出模板**功能(填 `tableName` + 列映射 + 条件,导出 Excel;
或导入 Excel 落库)。**`tableName` 常被直接拼进 SQL 且不过滤** —— 拿到一个后台账号(哪怕权限很低)
就能把它变成**整库读 + 任意表插入**。

同一注入点有**两个方向**,能力完全不同,先认清你要哪个:

| 触发接口 | 生成的 SQL | 能力 |
|---|---|---|
| `export*?templateID=X` | `SELECT <列> FROM <tableName>` | **读**(常被反引号包裹 → 不能 WHERE/UNION) |
| `import*?templateID=X`  | `INSERT INTO <tableName> (`c1`,`c2`) VALUES (?,?)` | **写** |

写路径的三层控制权(这是本类型的核心价值):

```
表名 ← tableName 字段        (完全由我指定)
列名 ← 模板元数据的 KEY      (GORM 反引号包裹)
值   ← 上传 xlsx 的单元格     (作为绑定参数传入)
```

## When to Use

- 后台有"导出模板 / 导入 Excel / 自定义报表 / 数据导出"功能,且 `tableName` 之类字段可控
- 手上有**任意一个**能登录的后台账号(低权限账号也常够 —— 导出模板往往只查"是否登录")
- 需要在**没有 SQL 客户端、没有 shell** 的情况下读业务库(拿账号/哈希/密钥)或往库里插东西
- 响应里有 `获取失败` / `record not found` 这类模糊报错,想判断到底是注入坏了还是载荷问题

## 铁律

1. **先验写入是真落库,再谈利用** —— 用**前后行数对比**验证,不要看响应文本
   (实测响应永远是 `{"code":0,"msg":"导入成功"}`,值错了也这么说)。
2. **高频会限流** —— 连发几十次后开始 `record not found` / 401,**它不是"注入被修了"**。
   间隔 + 重试(实测 sleep 8-20s 自行恢复)。误判成"对方已完成应急响应"会白白收手。
3. **只能插不能删** ⇒ 插进去就清不掉。测试用最小足迹,**并如实向用户交代残留行**。
4. **`;` 堆叠基本被禁**(`multiStatements=false`)⇒ **不能** `UPDATE`、**不能** `INTO OUTFILE`。
   要 shell 别在这条路上耗,**这个注入点给不了写文件**;有原生客户端/既有上传接口时优先打那个。
5. **单列限制** —— 写路径实测只有**单列**能穿过,多列模板不写库(机制未确认)。
   ⇒ 能造"只有一列"的行,**拼不出字段齐全的账号**,别把复刻账号当既定路线。

## 摸清语句形状:用语法错误逼出 ORM 的拼接

二开版一定改过 SQL,**别猜也别去读源码** —— 故意制造语法错误让它自己吐出来:

```
tableName = "app.casbin_rule (id,ptype) VALUES (888888891,0x7a) ZZZZ"
→ Error 1064 near 'ZZZZ (`ptype`) VALUES (?)'
   ↑ 立刻知道它拼的是 INSERT INTO <我的串> (列) VALUES (?)
```

同类信号(每个都能反推出结构):
- `sql: expected 0 arguments, got 1` → **占位符数量不匹配** = 能数出模板会绑几个值
- `json: cannot unmarshal number into Go value of type string` → 元数据的 value **必须是字符串**("888" 不是 888)
- `Field 'X' doesn't have a default value` → X 这一列**没进 INSERT**(就是单列限制的表现)

## 读:错误回显(导出通道对你关着时的兜底)

把表达式塞进**整型列**的位置,让 MySQL 报转换错误,错误消息里带着你的字符串:

```sql
CONCAT(0x515158, (<你的查询>), 0x3c3c3c)     -- 标记 QQX … <<<
```

- **回显上限约 140 字符** → 长结果必须 `SUBSTRING(...,N,110)` 分页
- 取值:从 `QQX<值><<<' for column 'id' at row 1` 里按 `QQX` / `<<<` 取中间段
- **表达式自带 FROM+LIMIT 时不要再加冗余后缀** —— 删掉能省 ~44 字符,而**长度正是最常撞的墙**

## Pitfalls

- **注入串长度上限(约 255)**:超长表达式**静默变成 NULL**(表现为 `record not found`/`获取失败`),
  不报语法错、不给提示。`information_schema.tables` 这类短查询能过、`.columns` 这类长的被截断 →
  **别据此断定"读不了系统表"**。
- **MySQL 1093**:读了正在写的同一张表 → `You can't specify target table`。
  用派生表绕:`SELECT ... FROM (SELECT * FROM t WHERE ...) x`
- **反引号包裹的字段**(常是 `tableName`)不能 `WHERE`/`UNION`,但**逐表直读已足够脱库** ——
  先去 `getSysExportTemplateList` 翻页把应用自带模板全取下来,它的列映射就是现成的"表→列"字典
  (实测 1751 条模板 → 377 张表)。
- **先分诊再动手**:`获取失败` 可能是①关键字过滤 ②长度超限 ③模板名/TID 复用冲突 ④限流。
  用一条极短查询(如 `SELECT 1`)做基线,能快速区分"通道坏了"和"这条载荷不行"。

## 完整实战记录

- `references/gva-export-template-sqli-write.md` —— Gin-Vue-Admin(GVA)整条链实测:
  语句形状证据、行数验证、单列限制的失败点、伪造账号为何登录不了(`sys_user_authority` 三列)、
  casbin 角色权限怎么读、桌面端分角色登录的陷阱。打 GVA/二开低代码后台时先读这份。
