<!-- archived from /root/.hermes/skills/security/hyperf-microservice-authz-sqli-family/SKILL.md on 2026-10-21 -->

---
name: hyperf-microservice-authz-sqli-family
description: Use when 打自研 PHP 微服务 fail-open 鉴权+RPC原始SQL注入。
---

> 归档卡：原目录 `/root/.hermes/skills/security/hyperf-microservice-authz-sqli-family`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hyperf-microservice-authz-sqli-family/…')`，不要相对 `references/legacy/` 解析。

# 自研 PHP 微服务平台：fail-open 鉴权 × RPC-原始SQL 注入族

适用：Hyperf/Swoole 系自研微服务（如 LinkESOP sy-esop / LINKTRADE allian-trs）。触发词：{svc}.v1 路由、whereRaw($where)、JsonRpc whereRaw、可选鉴权中间件、多服务并列仓库。

## 适用指纹（先判族）
- 路由形如 `/{服务名}.v{n}/{Controller}/{action}`（如 `/market.v1/IPO/IPOs`）
- 响应壳 `{"code":1,"msg":"操作成功"}`；失败 `buildFailed('common.xxx')`；错误统一 `Internal Server Error.`
- 自研 `CorsMiddleware` 同时给 `Access-Control-Allow-Origin: *` 与 `Allow-Credentials: true`
- 仓库内多服务并列（gateway/order/user/market/active/open/info/push/system）

## 打法 1：服务层鉴权 fail-open（先判是否白干）
```bash
find . -name AuthMiddleware.php -not -path "*/vendor/*" | while read f; do
  echo "--- $f"; grep -nE "getHeaderLine|checkToken|withAttribute|handler->handle|401" "$f"; done
```
若各服务内容一致且尾部为 `return $handler->handle($request);`（无 else 拒绝分支）⇒ **服务层零鉴权**，访问控制全靠网关。
⇒ 价值：网关白名单里任一免登录路径即直接触达业务代码；`getAttribute('uid', 0)` 静默降级为 uid=0 而不拒绝。

## 打法 2：跨服务 RPC 传原始 SQL（真正的注入杠杆）
```bash
grep -rn "whereRaw(\$\|selectRaw(\$\|orderBy(\$" --include=*.php --exclude-dir=vendor --exclude-dir=runtime .
```
链路：`Controller 拼接 → this->XxxRpc->method($whereExp,$field) → order-server: Model::query()->whereRaw($whereRaw)->selectRaw($field)->get()`
- 注入**在另一服务的数据库**执行（跨库放大，报告要点明）
- `selectRaw` 固定 N 列 ⇒ 天然对齐 `UNION SELECT`
- **坑**：变量若同时用于参数化查询（`where(['symbol','=',$v])`）与拼接，脏值使参数化查询查空 → 提前 return，**无回显**，只能盲注。

## 打法 3：双通道盲注 oracle + 并行外带
- **时间道**：`X" OR IF((cond),SLEEP(2),0) -- `；必须留对照（真 2.0s / 假 0.03s）。表空时 SLEEP 不逐行求值 ⇒ 用 `OR` 而非 `AND` 让全表参与。
- **error 道（快 50 倍，40ms/发）**：`X" OR IF((cond),(SELECT 1 UNION SELECT 2),0) -- ` → 真=子查询多行错误=500；假=200。以状态码判定，与延迟无关，**可安全并发**。
- **并行外带器**：URL-encode payload 写文件 → 目标机 `awk` 拼 URL → `xargs -P 8 -n 2 bash -c 'curl -sk -o /dev/null -w "%{http_code}" "$1"'`；每字符 7~8 轮二分，253 字符表清单约 1 分钟。
- 注释符：MySQL `-- `（尾空格）与 `#` 都试。取值模板：先 `CHAR_LENGTH((expr))`，再 `ASCII(SUBSTRING((expr),i,1)) > mid`。
- **坑**：存在性检查别用 `(x) <> 0` 判字符串（MySQL 强转必假），字符串一律先取 CHAR_LENGTH。

## 打法 4：边界判定（决定报告怎么写，别吹）
| 探针 | 结论 |
|---|---|
| `X"; SELECT SLEEP(3) -- ` → 500 | 堆叠不可用 ⇒ **只读**，不能 UPDATE/INSERT，不能 general_log 写马 |
| 堆叠可用 | 可写 ⇒ 可改资金数据 / general_log → webshell |
| `@@secure_file_priv` 非空 | `INTO OUTFILE` 被限目录，写马受挡 |
| `current_user()` = `root@%` | 注入即全库权限，影响面拉满 |
| 目标表全空 | 注入点仍可报 500/time 差分，但需改判“是否可回显” |

## 打法 5：元数据最小化取证（合规红线）
只取 `database()/version()/current_user()/@@secure_file_priv/GROUP_CONCAT(table_name)/资金表列结构与 COUNT(*)`。
**不取** user_id 明细、余额数值、提现内容；**不做**任何写操作。报告显式声明边界（只读/未取隐私/未留驻留）。

## 交付
正式报告结构：摘要 → 三处根因（鉴权/RPC/DB权限）+ 精确文件行号 → 生产实证表（200/500/2.04s vs 0.03s）→ 可粘贴 curl（经跳板 `ssh -N -D 1080` + `--socks5-hostname`）→ 修复建议（默认拒绝/结构化条件/参数绑定/root 降权）→ 证据文件清单。案卷见 `references/case-linkesop-2026-09.md`。

## Pitfalls
- 前置 CDN（whecloud 类）：quote 不改回显、延迟抖动大 ⇒ 先判是否命中缓存，加 cache-buster 或走源站直连再下结论。
- 域名环境漂移：同域 443 可能已被别的产品（如 MaxKB）占据、API 只在 :80 活着 ⇒ 先摸真实入口，别拿旧卷宗当现状。
- 500 不等于注入：必须留 control（基线 200 + 无效字符 vs 有效 JSON）配对。
- `grep` 全库正则易 exit 124 ⇒ 用 `--include/--exclude-dir` 收窄或改 Python 扫描器。
- 长报告/长 skill 一次写会被压缩截断 ⇒ 分片写 + 写后 `tail` 验尾部。
