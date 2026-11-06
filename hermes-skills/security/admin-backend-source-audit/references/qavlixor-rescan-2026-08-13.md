# Qavlixor 商城安全复扫对照(2026-08-13)

对 `qavlixor-admin-audit-2026-08.md` 的 21 项发现复扫 + 新功能/生产配置审计。**本文件为修复后最终状态(commit 7fc52ba 已部署)**,下次复扫先对照此表,避免重新发现同一批问题。

## 上次 21 项修复状态(最终:20 项已修,1 项接受风险)

### ✅ 已修复(20 项;7 项严重全部修复)
| 项 | 内容 | 修复方式 |
|---|---|---|
| 严重1 | storage/health 无鉴权 | 已加 requireRole |
| 严重2 | 校验单污染资金结算 | 资金统计已过滤 orderChannel=validation |
| 严重3 | 卖家提现无状态机 | 仅 submitted/paying 可变更 + updateMany 条件更新防 TOCTOU |
| 严重4 | confirmIntent 可确认已取消/驳回单 | wallet 分支拦 cancelled/rejected |
| 严重5 | 禁用买家/卖家仍可登录 | login 拦 disabled/deactivated + requireRole 查 status |
| 严重6 | 直营店明文密码对比 | 改 hashPassword 参与校验(源码常量仍在,已无害化) |
| 严重7 | 财务驳回已发货订单 | reject 仅 pending_payment+pending |
| 中8 | 禁用员工页面层 | adminUserStatusCache 30s 缓存 + requireRole 拦截 |
| 中9 | change-reviews 无权限 key | requireAdminPermission("ops") |
| 中10 | 员工管理仅 ops 可禁用员工(DoS) | **2026-08-13 修**:staff- 分支加 ROOT_EMAIL 检查,仅 root 可禁用/启用员工(403) |
| 中11 | 权限矩阵过宽 | ops 不再含 risk,risk 不再含 system(2026-08-07 用户拍板) |
| 中12 | 保证金审核无状态机 | 终态不可改 + 退还需打款凭证 |
| 中13 | 商品/商户审核无状态机 | submitted_for_review 守卫 + 409 |
| 中14 | 买家提现 TOCTOU | updateMany 条件更新 |
| 中15 | 审计 actorId 恒 "internal" | **2026-08-13 修**:local-db.ts 从签名会话取操作人邮箱(verifySession),失败才回退 internal |
| 中16 | 管理员密码硬编码 | 已删除明文常量 |
| 中17 | 代充无事务+浮点 | **2026-08-13 修**:balance route 三分支(卖家/买家/商户)$transaction 原子化 + Math.round(amount*100)/100 定点 |
| 中18 | ops/service-status 公开 | **2026-08-13 修**:加 requireRole(["admin"]) + refresh 30s 限流(实测未登录 401) |
| 中19 | 限流 XFF 首段可伪造 | **2026-08-13 修**:clientIp 取 XFF 倒数第二项(CF 链路=真实用户 IP);PM2 稀释仍存在(阈值×实例数,可接受) |
| 低21-部分 | Withdrawal 索引 | @@index([storeId, status]) 已加 |
| 低21-部分 | providerReference 无唯一约束 | **2026-08-13 修**:@unique + 数据清理(balance×44/空串×19 清 NULL)后建库成功,pg_indexes 验证存在 |

### ⚠️ 接受风险(未修,2 项)
| 项 | 原因 |
|---|---|
| SSH root 密码登录(12125) | 用户远程维护依赖密码 SSH,禁用会锁死自己;建议后续配密钥对再关 |
| Float/Decimal 资金字段混用(6 处) | 改 schema 影响全平台资金统计,风险大于收益 |

## 新功能审计(2026-08-13 客服系统/新增客服/域名隔离)— 全部通过
- staffs 新增客服 API:仅 root(requireRole + ROOT_EMAIL)+ 邮箱格式/唯一/密码≥8/hash/isAgentOnly 默认 true ✅
- logout API:无越权;跨站 POST 无 SameSite cookie 无实际影响 ✅
- /agent 守卫:已从邮箱后缀判断改为查 AdminUser 表(自定义邮箱客服可进)✅
- 客服系统 10 个 /api/chat/* 路由全部有 requireRole ✅
- middleware 域名隔离:固定域名重定向(规避 CF 回源 host 坑)✅

## 生产配置(最终状态)
| 项 | 状态 |
|---|---|
| .env 权限 | **2026-08-13 已 chmod 600**(原 666 世界可写) |
| nginx X-Forwarded-Host | **2026-08-13 已加 `proxy_set_header X-Forwarded-Host $host`**(×3 处,reload 后实测伪造 evil.com → 仍跳真实域名) |
| SSH root 密码登录 | 未处理(接受风险,见上) |
| CRON_SECRET/SESSION_SECRET/DATABASE_URL | 生产已配置 ✅ |
| 安全头 | CSP/X-Frame-Options/nosniff/referrer-policy 齐全 ✅ |
| /.env /.git | 404 不可达 ✅ |
| ufw | active INPUT DROP ✅ |

## 依赖审计(2026-08-13 已修复清零)
- 原 7 漏洞(5 high/2 moderate):sharp <0.35.0、postcss <=8.5.22、nanoid <3.3.17
- 修复:`pnpm-workspace.yaml` 加 `overrides:`(sharp >=0.35.0 / postcss >=8.5.23 / nanoid >=3.3.17)+ `pnpm install --force` 重解 lock → sharp 0.35.3 / postcss 8.5.26 / nanoid 6.0.1
- 验证:`pnpm audit --prod --registry=https://registry.npmjs.org` → "No known vulnerabilities found"(国内镜像无 audit 端点必须加官方 registry)

## 修复期技术坑(2026-08-13 实战)
- **db push 唯一约束 P2002 静默失败**:deploy.py 不检查 db push 结果,生产加 @unique 失败后索引不存在却部署成功。必须先清重复数据(业务标记值 `"balance"`/`""` 置 NULL)再 db push,最后 pg_indexes 验证。
- **pnpm v11 overrides 位置**:package.json 的 `pnpm` 字段已废弃(报 "[WARN] The pnpm field is no longer read"),overrides 必须放 `pnpm-workspace.yaml`。
- **生产验证 node 脚本**:服务器 /tmp 下 .mjs 常报 ERR_MODULE_NOT_FOUND / ESM loader 错,直接用 psql 查 pg_indexes 更稳(DATABASE_URL 去引号后 PGPASSWORD 提取)。
