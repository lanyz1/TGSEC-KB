---
name: gambling-family-router
category: business-logic
priority: P1
description: >-
  白标盘口家族分流：1Z、曼巴、鼎艺、MM8/GEN、GoFun、LSM、巴西 tRPC、
  充值凭证链、聚合商 launcher、前端签名/加密 WS、网狐QP库/TP5登录盲注。
  用户提到白标、1Z、曼巴、鼎艺、GoFun、MM8、绑卡才能充、凭证上传、
  VITE_HTTP_SINGKETY、qpuserapi、网狐、QPAccountsDB、protocal=167、Machine 注入时使用。
  芋道/Qzino 走对应专卡；假支付矩阵仍优先 payment-callback-forgery；
  网狐四库+登录 Machine 盲注走 whgame-tp5-login-sqli。
metadata:
  tags:
    - gambling
    - whitelabel
    - family-router
    - tma
    - payment
    - crypto-api
    - yudao
    - 1z
    - dingyi
    - gofun
    - lsm
    - brazil-trpc
    - mm8
    - qzino
    - wallet
    - fingerprint
  score: 6
  version: "2.0"
  updated: "2026-09-04"
---

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
├─ VITE_HTTP_SINGKETY？ → GoFun/AKS → aks-gofun-gambling-pentest
│   └─ 横切：gambling-api-crypto-reversal + gambling-password-reset-ato
│
├─ lsmview / mclsm？ → LSM → lsm-mclsm-gambling-pentest
│
├─ /api/trpc？ → 巴西
│   ├─ Daanrox/PHP → daanrox-br-gambling-pentest
│   └─ 纯 tRPC → br-gambling-trpc-spa-pentest
│
├─ Rails + /api/v1/games？ → MM8/GEN → mm8bet-gen-whitelabel-pentest
│
├─ QPAccountsDB / protocal=167？ → 网狐 → whgame-tp5-login-sqli
│
├─ /trial.do？ → 瓦力 → wali-tg-tma-pentest
│
├─ suid / 666bet？ → 666bet-tma-pentest
│
├─ /gc?c= 200？ → kk8 → kk8-tma-platform-pentest
│
├─ /dj.svg 200 或 use_balance？ → 独角 → dujiao-next-1yuan-pay
│
├─ keys= / pgsoft？ → PG → pg-soft-launcher-pentest
│
├─ Nogle MPS 标记？ → nogle-mps-pentest
│
├─ wallet_id / 双路径资金 API？ → fund-edge-ops（横切）
│
├─ com.ugame.* APK / protobufjs/light + Beego / wss://server.* / LF Grupo？
│   → **ugame-boi-platform-pentest**（gameForward SSRF → admin 暴破 → WS 用户树）
│
├─ 多租户 / eBetLab / 认不出？ → whitelabel-gambling-pentest（兜底）
│
└─ 技术面穷尽？
    ├─ 社工客服/代理 → autonomous-social-engagement
    └─ 宝塔/Actuator → 对应专卡
