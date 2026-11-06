<!-- archived from /root/.hermes/skills/security/generated-api-client-mining/SKILL.md on 2026-10-21 -->

---
name: generated-api-client-mining
description: "Use when a SPA ships an OpenAPI-generated API client."
version: 1.0.0
metadata:
  tags: "api,openapi,nestjs,swagger,spa,bundle,recon,admin,idore"
  category: "recon"
---

> 归档卡：原目录 `/root/.hermes/skills/security/generated-api-client-mining`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/generated-api-client-mining/…')`，不要相对 `references/legacy/` 解析。

# 生成式 API 客户端挖掘

## 触发条件

bundle / APK 里出现下面任一特征，就说明包里躺着**服务端 API 的机器可读全量地图**，比目录爆破高效得多：

- 函数名带 `Controller`：`genUserBankControllerUpdate`、`userImControllerFind`、`xxxControllerDelete`（openapi-generator / swagger-codegen 命名）
- 对象表：`{ path: "/api/xxx/${id}", method: "GET", ... }`
- 响应模型字段名成片出现（DTO 形状被内联进客户端）
- 后端是 NestJS / Spring / Go swagger 体系，前端用 axios/fetch 封装自动生成

**关键认知**：这不是"页面逻辑"，是接口清单。只要某个 controller 被任何页面 import 过，tree-shaking 就删不掉——**UI 没渲染的管理端接口也会一起被打进 C 端包**。

## 提取流程

1. **先定位生成的客户端文件**（常名如 `api-xxxx.js`、`client.ts`、`services/`）：
   ```bash
   grep -lE 'Controller(Find|Update|Delete|Create)|method:\s*["'"'"'](GET|POST|PUT|DELETE)' *.js
   ```
2. **跑脚本还原路由表**：
   ```bash
   python3 scripts/extract_client_routes.py ./js > routes.tsv
   ```
   输出 `METHOD<TAB>PATH<TAB>file`，`${...}` 模板参数保留原样。
3. **归类**：`/gen*` 与 `/generated/*` 往往是同一张表的两个命名空间（管理端 vs 用户端视图），分开列。
4. **逐个探活**：用**正确的动词**打，看 401 / 200 / 404 分层差异。

## 管理端面识别信号

包里出现下列任一，基本可判定 C 端包混进了管理端契约：

- `__ADMIN..._CACHE_KEY__` / `__ADMINSTER_LOGIN_INFO_CACHE_KEY__`（拼错也照抓，说明有独立的管理端登录态 store）
- 同一资源的写操作：`gen*ControllerUpdate`（POST `/api/genXxx/update/${id}`）、`*ControllerDelete`
- `export` / `import` / `resetPassword` / `role` / `menu` / `dept` / `assign`
- 双份 controller：`generated*`（读，较宽松）与 `gen*`（写，较严格）

## 双 Guard 差分（最值钱的一步）

同一个普通用户 token 打两类接口，结果不同就是两套 Guard：

| 现象 | 含义 | 动作 |
|---|---|---|
| `/api/gen*` → 401 | 管理端 Guard（admin/role 判定） | 不要停在这里，去找同资源的兄弟命名空间 |
| `/api/generated/*/list` → 200，但只回本人 | 登录级 Guard + 服务端强制 userId 过滤 | 测 detail / update / delete 是否也过滤 |
| `detail/{别人的id}` → 空 / null | 服务端按 token 过滤 | 记录"已防护"，不要再薅 |
| `PUT` 自己的记录 → 200 | 写接口对普通用户开放 | 仅此而已——**不要**拿别人的 ID 验证 IDOR |

**401 ≠ 没洞**。生成客户端同时给出 `gen*` 和 `generated*` 两套时，弱的那套往往就是登录即可的 CRUD。

## 动词纪律（真实误判来源）

- 响应体 `Cannot POST /api/x` + 404 ⇒ **方法错了**，不是路由没了。以客户端里的 `method:` 字段为准。
- 实测踩坑：captcha 在生成客户端里是 `method: "GET"`，脚本按 POST 打 → 404，一度误判"验证码接口下线"，实际是 POST 撞到了只能 GET 的路由。
- 双前缀：baseURL 已含 `/api` 时生成路径会写成 `/api/api/x`。**单前缀和双前缀都探**——WAF 与源站 nginx 的 rewrite 规则可能不一致（同一路径一边 200 一边 404）。

## 写入型接口的边界

- 验证写接口是否对普通用户开放：**改自己的记录**，看是否 200（足够定级）。
- 验证 IDOR 时绝不改他人记录：改受害者银行卡/地址是破坏性、不可回滚的，会伤到真实用户。报告写"写接口对普通用户开放，IDOR 未验证（避免破坏真实数据）"，如实标注，不夸大。

## Pitfalls

- **压缩后 `Controller` 后缀可能被抹掉**：改用 `path\s*:` + `method\s*:` 组合搜，别只 grep `Controller`。
- **别把整个 bundle 当页面代码读**：先抽表，再看模型字段，最后才读业务逻辑。
- **同一路径可能在 WAF 层存在、源站层不存在**（或反之），按通道分别记录，不要合并成一条结论。
- **客户端里的响应模型字段名 = 服务端真实字段名**，可直接用来构造越权读取的期望值（如列表不返回、详情才有的 `idCardNo`、`bankCardNo`）。

## 输出

1. 路由表（METHOD + PATH，标注单/双前缀实测结果）
2. 管理端命名空间清单 + 各自 Guard 实测状态
3. 已开放写接口清单（只列自己记录验证过的）
4. 未验证项 + 原因（避免破坏 / 需 admin 票）
