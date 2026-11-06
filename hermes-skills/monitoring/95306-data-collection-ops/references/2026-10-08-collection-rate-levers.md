# 采集率提升：口径、根因与杠杆（2026-10-08）

> 回答「还有什么可做的 提高采集率的」时先读本卡。
> 核心：**采集率要按平台侧权威口径算，别用我方自建字段自证**；
> **配置改动的生效条件必须先查 `conf.py` 是否单例**，否则改了等于没改。

---

## 一、口径：怎么算才叫「采集率」

### 1.1 必须用平台侧真值，不能用我方 `enterpriseCount`

`index.json` 的 `enterpriseCount` **与我方 `pack_map.enterprises` 逐项一致** ⇒
它其实是**我方采到的数量**，不是平台报名总数。
凡用「`enterpriseCount=0` ⇒ 该项目无人报名 ⇒ 非缺口」的推理都是**循环论证**。

平台侧真值在 **`/data_pool/plat_enroll_map.json`**：

```
{ "rows": 11012（整数，行数）, "projs": { "OW002026…": {...}, … } }
```

- 键是**平台项目编码 `projCode`**（`OW/OY/OH/OK/OQ/OR/OB…` 前缀），**不是 UUID**
- 桥接：`index.json` 的每条 project 也带 `projCode` ⇒ 用它 join
- 窗口默认 30 天，字段有限 ⇒ 只能做「企业条目数」级核对

### 1.2 真实数字（2026-10-08 实测）

| 口径 | 数值 |
|---|---|
| 平台映射覆盖项目 | 629 |
| 能对上 uuid 的 | 337 |
| 平台企业条目 | 2859 |
| 我方已采 | 2592 |
| **真实采集率** | **90.7%** |
| 缺口 | 290~331 |
| 有缺口项目 | 83 / 337（76% 项目是满的，缺口高度集中） |

**另有 187 个平台项目（1006 条企业）我方无对应 uuid**：全部 `OQ`（广州局）/
`OB`（哈尔滨局）/`OK`（济南局）前缀，企业名是「职业培训学校」「电子产品研究所」
「工程咨询」⇒ **采购/服务/工程类，不是废旧物资处置 ⇒ 范围外，不算漏采**。

### 1.3 缺口清单落盘

`gapfill_targets_all.json` = list，每项一个缺口项目（2026-10-08 共 106 项 / 331 条 /
199 家去重企业），其中 **184 家（92.5%）我方有账号映射** ⇒ 不是「没账号采不到」。

按局分布：乌鲁木齐 84 / 上海 49 / 广州 30 / 西安 26 / 北京 23 / 武汉 21 / 成都 20。

---

## 二、根因（代码级铁证）

### 2.1 每台每轮只探 1/3 候选 —— `collector/main_parts.py:19-24`

```python
cands = self.tickets.candidates(..., limit = probe_limit * 3)   # 候选池 = 24 × 3 = 72
if cands:
    gr = self.gap.run(cands, ..., probe_limit = probe_limit)    # 实探   = 24
```

实测 12 台全部吻合：`sh_cand = 72` / `sh_probed = 24` / `sh_sec = 92~93s`。
`collector.ini` 里 `[gapfill] probe_limit` 的注释也写明「每张票 1 次业务请求，
这个数 × 4s 就是单轮耗时下限」（24 × 4 = 96s ≈ 实测 93s）。

⇒ **`probe_limit` 是真限流点，一提就是候选池和实探同时翻倍。**

### 2.2 单轮 93s，调度却 5 分钟一轮 ⇒ 每轮白闲 200+s

```cron
2-59/5 * * * * cd /opt/v6 && flock -n /tmp/v6_orch.lock python3 /opt/v6/v6m.py orch > /tmp/orch8b_cron.log 2>&1 < /dev/null
```

`flock -n` 是**非阻塞锁** ⇒ 上一轮没跑完，下一轮直接跳过 ⇒ **加密轮次不会重叠**。

### 2.3 票池有料没挖 —— `/opt/v6/bid2_tokens.json`

```
结构: { "jwt": {…}, "st32": {…} }
实测: jwt 423 张（exp 全未过期）+ st32 329 张 = 752 张活票
覆盖 273 家企业，其中 243 家（89%）我方 pack_map 里从来没有过
```

票池条目带 `acct`（真账号，如 `hws0722`）与 `org`（企业名）⇒ **用 `org` 做比对**，
不要用 `acct` 比 `acct_to_ent` 的键（见 §3.1）。

### 2.4 账号映射有两套 ID，别混

`link8515.py:127`：

```python
key = 'lk_' + hashlib.md5(((NM2U.get(nm) or nm)).encode('utf-8')).hexdigest()[:12]
```

⇒ `acct_to_ent` 里大量键是 **`lk_<md5前12位>` 合成伪账号**（有真账号时才用真账号）。
它与票池真账号交集为 0 **是正常的**，不是数据缺失；
**企业名维度的 `ent_to_acct` / `ent_to_user` 才可用于缺口比对**。

