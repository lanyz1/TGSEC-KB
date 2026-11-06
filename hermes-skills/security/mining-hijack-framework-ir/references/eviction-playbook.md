# 清除作业手册：斩 timer → 清表层 → 静置复检

> 本分册是"被 icc/nvpmgr 类框架布点后怎么清干净"的可复制序列。
> 顺序不能反；每一步都要**回读验证**，不能"执行了就算清了"。

## 零、先定性：为什么常规清场会失败（四条血泪）

1. **只删 cron 无效** —— 真正的复活引擎是 **systemd timer**；删 cron 后 timer 秒级重建 cron。
2. **只 kill 进程无效** —— `Restart=always` 让进程秒级复活。
3. **只删文件无效** —— 只要任一钩子存活，目录/文件被重建。
4. **不静置就下结论 = 误判** —— 一次清完立刻复检"干净"，60 秒后全回来了。

⇒ 铁律：**清完必须静置复检 ≥60 秒（超过 timer 周期）**，并把复检结果落到案卷。

## 一、取证（清理前，只读）

```bash
# ① 全量布点（本卡探针，只读，不 kill 不改文件）
python3 icc_triage.py --root / --json --out /tmp/icc_triage_$(date +%s).json

# ② 把四层布点各自留档（后面复活与否靠它对照）
systemctl list-timers --all | grep -Ei 'nvpmgr|antirival|heal'
systemctl list-unit-files | grep -Ei 'nvpmgr|antirival'
ls -la /etc/cron.d/ | grep -E '^.*zz'
crontab -l; crontab -u root -l
for f in /root /home/*; do ls -la $f/.local/share/*/.mgr/ 2>/dev/null; done
grep -rn 'nvpmgr\|antirival' /etc/systemd/system /lib/systemd/system /usr/lib/systemd/system 2>/dev/null
stat -c '%n %y %s' /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null
ps -eo pid,ppid,lstart,cmd | grep -E 'persistenced --pool|\.mgr/|krig-miner|xmrig' | grep -v grep
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
ss -tnp | grep ESTAB | grep -vE ':22 |:443 '        # 矿池/隧道外连
ls -la /tmp/python /var/tmp/python /usr/local/bin/frpc 2>/dev/null   # 被污染成 no-op 的痕迹
```

## 二、斩 L1（systemd timer / unit）—— 先斩根，别先删 cron

```bash
# 1) 停 + 禁 + 删 unit（timer 与 service 都要）
for u in nvpmgr-heal.timer nvpmgr-heal.service zzantirival.timer zzantirival.service; do
  systemctl stop    "$u" 2>/dev/null
  systemctl disable "$u" 2>/dev/null
done
systemctl list-unit-files | grep -Ei 'nvpmgr|antirival'   # 确认 enable 状态已断

# 2) 找 unit 文件真实落点（可能在 /etc/systemd/system 之外）
grep -rl 'nvpmgr\|antirival\|\.mgr/' /etc/systemd/system /lib/systemd/system /usr/lib/systemd/system 2>/dev/null

# 3) 删文件 + 重载（daemon-reload 必须做，否则内存里还有单元）
rm -f /etc/systemd/system/nvpmgr* /etc/systemd/system/zzantirival* ...
systemctl daemon-reload
systemctl reset-failed 2>/dev/null
```

⚠️ 若 unit 被 `chattr +i` 锁住：`chattr -i <file>` 解锁后再删（`lsattr` 看到 `-i-` = 防清理锁）。

## 三、清 L2/L3（cron）

```bash
chattr -i /etc/cron.d/zznvpmgr* /var/spool/cron/root 2>/dev/null
rm -f /etc/cron.d/zznvpmgr /etc/cron.d/zznvpmgrg /etc/cron.d/zznvpmgript /etc/cron.d/zzantirev
# 别只删 zz 前缀：内容含 nvpmgr/.mgr//stratum/--pool 的都要清（框架会改名）
grep -rlE 'nvpmgr|antirival|/\.mgr/|stratum|--pool|xmrig' /etc/cron.d /etc/crontab \
     /etc/cron.hourly /etc/cron.daily /var/spool/cron 2>/dev/null
crontab -r; crontab -u root -r 2>/dev/null          # 用户级冗余
```

