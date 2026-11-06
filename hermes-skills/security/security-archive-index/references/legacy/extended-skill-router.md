<!-- archived from /root/.hermes/skills/security/extended-skill-router/SKILL.md on 2026-10-21 -->

---
name: extended-skill-router
description: >-
 路由到 docs/learning/extended-pack 的 120 张白标/家族业务卡（芋道TMA、Qzino、
 1Z/曼巴/鼎艺、加密网关、TG系统选择云控、易支付后台、FastAdmin代付）。
 用户提到白标盘口、家族站、TMA、sk_encrypt、app-config.js、支付管理中心、
 FastAdmin、/sh.php、/ks.php、part/index、shop_hq、GT filter、
 或问「扩展包有没有」时使用。
 假支付/Actuator/GVA/ACG/Sticker云控仍优先对应专用 Skill。
---

> 归档卡：原目录 `/root/.hermes/skills/security/extended-skill-router`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/extended-skill-router/…')`，不要相对 `references/legacy/` 解析。

# 扩展技能包路由（测绘引擎）

## 本仓探针

```bash
python3 tools/ops/pack_surface_probe.py drive --name <旁支卡> --case <案>
```

L2=挂号落到本仓 SKILL.md。证据进案卷 `测绘/`。

## 真源

| 内容 | 路径 |
|------|------|
| 总览 | `docs/learning/extended-pack/README.md` |
| 作业面索引 | `docs/learning/extended-pack/INDEX.md` |
| 卡全文 | `docs/learning/extended-pack/skills/<name>/SKILL.md` |
| 分流手册 | `docs/playbooks/白标博彩家族与加密API分流.md` |
| 导入清单 | `docs/learning/extended-pack/IMPORT.json` |

## 强制优先级

1. `config/scope*.json`
2. 业务专用：假支付 / ACG / PocketBase / GVA / Actuator / `tg-cloud-panel`（Sticker/Fernet）
3. 本包家族卡（认族后 Read 对应 `SKILL.md` 并执行）
4. 九阶段通用洞（`nine-stage`）
5. 广谱扫描

## 关键词 → 先读哪个

| 用户说法 | 先打开 |
|----------|--------|
| 白标 / 家族站 / 认不出哪套盘口 | **`白标博彩家族与加密API分流.md`** + `gambling-family-router` |
| 芋道 / `/app-api` / `app-config.js` / 世博 TMA | **`yudao-appapi-pentest`** |
| Qzino / `/api.html` / Mini App 赌 bot | **`telegram-tma-gambling`** |
| `sk_encrypt.json` / `/app-api/encrypt` | **`encrypted-api-spa`** |
| 直读失败、key 绑 token、ATO | **`account-takeover-chain`** |
| 「系统选择」`/tgcloud_pc` / OSS STS | 扩展包 `tg-cloud-control-pentest`（不是 feijikong 那套） |
| JWT `your_secret_key` / `/proxy/list` / `/admin/users` / Session ZIP | `tg-cloud-panel` 认族 → `jwt-bypass-pentest` + `rbac-bypass-authz`（第三族，勿打 OSS/Fernet） |
| 支付管理中心 / `admin_login.lock` | 扩展包 `epay-admin-pentest` + 假支付矩阵 |
| FastAdmin 代付 / `/sh.php` `/ks.php` / `part/index` | **`fastadmin-daifu-pentest`**（勿与彩虹易支付混） |
| FastAdmin Shop / `shop_hq` / GT filter / 跨商户 tdata | **`fastadmin-shop-tenant-bola`**（勿与代付、Sticker 混） |
| 号库 / 投递 session / 清库 | **`tg-account-library`** |
| 盯客服回复 / 代理社工推进 | **`tg-account-library`** |
| 扩展包齐不齐 | `IMPORT.json` + `INDEX.md` |

## 行为

- 读完卡给出**可执行下一步**（命令 + `$CASE`）。 
- 号库/投递/社工走 `tg-account-library` / `tg-account-library`（根目录 `_tg_accounts/`，不要 `/opt/data`）。 
- 不把 C2 / 免杀当本库命令。 
- 命中密钥或未授权读 → 立刻验证，不要只记指纹。
- 工具：`python3 tools/ops/auto_campaign.py --help`
