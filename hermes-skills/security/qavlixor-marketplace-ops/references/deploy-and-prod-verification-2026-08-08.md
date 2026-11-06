# 2026-08-08 生产事故与修复实录（部署/角标/文案/支付）

## 1. 生产 DB 静默全挂（最严重）
**症状链**：真实上线修复部署后，生产登录"新密码 401 / 旧密码 200"→ 排查产物（login route.js 含新分支）→ AdminUser 表哈希正确 → 最后 pm2 日志发现 `prisma:error Invalid prisma.sellerAccount.findFirst() invocation: the URL must start with postgresql://`。
**根因**：生产 `/www/tiktok/.env.local` 第 1 行（带 UTF-8 BOM）`DATABASE_URL="file:./dev.db"`（历史 sqlite 遗留）→ Next.js env 加载 `.env.local` 优先于 `.env` → 所有 Prisma 初始化失败 → 全站 DB 操作静默降级（`.catch(()=>null)` 兜底），登录走硬编码分支（旧密码 200）。
**修复**：删 .env.local 的 DATABASE_URL 行。⚠️ BOM 使 `sed '/^DATABASE_URL=/d'` 不匹配（grep -c 仍 1）→ 用 `sed '/^\xEF\xBB\xBF*DATABASE_URL=/d'`。
**验证**：新密码 200 / 旧密码 401；DB 查询恢复（商品 6995 订单 16）。
**教训**：pm2 进程的 env 加载顺序是 Next 的（.env.local 优先），不是 loadEnvFiles 脚本的。部署后先看 pm2 日志有没有 prisma 初始化错误。

## 2. gitignore 误伤 API 路由（修复 3 次都不生效的假象）
**症状**：卖家入驻上传营业执照仍 403「商户入驻尚未审核通过」——豁免代码已提交部署 2 次。
**根因**：`.gitignore` 第 29 行 `uploads/`（本意挡根目录存储）匹配了 `app/api/uploads/` 目录 → 该路由**从不进 git → 不进 git archive → 生产永远 7/30 旧文件**。服务器源码 `grep allowUnapprovedSeller` 0 命中，但 build 产物有（说明 build 时用的源码曾短暂是新版？——实为 tar 解压顺序/覆盖问题，最终以 grep 服务器源码为准）。
**修复**：`.gitignore` 改 `/uploads/`（根锚只挡根目录）；`git add -f app/api/uploads/route.ts`；重打 tar 后 `tar tf | grep "api/uploads"` 确认在包里。
**验证**：draft 卖家上传营业执照 200 + 商品管理仍 403（业务隔离保持）。
**排查套路**：`ls -la` 服务器目标文件时间戳（旧 = 没进包）→ `tar tf` 验证 → git ls-files 查跟踪状态 → .gitignore 逐条核对。

## 3. build 未完成就 restart（新功能 404）
**症状**：部署后 `/api/buyer/wallet` 404（登录 200 正常）。服务器产物文件在（09:13），但进程 09:03 启动 → 进程加载旧产物。
**修复**：build 完成后二次 `pm2 restart` → wallet 200。
**根因**：上一轮 `(nohup pnpm run build &)` 后立即 restart（build 还在跑）。
**规则**：轮询 build 日志确认 `Compiled successfully` + `ps aux | grep 'next build' | grep -v grep | wc -l` = 0 才 restart。

## 4. 增量编译产物一半新一半旧（前端 UI 没生效）
**症状**：服务端功能正常（wallet API 200、余额支付下单成功），但用户浏览器结算页没有「余额支付」选项；服务器 static chunks grep 不到新文案。
**修复**：`rm -rf .next-build && pnpm run build`（29.3s 全量）→ 二次 restart → 生产结算页 SSR 实测含「余额支付」。
**验证**：curl 结算页 HTML（登录态）`html.includes('余额支付')`。

## 5. 生产验证脚本模式（本机 curl 被出口 IP 限制时）
```js
// sftp 上传 verify.cjs 到 /www/tiktok → node verify.cjs → rm
const l = await fetch(B + '/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, password, role})});
const cookie = l.headers.get('set-cookie')?.split(';')[0] || '';
const page = await fetch(B + '/account/...', {headers:{cookie}});
const html = await page.text();
console.log('含X:', html.includes('\u5f85\u53d1\u8d27')); // 中文用 \uXXXX 转义
```
- 中文关键词在 node -e 里用 `\uXXXX` 防编码问题
- 脚本内嵌 `require('./node_modules/@prisma/client')` 直查 DB 对照
- 验证完删脚本 + 清理测试数据（订单删除按 FK 顺序：OrderItem/PaymentTransaction/Shipment/AfterSale → Order）

## 6. 角标三端修复
- **通知铃铛**（卖家/管理端）：NotificationMessage 无 readAt → count=7天总数 → 永不减。加 readAt + 已读 API + 未读口径 + 打开面板即已读 + 通知中心进入即已读。新建 `/admin/notifications` 页（原 404，复用 SellerNotificationList 纯展示组件）。
- **管理端侧栏/KPI**：sellers 计数 `notIn[approved,rejected]` 含 draft → 草稿永远计入。改 `status: "submitted"`。生产实测角标 2→0（DB submitted=0 draft=2）。
- **chat 角标**：readAt 口径本来正确（实测 10→9），不用动。

## 7. DynamicText 词级半译
- "Unshipped" → "Un已发货"、"未发货" → "未Shipping"：翻译表无键的词被词级半译。
- 修复：状态词用订单详情页词表（待付款/待发货/待收货/已签收/交易成功/售后中/交易关闭——均有翻译键）。
- 处理规则长英文句也改中文短句（82 字符英文会撑卡片）。

## 8. 买家余额支付
- 条件原子扣减：`updateMany where {userId, availableAmount:{gte: total}}` count===0 → 400 余额不足 + 回滚订单 + 回补库存。
- 订单直接待发货（内存对象 order.status 改"待发货"再 syncOrderToPrisma）+ syncPaymentForOrder method=balance status=paid + 跳过 createOrderIntent。
- PaymentMethod enum 加 balance（dev+prod db push）。
- 资金记录消费条目：paymentTransaction where {buyerEmail, method:'balance', status:'paid'}。

## 9. 其他
- 商户审核 draft 修复：cnStatus 补 draft→草稿/suspended→已限制/closed→已关闭 映射 + 快捷审核按钮仅 submitted 可用 + 详情页非 submitted 不渲染表单。SellerApplication 类型同步扩展。
- 入驻豁免矩阵：uploads / email-verification(send contact) / application draft+submit 加 `allowUnapprovedSeller: true`；19 个业务 API（商品/资金/发货/提现）保持拦截。
- 提现全局统一：最低 50 + 1.5%（0.75 起），前端弹窗文案+submit 校验+后端报错文案三处一致。
- 资金记录点击式 tab（全部/充值/消费记录）。
- QA 测试账号体系：qa-buyer-1/2/<EMAIL-REDACTED>（余额 200）+ <EMAIL-REDACTED>（QA测试店铺 approved，钱包 500），密码 QaTest!2026，测试完禁用。