## 四、多轮 kill + 删目录 + 换键（L4）

```bash
# 1) 多轮 kill（不能只 kill 一轮：timer 重建窗口内可能拉起新 PID）
for i in 1 2 3; do
  pkill -9 -f 'nvidia-persistenced --pool' 2>/dev/null
  pkill -9 -f '\.mgr/' 2>/dev/null
  for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null); do
    kill -9 "$pid" 2>/dev/null                    # 抢回 GPU（会打断机主业务，先确认授权）
  done
  sleep 5
done

# 2) 删框架目录与载荷（含伪装缓存/随机 profiles 路径）
rm -rf /root/.local/share/<app>/.mgr /home/*/.local/share/<app>/.mgr
rm -f  /root/.cache/*/.v3/gl_blob_*.dat /home/*/.cache/*/.v3/gl_blob_*.dat
# 保留 evidence_* 做取证，再单独归档（是框架留档，别当垃圾删掉）

# 3) 键重置：只留自己的 key（框架会定向删除对手 key，所以先看有没有对手残留）
cp /root/.ssh/authorized_keys /tmp/ak.bak.$(date +%s)
grep -vE 'nvpmgr|heal|antirival|guard' /tmp/ak.bak.* > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
grep -c '^ssh-' /root/.ssh/authorized_keys           # 与预期 key 数一致
```

## 五、静置复检（本役验证有效的收尾）

```bash
# 静置 ≥60s（超过 timer 周期 45s），再跑一遍全量复检
sleep 75
systemctl list-timers --all | grep -Ei 'nvpmgr|antirival'
ls -la /etc/cron.d/ | grep -E 'zz'
python3 icc_triage.py --root / --json          # 期望 verdict=CLEAN
ps -eo pid,cmd | grep -E 'persistenced --pool|\.mgr/' | grep -v grep   # 期望空
nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits   # 期望回落到正常
```

- 复检**再做一轮**（隔 5-10 分钟）更稳：框架的 cron 是"每分钟"，一次静置可能刚好错过一轮。
- 仍复活的定位法：`systemctl list-timers --all` 里找"下次触发时间很近"的陌生 timer，
  以及 `journalctl -u <unit> --since '-10min'` 看是谁在拉起它（往往 timer → cron → 目录重建链）。

## 六、必做的边界判定（别误清自己 / 误清运维）

- `authorized_keys` 里非预期 key ≠ 一定是攻击者：可能是**自己的持久化 key**或运维平台 key。
  先 `grep -l <自己的 key 名/secret>` 或对照自己的清单文件确认归属，再决定删不删。
  （同类纪律见 `attacker-eviction-hardening`：清场前先盘自己的家当。）
- `/tmp/*.py`、`/usr/local/bin/frpc` 内容是 `#!/bin/sh\nexit 0` ⇒ 是**挖矿框架污染**的产物，
  不是自己的清理；但若是自己的隧道脚本被对手污染，恢复要重新投递真实脚本。
- 该框架的目标是**算力**而非数据：清完后按 `host-ir-check` 复跑常规后门面（ld.so.preload /
  隐藏 uid0 / 监听口），确认没有被顺手装 key/后门之外的持久化。
- 同一团伙通常**同批同构机器**都有布点 ⇒ 清一台要顺手扫同批（同 IP 段/同镜像/同跳板来源），
  否则清过的机器会被邻居的同步逻辑重新布点。

## 七、防守侧把框架特征反过来用

- 黑名单直接当 IOC：`krig-miner|xmrig|nbminer|lolminer|trex|srbminer|peakminer|miner2|
  kdevtmpfsi|kinsing|rig3748|rev_tunnel|rev_gate_key|frpc`。
- 命名规律当检测规则：`zz` 前缀 cron 文件、`nvpmgr*` 单元、`.mgr` 目录、`gl_blob_*.dat`、
  `profiles/p<hex>/`、`evidence_*` —— 都可写成 Sigma/YARA/auditd 规则
  （见 `detection-engineering-sigma-attack`、`yara-rule-authoring`）。
