## 4. 枚举资源 id:参数名陷阱 + 下架资源

- 页面跳转 URL `?id=` **原样传接口**(常是 `id`,不是 course_id/user_id;如 course_detail?course_id=20 报 9999、?id=20 成功)。先还原前端页面 `onLoad` 取参逻辑。
- 顺序枚举 id(1..N)可挖**下架/隐藏资源**(列表接口 status 过滤,直查 id 仍返回数据)。

