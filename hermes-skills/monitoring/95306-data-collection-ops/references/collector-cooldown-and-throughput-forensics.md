# 采集机冷却模型与产能取证(95306 机队)

适用:排查"产出低/轮次白跑/账号被冻/churn"、读冷却日志、核定机队当日产能、裁定外部诊断报告。
代码基线:v9.34 全队 `md5(/opt/v6/collector.py)=525edd50`(版本变了先重新核行号)。

## 一、冷却三层

| 层 | 位点 | 语义 | 影响面 |
|---|---|---|---|
| 整机冷却 | `_COOL_UNTIL=[0.0]`(L49,**模块级 list 全局**)、`COOL_MIN=15`(L48)、`_mark_cooldown()`(L64)、闸门 `if _in_cooldown(): return {"code":100,"msg":"cooldown"}`(L188 bfwz_get / L204 bfwz_post)、触发 `if _is_cool_resp(j): _mark_cooldown()`(L195/L211) | **任一票收到 code=100 → 全机 business 冻 15 分钟** | 该机所有企业停摆 15min;审计与 tokenrailquery 不受影响 |
| 账号退避 | `_cool_backoff(st,t,state,minutes=30)`: `cs[st]={"acct":…,"until":…,"cnt":n}` | 单票 30min 后复活 | **键 = 票**,不是账号 |
| 冻结升级 | 同函数 `n>=3` 分支 | 同账号"当日"冷却 ≥3 次 → 冻到"次日" | 计数键 `cc[f"{acct}|{day}"]` |

- 判"平台封了我们没有":审计 ST 条数、tokenrailquery 拉取量正常 ⇒ 限流是 **per-session/per-account**,不是 per-IP(旁证:同一轮 5s 内多个不同账号并发吃 100;同一 IP 连续多票全部成功)。
- 派生副作用:`榨干队列执行` 首行 `if len(_hl)>=20 or _in_cooldown(): break` ⇒ 冷却期间入队照做、执行体整段 break(PEND 涨/榨干 0 先读 `cooldown_until`,§10/§15)。

## 二、时区错位(fleet 全 CST,代码按 UTC 写)

```python
day  = (datetime.now()+timedelta(hours=8)).strftime("%Y-%m-%d")                       # "当日"在 16:00 CST 翻桶
nxt  = (datetime.now()+timedelta(hours=8)).replace(hour=0,minute=10)+timedelta(days=1)
until= (nxt - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")                      # 注释"转回主服 UTC"
```

`_cool_restore` 用 `datetime.now()`(本机墙钟 CST 字符串)与 `until` 比较 ⇒
- **实际失效点 = 日志所印日期 D 的前一日 16:10 CST**(日志写 D 是错的;`/tmp/v6_state.json` 的 `cool_st[*].until` 落 D-1 可侧证);
- 下午/晚间触发的账号比设计多冻十余小时,上午触发的反而提前解冻 —— **冻结终点被钉在固定钟点**;
- "当日第 N 次"的日界在北京时 **16:00**,所以同一天的计数会分散在两个 day key 里(读 `cool_cnt` 必须把两个桶相加)。

## 三、状态文件(易失 + 活体判据)

`STATE_FILE = "/tmp/v6_state.json"`: `acct_inv`(账号簿,账号→企业)、`cool_st`(冻结票)、`cool_cnt`(计数)、`seen_st`、`drain`、`full_hour`。
- 重启 / tmpfiles 清理即全丢 ⇒ 账号簿与冷却计数归零、账号被当新票重打(退避风暴二次放大)⇒ 长期硬化方向是把 state 移出 `/tmp`(如 `/opt/v6/state_<shard>.json`)。
- **最快活体判据**:`stat -c %y /tmp/v6_state.json /opt/v6/v6_run.log` 都在当前分钟 = 在跑。

## 四、tokenrailquery 取票配方(无鉴权 dataplatform)

```
POST https://cg.95306.cn/proxy/dataplatform/api/findList
{"funcId":"tokenrailquery","appId":"system","pageNum":1,"pageSize":500,
 "params":[{"key":"startDate","value":"YYYY-MM-DD HH:MM:SS"},{"key":"endDate","value":"..."}]}
```

- **缺 `params` 窗口返 0 行** —— 调用错误,不是通道失效(最容易误判成"金矿不存在")。
- 翻页至空页 / 不足 pageSize 即止;实测 60min 窗 = 11 页 5,422 行,**连续 11 页零限流**。
- 字段:`userid`(登录账号名)、`username`、`token`(32B,同 bfwz ST)、`login_status`、`user_type_name`(供应商=03)、`login_time`、`login_mode_name`(证书登录)、`ip`、`latitude`/`longitude`、`login_device`、`os_version_number`、`return_url`。
- 可用票过滤 `login_status==1 and user_type=="03"`;供应商票即 bfwz ST,可直接 `user/info` / `getBuyPackageList`(选**新鲜票**,TTL 30–45min 量级)。
- 产量量级(60min):4.3k 不同 userid、2.5k+ 可用票 ⇒ **供给 ≈ 采集消费的 10^2 倍**,产能问题一律不要归因"没票";推进方向只能是①修整机冷却 ②修退避键错位 ③把识别链路从 `user/info` 迁移到该通道。
- 平台级可见(12 台同一批行)⇒ 一台拉、全队用,别 12 台重复拉(会白增平台压力)。
- 归属红线不变:出网只能在采集机(主服不得直连目标),探测脚本经主服 paramiko 跳到采集机执行。

## 五、机队当日产能 sweep(口径必须分日志源)

- 源分支:`[ -s /opt/v6/v6_run.log ]` 为真 → 文件源(sh8-11,`grep "$(date +%m-%d)"`);否则 `journalctl -u v6collector --since today --no-pager`(sh0-7)。
- 指标:轮次(`轮询开始`)、整机冻结(`风控冷却`)、账号冻结(`冷却升级`)、完成(`轮询完成`)、零产出(`新企业包件 0, 识别 0`)、以及 `新企业包件`/`识别` 数值累加(awk 按 `-F"新企业包件 "`、`-F"识别 "` 取字段)。
- 坑:①只查 journalctl 会把 sh8-11 算成"今天 0 轮" → 4 台假死机(先验 mtime);②`grep -c` 对空串算 1,空窗必须 `echo "$X" | grep -ac`;③monitor 的 EVID 计数窗对 sh8-11 是多日,跨台比大小前先取当日(§12)。
- 现成实现:`scripts/fleet_daily_throughput.py`(SFTP 把 shell 脚本推到各机再 `bash` 执行 ⇒ 零引号转义)。

## 六、外部诊断报告的裁定清单

1. 行号/机制描述 → 本机副本 grep 原句,逐条核对;
2. 统计数字 → 采集机重算;单机数字能对上 = 报告可信;
3. 阈值/节奏建议 → 与代码注释里的历史实测对撞(`_BIZ_GAP` 的 2.5s 限流实测、`_cool_backoff` 的"2 次即放弃=永久漏采"血案)→ 冲突的不做,只能 2–3 台 A/B;
4. 单列"报告漏掉的更致命项"(常见三类:退避键错位、时区错位、state 落在 /tmp);
5. 结论分三段给(✅成立 / ⚠️冲突 / ❌漏项),每段给可复现的数字或代码位点;
6. 只读复核(不重启/不 kill/不改采集逻辑),改动方案出计划等用户放行,灰度 2–3 台 × 24h 再全队。
