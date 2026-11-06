# 前端 bundle 挖矿：硬编码凭据 + API map + 版本 diff

适用：目标面板/白标前端是 SPA（Vue/React/SvelteKit/Vite），源码在 CF 后面拿不到 ——
**别盲爆登录，先把 bundle 读成源码。**

## 1. 把 bundle 全量抓下来
- 从 index.html 抽 `<script src>` 与 chunk 目录：Vite = `/assets/index-*.js`；Vue CLI = `/js/app.*.js`；
  SvelteKit = `/_app/immutable/chunks/*`。**chunk 要全抓**，路由级页面常把接口/配置写在各自 chunk 里。
- 抓不动时按出口能力选：自有 CF Worker（CF 网络内）→ 住宅代理 + Camoufox → Tor。
  Worker 的 fetch 有截断（~1.5KB），大文件走真浏览器 `page.evaluate` 内取。

## 2. grep 清单（按命中率排）
| 目标 | 模式 |
|---|---|
| 硬编码 key/secret | `[0-9a-f]{32,64}`、`[A-Za-z0-9_\-=]{32,}` 且附近有 `key|secret|token|apikey` |
| 头名 | `X-API-Key`、`api[_-]?key`、`Authorization`、`token:<REDACTED> |
| 后端基址 | `baseURL`、`VITE_[A-Z_]*`、`localhost:\d+`、`127.0.0.1`、`http://` |
| 端点表 | `\.(get|post|put|del(ete)?|patch)\(\s*["'`]/` 与模板字符串 URL |

**本次实证**：568KB 的 `PROD_index-*.js` 里躺着 **64 位 hex 的 `X-API-Key`** + `http://localhost:4000/api`。
用该 key 直打目标自己域名的 `/api` 基址 ⇒ **200 + 全量 CRUD**（`/accounts /transactions /portfolio /assets /prices/refresh`，韩元计价白标假投资盘）。
**要点**：bundle 里漏的 `localhost` 基址要换成目标域名的基址再试一遍，别因为 localhost 不通就放弃这把 key。

## 3. 验 key 用「只读 oracle」，不要用会产生副作用的端点
- 撞一批候选 key 时，选**幂等只读**端点当 oracle。LLM 网关用 `GET /v1/models`（**不花 token、不留对话记录**），
  绝不能用 chat/completions 或任何写端点做爆破。
- 中控/白标类 oracle：`GET /api/config`、`GET /api/settings/public`、`/api/getInfo`。
- **结果要按「是否存在」判，不按「是否有数据」判**：本次 Sub2API 227 个 admin key + 197 个网关 key 全灭，
  而 `GET /api/v1/settings/public` 是免鉴权 200 但**不含任何 key** —— 免鉴权端点不等于密钥泄漏点。

## 4. 后端同源指纹（一个会话打通全部白标）
白标工作台的 `/api/config` 若回的是**母产品的错误体形状**（如 RuoYi 的 `{"code":401,"msg":"认证失败"}`），
⇒ 该白标与母中控**共用同一个后端**，一套会话可平移。本次 `single.<域>` = 「U8国际短信」工作台，指回同一中控。
反之：前端硬编码 key 打的是**另一个独立后端**（假投资盘）⇒ 两个后端要分开打，别把结论混一起。

## 5. 版本指纹 → 仓库 → 只读补丁 diff
1. 版本从 bundle 注释、`/version`、`/api/v1/settings/public`、`<meta name="version">` 里抠。
2. 认仓库：`https://api.github.com/search/repositories?q=<name>` —— **无需 key，web_search 挂了它也能用**。
3. clone 清代理：`git clone -c http.proxy= -c https.proxy= <repo>`（先 unset 所有 `*_proxy`）。
4. 定位版本锚点：`git log --all --grep="<version>"` / tag 列表找 `sync VERSION to <v>` 提交。
5. **只审锚点之后的提交**：`git log <anchor>..origin/main --oneline | wc -l` 先量规模（本次 3805 提交），
   再按目录收窄 `-- <middleware|auth|router|setup 路径>`，最后按关键词捞
   (`grep -iE "security|fix|auth|鉴权|password|filter"`) —— 比通读几千条提交快一个量级。
6. 首启向导（`/setup/status`、`/setup/install`、`/setup/test-db`）要单独看源码：**通常有 guard 且已初始化**，
   属于「存在但不可用」，别把它写进可打面。

## 6. 输出格式
挖到的东西按「**可直打**（key/端点/契约）/ **待验**（候选 key、未审补丁）/ **已排除**（无 key 的免鉴权面、已装死的向导）」
三档写进报告，别把「找到端点」写成「拿到权限」。
