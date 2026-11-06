<!-- archived from /root/.hermes/skills/security/whgame-tp5-login-sqli/SKILL.md on 2026-10-21 -->

---
name: whgame-tp5-login-sqli
description: >-
 网狐棋牌 + ThinkPHP5 登录布尔盲注：Cocos/CashVegas、?data=base64、
 protocal=167、Machine 注入、QPAccountsDB/QPPlatformDB/QPTreasureDB/
 QPPlatformManagerDB、DataBaseInfo、GameScoreInfo、1010/10477 三值码。
 探测必须 SELECT 1，禁止写死列名。用户提到网狐、QP 库、登录机器码注入、
 hex LIKE 绕 WAF 时使用。ThinkPHP RCE/Client-IP 仍走 ThinkPHP 卡；
 假支付走 payment-callback-forgery。
---

> 归档卡：原目录 `/root/.hermes/skills/security/whgame-tp5-login-sqli`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/whgame-tp5-login-sqli/…')`，不要相对 `references/legacy/` 解析。

# 网狐 ThinkPHP 登录盲注（Cursor Skill）

## 何时用

- 指纹出现 `QPAccountsDB` / `QPPlatformDB` / `QPTreasureDB` / `QPPlatformManagerDB`
- 登录 `?data=` Base64 + `protocal=` + `Machine` / `login_machine`
- Cocos Creator H5、`/CashVegas`、`location.replace` 跳进壳
- 用户点名网狐、机器码盲注、DataBaseInfo、GameScoreInfo

## 真源

1. `docs/playbooks/网狐ThinkPHP登录盲注杀伤链.md`
2. `python3 tools/ops/whgame_blind_helper.py selftest`
3. TP 面并行：`thinkphp_surface_probe.py`（RCE/`.env`/Client-IP）；RCE 阴性不算结案

## 强制

1. 目标在 `config/scope*.json`。
2. **先跑 `oracle`** 标定真/假/错三码，禁止套上一站 1010/10477。
3. **探表只用** `EXISTS(SELECT 1 FROM db.table WHERE 1=1 LIMIT 1)`。列名未证之前禁止 `SELECT UserID`。
4. 授权内立刻 `map`（四库 SELECT 1），不要只生成 payload 结案。
5. WAF：字符串 → `LIKE 0x..25`（默认后缀 %）；数字 → `0x`；`ASCII` → `ORD(SUBSTR)`；长链拆前缀。
6. GRANT 拒 ≠ 探测失败；直连 1130 ≠ 注入失败。全表拖哈希 / 撞库 / 改分先问。

```bash
python3 tools/ops/whgame_blind_helper.py selftest
python3 tools/ops/whgame_blind_helper.py oracle --url https://授权API/ \
 --plain 'Machine={INJECT}&login_machine={INJECT}&protocal=167&username=test&password=<REDACTED>' \
 --case <案卷>
python3 tools/ops/whgame_blind_helper.py map --url https://授权API/ --plain '...' --case <案卷>
python3 tools/ops/thinkphp_surface_probe.py -u https://授权API --case <案卷>
```

## 成功口径

| 级 | 口径 |
|----|------|
| L1 | 登录协议可构造；Machine 真/假码差分稳定 |
| L2 | 至少一库 `SELECT 1` 为真；或抽出 DataBaseInfo 前缀 / Score 区间 |
| 边界 | Manager GRANT 拒 + 直连 1130 + 后台入口已复测 → 可写权限边界，不停在「再注一次」 |

## 不要做

- 用写死列名探表然后判「库不存在」
- 把本站盐、status、库密抄到下一站当常量
- 注入当超管：突破不了 MySQL GRANT
- 只扫 ThinkPHP RCE 阴性就结案（登录参数还没 fuzz）

## 衔接

- 支付商户 key → `payment-callback-forgery` / `pay_matrix`
- TP 调试页 / `.env` / Client-IP → `ThinkPHP手法.md`
- 有身份 → `object-matrix-authz`（他人×读凭据/余额）
- WS 大厅命令面 → `WebSocket消息注入与越权手法.md`（协议另逆）
