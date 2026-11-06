# 框架解剖：icc / nvpmgr 类 GPU 挖矿劫持框架

> 来源：一份纯技术分析报告（分析者 Corsair-17，代号 `icc`，主伪装名 `nvpmgr`）。
> 报告明确不含目标/IP/凭据；本分册只保留可复用的结构与技法，并把框架自身的
> 指纹当作**检测特征**固化下来。

## 一、三件套组件

| 组件 | 作用 | 关键行为 |
|------|------|----------|
| `boot.sh` | 主逻辑 | 拉起矿机 + 反竞争者 + key 固化 |
| `guard.py` | 进程层杀毒 | 扫 `/proc/*/cmdline`，kill 一切非己矿机 |
| `antirival.rules` | 竞争者黑名单（热加载） | 指纹库，跨主机同步 |

安装根目录伪装成应用数据：`~/.local/share/<app>/.mgr/`。

## 二、四层持久化（它难清的原因）

```
L1 systemd timer  : nvpmgr-heal.timer (~45s) + zzantirival.timer   ← 真正的复活引擎
L2 /etc/cron.d    : zznvpmgr / zznvpmgrg / zznvpmgript / zzantirev  ← 每分钟
L3 root crontab   : 用户级冗余
L4 authorized_keys: 每分钟重写作者键文件，只留自己
```

设计哲学：**每层互为备份，任一层存活即可重建其余全部**。
⇒ 这是"删除任意单层无效"的结构性原因，不是脚本写得好。

## 三、guard.py 反竞争者逻辑（可复用形态）

```python
OUR = re.compile(WALLET + '|' + WORKER + '|nvidia-persistenced --pool')
BAD = re.compile(r'krig-miner|xmrig|nbminer|lolminer|trex|srbminer|peakminer|'
                 r'miner2|kdevtmpfsi|kinsing|rig3748|rev_tunnel|rev_gate_key|'
                 r'/usr/local/bin/frpc', re.I)

# 遍历 /proc/*/cmdline:
#   命中 OUR  -> 跳过
#   命中 BAD  -> kill -9        (另: /tmp/python、含 stratum 的命令行也杀)
# 随后把常见落脚点覆写成 no-op:
#   /tmp/python, /var/tmp/python, ~/.ssh/<tunnel>.sh, /usr/local/bin/frpc
#   => printf '#!/bin/sh\nexit 0\n'
```

三个要点：
1. **纯 stdlib 实现**（`/proc` 扫描 + 正则），零依赖 ⇒ 任何容器/精简系统都能跑。
2. **污染而非删除**：把对手落脚文件写成 no-op，对手重启也白搭 —— 高级"拒绝服务式反制"。
   防守侧反推：机器上出现**内容为 `#!/bin/sh\nexit 0` 的可执行文件**（尤其 `/tmp/python`、
   `~/.ssh/*.sh`、`/usr/local/bin/frpc`）= 有挖矿框架在清场，**是劫持信号而不是自己的清理**。
3. 黑名单是**竞争者矿机名**（krig-miner/xmrig/nbminer/lolminer/trex/srbminer/peakminer）
   + 隧道/密钥名（rev_tunnel/rev_gate_key/frpc）+ 家族名（kdevtmpfsi/kinsing）⇒ 直接当 IOC 用。

## 四、antirival.rules 指纹库（最值得学的情报化设计）

```ini
gate_ip=<redacted>          # 拉黑特定来源 IP
[name_patterns]             # 进程名 / 命令行特征
<miner-binary-names>        # 矿机二进制名
<tunnel-key-names>          # 对手隧道 / 密钥名
<fleet-tag>                 # 对手"舰队"标识
<wallet-address>            # 对手钱包地址
<worker-name>               # 对手 worker 名
[paths]                     # 要污染的路径
[block_ips]                 # iptables 封禁列表
```

情报闭环价值（双向可用）：
- 框架**能反向识别竞争者的钱包 / worker / 脚本 / 来源 IP**，并跨主机同步、动态扩充。
- ⇒ 同一攻击者的钱包/worker 名可作为**跨机关联键**：在一台机器上抓到的 wallet，
  可直接到其它机器/链上活动里检索（"同一运营方判定"思路，见 `operator-attribution`）。
- ⇒ 防守侧拿到 `antirival.rules` 就是一份现成的对手 IOC 清单（其中 `gate_ip`、
  `[block_ips]` 是竞争对手的 IP，**不要**当成攻击者自己的 C2 直接封）。

## 五、矿机存活判定（boot.sh）

```bash
alive=0
if ps -ef | grep -- "--worker <worker>"; then
  u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits \
      | awk '{s+=$1} END{print s}')
  [ "$u" -ge 40 ] && alive=1        # GPU 利用率 ≥40% 才算"活着"
fi
if [ "$alive" = 0 ]; then
  for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do
    kill -9 "$pid"
  done
  # 解包矿机 -> nohup setsid 启动
fi
```

- **用 GPU 利用率当健康探针**，而不是进程存在性 ⇒ 能识别"进程在但没干活"的假活。
- 判定假活后**强杀全部 GPU 计算进程**抢算力 ⇒ 会打断机主正常业务（渲染/训练）。
  ⇒ 防守侧现象：GPU 占用莫名接近 100%、训练/渲染进程被外力 kill、`nvidia-smi` 里
  出现不认识的计算进程，而 `ps` 里那个进程名长得像 `nvidia-persistenced --pool ...`。

## 六、证据留档（框架自带取证意识）

```
evidence_<artifact>.<unix-ts>          # 竞争者每件入侵产物的样本
evidence_<unit>.service.<ts> -> /dev/null
```

⇒ 主机上出现 `evidence_*` 文件即高置信度命中：**框架在保存对手（或你自己）的落地产物**，
文件名带 Unix 时间戳，可用于反查同一攻击者跨机活动。

## 七、画像与致命弱点

- 性质：专业 GPU 挖矿劫持框架（非业余脚本）；持久化 + 反制设计接近 APT 水准（目的仍是挖矿获利）。
- 能力：多主机同步、动态指纹、四层持久化、进程/路径伪装、GPU 级算力抢占、取证留档。
- **致命弱点：复活链最终收敛到 systemd timer 单点 —— 斩断它即全线崩溃。**
  所有其它层（cron.d / crontab / key 固化）都是这条 timer 的下游产物。
