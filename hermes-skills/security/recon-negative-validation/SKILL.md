---
name: recon-negative-validation
description: "Use when a scan returns 0 hits: validate the probe first."
version: 1.0.0
license: MIT
---

# 假阴性闸：拿到「0 命中」先证伪探针

## When to Use

任一条命中就进来：

- 批量枚举/目录扫描/路由 fuzz 输出 **总计 0**、**无命中**
- 扫出来的端口/路径数量远低于直觉（比如“唯一洞口是宝塔面板”）
- 准备把「不存在 / 全关着 / 无路可走」写进报告之前
- 上一次批量扫描跑到一半被目标拉黑、超时、换过出口
- 代理/relay/边缘回「200+完整正文」，要判它是**活窗**还是**缓存复读旧窗口**（→ §K2）

**核心纪律：一个假阴性会让你换目标、写错结论、再回头改口。**
假阳性最多多花几个请求，假阴性会直接毁掉整条路径。

---


## 全文导航（已拆分）

主卡保留前 1 节；其余 9 节在 `references/full.md`：

- 1. 三类假阴性源（全部实测）
- 2. 纪律：每批枚举都塞「已知阳性自检」
- 3. ground truth 优先：能拿源码就拿
- 4. 顺带：路径签名拦截下的路由存在性 oracle
- 4b. 反面：签名先于路由时，泛化 5xx 无存在性信息（`references/status-code-does-not-prove-route.md`）
- 5. 节流（throttle）key 判定与出口轮换
- Response and Error-Page Discriminators
- Pitfalls
- 关联
- References

加载：`skill_view(name='recon-negative-validation', file_path='references/full.md')`

> **本地盘上的「0 命中」同样是假阴性源**（探针不存在 / 索引表缺失 / 输出被吞）：
> `references/local-search-false-negatives.md`（实测：`rg` 不在 PATH + `2>/dev/null` 吞掉 127，
> 差点把「档案还在」答成「没了」；`session_search` 缺 `messages_fts` 时直连 `state.db`）

> **API 探针的两道必检闸**（同时错位时，整轮「全站 0 泄露」会是纯粹的假阴性）：
> ① **鉴权承载头名**——登录 200、JWT `exp` 未到、却所有端点回同一个 `401 INVALID_TOKEN` ⇒ 是头名错（`token:` vs `Authorization:`），不是票错；
> ② **参数作用域**——参数「生效」不等于「全局」，失败关闭式过滤（`WHERE parent_id=? AND 你在我的树里`）会让你把自有团队当成全站。
> 详见 `references/api-probe-validity-gates.md`。

> 全文较大（24986 字符），已分 2 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
