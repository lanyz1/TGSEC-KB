# 95306 采集吞吐天花板 · 结构级地图（2026-10-09 实测，供下次别再重挖）

> 一句话：**瓶颈不是候选池、不是预算、不是触发频率** —— 是「账号/票面」。下面是全部结构与已证伪项。

## 一、轮次与调度的真身

```
采集端: 自轮询 360s/轮 ([rail] every_sec=360; collector/main.py:139), 与主控 cron 无关
        每轮重置 max_biz_per_round=620 (main.py:91-92)
主控:   cron `2-59/5 * * * *` → v6m.py orch (flock -n /tmp/v6_orch.lock)
        master/orch.py:139 dispatch(i) → 采集机 nohup python3 tools/gap_once.py /tmp/bk8_ctx.json <i>
        ★ orch.run() 是**纯串行**: for 12 台 { dispatch; wait_done(≤window_min=30min) }
          ⇒ 一轮 orch 最坏 12×30=6 小时; 期间 5 分钟 cron 全被 flock 挡掉
        ★ dispatch() **没有忙台检查**(orch.py:139-150), 靠 flock 保证 orch 单实例
```

**推论**：加密 orch cron（5min→3min）**无效**（实测吞吐无差异 —— 因为一次 orch 跑得比 cron 间隔长，后续触发全被 flock 跳过）。

## 二、`_cstats` 五个键的真身（别再猜）

```
采集端每轮写 /tmp/v6_cstats.json (collector/store.py:131; main.py:122)
主控 merge_parts2.py:332 汇总 → /data_pool/collector_budget.json  (这就是 bot 里的「预算」看板)

★ ui_ok / ui_fail 真身 = probe_ok / probe_fail  (collector/main.py:126 `"ui_ok": cs.get("probe_ok", 0)`)
  ⇒ 「ui_ok=0」= 本轮**探活成功 0 次**，不是「机器空转」
★ 缺口补采轮会整体覆盖 cstats: main_parts.py:15-27 `_phase_gapfill` → `st["_cstats"] = dict(gr)`
  ⇒ 被 orch 派去跑「只做补齐」的台，该轮 ui_ok 显示的是 gapfill 自己的计数（常为 0）
```

## 三、候选池来自哪（唯一来源）

```
tickets.py:149-192 candidates():
  pool = state["rail_pool"]
  跳过 acct_cooled(uid) 冷却账号
  跳过 len(token) < 16 的无效票
  跳过 prod_blocked_st() 线上判死的票
  out = need(命中缺口名册的) + other   →  return out[:limit]  (limit = probe_limit*3 = 144)
```

**实测 12 台车票池（2026-10-09 03:2x，文件 = 每台 `/opt/v6/v6_state.json`）**：

| shard | 0 上海 | 1 宁波 | 2 广州 | 3 成都 | 4 上海2 | 5 成都2 | 6 青岛 | 7 深圳 | 8 北京 | 9 武汉 | 10 乌兰察布 | 11 河源 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rail_pool | 49 | 42 | 83 | 56 | 55 | 58 | 54 | 66 | 70 | 72 | 52 | 47 |
| 票有效(≥16) | 49 | 42 | 83 | 56 | 55 | 58 | 54 | 66 | 70 | 72 | 52 | 47 |
| 冷却 | 5 | 2 | 7 | 6 | 1 | 5 | 5 | 5 | 8 | 3 | 6 | 8 |

⇒ **票 100% 有效、池子 42~83 张 ≥ probe_limit 48** ⇒ **「候选饿死」假设作废**。
（池子 = 752 张活票按台分发，Σ = 704 ≈ 752，每台自有 `/opt/v6/v6_state.json`。）

## 四、已证伪的杠杆（别再试）

| # | 假设 | 实测 | 判定 |
|---|---|---|---|
| 1 | 候选池饿死 ⇒ 扩池 | rail_pool 42~83 张、100% 有效 | ❌ 作废 |
| 2 | 预算 620 是瓶颈 | 每轮只消耗 ~10%（Δ业务 60~105） | ❌ 非瓶颈 |
| 3 | 加密 orch cron ⇒ 更多补采 | flock + orch 串行 6h/轮 | ❌ 无效 |
| 4 | gapfill probe_limit 还是默认 24 | ini 已是 48（上轮已抬） | ❌ 无此杆 |
| 5 | ui_ok=0 的 4 台（广州/成都/成都2/青岛）在空转 | = 被 orch 派去跑「只做补齐」轮 | ❌ 不是空转 |
| 6 | 缺口名册还能持续出货 | `[gapstock] 扫 196 项目 ⇒ 仅 15 项目待补 / 13 家企业 / 17 点位` | ⚠️ 近吃完 |

## 五、真正的天花板 = 账号/票面

```
平台真值源 /data_pool/plat_enroll_map.json (03:30:01 更新): projs=618 项目 / rows=10919 条
  每个项目值结构: {"企业数": N, "企业": [...], "公告日": "YYYY-MM-DD"}
  公告月分布: 2026-10 68 个 / 2026-09 550 个
我方: /opt/v6/gap_projects.json → 项目总数 14394 / 在网项目 166 / 缺口企业 188 / 缺口账号 29
两套键空间: 平台 proj id = 20 字符 (OF/OQ/OB/...) ; 我方 /data_pool 下 53959 个目录 = UUID 命名
  ⇒ 不能用字符串交集算「未跟」；必须经 sync_plat_enroll.py / plat_enroll_map.rows 的桥接字段

缺口真因: 采集数据是**按账号维度**的（探活只拿账号信息；buyed_matrix 是 per-account）
  ⇒ 缺的 1273 条（199 家企业）里 184 家**有账号但采不全**、15 家**连账号都没有**
  ⇒ 票池 752 活票覆盖 273 家 org，其中 243 家从未采；但与缺口企业 **交集 = 0**
  ★ 结论: 要破 67.1%，只能扩「账号/票面」覆盖到那些缺的企业 —— 属需要拍板的运营动作
```

## 六、下次开工先跑的工具（$T/tools/，只读）

- `cstats_now.py` —— 探测面权威读数（读 `/data_pool/collector_budget.json` + 各台 `/tmp/v6_cstats.json`）
- `biz_delta.py` —— Δ业务/台/轮 差分（**唯一正确**的增益口径；日志 请求/业务/数据 = 生命周期累计值）
- `ctx_fleet_check.py` —— 12 台名册内容级核对（应恒为 名单 188 / 账号 29）
- `pool_size.py` —— 12 台车票池体检（本次新增）
- `orch_chain.py` / `orch_fanout.py` —— orch 调度链与扇出参数
- `rounds_raw.py` —— 判「每轮值 vs 累计值」
