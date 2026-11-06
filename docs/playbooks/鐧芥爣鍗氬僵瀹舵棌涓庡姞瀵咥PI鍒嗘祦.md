---
title: "白标博彩家族与加密API分流.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# 白标博彩家族与加密API分流.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/gambling-family-router/SKILL.md`
- `/root/.hermes/skills/security/whitelabel-gambling-pentest/SKILL.md`

## 汇总内容

### gambling-family-router

来源：`/root/.hermes/skills/security/gambling-family-router/SKILL.md`

# 白标盘口家族路由（Cursor Skill · score≥5 实战级）

> **定位**：这是博彩/白标站的 **入口路由卡**——侦察指纹后精确分发到对应家族专卡。
> 自身不做深度利用，但提供完整的指纹识别命令、自动分发决策树和 L1 级侦察手法。
> 深度打击交给下游专卡。

---

## 0. 硬闸

1. 目标必须在 `config/scope.company.json`，否则先 `scope_expand --grant`。
2. 禁止无域 FOFA 全网扫；FOFA 查询必须 `host=` / `ip=` / `domain=`。
3. 识别家族后 **立刻 Read 下游卡并打**，禁止「已识别」后结案。
4. 资金闭环阴性后再打宝塔/Actuator。
5. 叠层不并卡：入口 + 家族细则 + 横切手法可同案同打，禁止合并不同协议。

---

## 1. 立即打开（真源）

1. `docs/playbooks/白标博彩家族与加密API分流.md` ← 完整家族指纹矩阵
2. `docs/playbooks/博彩站打法分流手法.md` ← 资金/代理主线
3. `docs/playbooks/博彩站完整杀伤链.md` ← 全链总览
4. `docs/playbooks/博彩站API协议破解链.md` ← 加密 API 通用
5. `docs/playbooks/博彩站代理社工+后台接管杀伤链.md` ← 社工补充
6. `docs/learning/extended-pack/INDEX.md` §1 ← 家族卡全表

---

## 2. 指纹识别命令（Phase-0 侦察）

### 2.1 一键指纹扫描

```bash
# 本库家族探针：每族自己的路径/头/签名面（认到哪族打哪族）
python3 tools/ops/gambling_family_probe.py --list
python3 tools/ops/gambling_family_probe.py --family 1z --base https://授权站 --case <案卷>

# 一键战役菜单（认不出族时）
python3 tools/ops/auto_campaign.py plan -d <授权域名> --case <案卷>

# 芋道专项探针（/app-api / /admin-api / app-config.js）
python3 tools/ops/yudao_appapi_probe.py -u https://授权站 --case <案卷>

# 通用突击（无明确栈时先用，S1-S8 黑盒）
python3 tools/ops/strike_probe.py --base https://授权站 --case <案卷>
```

### 2.2 手动指纹 curl 命令集

