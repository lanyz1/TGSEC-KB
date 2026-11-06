# Vue webpack SPA 侦察补充(D5智慧通行实战,2026-08)

本文件补充 SKILL.md 主流程之外的 Vue2 webpack 老式 SPA 打法(与 Next.js 章节并列)。

## 多端口多 SPA(重点)

同一主机**不同端口可能挂不同前端**,API 共用同一 Kestrel 后端:

| 端口 | 常见角色 |
|---|---|
| 80 | 管理后台 SPA(webpack chunk 独立一套) |
| 443 | 移动端 H5(微信 jweixin) |
| 8080 | nginx 默认页(可能空转) |
| 6160 等 | 第三方接口服务(独立 Kestrel 实例,常无 token 但另有鉴权) |

**每个端口都要抓 index.html 拉各自的 chunk 集**,别只查一个端口。

```bash
# 每个端口:
curl -sk http://$IP/ | grep -oE 'static/js/[a-zA-Z0-9_.-]+\.js' | sort -u
# 批量下载后全量 API:
grep -ohE '"api/[A-Za-z0-9_/-]{2,80}' js/*.js | sed 's/^"//' | sort -u
# 前端路由 = 管理功能面:
grep -ohE '"/[a-zA-Z0-9_/-]{3,60}"' js/app.*.js | sort -u
```

## API 封装模块(webpack b775 模式)

Vue2 webpack 老式 SPA 里,业务 API 函数集中在某个模块(如 `b775`),导出多个函数:

```js
// app.js webpackJsonp push 里:
function a(e){ return Object(c["c"])({url:"api/Login", needLoading:!0, data:JSON.stringify(e)}) }  // POST JSON
function s(e){ return Object(c["b"])( "api/login/UserValidate", e) }                               // GET 带 query
```

- `c["b"](url, e)` = **GET 带 query 参数**(第三个参数可能是 needLoading)
- `c["c"]({url, data:JSON.stringify(e)})` = **POST JSON body**
- **先确认方法语义再测试**,否则 405 迷路
- 定位:`grep -oE '"[a-f0-9]{4}":function' app.js`;模块定义在 chunk 里,`grep -l '"b775"' js/*.js`
- 登录/查询函数定义集中,从那里可一次性抄出 20+ 个核心 API 路径

## 登录字段与密码编码

- 字段名常是 `UserCode`/`Password`(不是 userName/password)——字段名错报「参数不正确」
- 密码编码常为 `D()(userPwd).toUpperCase()` = **MD5 大写**(D 是 md5 库)
- 验证: `python -c "import hashlib;print(hashlib.md5(b'123456').hexdigest().upper())"` = `E10ADC3949BA59ABBE56E057F20F883E`

## 哈希传递登录

登录接口可能**直接比对 MD5 哈希**(不做二次哈希):
- 从接口泄露 `passWord` 字段原文(如 OperatorQuery 返回)后,把哈希原文直接当 `Password` 提交即可登录
- **拿到哈希 = 拿到密码**,无需破解
- 哈希一眼认: `E10ADC3949BA59ABBE56E057F20F883E` = 123456

## JWT 单活跃会话

- HS256,有效期短(~20 分钟),`exp` 在 payload 里
- **每次登录旧 token 立即失效**(返回 `invalid_token`)
- 批量测试脚本必须:捕获 `invalid_token`/401 → 自动重登 → 重试当前请求

## 统一 JSON 包装的未授权判定

响应 `{"code":...,"data":...,"msg":...}`:
- `code:1000` = 认证失败(需 token)
- `code:1` + `请求异常,状态码:405/404` = 接口存在但方法/路径不对(405=方法错,换 GET/POST)
- `code:1` + `参数不正确/One or more validation errors` = 接口活,字段名/结构错
- `code:2` + `操作异常` = 业务参数不够(继续补字段)
- 部分接口返回 .NET 原生格式(`isSuccess/stateInfo`) = 接口存在,可能未登录或参数缺

## 案例要点

- 完整案例: `parking-access-platform-pentest` 技能 `references/dnake-d5-case.md`
- 狄耐克 D5: 80=管理后台(admin/123456), 443=移动端, 6160=第三方接口;481 个 API;2960 账号哈希泄露→哈希传递登录;发免费卡/远程开闸/支付密钥泄露
