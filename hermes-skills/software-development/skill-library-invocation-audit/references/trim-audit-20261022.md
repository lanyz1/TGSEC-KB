# 精简/裁卡审计（2026-10-22）

触发：老板问「那能精简什么用不到的」。这是**删卡决策**，不是检索体检；答错的代价是把长尾砍掉。

## 结论先行（实测数字）

| 桶 | 内容 | 量 | 依据 |
|---|---|---|---|
| 零损失可删 | 32 张 `redteam-*-detail-pack` + `laravel-app-pentest` | 33 张 / 379KB | 模板样板、0 refs、0 使用、被更全的卡覆盖 |
| 可停用（不删） | `apple-notes`/`apple-reminders`/`findmy`/`imessage`/`sdlc-review`/`teams-meeting-pipeline` | 6 张 / 157B 常驻 | enabled 且 44 天零使用 |
| 纯磁盘（可再生） | 旧周快照 70MB + `arsenal.db.bak-*` 170MB + `findcache.pkl` 49MB + ledger 11MB | ≈300MB | 快照/缓存/迁移备份 |
| 有体积但别整删 | `72stack-sec/references/h1-reports` 46MB/3,035 份 | 46MB | 卡本体还有 payloader+playbook |
| 不能删 | 1,799 张 disabled 长尾（其中 903 张只有 SKILL.md） | — | 98.76% 可达，删了掉能力 |

合计可回收 ≈345MB、-33 张卡（2178 → 2145）。

## 为什么 `use_count=0` 不能当依据

- 全库 1,841/2,178 张计数为 0（84.5%）。
- 其中 1,799 张是 `disabled` 归档卡：加载时记在目录卡上，自身永远 0。
- enabled 379 张里零使用 79 张，73 张是当天新吸收（<7d），超 7 天仍零使用仅 6 张。
- `query.log` 2026-10-22 14:31 才开始记录，本会话时只有 1.3KB。真实「调不到」要按检索命中统计，不是看计数。

## 模板填充卡检测（最快的一刀）

```bash
grep -rl "只用于帮助代理判断当前任务属于什么安全测试领域" --include=SKILL.md . \
  | sed 's#^\./##;s#/SKILL.md##'
```

实测 31–32 张 `redteam-*-detail-pack`（ad/api/auth/cache-poison/clickjacking/cloud/cmdi/container/cors/crypto/csrf/deserialize/evasion/file/injection/logic/mobile/network/open-redirect/payload/postex/reverse/sqli/ssrf/ssti/xss/xxe/recon/web/code-audit/subdomain-takeover）。

特征：
- 每张 ~2.8–3.1KB，目录里只有 `SKILL.md`，零 references。
- 正文结构完全相同（Domain / Boundaries / Pivot Hints），`diff` 两卡只有域名词不同。
- 自述「本 skill 只用于帮助代理判断当前任务属于什么安全测试领域……它不是方法论教程，不提供固定攻击步骤」。
- 全部 disabled、use=0。

→ 零能力损失删除项。真正的打法在 `pentest-redteam`、各技术专卡、`campaign-router` 里。

## 重复判据（描述相似度会骗人）

| 对 | 描述 Jaccard | 正文 Jaccard | files | 判定 |
|---|---|---|---|---|
| `laravel-app-pentest` / `laravel-pentest` | 0.45 | 0.45 | 1 / 2 | 真重复，删前者 |
| `php-audit-pipeline` / `java-audit-pipeline` | 0.90 | 0.53 | 1 / 1 | 模板套壳，可合但要手工保语言细节 |
| `hunt-xss` / `hunt-idor` | 0.77 | 0.21 | 17 / 多 | 假重复，各有 full.md，不能删 |
| `spa-api-discovery` / `spa-backend-api-pentest` | — | 0.50 | 25 / 2 | 同题不同侧重，暂不合 |
| `apk-recon` / `reverse-skill` | — | 0.71 | 8 / 8，6 个文件 md5 相同 | 部分重复，各有独有 ref，暂不合 |

规则：描述 Jaccard ≥0.30 进候选 → 再看正文 Jaccard 与 `files/refs` 数 → 只有在「正文 ≥0.45 且一方无 refs / 是子集」时才判可删。

## 磁盘账（2026-10-22 实测）

```
skills 316MB = security 184MB + .curator_backups 109MB + 其他 23MB
  .curator_backups: 2.1M(09-22) 22M(09-29) 22M(10-06) 24M(10-13) 40M(10-20)
  security/72stack-sec 51MB (h1-reports 46MB / 3,035 文件)
  security/security-encyclopedia 11MB, security-archive-index 8.5MB
arsenal 579MB = arsenal.db 362MB + .bak 104+67MB + findcache.pkl 49MB
```

顺序：可再生字节（快照/bak/pkl/ledger）→ 模板卡 → 胖卡外搬 → 才考虑合并真重复。**别先动卡**。

## 报告模板（老板要的形状）

1. 一句话结论 + 先纠口径（`use_count=0` ≠ 用不到，给分档数字）。
2. 真能删：卡名/数量/KB/为什么零损失。
3. 纯磁盘：路径 + MB + 为什么可再生。
4. 看着像垃圾其实不能删：点名 + 证据（refs 数、可达率、口径偏差）。
5. 收尾一句「说删就备份→删→重建→过 gate」。不要问「要继续还是换目标」。
