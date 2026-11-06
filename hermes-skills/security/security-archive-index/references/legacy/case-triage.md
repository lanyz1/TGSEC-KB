<!-- archived from /root/.hermes/skills/security/case-triage/SKILL.md on 2026-10-21 -->

---
name: case-triage
description: >-
 案卷可打性分级 A/B/C、复工条件、当前攻击手法索引。
 在用户提到 triage、定级、瓶颈、进不去、冷冻、复工条件、
 手法索引、session_import、很多站半吊子时使用。
 开新案或暂停后整理案卷时也应主动套用。
---

> 归档卡：原目录 `/root/.hermes/skills/security/case-triage`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/case-triage/…')`，不要相对 `references/legacy/` 解析。

# 案卷 Triage（A/B/C）

## 真源

| 内容 | 路径 |
|------|------|
| Playbook + 手法索引 | `docs/playbooks/案卷Triage与手法索引.md` |
| 模板 | `exports/bot-recovery/_templates/TRIAGE.md` |
| CLI | `tools/ops/case_triage.py` |
| 长时多假设账本 | `假设驱动作业账本手法.md` · `case_ledger.py` |
| 会话校验 | `tools/ops/session_import.py` |

## 强制行为

1. 新授权站开案后 **先 triage**（或用户说瓶颈/进不去时补做），写入 `TRIAGE.md` + `triage.json` + `测绘/object_matrix.md`。 
2. 主级只标 **A / B / C** 之一；B/C 必须有可勾选的 **复工条件**。 
3. 同时 ACTIVE 的 A 级建议 ≤ 2；C 级停进攻，只改文档。 
4. CF / 会员站缺会话时：先 `session_import`，JWT 校验失败则 **禁止** 假装已登录继续打。 
5. 选手法时查 Playbook §3 索引；**有身份先填对象矩阵**，业务专用 Skill 只填格子；专卡阴性禁止直接结案。  
   `/actuator/heapdump` 或案卷已有 hprof → 立刻 `heap_cred_scan.py`，不等用户说蓝鸟。 
6. 案卷根状态文件：`STATUS_<案卷>.md` 正文 + `STATUS.md` 软链（`init` / `migrate-status-names`）；子目录过程 STATUS 不强制改名。
7. 结束、部分成功或暂停案卷必须建脱敏 `RETROSPECTIVE.md` + `retrospective.json`；不得写入 Token、Cookie、密钥或原始响应。矩阵仍有「未测」时 `set --status PAUSED` 会警告。

## 最短命令

```bash
python3 tools/ops/case_triage.py init --case <站_日期> --url https://目标 --grade B
python3 tools/ops/object_matrix.py next --case <站_日期>
python3 tools/ops/object_matrix.py check --case <站_日期> --strict
python3 tools/ops/case_triage.py set --case <站_日期> --grade B --status PAUSED \
 --resume "session_pipeline 通过且 session_alive" \
 --technique payment-callback-forgery
python3 tools/ops/case_triage.py board --print
python3 tools/ops/case_triage.py retrospect init --case <站_日期> --outcome PAUSED
python3 tools/ops/case_triage.py recommend --case <站_日期>

python3 tools/ops/session_pipeline.py \
 --domain 目标.com --case <案卷> --require-session --require-cf \
 --input <cookies.json>

python3 tools/ops/pay_matrix.py \
 --base https://目标.com --handles Epay,TokenPay \
 --trade-no <oid> --money 10 --pay-url '<跳转URL>' \
 --site-scope config/scope_sites/scope.<站>.json --case <案卷>
```

主站链发现的中转域：**静默扩权**，不要再问用户「是否写入 scope」。

CF 站：`cf_session.py capture`（有头）→ `consume` / `session_pipeline`（无头）。 
源站：`origin_recon.py`。ACG 站：`tools/acg-faka/bin/acg_probe.py`。 
收工汇编：`case_report.py --case <案卷>` → `DRAFT_REPORT.md` + `CHAIN.mmd`。  
结案前：`evidence_gate.py --from-status` + `object_matrix.py check --strict`（手法 `编解码对照与证据闸手法.md`）。

## 与其它 Skill

- 盘口 IDOR 阴 → `ato_reset_withdraw_probe.py`（任意 code + BOLA + 提现三件套，自控号）
- TG `main.wasm` / 掩码票 → `tg-cloud-panel` 第四族
- 假支付 → `payment-callback-forgery` + `pay_matrix.py` 
- USDT 共享收款/绑定归属 → `usdt-deposit-attribution-hijack` + `usdt_attr_hijack.py` 
- FastAdmin 代付/卡商 → `fastadmin-daifu-pentest`（part 拖树；multi money ≠ 结算） 
- GVA 管理面静默提权 → `ginvue-admin-stealth-takeover`（勿默认 resetPassword） 
- 硬编码 Token+CF-IP 加款 → `hardcoded-token-cfip-fund` 
- TG bot 管理面越权/webhook → `tg-bot-webhook-hijack`（getMe/列 webhook 直接做；`--set-webhook` 截原通知先问） 
- 白盒密钥命中 → `deepaudit-code-audit`（会提示回灌假支付） 
- 通用收集 → `nine-stage-router` 
- 用户「暂停」→ 停进攻；仍可更新 Triage/STATUS / board 

---

## 案卷生命周期完整流程

### 新建案卷

```bash
# 1. 新站写入 scope（禁止整文件改写 company.json）
python3 tools/ops/scope_expand.py \
 --grant <域名> --case <站_日期> --note "用户授权"

# 2. 初始化案卷（triage init）
python3 tools/ops/case_triage.py init \
 --case <站_日期> --url https://<目标> --grade B

# 3. 初始化对象矩阵
python3 tools/ops/object_matrix.py next --case <站_日期>

# 4. 查看当前 board（所有案卷状态总览）
python3 tools/ops/case_triage.py board --print
```

### 案卷推进

```bash
# 更新等级/状态/复工条件
python3 tools/ops/case_triage.py set \
 --case <站_日期> --grade A --status ACTIVE \
 --technique auth-brute

# 推荐下一步手法
python3 tools/ops/case_triage.py recommend --case <站_日期>

# 检查矩阵是否有未测格（阳性案卷结案前必查）
python3 tools/ops/object_matrix.py check --case <站_日期> --strict
```

### 暂停/结案

```bash
# 暂停（记录复工条件）
python3 tools/ops/case_triage.py set \
 --case <站_日期> --status PAUSED \
 --resume "session_pipeline 通过且 session_alive"

# 生成脱敏回顾（结案前必做）
python3 tools/ops/case_triage.py retrospect init \
 --case <站_日期> --outcome PAUSED

# 生成报告草稿
python3 tools/ops/case_report.py --case <站_日期>
# 产物: exports/bot-recovery/<案卷>/DRAFT_REPORT.md + CHAIN.mmd
```

### 技术面穷尽后的手法决策树

| 情况 | 下一步 |
|------|--------|
| 有弱口令/后台 | `auth-brute` → 填矩阵 |
| 有支付跳转 | `pay_matrix` → 假支付 |
| 有 JWT token | `api-auth-and-jwt-abuse` |
| CF/会员站 | `session_pipeline` → `cf_session.py capture` |
| 有 SSRF | `cloud-metadata-harvesting` + `echo-ssrf-internal-scanning` |
| 中间件暴露 | `middleware-unauth` |
| WP 站 | `wp-shell-drop-hunt` + `auth-brute` |
| API 文档泄露 | `api-param-name-discovery` + `core-web-vuln-kit` |
| 技术面穷尽 | `tg-account-library`（盯客服） |