```bash
# ── 芋道指纹 ──
curl -sk "https://TARGET/app-api/member/auth/sms-login" -o /dev/null -w '%{http_code}'
# 200/405 → 芋道；配合 app-config.js
curl -sk "https://TARGET/app-config.js" | head -20
# 看 VITE_APP_TENANT_ENABLE / VITE_DEV_SERVER_URL

# ── 1Z / qpuserapi 指纹 ──
curl -sk "https://TARGET/qpuserapi/" -o /dev/null -w '%{http_code}'
curl -sk "https://TARGET/api/game/list" -o /dev/null -w '%{http_code}'
# 200 + JSON → 1Z 族

# ── 鼎艺 / verifyKey 指纹 ──
curl -sk "https://TARGET/api/v1/user/verifyKey" -X POST \
  -H "Content-Type: application/json" -d '{}' | head -c 200
# "code":0 / 字段含 verifyKey → 鼎艺；绑卡才能充也是线索

# ── GoFun / AKS 指纹 ──
curl -sk "https://TARGET/" | grep -oP 'VITE_HTTP_SINGKETY|VITE_APP_API_BASE'
# 有 SINGKETY → GoFun 族；Vite 密钥在 JS 里

# ── MM8 / GEN Rails 指纹 ──
curl -sk -I "https://TARGET/" | grep -i 'x-powered-by\|server'
curl -sk "https://TARGET/api/v1/games" -o /dev/null -w '%{http_code}'
# Rails 痕迹 + /api/v1/ → MM8/GEN

# ── LSM / lsmview 指纹 ──
curl -sk "https://TARGET/" | grep -oP 'lsmview|mclsm|LSM'
# 命中 → LSM 家族，立刻转 lsm-mclsm-gambling-pentest

# ── 巴西 tRPC 指纹 ──
curl -sk "https://TARGET/api/trpc/health" -o /dev/null -w '%{http_code}'
curl -sk "https://TARGET/" | grep -oP 'trpc|daanrox'
# tRPC 端点 → 巴西族；有 Daanrox/PHP → daanrox-br-gambling-pentest

# ── 网狐 QP 指纹 ──
curl -sk "https://TARGET/" | grep -oiP 'QPAccountsDB|protocal=167|qpuserapi'
# 命中 → 网狐四库，走 whgame-tp5-login-sqli

# ── Qzino 指纹 ──
curl -sk "https://TARGET/api.html" -o /dev/null -w '%{http_code}'
# 200 + 文档页 → Qzino，走 telegram-tma-gambling

# ── 独角 Next 指纹 ──
curl -sk "https://TARGET/dj.svg" -o /dev/null -w '%{http_code}'
curl -sk "https://TARGET/" | grep -oP 'use_balance|auth-defaults'
# 命中 → 独角，走 dujiao-next-1yuan-pay

# ── 瓦力 XOR 指纹 ──
curl -sk "https://TARGET/trial.do" -o /dev/null -w '%{http_code}'
# 200 → 瓦力，走 wali-tg-tma-pentest

# ── 666Bet 指纹 ──
curl -sk "https://TARGET/" | grep -oP 'suid|666bet'
# 命中 → 走 666bet-tma-pentest

# ── kk8 指纹 ──
curl -sk "https://TARGET/gc?c=test" -o /dev/null -w '%{http_code}'
# 200 → kk8，走 kk8-tma-platform-pentest + tma-encrypted-api-reversal

# ── PG Soft launcher 指纹 ──
curl -sk "https://TARGET/" | grep -oP 'keys=|pgsoft|pg-soft'
# 命中 → PG launcher，走 pg-soft-launcher-pentest

# ── 通用 TMA / Telegram Mini App 指纹 ──
curl -sk "https://TARGET/" | grep -oP 'tma|telegram|miniapp|initData'
```

### 2.3 前端 JS 指纹抓取

```bash
# 拉首页 JS 看框架与密钥
curl -sk "https://TARGET/" \
  | grep -oP 'src="[^"]*\.js"' \
  | head -5 \
  | while read -r src; do
      url=$(echo "$src" | grep -oP '"[^"]*"' | tr -d '"')
      echo "=== $url ==="
      curl -sk "https://TARGET${url}" | grep -oiP \
        'SINGKETY|sk_encrypt|AES|RSA|signKey|secretKey|TENANT|qpuserapi|verifyKey|lsmview' \
        | head -5
    done
```

---

## 3. 自动分发决策树

