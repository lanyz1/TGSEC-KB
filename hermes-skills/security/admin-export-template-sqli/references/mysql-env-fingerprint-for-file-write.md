# 注入到手后:先探 MySQL 环境指纹,再决定"能不能写文件"

拿到 SQL 注入 + root 之后,**不要直接开始试 `INTO OUTFILE`** ——
先用**三条极短查询**判断这条路线在这个目标上到底存不存在。
实测:这三条查询省掉的是**整晚**在 `INTO OUTFILE` / `LOAD_FILE` 上的反复试错。

## 一、三条指纹(每条都是单值,短到不会被载荷长度墙截断)

```sql
SELECT @@version          -- 5.7.43-log
SELECT @@secure_file_priv -- NULL / (空串) / 某个目录
SELECT @@datadir          -- /www/server/data/
SELECT @@hostname         -- ip-172-31-36-4.ap-south-1.compute.internal
SELECT CURRENT_USER()     -- root@localhost   ← 权限够不够
```

## 二、`secure_file_priv` 的三种取值 = 三种命运

这是**决定性的那一条**,而且最容易看错:

| 取值 | 含义 | 能不能走"MySQL 写文件" |
|---|---|---|
| `NULL` | **完全禁用**文件导入导出 | ✗ **不能** —— `INTO OUTFILE` / `LOAD_FILE` 全废 |
| `''`(空串) | **无限制**,任意路径 | ✓ 能,这是最理想的情况 |
| `/some/dir` | 只允许该目录 | △ 半能,落点被限制在一个目录里 |

⚠️ **`NULL` 和空串是天壤之别,别扫一眼"没限制"就冲**。
实测目标回 `NULL` ⇒ 无论怎么构造 `INTO OUTFILE` 都不会成功;
同样地 `LOAD_FILE` 也恒回 NULL —— **这解释了"读配置文件读不到"的现象**,
不要把它误判成"路径写错了"或"文件不存在"。

## 三、`@@datadir` 顺手暴露服务器形态(高价值副产品)

```
@@datadir = /www/server/data/   ⇒ 宝塔(BT Panel)布局
                                  ⇒ 网站根目录大概率在 /www/wwwroot/<域名>/
@@basedir = /www/server/mysql/
```

- 宝塔系 ⇒ **同机常有 nginx + PHP**,所以"写进 webroot 的 .php 会被执行"这个前提**可能是成立的** ——
  比 Go 单体应用(写 .php 也不会执行)乐观得多。
- 但**前提是你有办法把文件写到那台机器上**。注意区分两台不同的主机:
  **数据库主机 ≠ 应用主机**。注入跑在 DB 上,`INTO OUTFILE` 只会写在 **DB 主机的**盘上;
  能不能打到 web 根,取决于 web 与 DB 是否同机。
- `@@hostname` 形如 `ip-<私有IP>.<region>.compute.internal` ⇒ 云上 VPC 内主机
  (AWS 系),**私有 IP 从外部不可达** ⇒ 别指望直连它的 3306。

## 四、这条路走不通时的正确输出

`secure_file_priv=NULL` ⇒ **明确把"MySQL 写文件"从路线清单里划掉**,转向:

- **应用自己的文件写接口**(上传 / 导入 / 导出模板 / 配置写)—— 真正该投时间的地方,
  见 `lowcode-admin-rce-primitives`
- 读能力仍然完整:**注入的读通道不受 `secure_file_priv` 影响**,
  脱库/读配置值(存在库里的那些)照旧可用

**纪律**:不要因为"经典 MySQL→webshell 路"被堵就宣布整条链没戏 ——
它只是**一个**落点面,而且是被服务端配置关掉的那种。
