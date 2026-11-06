# 真实上线收尾全记录（2026-08-07）

生产：qavlixor.com（Cloudflare DNS/代理）+ 202.95.1.135:12125（SSH），PM2 4 fork，PG16。

## 1. 🔴 pm2 进程 DATABASE_URL 被 .env.local 覆盖 → 生产 DB 全挂（最重大发现）

**现象链**：部署新登录逻辑（AdminUser 表优先）后验证：新密码 401、旧密码 200——行为仍旧。源码 grep 有新逻辑、build 产物 grep 有新分支（passwordHash×2、timingSafeEqual 在）、BUILD_ID/产物/进程时间戳全对得上，但运行时就是旧行为。

**根因**：`pm2 logs` 抓到 `prisma:error Invalid prisma.sellerAccount.findFirst() invocation: Error validating datasource db: the URL must start with the protocol postgresql://`。Next.js env 加载 **.env.local 优先于 .env**；生产 `.env.local` 第 1 行（带 UTF-8 BOM）历史遗留 `DATABASE_URL="file:./dev.db"`（sqlite）→ pm2 的 next start 进程 DATABASE_URL=sqlite → provider=postgresql 的 Prisma **所有查询初始化失败**。

**为什么"看起来正常"**：所有 API 的 prisma 调用都是 `.catch(() => null)` 静默降级——login 的 staff findUnique catch→null → fallthrough 硬编码分支（旧密码仍 200）；页面 SSR 数据空但不报错。**生产此前大量 DB 操作一直在失败**。

**修复**：
```bash
cp /www/tiktok/.env.local /root/nginx-backup-20260807/env.local.bak
sed -i '1s/^\xEF\xBB\xBF//' /www/tiktok/.env.local   # 先删 BOM！
sed -i '/^DATABASE_URL=/d' /www/tiktok/.env.local   # 再删行（BOM 不删则匹配不到，grep -c 仍 1）
pm2 restart tiktok-marketplace --update-env
```
验证：新密码 200 / 旧密码 401（表优先生效）。生产 DB 配置只留 `.env`（PG）。

**同根因两面**：脚本层（sync-*/gen-* 脚本的 loadEnvFiles）已改为 .env 覆盖 .env.local；**Next 进程层必须删 .env.local 的 DATABASE_URL 行**（Next 不认"覆盖"逻辑）。后续加生产 env 时检查 .env.local 有无 sqlite/旧路径残留。

## 2. 服务器 build 缓存坑

tar 解压更新代码 → build → 产物可能仍含旧逻辑（webpack 增量缓存误判）。排障顺序：
1. `grep -c '<新逻辑关键词>' 服务器源码文件`（tar 是否覆盖）
2. `grep -oE '.{60}passwordHash.{100}' .next-build/server/app/api/auth/login/route.js`（编译产物是否含新分支）
3. `ls -la .next-build/BUILD_ID` + `ps aux | grep next` 进程启动时间——对不上或仍旧 → `rm -rf .next-build` 全量重建（~30s）+ pm2 restart

注：中文注释会被编译剥离，grep 产物要用**代码特征**（变量名/字符串），不能 grep 注释。

## 3. AdminUser 密码迁移

- 登录逻辑：表优先（全字段 findUnique → disabled 403 → verifyPassword(passwordHash) → cookieLogin），无记录回退硬编码
- 生产脚本（临时文件跑完删）：
```js
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.createHash('sha256').update(`${salt}:${password}`).digest('hex');
  return `sha256:${salt}:${hash}`;
}
// upsert adminUser: email=`${role}<EMAIL-REDACTED>`, displayName=角色名, status='active'
```
- 密码：随机 16 位（大小写+数字+符号），**明文只在聊天交付一次**，work/ 临时文件用完删
- 验证：新密码 200 / 旧密码 401；若旧密码仍 200 → 查 pm2 prisma:error（第 1 节）

## 4. 买家充值真实核验化（堵无限套现后门）

