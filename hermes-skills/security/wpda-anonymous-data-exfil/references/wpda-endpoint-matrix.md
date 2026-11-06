# WPDA REST API 端点权限矩阵

> 基于 WP Data Access Premium 5.5.82 实测

## 匿名可用（authorization: "anonymous" 时）

| 端点 | 方法 | 功能 | 攻击价值 |
|------|------|------|----------|
| `app/meta` | POST | 完整 schema + 应用配置 + WP 角色/用户/表列表 | ★★★★★ 信息收集起点 |
| `app/get` | POST | 按主键读取任意单条记录 → **IDOR** | ★★★★★ 数据提取核心 |
| `app/select` | POST | 列表查询（受 defaultWhere 限制） | ★★☆☆☆ 需要知道合法参数值 |
| `app/lov` | POST | **绕过 defaultWhere** 枚举全表列值 | ★★★★★ 行级安全绕过 |
| `app/copy` | POST | 匿名克隆应用（继承 anonymous） | ★★★★☆ save 链前提 |
| `app/export` | POST | 导出完整 SQL DDL | ★★★★☆ 表结构泄露 |
| `app/detailmeta` | POST | 详情视图元数据 | ★★★☆☆ 补充 schema 信息 |
| `app/details` | POST | 详情数据（通常为空） | ★☆☆☆☆ |
| `app/lookup` | POST | 关联查询（需配置关系） | ★★☆☆☆ 通常返回空 |

## 鉴权绕过但被参数阻断（FormData 路径）

| 端点 | FormData 结果 | JSON 结果 | 阻断原因 |
|------|---------------|-----------|----------|
| `app/save` | 400 Invalid app_cls | 401 Unauthorized | isSelected 需布尔值 |
| `app/insert` | 400 Invalid val | 401 Unauthorized | val 需 JSON 数组 |
| `app/update` | 400 Invalid val | 401 Unauthorized | val 需 JSON 数组 |
| `app/delete` | 400 Missing key | 401 Unauthorized | key 格式未知 |
| `relationship/create` | 400 Invalid app_cls | 混合结果 | app_cls 同上 |
| `app/download` | 400 pk 格式 | 401 Unauthorized | pk 需 JSON 字符串 |
| `app/upload` | 400 格式 | 401 | 同上 |

## 需要 WP 管理员登录

| 端点 | 功能 | 备注 |
|------|------|------|
| `app/saveapp` | 修改应用容器配置（包括 table_name） | 打穿目标 |
| `app/create` / `createapp` | 创建新应用 | |
| `app/settings` | 修改 defaultWhere 等设置 | |
| `app/init` / `app/list` | 初始化 / 应用列表 | |
| `app/call` | PHP 类方法调用 | wpdb 类存在但需鉴权 |
| `table/*` | 直接表操作（select/meta/get） | 目标表的唯一路径 |
| `tree/*` | 数据库浏览器（dbs/tbl） | |
| `qb/*` | 查询构建器（open 需 access token） | |
| `ai/*` | AI SQL 执行 | |
| `action/import` | SQL 导入 | WAF 也会拦截 |
| `save-settings` | 全局 WPDA 设置 | |

## AJAX 端点（admin-ajax.php）

| Action | 需要 | 备注 |
|--------|------|------|
| `wpda_datatables` | pub_id + nonce | 前端表格渲染回调 |
| `wpda_autocomplete` | 未知参数名 | "Wrong arguments" |
| `wpdapro_inline_editor` | nonce + 编辑权限 | "INV-Not authorized" |
| `atticus_print_claimant_forms` | 登录 session | "Not authenticated" |

## 参数格式速查

| 参数 | 类型 | 格式 |
|------|------|------|
| `app_id` | int | `3` |
| `cnt_id` | int | `2` |
| `key` | 对象 | `key[列名]=值` |
| `col` | string | 列名（反引号会被剥离） |
| `search` | string | 搜索词（可能不参与 SQL） |
| `app_cls` | array[object] | `[{"columnName":"xxx","isSelected":true}]` |
| `val` | array[object] | `[{"列名":"值"}]` |
| `app_tbl` | string | 表名 |
| `app_relation` | string | `"lookup"` 或 `"1:n"` |
