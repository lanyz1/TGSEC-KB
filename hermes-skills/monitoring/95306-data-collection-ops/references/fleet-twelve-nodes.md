# 95306 采集机 12 台节点表（shard → IP → 服务名）

所有节点：`systemctl restart v6collector`、`Environment=V6_SHARD=<n>`、
conf 在 `<tree>/conf/collector.ini`（tree = `readlink -f /opt/v6/current`）。

| shard | 名称 | IP | 备注 |
|---|---|---|---|
| 0 | 上海 | 8.133.188.178 | 灰度首选 |
| 1 | 宁波 | （见 jumpers.json） | 灰度次选 |
| 2 | 广州 | 8.138.236.124 | |
| 3 | 成都 | 47.108.152.60 | |
| 4 | 上海2 | 8.133.212.134 | |
| 5 | 成都2 | 47.108.173.230 | |
| 6 | 青岛 | 47.104.139.212 | |
| 7 | 深圳 | 47.107.124.62 | |
| 8 | 北京 | 39.96.146.230 | 乌兰察布 IP 被 zb.lyc.cn 拉黑时的备用出口 |
| 9 | 武汉 | 47.122.107.121 | |
| 10 | 乌兰察布 | 8.130.150.18 | |
| 11 | 河源 | 47.115.204.175 | |

**不要硬编码更可靠的做法**（IP 可能变）：从主控读权威清单

```bash
python3 -c "
import json
d = json.load(open('/opt/v6/jumpers.json'))
for c in d['collectors']:
    print(c['shard'], c['ip'], c['port'], c['name'])
"
```

跳板链：本机 `$HOME/.ssh/v6_master_key` → 主控 `207.57.167.92:12971` →
采集机 `/root/.ssh/id_ed25519`（`ssh -n`，**必须 -n，否则 while 循环只跑第 1 台**）。

## 与本表并列的腿

- **登录线(priv)不是采集机上的腿** —— 它跑在**主控**上(`v6m.py priv` 常驻循环,不在 cron/systemd),
  只在出网时经采集机中继。架构 / 产物判读(以 `priv_cov.json` 为权威) / 两层墙 / 已修过的断奶 bug /
  停机与回滚命令:**见 `references/priv-login-line.md`**。
- 因此排查「没有新数据」时先分清是哪条腿:票池线看采集端 `collector.ini` 与票池,
  priv 线看主控的 `priv_tokens.json` / `priv_probe_state.json` / `priv_cov.json`。
