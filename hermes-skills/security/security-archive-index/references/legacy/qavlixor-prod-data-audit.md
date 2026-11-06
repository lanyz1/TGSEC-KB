<!-- archived from /root/.hermes/skills/security/qavlixor-prod-data-audit/SKILL.md on 2026-10-21 -->

---
name: qavlixor-prod-data-audit
description: >-
  测绘引擎·核对/修正 qavlixor 生产库商品价格(SKU vs 上架Excel基准)。psql 通道+广播。
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/qavlixor-prod-data-audit`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/qavlixor-prod-data-audit/…')`，不要相对 `references/legacy/` 解析。

# qavlixor-prod-data-audit（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-prod-data-audit/`

溯源（仅标记）：`hermes/devops`

---

# qavlixor 生产库数据核查与修正

## When to Use

- 商品 SKU 价格对不上 / 多 SKU 价格被统一 / 店铺价格与上架表不一致
- 任何 psql 直连 qavlixor 生产库的查数、改数、价格审计任务
- 部署/发版流程见 `qavlixor-prod-ops`(用户自有,可 `hermes curator adopt` 后并入)

## 生产库访问通道(2026-08-15 实战)

- SSH: `root@202.95.1.135:12125`,密码在 `~/.ssh/deploy_pw`(12 位;`~/.ssh/askpass.sh` 内容=`cat ~/.ssh/deploy_pw`)
- ★Windows ssh 弹 GUI 密码框且**命令挂起等输入**(表现为"超时/中断")→ 必须 askpass 免弹框:
  ```bash
  export SSH_ASKPASS_REQUIRE=force SSH_ASKPASS="$(cygpath -w ~/.ssh/askpass.sh)" DISPLAY=:0
  ssh -p 12125 -o ConnectTimeout=20 -o StrictHostKeyChecking=no root@202.95.1.135 'bash -s' <<'EOF'
  ...远端命令...
  EOF
  ```
- 应用目录 `/www/tiktok`;DB 连接串在 `/www/tiktok/.env` 的 DATABASE_URL

## psql 连接坑

- ★DATABASE_URL 带 Prisma 参数(`?schema=public&connection_limit=15&pool_timeout=20`),psql 直连报 `invalid URI query parameter: "schema"` → 拆 PGPASSWORD + 单机参数:
  ```bash
  DBURL=$(grep -oE 'DATABASE_URL="[^"]*"' /www/tiktok/.env | head -1 | sed 's/DATABASE_URL=//;s/^"//;s/"$//')
  PGPASSWORD=$(echo "$DBURL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
  psql -h 127.0.0.1 -U qavlixor -d qavlixor_prod -f /tmp/x.sql
  ```
- 复杂 SQL 写文件 + `psql -f`(heredoc/内嵌引号会被吃);表名大小写敏感要双引号

## 价格数据模型

- `Product` 表**无 price 列**;价格在 `ProductVariant`(`productId`+`sku` 组合唯一,`price` numeric(65,30),`stockQuantity`),列表价取 variants 值
- 商品变体查询:
  ```sql
  SELECT s."name" AS store, p."id", p."title", pv."sku", pv."price"
  FROM "Product" p JOIN "Store" s ON s."id"=p."storeId"
  JOIN "ProductVariant" pv ON pv."productId"=p."id"
  WHERE p."title" LIKE 'Bambu Lab%' AND p."status"='published';
  ```

## SKU 价格异常审计(多 SKU 被统一成末位 SKU 价)

- 异常模式:多 SKU 商品全部变体价格 = **最后一个 SKU 的价格**(上架后某次编辑覆盖 SKU 列表所致;2026-08-15 实测 P2S/X2D/PLA Pure/TPU 85A 中招)
- 审计流程:
  1. 导出全量变体:`psql -A -t -F '|' -c "..."`(注意 title/sku 可能含 `|`,本地解析用 `split("|", 4)` 或从末尾取 sku/price)
  2. 与上架 Excel「SKU明细」列(`规格|编码|价格|库存;...`)建基准 dict,sku **去掉店铺后缀 `-lv`/`-nx` 再匹配**
  3. 全量比对 `abs(price-baseline)>0.001` 列出不一致;Amazon 采集店(Nova 等,数字长 sku)不在基准内,跳过
- 修正:事务 UPDATE 逐行回正确值 + **必须 bump CatalogVersion**(否则 4 实例目录缓存不刷新,买家端看不到新价):
  ```sql
  INSERT INTO "CatalogVersion" (id, version, "updatedAt") VALUES (1,1,now())
  ON CONFLICT (id) DO UPDATE SET version="CatalogVersion".version+1, "updatedAt"=now();
  ```
  (`CATALOG_VERSION_ID=1` 固定单行;psql 直插必须带 `updatedAt` 否则 not-null 报错)
- 改完重导全量复验(应为 0 差异)再交付

## 已知坑

- `/www/tiktok/work/local-db.json` 镜像可能停更(2026-08-10 后无更新),`productOperations` 历史追溯不可靠——定位错价靠"全库对比基准",别指望操作日志
- 上架工具(桌面 `qavlixor_auto_shelf.py` build_payload)逐 SKU 解析 `parts[2]` 价格,本身无统一价格逻辑;服务端 `syncProductToPrisma` 也逐条 upsert——新品上架不会触发该异常,错价只出现在存量被编辑覆盖
