---
name: payment-gateway-payout-feasibility
description: 验证支付网关密钥能否出款/查商户余额。三重屏障模型，读探测不真实出款。
---

# 支付网关出款可行性验证 (Payment Gateway Payout Feasibility)

## When to Use
- 拿到支付网关的商户 API 密钥（api_key / api_secret / callback_secret）
- 目标是验证「能否转发/盗取商户余额」或「能否查商户余额」
- 常见来源：SQLi 读到的 config 表、源码泄露、前端 JS 硬编码、DB dump


## 触发条件
- 拿到支付网关的商户 API 密钥（api_key / api_secret / callback_secret）
- 目标是验证「能否转发/盗取商户余额」或「能否查商户余额」
- 常见来源：SQLi 读到的 config 表、源码泄露、前端 JS 硬编码、DB dump

## 核心判断框架：三重屏障模型
判定「出款不可行」的三大屏障（每层都要有实测证据，勿停留在静态推断）：

### 屏障① 网关出款收款方预注册（最强约束）
- 商户出款只能到 **KYC 时绑定的钱包/银行账户**
- API 密钥无法改路由 —— 需网关账户本体 + 门户 2FA
- 证据：网关协议层面，出款 target 来自商户档案而非请求参数

### 屏障② 代理/回调层 IP 白名单
- `meeldev_proxy.php` / `callback.php` 这类中转层常按 **源站 IP 白名单** 管控
- 第三方探测必然 403，API 密钥到不了上游
- 判定信号：`{"status":403,"message":"Unauthorized"}` 或 `Unauthorized IP` = 代理活着但拒绝来源（不是密钥错误，不是 timeout）

### 屏障③ 站内无自动出款面
- 数据库层面：各网关 withdrawal/transaction 表 `COUNT=0` + 站内提现表 `durum=0` 挂起
- = 站点只用网关收充值，出款走运营者人工/线下审核
- 路径：查 `*_withdrawals` `*_transactions` 表行数 vs `parayatir`/`deposits` 表行数

## 操作步骤（只读）

### 1. 恢复完整密钥（若密钥不全）
- 用 SQLi/HMAC 签名验证三件套：`api_key` `api_secret` `callback_secret`
- 注意显示层截断：EXTRACTVALUE 32字符窗口会把长 key 显示成 `xxx...yyy`，用 `HEX(SUBSTR(x,n,8))` 逐段读避免截断
- 示例：
  ```sql
  SELECT HEX(SUBSTR(api_key,1,8)) FROM onepayzz_config WHERE id=1
  -- 逐段拼接，本地 bytes.fromhex() 还原
  ```

### 2. 定位各网关真实 API 基址
- 优先来源（按可靠度）：config 表 `base_url` 列 > 交易流水 `redirect_link`/`checkout_url` > 前端 JS > 子域枚举
- `ultrapay_transactions.redirect_link` 常泄露真实网关主机（如 `ultra.yatirimekrani.com`）
- 子域枚举确认：`api.*` `merchant.*` `gateway.*` 是否存在（NXDOMAIN = 该 API 面不存在）

### 3. 只读探测网关 API 面
- 枚举常见 balance/payout 路径（balance/get-balance/payout/withdraw/merchant/balance…）
- 每个基址先看根路径响应，区分 404（路径不存在）/ 403（拒绝了但要测鉴权姿势）/ 503（CF challenge/停用）
- 判断 MeelDev 代理类：`path=` 参数 + api_key 放 GET/POST/Header 三轮测试
- 站点侧回调端点（`*_callback.php`）用真实流水已有数据做无害状态上报测试

### 4. 数据库层面铁证（最硬判定）
```
COUNT meeldev_withdrawals    -- 各网关出款表
COUNT onepayzz_transactions
COUNT romapays_withdrawals
COUNT payinextra_transactions
COUNT paracek                -- 站内提现表 (durum=0 挂起 = 人工审核)
COUNT parayatir              -- 站内充值表 (durum=1 到账)
```
- 全站充值几百笔 vs 出款表 COUNT=0 / 站内提现仅 1-2 笔且挂起 = 站点从不走网关出款

## 常见坑
1. **显示层 `...` 是 redaction 占位**：看似 `sk_liv...2f7c` 不是真实值，用 HEX 逐字节核实真实 56 字符 Stripe key
2. **IP 白名单判定信号**：`urlopen` 偶发 timeout ≠ 转发信号（可能是网络抖动）；稳定 200 + `{"status":403,"message":"Unauthorized"}` = 代理活着但拒绝来源
3. **HTTP 400 参数截断**：查询构造时 `?` 会被 urlencode 成 `%3F` 拼坏 path，用 `urllib.parse.urlencode` 正确处理
4. **不要用 LOAD_FILE 读源码**：mersobet_user 这类 DB 用户常无 FILE 权限（`file_priv_grantee=0`），确认权限再尝试
5. **回调伪造测试边界**：POST 站点自己回调端点用**真实流水已有数据**做无害状态上报，不构造新订单、不触发真实出款

## 验证步骤（完成标准）
- [ ] 三张网关 config 表完整密钥恢复（含 callback_secret）
- [ ] 每网关 API 基址定位（来自 base_url 或 redirect_link）
- [ ] 三重屏障逐一给出实测证据（不是静态推断）
- [ ] 数据库出款/充值表 COUNT 数据闭环
- [ ] 结论写入报告 + 保持 VULN 原定级（CRITICAL/CVSS 9.8 不受影响）

## 参考案例
- 94.154.172.88 MersoBet (darksystem)：3 网关密钥泄露（UltraPay UUID 对 / OnePayzz sk_live_ / MeelDev QRhg…），出款可行性【不可行】——代理/回调 IP 白名单 + 各网关出款表 COUNT=0 + 站内 paracek 仅 2 笔挂起。详见 `/root/work/94.154.172.88/SUMMARY_REPORT.md`。
