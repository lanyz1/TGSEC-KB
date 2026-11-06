# 商品改库存"刷新不变"根因:PM2 多实例进程内缓存(2026-08-12)

## 症状
卖家端改库存(行内/批量)或改价:PATCH 返回 ok,前端提示成功,但刷新/重进页面显示旧值。
本地单实例 dev 复现正常;生产必现或概率复现(取决于 nginx 轮询命中哪个实例)。

## 根因
生产 PM2 fork 4 实例(3000-3003,nginx 轮询),lib/product-repository.ts 的
catalogCache(60s TTL)+ catalogInflight 为模块级进程内变量,每实例独立一份。
invalidateProductCatalog() 只清当前进程缓存 → PATCH 命中实例 A(更新 DB+清 A 缓存),
router.refresh()/新请求命中 B/C/D 返回 60s 内旧 catalog → 旧值。
19998 = 9999×2:双 SKU 商品(拓竹铺货 0.5kg/1kg、单机/Combo 各 9999)。

## 排查顺序(先证真源再疑缓存)
1. 生产 DB 直查该商品 variants.stockQuantity 是否已变(变了=写入成功,问题在缓存层)
2. 本地端到端 PATCH 复现(见下)确认代码逻辑无 bug
3. pm2 jlist 确认 fork 多实例;grep catalogCache lib/product-repository.ts 确认进程内缓存
4. 生产事务+回滚模拟 syncProductToPrisma 的 variant upsert,验证 DB 层写入不报错(零副作用)

## 本地端到端复现(2026-08-12 实测)
1. `pnpm db:gen:dev && pnpm dev`;缺列先 `pnpm db:push:dev`
2. 改一个测试商品 variants 为 9999/9999(记录原值,测完恢复)
3. curl 登录卖家账号(本地 <EMAIL-REDACTED> / Demo@2026view):
   `POST /api/auth/login {role:'seller',email,password}` -c cookie
4. `PATCH /api/seller/products/<id>` body `{skuItems:[{sku,price,stock:0},{sku,price,stock:9999}]}`
   → 返回 inventory:9999 = 正常;node 直查 DB 已落库 = 代码逻辑无 bug
5. 结论:本地一切正常 → 问题在生产多实例缓存,不是代码

## 生产 DB 查询/模拟脚本模式
- 本机 paramiko 环境坑:hermes venv 的 paramiko 坏(cryptography 50.0.0 vs 共享对象 48.0.1),
  全局 PYTHONPATH 指向 hermes site-packages 污染所有 python(连新建 venv 也中招)
  → `unset PYTHONPATH` + `python -m venv` + `pip install paramiko`,复用 `scripts/qav-prod-query.py`
- 服务器脚本一律 `.mjs`(ESM):`require` 报 ReferenceError,用 `await import("@prisma/client")`;
  .env.local 正则逐行注入 env
- **productOperationMetric 不是 Product 的 include 字段**(schema 无反向 relation),
  单独 `findUnique({where:{productId}})` 查询
- 对生产做"模拟写入验证"一律 `$transaction` + 末尾 `throw new Error("ROLLBACK_NOW")` 回滚,
  捕获后确认原值未变 —— 零副作用
- 连接配置从 scripts/deploy.py 读取,勿硬编码(红线:禁凭证入 memory)

## 修复方案(已实施 ✅ 方案 A,commit edb07f3,2026-08-12 用户拍板)
- **A 治本(已落地)**:加 CatalogVersion 表;invalidateProductCatalog() 递增 DB 版本号;
  各实例 getProductCatalog 前查版本号,不一致即重建缓存。标准分布式缓存失效,写后全实例秒级一致。
- B 临时(未采用):nginx upstream ip_hash sticky,同 IP 固定实例(PATCH 与刷新同实例,缓存自然同步)。
- C 最小(未采用):TTL 60s→5s(窗口缩小,不根治,多设备仍会碰到)。

### 实施细节(commit edb07f3)
1. `prisma/schema.prisma` 加模型:
   ```prisma
   model CatalogVersion {
     id        Int      @id
     version   Int      @default(0)
     updatedAt DateTime @updatedAt
   }
   ```
2. `lib/product-repository.ts`:
   - `const CATALOG_VERSION_ID = 1`;`readCatalogVersion(): Promise<number|null>`(读失败返回 null,勿返回 -1 会误触发重建)
   - `bumpCatalogVersion()`:`upsert where id=1, update version increment 1, create version 1`
   - `invalidateProductCatalog()` 改 `export async function`,末尾 `await bumpCatalogVersion()`
   - `loadPrismaCatalogCached()`:读 version 后 `if (catalogCache && expires>now && (version===null || cache.version===version)) return cache.data`;写入缓存时带 version
3. **调用点加 await**(关键):`app/api/seller/products/[id]/route.ts` PATCH+DELETE、`app/api/seller/products/route.ts` POST×2、lib 内部 347/403/475/489 行(全部已是 async 函数上下文)。confirm route 只 import 未调用,不用改。
4. dev 流程:改主 schema → `pnpm db:push:dev`(自动派生 dev schema 建表)→ 重启 dev(改表后旧进程不认新模型);generate 前先确保 dev 已停(EPERM)。

### 验证(本地模拟多实例,2026-08-12 实测)
```bash
# ① 建立缓存:GET 首页 → ② 外部进程模拟"另一实例写":
node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient();
(async()=>{await p.productVariant.updateMany({where:{productId:'<id>',sku:'<sku>'},data:{stockQuantity:4321}});
await p.catalogVersion.upsert({where:{id:1},update:{version:{increment:1}},create:{id:1,version:1}});await p.\$disconnect()})()"
# ③ 60s TTL 窗口内立即 GET 首页 → grep 4321 必须命中(修复前读旧值)
```
- 无变更时连续 GET 大小一致(缓存仍命中,不退化)
- 版本号跳 2 属正常:syncProductToPrisma 内部 + 路由各 bump 一次,无害
- tsc --noEmit EXIT 0;测试数据恢复原值(改测试账号数据必还原)