```
收到授权博彩站 URL
│
├─ auto_campaign.py plan → 识别栈
│
├─ /app-api 或 /app-config.js 存在？
│   ├─ TENANT + admin-api → 芋道 → yudao-appapi-pentest
│   ├─ sk_encrypt → encrypted-api-spa（密钥在 JS）
│   └─ mock-enable → yudao-daifu-mock-file-rce
│
├─ /api.html 200？ → Qzino → telegram-tma-gambling
│
├─ /qpuserapi 或 QPAccountsDB？ → 1Z → 1z-gambling-family-pentest
│
├─ verifyKey / 绑卡才能充？ → 鼎艺 → dingyi-whitelabel-gambling-pentest
│   └─ 横切：gambling-deposit-chain-pentest
│
├─ VITE_HTTP_SINGKETY？ → GoFun/AKS → aks-gofun-gamb

…（截断，全文见来源卡）

### whitelabel-gambling-pentest

来源：`/root/.hermes/skills/security/whitelabel-gambling-pentest/SKILL.md`

# 白标博彩平台渗透（多家族通用）

<!-- MERGED-INDEX:START -->
## 归档子卡（已合并 125 张）

- 索引：`references/index.md`
- 加载：`skill_view(name='whitelabel-gambling-pentest', file_path='references/legacy/<name>.md')`
- 子卡脚本/字典仍在原目录（索引里给了绝对路径），可直接 `read_file` / `terminal`。
- **先按本卡判据决策**；本卡不够时才展开对应子卡，不要一次全读。
<!-- MERGED-INDEX:END -->


## 触发条件
- 目标为多租户白标博彩/赌场平台，**尚未认到专族**（1Z/曼巴/鼎艺/芋道/Qzino/网狐等）。
- 土耳其 eBetLab 系: `site-configs/{id}.json`、`play.bonuseblb.com`、主域 CF Managed Challenge、镜像 `{brand}{NNN}.com`
- 前端 Next.js + Laravel `/api/*` 后端

**LSM 立刻交出**：域名/JS 出现 `lsmview.com` / `mclsm.com` / `lsmplay.com` / `cdnrc.com` / `{brand}.l{3-7}t.lsmview.com` → 停本卡，改读 **`lsm-mclsm-gambling-pentest`**（S3 公开桶与租户表以那张为准）。本卡只保留 eBetLab + 「认不出的多租户」通用面。

## 核心认知（两家族共通）
1. **平台=多租户**，一个后端 50+ 白标客户；前端同构建（chunk hash 相同）→ 同 API 端点 → **一个租户验证的漏洞全平台通用**。
2. **前端是壳**：Vercel/Next.js 站点的真实资产在 JS chunk 里 —— `grep -o 'https://[a-z0-9.-]*'` 找 API 域，`grep -o '"/api/[a-z-]*"'` 找端点表。静态 CDN（`l{3-7}.cdnrc.com`）常 CF 放行 `/_next/static/`，可直接 curl。
3. **对象存储是金矿**：公开可列的 S3 桶 = 财务导出/银行凭条/APK 全家桶，变现核心。
4. 租户隔离靠 Host；`website-settings?sub_domain=` 类端点未授权 = 全租户 merchant/agent 代码枚举。

## 家族一: eBetLab（土耳其）— 要点
- 主域 CF 铁墙 → 先打镜像域名；`/favicon.ico` 常漏放行返回 SPA HTML → 解析 RSC payload 拿 `w_id/site_id/secret`。
- 未授权 API: `/api/debits/win`（中奖流水）、`/api/stats`（用户枚举）、`/api/games2/sportsbook`（游客 token）。
- 注册卡点: `sms_required: true`，找 `sms_required:false` 租户；别死磕注册，先打未授权面。
- 同技能 default profile 有 eBetLab 细节（本 bot3 副本为全量内联版）。

## 家族二: LSM99/mclsm（泰国）— 已移交
完整链以 **`lsm-mclsm-gambling-pentest`** 为准（个案附件未入库，原 references/lsm99-mclsm-family.md）。下面只留对照摘要：
1. FOFA `domain="lsmview.com"` → 全租户子域；`domain="mclsm.com"` → 后端服务清单（api/accounting/audit/partner/report/promotion/rebate/payment/affiliate/blacklist.service.mclsm.com，全在 34.87.172.253）。
2. JS chunks → `api.mclsm.com`（Laravel PHP 8.1.34）。
3. **S3 桶公开读写**: `?list-type=2` 枚举 40,000 对象 → `exports/financial_deposits/{merchantId}/*.json`（存款流水，28K 条/13.2M THB）+ `account/slip/`（凭条，文件名带玩家实名+银行账号）+ `file_app_apk/`。写验证: PUT 探针→GET→DELETE。**桶内已有 FORCEINJECT 伪造流水 = 对账污染链被前攻击者验证**。
4. 未授权: `website-settings?sub_domain=`（租户枚举）、`slide-images`、`banks`、`system-settings`、`checklock`。
5. 用户枚举: `auth/login` + `forgot-password`（参数 `subdomain`）→ "This username is not found on the website."
6. APK（Flutter）: `strings libapp.so | grep https` → `rcson.com/configs/lsm99ai.json` → 钱包域 `gamev2.lsm99ai.net` + whitelist。

## 硬墙（已试，别重复）
- **Filament 后台**（accounting/backoffice, v3.2.110）: 传统 POST → 405（只走 Livewire，必须浏览器填表单）；错误 `ข้อมูลนี้ไม่ตรงกับบันทึกในระบบ` = 凭据不匹配（无枚举）；无注册/重置入口；弱口令多组不中 → 别 curl 爆破，直接用浏览器，几组不中就换面。
- **Horizon**: 401 "Invalid credentials."，token 认证，basic auth 字典无效。
- **注册 marketing 墙**: check-register 反查 phone 是否已存在（新号 → "Marketing not found"），OTP 6 位 SMS 服务端真校验 + 429 → 注册路别死磕。
- **微服务 API**（*.service.mclsm.com /api/*）: 外部全 404，内部调用。

## 交付
- 主成果: 财务流水 TSV（gz 打包）+ Top 用户 TSV + 租户枚举 TSV + S3 目录清单 + MD 报告，MEDIA 逐个发。
- 金额字段带逗号（`1,950.00`），解析前 `replace(",","")`。
- 报告含: 资产地图、漏洞分级、数据统计、未突破面记录。

## 真源

- 手法：`docs/playbooks/白标博彩家族与加密API分流.md`
- 工具：`python3 tools/ops/gambling_family_probe.py --family whitelabel --base https://授权站 --case <案卷>`