```

---

## 4. 家族完整分发表

| 层 | 族 | 先开（主卡） | 细则 / 横切（不替代先开） |
|----|-----|------|---------------------------|
| 入口 | 芋道 `/app-config.js` `/app-api` | **`yudao-appapi-pentest`**（探针） | TMA/Web 旧名已并入；创世/世博补 `telegram-gambling-yudao-pentest`；只见 `sk_encrypt.json` → `encrypted-api-spa` |
| 入口 | 芋道代付 mock+file | **`yudao-daifu-mock-file-rce`** | `Bearer test1` → basePath=/；勿与 TMA 卡混 |
| 入口 | Qzino `/api.html` | `telegram-tma-gambling` | 勿套芋道信封 |
| 入口 | 瓦力 XOR / `trial.do` | `wali-tg-tma-pentest` | |
| 入口 | 666Bet `suid` | `666bet-tma-pentest` | |
| 入口 | Laravel TMA `X-Device-Id` | `laravel-gambling-tma-pentest` | |
| 入口 | kk8 `GET /gc?c=` | `kk8-tma-platform-pentest` | 认族后再叠 `tma-encrypted-api-reversal`（UMI 无签信封） |
| 家族 | 1Z / qpuserapi | `1z-gambling-family-pentest` | |
| 家族 | 鼎艺 / verifyKey / 绑卡 | `dingyi-whitelabel-gambling-pentest` | **横切** `gambling-deposit-chain-pentest` |
| 家族 | 曼巴 / HSBox | `m8-manba-gambling-pentest` / `m9-hsbox-gambling-pentest` | |
| 家族 | GoFun / Vite 密钥 | `aks-gofun-gambling-pentest` | **横切** `gambling-api-crypto-reversal`；重置口 `gambling-password-reset-ato` |
| 家族 | MM8 / GEN Rails | `mm8bet-gen-whitelabel-pentest` | |
| 家族 | LSM / lsmview / mclsm | **`lsm-mclsm-gambling-pentest`** | 勿停在通用白标卡 |
| 家族 | Nogle MPS | `nogle-mps-pentest` | |
| 家族 | 巴西 tRPC | 有 Daanrox/PHP 后台 → `daanrox-br-gambling-pentest` | 只有 tRPC 壳 → `br-gambling-trpc-spa-pentest` |
| 家族 | 网狐 QP / Machine | `whgame-tp5-login-sqli` | 探表必须 SELECT 1 |
| 家族 | 独角 Next | `dujiao-next-1yuan-pay` | `/dj.svg` / `use_balance` / 1 元购 |
| 家族 | ACG 共享货 | `acg-faka` | 异次元发卡；含 callback/USER_SESSION |
| 厂商 | PG `keys=` 启动器 | `pg-soft-launcher-pentest` | 会话 `ot`+`ops` → `pg-operator-session-chain`（两段链，不并） |
| 横切 | 加密 `?c=` 未知族 | `gambling-saas-pentest-workflow` | |
| 横切 | `wallet_id` / 展示层地址 / 双路径 / 提款 saga | **`fund-edge-ops`** | 假付/归属仍并行；uid 阴必须换键 |
| 横切 | 赔率/开奖 WS | `gambling-platform-odds-audit` / `pc28-odds-ws-intel` | |
| 横切 | USDT 共享收款 | `usdt-deposit-attribution-hijack` | 假付硬化仍并行 |
| 横切 | 假支付回调 | `payment-callback-forgery` | 通用签名可控/金额可改 |
| 横切 | 支付栈旁站取钥 | `docs/playbooks/支付栈旁站弱口取钥回灌手法.md` | 禁止爆破 key |
| 侦察 | FOFA 找 TMA 壳 | `tma-web-asset-discovery` | 不是打法卡 |
| 认不出 | 多租户 / eBetLab | `whitelabel-gambling-pentest` | `lsmview`/`mclsm` 立刻交出 LSM 卡 |

---

## 5. 常见栈快速识别清单

### 5.1 芋道（Yudao / RuoYi-Vue-Pro）

| 指纹 | 位置 | 置信度 |
|------|------|--------|
| `/app-api/member/auth/sms-login` 200/405 | API 路由 | 高 |
| `/app-config.js` 含 `VITE_APP_TENANT_ENABLE` | 前端配置 | 高 |
| `/admin-api/system/auth/login` 200 | 管理后台 | 高 |
| `Bearer test1` 可访问 `/admin-api/` | Mock 开启 | 极高（代付卡） |
| `X-Tenant-Id` 头 | 请求头 | 中 |
| `/profile/` 上传路径 | 文件上传 | 中 |

### 5.2 1Z（棋牌/博彩整合）

| 指纹 | 位置 | 置信度 |
|------|------|--------|
| `/qpuserapi/` 200 | API 入口 | 极高 |
| `/api/game/list` JSON | 游戏列表 | 高 |
| `protocal=167` | 通讯协议 | 极高 |
| `QPAccountsDB` | 数据库名 | 极高（网狐变种） |

### 5.3 鼎艺（Dingyi）

| 指纹 | 位置 | 置信度 |
|------|------|--------|
| `/api/v1/user/verifyKey` | 验证接口 | 极高 |
| 绑卡才能充值 | 业务流程 | 高 |
| 充值凭证上传 | 业务流程 | 高 |

### 5.4 GoFun / AKS

| 指纹 | 位置 | 置信度 |
|------|------|--------|
| `VITE_HTTP_SINGKETY` | JS 环境变量 | 极高 |
| Vite + signKey 硬编码 | 前端 JS | 高 |
| `/api/v1/member/login` | API 路由 | 中 |

### 5.5 LSM

| 指纹 | 位置 | 置信度 |
|------|------|--------|
| `lsmview` / `mclsm` | HTML/JS | 极高 |
| LSM 标识 | 页面内容 | 高 |

### 5.6 巴西 tRPC

| 指纹 | 位置 | 置信度 |
|------|------|--------|
| `/api/trpc/` 端点 | API 路由 | 极高 |
| `daanrox` 字样 | HTML/JS | 高（Daanrox 分支） |
| PHP 后台 + tRPC 前台 | 架构 | 高 |

---


## 全文导航（已拆分）

主卡保留前 6 节；其余 21 节在 `references/full.md`：

- 6. 通用侦察命令（Phase-0.5）
- 7. 成功口径
- 8. 上下游关联
- 9. FAQ / 常见陷阱
- When to Use
- Prerequisites
- Quick Reference
- Procedure
- 二进制 WebSocket 协议平台(非 SignalR)
- `/wps/*` REST + RSA/DES 加密请求平台(非 SignalR / 非 wasm-WS)
- Next.js SPA + X-API-* 自定义头平台(AYX/c7 爱游戏体育系)
- PHPWind 落地页 + 彩虹易支付(epay)平台(必发系镜像站群)
- Pitfalls
- Verification
- References
- When to Use
- Prerequisites
- 核心方法论
- Pitfalls
- Verification
- References

加载：`skill_view(name='gambling-family-router', file_path='references/full.md')`

> 全文较大（37909 字符），已分 4 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
