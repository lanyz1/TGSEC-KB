## 2026-10 情报批增量（数组包裹 → ORM 批量越权，Node 系）

- **载荷**：JSON `{"user_id": [124, 123]}`（你是 123，受害者 124）；或重复参数 `user_id=124&user_id=123` → Express 聚成数组 `["124","123"]`。
- **机理**：Sequelize/Mongoose 不取首元素，数组 → `WHERE id IN (124,123)` → **两行都写**；findOne 读回自己行，findAll/find 返回两行。
- **要点**：单独 `[124]` 会被中间件拒（校验里没有你自己的 ID）→ **必须含自己**才过检查，ORM 会写全列表；`includes(123)` 对字符串数组失败而 `some(x => x == 123)` 通过、仍触发 `IN ('124','123')`。
- **测试矩阵**（实测定稿）：sequelize 6.37 / mongoose 9.9 / typeorm 1.1 / knex 3.3 / prisma 7.10 / express 5.2。Mongo `{"$in":[124]}` 可只打受害者但常被中间件挡，仅在字段未被检查处可达。
- 源：@Zerodaylabowner 2026-09-14 实测系列。
