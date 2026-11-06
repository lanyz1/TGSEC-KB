---
name: ginvue-admin-reward
description: >-
 GIN-VUE-ADMIN 管理后台 + 领奖中心业务 API 杀伤链：未授权 getConfigs/getServers、
 CORS 反射 credentials、前端 JS 隐藏 reward 路由、HPP、getName 用户枚举、
 sendCReward 字段探测与验证码墙。用户提到 gin-vue-admin、领奖中心、sendCReward、
 getConfigs、游戏奖励配置裸奔时使用。
---

# GIN-VUE-ADMIN 领奖 / 业务 API

## 真源

1. `docs/playbooks/GIN-VUE-ADMIN领奖与业务API杀伤链.md`
2. `tools/ops/ginvue_admin_probe.py`
3. 参考报告：`docs/references/报告-GIN-VUE-ADMIN领奖中心渗透.txt`（**未授权 IP，勿自动开打**）
4. 结合：`cors-cross-origin-misconfiguration` · `business-logic-testing` · `free_claim_bypass`
5. **管理面接管**（注册写 `authorityId` / 伪造 JWT / 成功通知；**禁止**默认 reset 原 admin）→ Skill `ginvue-admin-stealth-takeover`

## 强制步骤

1. 确认 host 在 scope；报告样例 IP 只学手法。 
2. `ginvue_admin_probe.py recon --base <URL> --case <案卷>`（后台/领奖端口各跑一次）。 
3. 证据：`测绘/ginvue/`。 
4. 验证码墙未过前，勿把「注入全拦」当无洞；先 `field-probe` 确认字段，再人工验证码 + `--confirm`。 
5. 领奖逻辑深挖可衔接 `free_claim_bypass` / 业务逻辑竞态。

## 入口

```bash
python3 tools/ops/ginvue_admin_probe.py recon --base 'http://授权:端口' --case <案卷> --insecure
```


---

## 外部库增量（2026-10-11 分享包）

## 报告增量（GIN-VUE-ADMIN 领奖中心报告 → 已落地手法）

### A. 报错阶梯 oracle：免过验证码探字段名/类型/必填

处理顺序固定为 **绑定层(ShouldBindJSON) → 门禁层(验证码/token) → 业务层**，三类错误文案可互相区分：

| 文案 | 层 | 价值 |
|---|---|---|
| `请认真填写` / `xxx.notBlank` / 格式错 | 绑定层 | **不用过验证码**就能探结构 |
| `验证码错误` / `token 无效` | 门禁层 | 说明字段名猜对了（已进 handler） |
| `该奖励已领取` / `暂未开放` | 业务层 | **已过墙**，是业务结论 |

`account`(对)→验证码错误 vs `username`(错)→请认真填写 ⇒ oracle 成立。
**假阳性防线**：空值被「必填」拒 ≠ 空值绕过；`验证码不存在` 属门禁层，不是业务结论。
自动跑：`captcha-probe` 的 `binder_before_captcha` finding。通用化写法见 Skill `api-param-name-discovery` 核心技术 3。

### B. 验证码墙：报告「无法暴力提升成功率」是判据写错，别照抄

一次性验证码下「同 id 第二次」与「码识别错」同文案 ⇒ 拿一个 id 硬刷必然全灭（报告 5 线程全灭不是并发被防，是 id 被首请求消耗）。

1. **先测强度**（`captcha-probe`）：固定码 `00000` 进业务层 = 只查格式（直接跳过 OCR）；空码进业务层 = 空值绕过；自增 captchaId 且「未发放 id」文案可区分 = id 空间可枚举。
2. **人工读码兜底**（OCR 30–40% 时的正解）：`captcha-dump` 落 PNG + captchaId → 人工读 → `claim-loop --captcha-id <id> --code <码> --confirm`；**图文必须同一次取图**，错配 = 白刷。
3. **重试纪律**：只在 `captcha_error` 重试（期望次数 ≈ 1/命中率）；`binding_error` 去修字段名；`duplicate`/`business_error` **立即停机**并落证据。
4. **提吞吐**：一次取多个 id 各自独立尝试（`captcha-dump --times N`），不是并发撞同一 id。

### C. 过墙后必测矩阵（报告的「未完成项」）

重复领（同 `account+serverid+configids` 连提）· `configids` 跨档/批量（`"1,2,3"`/数组/重复 JSON key）· 跨服 `serverid`（用未授权 `getServers` 的全量逐个提）· 换 `channel`/`gid`/`name` 重放 · 隐藏路由 `/breward` `/nreward` `/reward` `/treward` 直接 POST · 越权代领（限授权账号范围）。

### D. CORS 定级：先证「凭据怎么传」

GVA 默认 token 在 header/localStorage（`x-token`）→ 浏览器不自动携带 ⇒ 反射 ACAO **读不到**后台数据（配置错误但不可利用，Medium/Low）。只有存在 cookie 会话时才是 High。报告把它报 HIGH 属定级过高。

### E. 指纹确认后的强制下一步

不要停在「未授权读配置」（只是 L1）：① 试开放注册写 `authorityId=888` 静默提权 → `ginvue-admin-stealth-takeover`；② 试 GVA 默认 `jwt.signing-key` 伪造超管票 → `gva-knownkey-local-write`；③ 后台端口与领奖端口**各跑一次** `recon`。

### F. 本机演练靶（改工具/教人前先跑）

```bash
python3 tests/fixtures/gva_reward_mock.py --port 28888 --echo-codes   # 复刻报告语义
python3 tools/ops/ginvue_admin_probe.py captcha-probe --base http://127.0.0.1:28888 --case _lab
python3 tests/unit/test_ginvue_captcha_wall.py                        # 11 项判据回归
```

完整判据与命令：`docs/playbooks/GIN-VUE-ADMIN领奖与业务API杀伤链.md` §6–§10。
