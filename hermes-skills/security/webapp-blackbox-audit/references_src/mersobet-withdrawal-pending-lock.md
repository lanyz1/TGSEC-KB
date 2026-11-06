# MersoBet 提现 Pending 锁 + 余额对账 + 链上核验 (2026-09-02 实战)

> 补充案例: 同站第二账号 Ksknlek 提现 15,000 TRY → TUwCwVgsvPK8G1LNosM5c17W1U2rJFYdeH。
> 与 `mersobet-withdrawal-field-drift.md` (第一账号 UmutCN, 字段漂移案例) 配套阅读。

## 1. Pending 提现锁判定法 (Bekleyen Çekim)

正确字段提交 15,000:
```json
{"vResult":"FALSE","vHeader":"Error","vContent":"Bekleyen Çekim Talebiniz Bulunmaktadır.Lütfen Bekleyiniz!"}
```

**关键区分实验**: 换极小金额 (10 TRY) 重提交 → **同样返回 Bekleyen**
= 账号级 pending 锁, 与金额/地址无关。
若小额通过而大额被拒 = 限额/风控, 而非锁。

判定表:

| 现象 | 结论 |
|---|---|
| 大额+小额均 vResult:FALSE Bekleyen | 账号级 pending 锁 (已有未处理提现) |
| 小额成功+大额拒绝 | 单笔限额/全局额度风控 |
| 任意金额都成功 | 无锁, 流程通畅 |

`vResult:FALSE` 恒定 + UI 无任何提示 = 服务端 pending 状态未暴露给前端。
玩家体验: 点击后只看到 Loading 消失、无弹窗无反馈 (本案例 UI bug 发送
undefined → `$.parseJSON` 异常吞掉了错误提示)。

## 2. 余额缺口对账法 (定位隐藏 pending)

```
账本: 仅 1 笔 +16,000 充值 (8/19 12:12) → 当前余额 15,000 → 差额 1,000
```

- 流水无提现记录但余额 ≠ 充值总额 → 后台挂单/审核扣减或隐藏支出
- 差额金额往往就是那笔 pending 提现对应的预扣款
- Darksystem 系模式: 提交即扣余额、出账时再结算 → 卡单时余额先被拿走
- 卡单用户画像: 充值正常 → 余额被预扣 → 新提现被 Bekleyen 拦截
  → 只有等后台处理或联系客服才能解开

## 3. 链上地址核验 (到账确认)

```python
import requests
# TronGrid 公开 API (免费, 无需 key)
r = requests.get(f"https://api.trongrid.io/v1/accounts/{addr}").json()
# data[0].balance 单位 sun (1 TRX = 1e6); data[0].trc20 数组查 USDT
# 兜底: https://apilist.tronscanapi.com/api/accountv2?address= (偶发非 JSON)
```

判定:

| 发现 | 结论 |
|---|---|
| 地址存在 + 有历史转账 | 活跃地址 (非误输) |
| USDT 未到 + 平台声称处理中 | 提交成功待出账 (等平均 15 分钟) |
| 地址不存在 | 地址格式/网络错误 |

网络风险 (报告必提): BTC (bc1/1 开头, 34/42 位) vs TRON (T 开头 34 位)
vs ETH/BEP20 (0x 开头) — 选错网络永久丢币。

## 4. adminGenelRapor SQLi 复测失败 (勿盲信历史战报)

- 历史战报: `POST /panel/ajax/admin.ajax.php tip=adminGenelRapor` 的
  baslangic 参数 EXTRACTVALUE error-based SQLi (无认证)
- 复测结论: **baslangic 值经 PHP `strtotime()` 预处理**
  - 单引号闭合 → 1064 语法错误 `near ''` (日期失效 → 空查询)
  - 无引号布尔 / 双引号 / AND '1'='1' / bitis 注入 → 均无响应差异
  - sqlmap level4/risk3 未判定
- `tip` 枚举: 仅 adminGenelRapor 返回数据 (未鉴权可读财务聚合:
  deposit/withdraw/remaining JSON), 其余 tip 全部空响应 (len=2)
- 教训: 老 PHP 系统参数经 strtotime/布尔化预处理后会天然阻断注入闭合;
  复测历史利用点前先验证参数是否仍原样进 SQL
