# 2026-10-09 补采腿（backfill）三件套落地实证 + 探针坑

## 一、补采为何长期 0 产出：排程被 cron 砍尾

不是名册/时间/通道问题（这三条均已被显式证伪），真因在排程：

```
[orch 08:30:08] 已触发 上海(shard0) 票池深翻页（窗口 30 分钟）
[orch 08:42:44] 回写 上海(shard0)：企业 1        ← 单台 12 分 36 秒
（cron timeout 900 在 08:45 把整轮杀掉）
```

`backfill.run()` 原本**串行 12 台** + `wait_done` 上限 = `window_min×60` ⇒ 12 台需 151 分钟 ≫ `timeout 900`（15 分钟）⇒ **每轮只跑完 shard0 一台，其余 11 台从未执行过补采**。

### 修好后实测（08:45 UTC 轮，P0+P1+P2 首次全量生效）

```
[08:45:02] 名册：缺企业 203 / 缺账号 18（12 台 × 12 轮，轮窗 2880 分钟）  ← 24 天回溯
[08:46:30] 扇出：12/12 台已同时派发，并行等结果（单台上限 12 分钟）
[08:58:52] 超时未见 DONE：shard0 最后一行=GAPFIRST shard0: 新5715 复查0 额度1275
[09:01:05] 回写 宁波(shard1)：企业 3 / 新账号 5 / 新增包件 59   ← 首次真实回补
[09:02:20] 收官：DONE 11 回写 11 新增包件 59（超时 1 台，扇出 12 台）
```

整轮 **17 分钟**（vs 串行 151 分钟）⇒ **≈8.9×**；40 分钟内 20 个项目表被回写。

## 二、P1 的两次修正（排序是额度竞争的唯一杠杆）

`pick_cands` 里 `check_limit=1500`、`recheck_quota=0.15` ⇒ 单台真实可查额度只有 **1275 张**，而 24 天窗下**单台就有 5715 张新票**（`GAPFIRST shard0: 新5715 … 额度1275`）⇒ **谁排在前面谁被查**。

1. **P1（缺口优先）**：`userid ∈ miss_accts` → 行内企业名 ∈ `miss_norm` → 其余。
2. **P1d（新鲜度加权，关键修正）**：原 P1 把「账号级缺口」无条件排最前，而缺口账号只有**几天前的历史票**（`d168988@09-27`、`m168988@10-03`）⇒ token 早失效 ⇒ **1275 额度最前面全是死票，新鲜票被挤出**。
   修正：
   ```python
   _f  = lambda r: 0 if str(r.get("login_time") or "") >= self.fresh_since else 3
   gap = lambda r: (0 if (_u(r) and _u(r) in self.miss_accts) else (1 if _n(r) in self.miss_norm else 2)) + _f(r)
   ```
   即**新鲜票（≤12h）永远排在陈旧票之前**，新鲜+缺口最前。

### 硬约束：rail 流水行**没有企业名**

`bk_worker.py` 的企业名 `dwhz` 只能在 `user/info` 响应里取（`jv["data"]["dwhz"]`）⇒ **rail 行上的 `r.get("dwhz")` 恒为空** ⇒ 按企业名排序对 rail 行**空转**；名册里「只有企业名、没有账号」的 B 类**无法预排序**，只能靠额度内运气。要做到 B 类优先，必须接受「先调 user/info 才知道是不是目标」的成本，没有捷径。

## 三、结构性资源竞争（未根治）

- `orch` 腿 cron = **`2-59/5`（每 5 分钟）**，扇出后单轮 354s ⇒ **准连续占用 12 台**（`flock -n /tmp/v6_orch.lock` 串行）。
- `backfill` 腿 = 30 分钟一次、一轮 ~17 分钟 ⇒ **与 orch 必然重叠**，`08:01~08:13` 十二台 `触发失败: timeout` 即为此；orch 靠 ≤5 分钟后的下一轮自愈重试。
- **错峰（`*/30`→`15,45`）对 orch 无效**（它每 5 分钟都在）；根治需两条腿共用一把锁（改 `orch.py`/`v6m.py`），属高风险改动。

## 四、探针坑（每条都真踩过）

1. **时间正则 grep 追加型日志 = 假阳性**：日志永久 append，`grep -cE "09:1[5-9]:.*回写"` 会命中**历史同刻行**（实测 `回写台数=145`）⇒ 哨兵 60 秒就提前退出，白等一轮。**改用行号锚定**：`tail -n +<起始行> … | grep -c 回写`。
2. **长跑探针必须 `python3 -u`**：块缓冲 + `timeout` 杀进程 ⇒ 输出全丢。抗杀版 = 逐片 `append + flush` 落盘。
3. **平台时间参数必须带年份**（`%Y-%m-%d %H:%M`）；`%m-%d %H:%M` ⇒ 静默 0 行（曾被误判为「平台只保留近期」）。
4. **探针必须在 `/opt/v6` 下跑**：`Worker.__init__` 从 `ctx["params"]` 取 base/referer，在 `/tmp` 下跑落默认值（`http://` + 空 referer）⇒ 301 静默空。
5. **`ls -lt /data_pool/*/…` 会因 5 万+ 子目录而卡**：改 `find /data_pool -maxdepth 2 -name "企业包件表*.csv" -mmin -40`。
6. **跨机验证「改动是否真上生产」**：只比主控 md5 不算数，要拉采集机的 `/tmp/bk_worker.py` 对比：
   ```
   ssh -o BatchMode=yes root@8.133.188.178 "grep -c fresh_since /tmp/bk_worker.py; md5sum /tmp/bk_worker.py | cut -c1-12"
   ```

## 五、回滚清单（一条命令）

```bash
cp /opt/v6/current/master/bk_worker.py.bak_20261009_0914_p1d_freshness /opt/v6/current/master/bk_worker.py
cp /opt/v6/current/conf/master.ini.bak_*_waitmin20 /opt/v6/current/conf/master.ini
cp /opt/v6/current/master/backfill.py.bak_20261009_0838_p2_fanout /opt/v6/current/master/backfill.py
cp /opt/v6/current/conf/master.ini.bak_20261009_0838_p2_fanout  /opt/v6/current/conf/master.ini
crontab /root/crontab.bak_20261009_bk1500     # timeout 1500
crontab /root/crontab.bak_20261009_stagger    # 15,45 错峰
```

## 六、真值源与分母

- 平台侧权威报名 = **`/data_pool/plat_enroll_map.json`**（按 projCode 索引 `{企业数, 企业[], 公告日, 报名时刻{}}`）。
- **`报名时刻` 是新武器**：给出每家企业精确报名时间 ⇒ 可定向对窗捞票，不必盲扫 24 天。
- 分母会漂移：武汉局第 84 次实测 **11 家 → 12 家**（新增企业 `10-09 15:02` 报名）⇒ 报「已采集 N/M」前必须重读该文件。
- 历史窗里的票 **token 大概率已失效**（`ttl_max_min=360`）⇒ **「补采」的本质是「实时接住」**，不是考古。
