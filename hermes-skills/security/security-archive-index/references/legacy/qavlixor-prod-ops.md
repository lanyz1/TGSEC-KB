<!-- archived from /root/.hermes/skills/security/qavlixor-prod-ops/SKILL.md on 2026-10-21 -->

---
name: qavlixor-prod-ops
description: >-
  测绘引擎·用 when qavlixor 生产部署/查库/验证。SSH+psql+部署+产物验证全套命令与坑位。
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/qavlixor-prod-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/qavlixor-prod-ops/…')`，不要相对 `references/legacy/` 解析。

# qavlixor-prod-ops（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-prod-ops/`

溯源（仅标记）：`hermes/devops`

---

# qavlixor 生产运维与部署验证

## 连接信息
- SSH: `root@202.95.1.135:12125`(密码见 `%LOCALAPPDATA%\Temp\_run_q_*.py` 明文;勿禁 root 密码)
- 应用目录: `/www/tiktok`(**不是** /root/qavlixor)
- 构建产物: `/www/tiktok/.next-build`(**不是** .next;deploy 用 .next-build 再切)
- 端口: 4 实例 3000-3003(CF 回源 localhost:3003)
- DB: psql 直连 qavlixor_prod(DATABASE_URL 在 /www/tiktok/.env)

## 部署流程(标准三步)
```bash
cd "/d/跨境商城/qavlixor-marketplace"
npx tsc --noEmit 2>&1 | grep -vE "npm warn|npm notice" | grep -vE "TS2307|TS2802|TS18028|library.d.ts|next/dist" | head -3
git add -A && git commit -m "..." --quiet
unset PYTHONPATH && "$LOCALAPPDATA/Temp/_qav_env/Scripts/python.exe" scripts/deploy.py "说明" 2>&1 | tail -3
```

## 生产验证三步(部署后必做)
1. **BUILD_ID 时间**: `ls -la --time-style=+%m-%d_%H:%M /www/tiktok/.next-build/BUILD_ID` 确认是最新构建
2. **产物 grep**: 在 /www/tiktok/.next-build/server/chunks/*.js 搜新代码特征字符串(注释不进产物,搜文案/函数名;本地函数会被压缩改名,用中文文案或 export 名)
3. **SSR 直出**: 服务器本地 curl(绕 CF 缓存): `curl -s -b cookie http://localhost:3003/页面` 或 grep 产物

## psql 查库(铁律)
- **heredoc/内嵌 SQL 引号会被吃**("Order" 变 Order)→ **必须 SQL 文件方式**:
  ```python
  sftp 写 /tmp/x.sql → PGPASSWORD='..' psql -h 127.0.0.1 -U qavlixor -d <db> -f /tmp/x.sql
  ```
- 表名大小写敏感: `"Order"`/`"NotificationMessage"`/`"ProductVariant"` 都要双引号
- 密码: 从 /www/tiktok/.env 的 DATABASE_URL 正则提取

## 已知坑
- **★改价格必须双表同步**:页面/SSR 价格优先读 `ProductOperationMetric."skuItemsJson"`(上架快照),只改 `ProductVariant.price` 页面不变!两表都要改,再 bump CatalogVersion(psql: `INSERT INTO "CatalogVersion"(id,version,"updatedAt") VALUES(1,1,now()) ON CONFLICT(id) DO UPDATE SET version="CatalogVersion".version+1,"updatedAt"=now()`)。jsonb 改价: `jsonb_agg(CASE WHEN item->>'sku'='x' THEN item||'{"price":N}'::jsonb ELSE item END) FROM jsonb_array_elements("skuItemsJson") item`
- CF 缓存旧版 → 外部 curl/浏览器验证不可靠,用服务器本地 curl 或产物 grep
- 管理端/admin 登录密码非种子(生产改过),测试用 <EMAIL-REDACTED> / QaTest!2026(卖家)
- db push --accept-data-loss 静默失败 → 加列用 psql ALTER TABLE
- 卖家登录 API 需 `role:"seller"` 参数
- 部署耗时 88-140s,等 "✅ 部署完成"
