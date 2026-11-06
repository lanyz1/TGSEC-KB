# TikFlow 复扫 + 新功能审计(2026-08-16)

范围:复扫 2026-08 审计 13 项 + 新增功能(提现收款地址、CK/代理采集、支付通道 API、工具云端更新)。对照 `tikflow-audit-2026-08.md` / `tikflow-audit-fix-2026-08.md`。

## 历史 13 项复扫:全部确认已修复 ✅
S1 沙箱 webhook(NODE_ENV+session+归属+type 四重)/ S2 弱口令(seed 随机化+生产改密)/ S3+M2 tokenVersion+status / M1 CRON_SECRET(生产已设,实测 401)/ M3 登录限流 / M4 注册枚举 / L1-L5 全修。

## 新发现(4 项,全部修复上线,commit 2a68439)

### 中危
1. **提现审核 TOCTOU 竞态 → 双花** `src/lib/wallet.ts:185-209`
   - approve/reject 守卫是"读后写"(findUnique 查 REVIEWING → update)——两个管理员并发处理同一单:approve 后(已打款)被并发 reject → **余额退回 = 用户收到打款 + 余额 = 双花**
   - 修复:条件更新——approve `updateMany({where:{id,status:"REVIEWING"},data:{status:"COMPLETED"}})` + `r.count===0` 幂等返回;reject 先 `updateMany(→"REJECTING")` 临时锁占位(事务回滚保证不残留)再退余额置 REJECTED。**规律:资金状态机守卫一律条件更新,别用读后写**
2. **生产敏感文件权限 644** `/srv/tikflow/.env`(DB 密码/COOKIE_SECRET/USDT 地址) + `prisma/prod.db`(用户密码 hash + TikTok Cookie)→ `chmod 600`(部署后必查)

### 低危
3. **GET /api/wallet/methods 无鉴权**——泄露支付通道配置状态(哪些通道配了凭证)→ 加 `getSession()` 401
4. **withdraw route `req.json()` 未 catch**——非法 JSON → 500(admin 版已 catch)→ 统一 `await req.json().catch(() => ({}))` 走 schema 400

## 加固
- Caddy 全站安全响应头:`Strict-Transport-Security max-age=31536000` + `X-Content-Type-Options nosniff` + `X-Frame-Options SAMEORIGIN` + `Referrer-Policy strict-origin-when-cross-origin`(header 块,实测生效;勿加 CSP——Next 动态页面内联脚本易误伤)
- CORS 默认无头(安全)✅;CRON_SECRET 已设 ✅

## 无问题确认项(已覆盖,复扫跳过)
- IDOR 全带 userId 过滤;管理 API 三处 role==ADMIN;stripSensitive(CK/代理不返前端);TRC20 地址格式校验+金额下限+事务原子扣减;驳回必填理由;USDT txHash 幂等+来源审计;bcrypt cost 10
- 已知可改进(非漏洞):提现地址无 checksum 校验(防误填已够)、approve 无二次确认弹窗(操作习惯)

## 审计方法备忘
- 复扫快路径:`grep -n` 关键修复锚点(NODE_ENV/tokenVersion/secret/updateMany where status)确认代码仍在,再测生产配置(chmod/curl 401/响应头)
- 资金竞态审计必查:所有状态机守卫是否"读后写"(findUnique → update)——该模式在并发下必现双花类漏洞
