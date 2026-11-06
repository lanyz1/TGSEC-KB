---
title: "FastAdmin代付平台杀伤链手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# FastAdmin代付平台杀伤链手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/fastadmin-daifu-pentest/SKILL.md`

## 汇总内容

### fastadmin-daifu-pentest

来源：`/root/.hermes/skills/security/fastadmin-daifu-pentest/SKILL.md`

# FastAdmin 代付 / 下发 / 卡商

**前提**：目标在 `config/scope*.json`。同源支付中转域静默扩权；报告旁站 / 第三方 UAT 不扩。

**成功口径（按档，禁止跳级）**

| 档 | 成立条件 | 不算 |
|----|----------|------|
| L1 | 未授权 demo / 公网 backend JS 出路由或余额/代理名单 | 只看到登录页 |
| L2 | 任意身份进门 + `part/index` 泄 hash/salt/google_key/apikey | 只登录成功 |
| L2b | 离线破解明文 **或** 2FA oracle 确认密码 | 只有 hash |
| L3 | **真结算余额**跟自己/他人 uid 变化（B 票回读） | `part/multi` money 落库、`makemoney` 流水 |
| L4 | 超管会话 / 通道出款可控 | 改原超管密（默认禁止） |

## 何时启用

- 入口 `/sh.php`（总后台）`/ks.php`（卡商）+ `/assets/js/backend/`
- 登录字段 `username password captcha code keeplogin __token__`
- 验证码 `/index.php?s=/captcha`（图形，可 OCR）
- 哈希 `md5(md5(password)+salt)`；签 `md5(sorted + "&key=" + apikey).upper()`，时间戳常叫 `paydate`
- 业务词：代付、下发、卡商、通道 8801/8802、支转卡

**不要走这张卡**

| 指纹 | 走 |
|------|-----|
| 「支付管理中心」/ `admin_login.lock` / `api.php?act=` | `epay-admin-pentest` |
| 发卡 `notify`/`callback` | `payment-callback-forgery` |
| GVA `authorityId` | `ginvue-admin-stealth-takeover` |
| 只有 `X-Powered-By: ThinkPHP`、无代付面 | `ThinkPHP手法.md` |
| `/shop_hq` · `shop_keeplogin` · 多商户 `shop_id` / GT filter | `fastadmin-shop-tenant-bola` |

## 强制行为

1. 有任意身份先填 `测绘/object_matrix.md`（自己 vs 他人 × 读/写/加款/配置）。 
2. **流水 ≠ 结算**：`part/multi` money、`makemoney/add` 默认 journal-only，必须用 **B 的票查结算余额** 才算加款格。 
3. `part/index` 出 hash/salt/TOTP/apikey → 立刻离线破解 + 建凭据树，不要只记「信息泄露」。 
4. 子号可改自己下级 `is_google`，**不能**改上级/超管 2FA。缺 `google_key` 就换格子，不要空转绕 2FA。 
5. 同源 OEM 站（同一 hash 算法、同一弱口）→ 静默扩权后横向；无关旁站不扩。 
6. 默认不改原超管密、不耗真余额出款、不把完整 TOTP/apikey 写进可同步 STATUS。 
7. 图形验证码走 `captcha-ocr`；滑块/CF 勿硬 OCR。

## 最短命令

```bash
# 未授权面 + 入口 + backend JS（先跑）
python3 tools/ops/fastadmin_daifu_probe.py recon \
 --base 'https://授权站' --case <案卷> --insecure

# 有 Cookie 后：拖代理树敏感字段（打码落盘）
python3 tools/ops/fastadmin_daifu_probe.py dump-part \
 --base 'https://授权站' --case <案卷> \
 --cookie 'PHPSESSID=…' --portal ks --insecure

# 离线破解 FastAdmin 哈希
python3 tools/ops/fastadmin_daifu_probe.py crack \
 --hash-file exports/bot-recovery/<案卷>/测绘/fastadmin_daifu/part_rows.json \
 --wordlist dict/gambling_admin_passwords.txt

# 支付签试算（有 apikey 后）
python3 tools/ops/fastadmin_daifu_probe.py sign \
 --params '{"mchid":"1","paydate":"20260817120000","money":"1.00"}' \
 --apikey '<打码>'
```

## 八步（缺一环就停在该档，不要写 RCE/接管）

```text
① 指纹：/sh.php /ks.php /assets/js/backend /api/demo
② 未授权 demo：通道余额 / 代理名单 / backOrder·selfBack
③ 公网 JS：路由、字段、权限组（不登录）
④ 任意身份进门（弱口 / 自建下级 / 跨站同密）
⑤ part/index 拖树 → hash+salt+google_key+apikey
⑥ 离线破解 + TOTP 登录更多号；2FA 顺序当密码 oracle
⑦ 对象矩阵：part/multi 写字段 / makemoney 流水 / 真结算口
⑧ 真加款或超管会话成立 → 假支付/出款 API；否则写复工条件
```

## 真源

- 手法卡：`docs/playbooks/FastAdmin代付平台杀伤链手法.md`
- 探针：`tools/ops/fastadmin_daifu_probe.py`
- 对象矩阵：`object-matrix-authz`
- 图形码：`captcha-ocr`
- 假支付：`payment-callback-forgery`（本卡出 apikey 后再交）
- 对照（勿混）：`epay-admin-pentest` · `ThinkPHP手法.md`


---

## 外部库增量（2026-10-11 分享包）

## 附属/旁站 FastAdmin 识别（只出指纹也算发现）

主站是别的栈（如 Node/Express），但资产表里挂着**裸 IP:端口**直出 FastAdmin 登录页时，单开一段：

- 判据：页面 title 常带品牌名（如「商户\代理商登录口 – 鸿运SL」）、`/assets/js/backend/...`、
  `/admin.php` 或 `/admin.php?s=/` 入口、`fastadmin` 字样 / 版本号（1.1.1 等）。
- **TP5 系 CVE 标准 payload 返回 404 ≠ 无洞**：FastAdmin 把入口改写成
  `admin.php?s=/controller/action`，原 payload 路由天然不匹配。继续穷举
  `?s=` / `?r=` / PATH_INFO / `index.php/` / 大小写 / 后缀（`.html`）变体，
  并抓公网可读的 **backend JS** 拿真实控制器名再组链。
- 同 IP 常并列多站 + phpMyAdmin + 独立上传点 ⇒ 换端口 / 换 `Host:` 再扫一轮
  （`admin-console-discovery`）。
- 打不动就录**指纹 + 版本 + 路由形态**进报告 —— 附属系统暴露本身就是一条 P2（信息暴露），
  不要因为主链打穿就跳过它。
- 案例：777VVIP 报告 VUL-08（`8.210.148.155:443`，FastAdmin 1.1.1 + TP5.x，无 IP 白名单）。