---

## 三、改配置前必须查：配置是单例还是每轮读

**★ 最大的坑。** `collector/conf.py`：

```python
_CONF = None
def conf(path=None):
    """全局单例。重复调用不会重复解析文件。"""
    global _CONF
    if _CONF is None or (path and path != _CONF.path):
        _CONF = Conf(path)
    return _CONF
```

⇒ `collector.ini` 在 `Conf.__init__` 里 `cp.read()` **一次**，之后永远用内存副本。
⇒ **改 ini 文件对运行中的 `v6collector` 服务零影响，必须重启服务才生效。**
⇒ 反之：只改 **crontab**（orch 调度）是**立即生效**的，不需重启。

验证改没改生效：去**采集机本地**看 `/opt/v6/v6_state.json` 的 `_cstats`
（`probed` / `hit` / `written` / `probe_ok` / `probe_fail`，带 `saved_at`）；
**不要**只看主控的 `master_state.json` —— 它的 `汇总` 是**窗口累计**（`窗口分钟`/`轮数`），
`分片.<局>.probed` 才是每轮值，且只在窗口滚动时更新。

### 改法与回滚

```bash
# 推送（带备份 .bak_20261008_probelimit，幂等，支持灰度）
python3 /tmp/push_probe_limit.py --hosts 0 --set 48      # 先单台
python3 /tmp/push_probe_limit.py --hosts 0 --restore     # 回滚

# 采集机路径: /opt/v6/current/conf/collector.ini（current 是软链，实际在 /opt/v6/lib/v6rel_*/conf/）
# 连接: paramiko + /opt/v6/jumpers.json + /root/.ssh/id_ed25519
# 注意 shard1(宁波 114.66.40.208) 的 sshd 在 —— 端口是 25175，不是 22
```

**整树部署** `deploy/fleet_deploy.py`（`--tar` + `--rel` + `--stage`/`--activate`）会把
整棵树替换并重启服务 ⇒ **改一个参数不要用它**，直接覆盖 `conf/collector.ini` + 滚动 restart。

---

## 四、杠杆清单（按性价比）

| # | 杠杆 | 效果 | 代价 |
|---|---|---|---|
| ① | `orch` cron `2-59/5` → `2-59/3` | 12→20 轮/h，**吞吐 ×1.67** | 无（改 crontab，立即生效，可回滚） |
| ② | `[gapfill] probe_limit` 24 → 48/72 | 候选 144/216、实探 48/72，**吞吐 ×2~3** | **需重启 12 台 v6collector** |
| ③ | 攻 199 家缺口企业 | 补 331 条 | 184 家是 `lk_` 伪 ID ⇒ 要真账号 |
| ④ | 扩采集范围（那 187 个采购/服务类项目） | +1006 条 | 需改采集口径 |

**①②可叠加**，但注意时间账：单轮耗时 = `probe_limit × 4s`。
`probe_limit=48` ⇒ 单轮 192s ⇒ cron 间隔必须 ≥4 分钟；`=72` ⇒ 288s ⇒ 间隔需 ≥5 分钟。
⇒ **提 probe_limit 的同时要把 cron 调回 `2-59/5`，别再加密**，否则每轮都会被 flock 跳过。

`[budget] max_biz_per_round = 620`（每台）不是瓶颈（实测只用到 2.7%，`预算剩` 还是 10 亿）。

---

## 五、教训：这个库的注释多处过时，不能凭注释下结论

| 注释说 | 实际 |
|---|---|
| `gapfill.py:203`「`note_acct_risk → escalate → freeze` 全库无调用者，永远不触发」 | `gapfill.py:170/207` **都有调用者**，`guard.py` 实现完好 ⇒ 风控链是通的 |
| `inject_max` 那类「配置项」 | 这个**确实是死键**（`tickets.py:48` 定义，全库 0 消费点） |
| `probe_limit` 曾被判为死键 | **实测有效**（12 台 `sh_probed` 全 = 24 与配置一致） |

**规矩：判断一个配置项/机制是否有效，只认两样东西 —— ① 调用点（grep 消费处）
② 运行时实测值。注释、变量名、默认值都不作数。**

---

## 六、复现命令

```bash
# 采集率精算（主控）
scp precise_rate.py gapfill_feasible.py pool_org_check.py root@207.57.167.92:/tmp/
ssh -i ~/.ssh/v6_master_key -p 12971 root@207.57.167.92 'cd /tmp && python3 precise_rate.py'

# 每台每轮实况（采集机本地）
ssh … 'cat /opt/v6/v6_state.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[\"_cstats\"])"'

# 调度与生效检查
ssh … 'crontab -l | grep orch'
ssh … 'grep -n "^probe_limit" /opt/v6/current/conf/collector.ini'
```
