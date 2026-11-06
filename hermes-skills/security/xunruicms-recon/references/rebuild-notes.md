# 长安COD重建版 — 自建复刻技术笔记(zengda.shop 案例延续)

> 逆向完成后按"一模一样"标准手写重建版(PHP 8.3 + SQLite 零外部依赖),
> 位置 `D:\渗透\zengda_recon\rebuilt\`。以下是与线上不同的**自建实现细节**,
> 逆向时不可见,踩坑得来。

## 1. 路由分发器命名规则(关键坑)

`lib/util.php` 路由分发:`$fn = $ctrl . '_' . $method;`

- 请求 `?s=admin&c=index&m=dashboard` → 找函数 **`index_dashboard`**(不是 dashboard_index!)
- 新增控制器方法必须按 `{c}_{m}` 命名,否则返回 `{"code":0,"msg":"方法不存在"}`
- 模块内现有函数即索引:index_index / index_login / order_index / order_show / order_status / weblog_index / logout_index

## 2. 后台登录跳转要改两处

- `index_index()` 已登录时 302 目标(访问后台根时跳哪)
- `index_login()` 登录成功后 302 目标
- 两处都写死 URL,新增页面(如 dashboard)时容易只改一处 → 用户登录后仍跳旧页

## 3. CSRF 复刻(与线上 CI3 行为一致)

- `lib/csrf.php`:cookie `csrf_cookie_name`(32hex, HttpOnly, 2h)+ 表单字段 `csrf_test_name`
- 无 cookie 时生成并 setcookie;POST 校验 `hash_equals(cookie, post)` 后**刷新 token**(响应 `res.token` 供前端更新)
- 端到端脚本必须:同 cookie jar `-b` + `-c` 读写,从**同一次响应** HTML 提取字段值

## 4. 订单号与防刷

- 订单号 `H` + yymmddHHMMSS + 4位随机;`submit_limit` 秒内限速返回 "Submit too fast"

## 5. SQLite 统计 SQL(仪表盘用)

```sql
-- 今日按小时分布(时间戳为 Unix 秒)
SELECT CAST(strftime('%H', inputtime, 'unixepoch', 'localtime') AS INTEGER) h, COUNT(*) c
FROM dr_order WHERE inputtime>=<today0> GROUP BY h;
-- 近12月
SELECT strftime('%Y-%m', inputtime, 'unixepoch', 'localtime') m, COUNT(*) c
FROM dr_order GROUP BY m ORDER BY m DESC LIMIT 12;
-- PHP 侧: strtotime('today') / 'yesterday' / 'first day of this month'
```

## 6. 城市名映射

订单 `city` 存 region_id;显示名称查 `dr_linkage(region_id, region_name)`:
```sql
SELECT region_id, region_name FROM dr_linkage WHERE region_id IN (SELECT DISTINCT city FROM dr_order WHERE city!='')
```
用 try/catch 包住(旧库可能无 linkage 表)。

## 7. 端到端验证脚本要点(e2e_test.sh 模式)

- **原生 Windows curl 不认 `/dev/null`**(exit 23)→ 用 `-o NUL`
- 下单响应 JSON 里 URL 带 `\/` 转义 → 用 `python -c "import json; json.loads(...)['data']['url']"` 解析,勿用正则
- 后台确认:GET 登录页拿 session → POST login → 带 cookie 访问列表并 grep 订单号

## 8. 后台 UI(2026-08 重设计)

- 公共布局 `templates/admin_layout.php`:`admin_head($title, $active)` + `admin_foot()` 输出侧边栏/顶栏/全部 CSS/JS(页面内 include 复用)
- 设计语言:Ozon(主蓝 #005bff、白卡 14px 圆角、浅蓝选中态、线性 Material 图标 path)
- 图表全 SVG 手绘零依赖:折线(渐变面积 + 圆点 + `<title>` tooltip)、环形(stroke-dasharray + rotate(-90))、柱状
- 占位菜单:`data-placeholder="1"` + JS toast「模块为占位入口,功能开发中」
- 详见技能 `web-admin-ui-redesign`
