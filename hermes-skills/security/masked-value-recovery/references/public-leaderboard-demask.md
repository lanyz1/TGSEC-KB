# 公开静态榜单 JSON 的掩码登录名还原（surewin 案例，2026-10）

## 数据形态
- URL：`/public/html/leaderboard/history/{year}/{month}/rank_leaderboard_{month}_{currency}.json`
- 结构：`{"dateRange":..., "leaderboard": {"SLOTS": {"GOLD": [{login, totalValidBet, rank, previousRank, totalPoint}, ...], ...}, ...}}`
- 掩码规则实测：**隔位可见**——`l*e*h*h*a`（10 位登录名，1/3/5/7/9 位可见）；同时保留 `totalValidBet/rank/totalPoint`
- 覆盖：2025-03 ~ 2026-10 共 40 文件（MYR ~190 行/月 + SGD ~70 行/月）= 3,227 行

## 还原代码（核心）
```python
def mask_pattern(m):
    vis = {i: ch.lower() for i, ch in enumerate(m) if ch != '*'}
    return len(m), vis

def demask(m, by_len):
    n, vis = mask_pattern(m)
    return [c for c in by_len.get(n, [])
            if all(c[i] == ch for i, ch in vis.items())]
```
- `by_len` = 已知登录名总集按 `len()` 分桶（本案 105,327 条，含大小写归一）
- 结果：1,103 条唯一掩码 → 1,073 还原（97.3%）；未还原的多为 13+ 位长名（字典没覆盖）或含数字的随机名

## 工程细节
- 静态文件被 CF 挑战挡 curl：Playwright `page.goto(url, wait_until='domcontentloaded')` + `document.body.innerText`（JSON 会直接渲染成文本），`startswith('{')` 再 parse；每页 ~2s
- 姊妹域名（myr8/9/66/88 系）同路径文件 `len()` 完全一致 = 同一份数据，不用重复拉
- 产出两件：`platform_leaderboard_history.csv`（3,227 行，含 mask+candidates）与 `platform_leaderboard_members.csv`（1,103 行/人：月数、最高单月投注、最佳排名、积分）
- 掩码值 + 金额/排名本身可反查历史行为：头部大客单月 totalValidBet RM112M/41M/34M；还原后并入 dossier 做资金画像

## 延伸
- 同一 SPA 的 `/public/html/` 下还有 raffle winner / sponsor post / 各类 settings JSON；用同一「浏览器同源取静态 JSON」套路扫一遍
- 若榜单里的登录名能对上手机/邮箱字段（其它公开源），可继续喂账号接管/存在性神谕