- schema：BuyerRecharge `status default "pending"` + `txHash/network/paidAt`；**管理端代充 users/[id]/balance 显式 `status: "approved"`**（default 改了之后不显式传会 pending 不到账）
- `createBuyerRechargeIntent`（kind="buyer_recharge"，金额指纹 base+唯一尾数）+ confirmIntent 分支（pending→approved + BuyerWallet upsert increment + appendOperationLog/notify；chain-auto / finance 人工确认均可）
- `/api/buyer/recharge`：pending 单 + intent → payUrl；前端充值提交 `window.location.href = payUrl`
- 生产 DB push 需 `npx prisma generate && npx prisma db push --skip-generate`

## 5. 生产清理

- **校验单删除级联顺序**：Shipment → OrderItem → PaymentTransaction → AfterSaleCase（若引用）→ Order。外键约束逐个暴露（`Foreign key constraint violated on the constraint: Shipment_orderId_fkey`）——按报错补删
- demo 账号禁用：`user.updateMany({ where: { email: { in: [...] } }, data: { status: 'disabled' } })`（保留数据只禁用）
- nginx 旧 IP：`sed -i 's/ 118\.107\.21\.97//g' /etc/nginx/sites-enabled/tiktok-marketplace`（备份到 /root/nginx-backup-20260807/）→ `nginx -t` → `nginx -s reload` → curl 127.0.0.1 http/https 200

## 6. 商品盘点结论

生产 6995 商品：6989 published + 6 delisted，全部 reviewStatus=approved；0 零价变体、0 PENDING 占位标题、0 无变体 → 数据健康。70+ 直营店每店 50-200 商品；3 个普通店（星桥优选店/小飞的百货店铺/南星）0 商品（空店无影响）。

## 7. Cloudflare 源站保护（2026-08-07 已执行）

qavlixor.com DNS 指向 Cloudflare（2606:4700 = 橙云代理）。用户确认后已加 iptables 白名单：

```bash
CF_IPS=$(curl -s --max-time 15 https://www.cloudflare.com/ips-v4)
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
for ip in $CF_IPS; do
  iptables -A INPUT -p tcp --dport 80 -s $ip -j ACCEPT
  iptables -A INPUT -p tcp --dport 443 -s $ip -j ACCEPT
done
iptables -A INPUT -p tcp --dport 80 -j DROP
iptables -A INPUT -p tcp --dport 443 -j DROP
iptables-save > /etc/iptables/rules.v4   # 持久化（apt-get install iptables-persistent 可能卡超时，规则已生效无碍）
```

- ⚠️ **先告知用户再执行**：加白名单后 IP 直连（202.95.1.135:80/443）断，必须走 qavlixor.com；SSH 12125 不受影响
- 验证：本机 curl `https://qavlixor.com/` = 200（CF 回源，首次握手慢 ~12s 正常）；curl `http://202.95.1.135/` = 000（被拦）
- 服务器上 ufw/iptables 链并存：INPUT policy DROP + CF ACCEPT 规则在 ufw-before 链之后追加生效；SSH 放行靠 ufw-before（测试时 SSH 全程在线）

## 8. 验证注意事项

- 生产注册测试账号需邮箱验证码（`请填写邮箱验证码`）——**绕过模式**：生产 DB 直插测试买家（`user.upsert` + sha256 哈希密码 + status=active）→ 登录 → 跑通链路 → **测完禁用（status=disabled）+ 清数据**（buyerWallet 清零、buyerRecharge/paymentIntent deleteMany）。2026-08-07 已用此模式跑通充值全链路：充值 66 → 余额 0 + 单 pending → 财务确认（POST /api/admin/pay-intents/[intentNo]）→ 余额 66 + approved + txHash ✅
- 登录限流：每 IP 20/分、每账号 10/分——密集测试会 429
- 新管理密码交付：明文只放桌面 txt 文件（`C:\Users\Administrator\Desktop\Qavlixor管理密码.txt`）+ 聊天一次；work/ 临时 JSON 用完删
