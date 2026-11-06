# Suite 可发现性与 CASE 总索引（2026-09-20）

## 症状
用户：「本地是不是太多太杂了，AI 调不到每一个，比如实战报告。」

## 实测快照（security-suite）
- `domains/` 文件约 **18766**；MASTER 仍写「约 5200+ / 24 域」→ **过期**
- 实战：`case-lessons` ~52 文件 / 10 域；`case-reports` ~106 文件 / ~44 案子（结构正确）
- 噪声：`sinian-*` ~115 目录挤在 `src-methods/`；另有 `claude-red`/`aimy-*` 层
- ROUTING 只点少量老 case；发卡/钱包/博彩/TG 云控多数进不了关键词表
- Hermes `tgsec-suite` 只笼统提 `case-lessons/`，不枚举具体报告

## 根因（不是“报告丢了”）
1. 缺 **CASE 总索引** → AI 盲逛多域
2. 同目录噪声 → 通用方法论权重压过具体 case
3. MASTER/ROUTING 滞后
4. 0day/ctf 体量巨大淹没信号

## 轻量整理（推荐，等用户「开干」）
1. 新建 `domains/CASE-INDEX.md`：域名 | slug | 一句话 | case-lessons 路径 | case-reports 路径
2. 扩 `domains/recon/case-lessons/README.md` 为跨域入口
3. 更新 `MASTER.md` 文件数/域数（含 `wireless`）
4. `ROUTING.md` 加关键词：实战报告、发卡、钱包、博彩、TG云控、白标大厅 → 具体 case
5. 域 README 优先级：`case-lessons` ≥ `playbook-6000` ≥ `hunter-6000` ≥ `src-methods`（含 sinian）
6. 可选：`src-methods/sinian-*` → `src-methods/_vendor/sinian/`（降噪，不删）
7. 同步 Hermes `tgsec-suite` 指向 CASE-INDEX

## 吸收批（同日，已落地）
外层 Telegram zip → 内层两包：
- TGSEC-absorb-batch：已是 `domains/<face>/` → 按 ABSORB.md 铁则落位；冲突保留本地更丰富，更大源旁路 `.upstream-new`
- sinian 技能包：114 卡 → `domains/<face>/src-methods/sinian-<name>/`，禁止整包落 Hermes skill 目录
- 账本：`domains/FUSION-20260920-absorb.{md,json}`；新增约 519 文件 + wireless 域

## 用户偏好
- 「先告诉我」评估 → 等拍板再融/再整理；给档位选项（轻量/中量/先别动/整仓）
- 自述/融合说明只改 README+START；路由大改要点名
- 「能闭环」= CASE-INDEX + 矩阵闸门 + sync 备份出树 + 推 GitHub + `bootstrap --force`，不是只改本地 md

## 后续增量（同日）
- Cloudflare `security-audit-skill` → 轻量提炼进 `file-vulns/code-audit/cloudflare-security-audit/`（非整仓、不新建伞形）；见 `references/lightweight-methodology-distill.md`
