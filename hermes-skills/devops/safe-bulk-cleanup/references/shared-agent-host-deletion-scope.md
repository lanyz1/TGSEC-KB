# 共享多 agent 主机上的清理范围纪律（含归属判定 full playbook）

触发：本机跑着多个 agent/机器人（共享宿主机），用户让「清理打扫磁盘/释放空间/不要的都删掉」——尤其是追加限定「别清理到其他机器人在执行的任务」。

## 铁律（不可越界）
- 删除范围 = **自己名下 + 已完结 + 零活跃引用** 的案卷 + 系统缓存（apt/journal/tmp/trae 死日志等）。同机其它 case 可能属于别的 bot 正在跑的任务，**永不触碰**。
- 即使用户说「都删除掉」，那句通常指**你自己早前的目标产物**，不是别人目录。
- 拿不准 → 一律归 KEEP 并写进保留清单（宁留勿删）。
- 收尾必写：删了什么 / 保留什么+理由 / before→after df。用户最高优先级检查项 = **其他 bot 零误伤**（附证据）。

## 1. 热区图（动手前第一步，先侦察再动手）
```bash
ls -l /proc/[0-9]*/cwd 2>/dev/null | grep -o "/root/cases/[^/]*" | sort | uniq -c | sort -rn
ls -l /proc/[0-9]*/fd  2>/dev/null | grep "cases/"
```
有活进程 cwd 的案卷 = 正在跑的任务（可能是别 bot）→ 直接拉黑。**进程数=活跃度**（2026-10-10: zhitian 56 / mark.the9.cloud 12 / reliefs 8）。

## 2. 归属四查（每个退役候选逐一过）
1. 热区扫描（上）+ 该 case 的 /proc/*/fd 占用；
2. **运行设施引用**：`/etc/cron.d/*`、`/root/.hermes/scripts/`、自身 cron jobs 里的路径引用；
3. `session_search <case名>` 判自有/他人（历史会话原话可实锤归属）；
4. 终版报告 + 完结标记（「完结封卷/FINAL/交付」= 可退役；「持续中/未拖/未拿」= 未完结，留）。

**借用资产规则（核心新教训）**：一个 case 的 SSH 钥匙若被**别的 bot 正在跑的隧道保活脚本**周期性引用（保活循环每轮重读，如 `grep -rl <keypath> /root/cases/<other>/` 命中 zhitian 的 ssh_tunnels*.sh），即使 cwd/fd 零命中也**不可删**。3.8G 的案卷就是这么保下来的。

## 3. 结论分级
- **RETIRE**：自有 + 有终版报告 + 冷（四查全空）→ 归档→删大件。
- **KEEP**：别 bot 活跃案（zhitian/mark 类）/ 借用资产宿主 / 自有未完结 / 活数据（state.db）/ 其他 profile 目录 / 跳板与隧道设施。

## 4. 退役协议（2026-10-10 实操）
- 归档 `/root/reports/old-campaigns/<case>/`：≤300K 文本（*.md/*.txt/*.py/*.sh/*.json/*.html/*.csv）+ 指定豁免件（jwt_secrets.txt、*FINAL*.zip ≤10M）；大件（扫描输出、dump、工具罐）直接删。
- 每个 case 删前守卫：`ls -l /proc/[0-9]*/cwd 2>/dev/null | grep -cF "cases/<name>"` 非零 → skip；全部动作落 manifest。
- 本轮战果：9 冷案退役（xn30r787a 1.8G / sumdapp / 38.47 / firstgo / tgetitx / mshws / 143.14 / akunosai / tousphl）≈3.2G，小件归档 152M。

## 5. Hermes 活数据纪律
- `state.db` 只读测可回收量：`file:/root/.hermes/state.db?mode=ro` → `PRAGMA page_count/freelist_count/page_size`；freelist 极小（如 179 页≈1MB）= 全是活数据 → **不动**。
- 禁止对多 GB 库跑 `COUNT(*)`（超时）；禁止 vacuum/替换 gateway 正持有的库。
- 其他 profile 目录（botA/botB）只读盘点，永不修改。

## 6. 脚本卫生
- 清理脚本一律 `execute_code` 写盘——`write_file` 会静默截断（连 9 行 kill 脚本都截过）；跑前 `bash -n` 语法检查；每条 rm 都带守卫 + manifest。

## 教训来源
- 用户警告「别删除掉其他机器人的东西了」→ 越界必挨骂；多 bot 共享机上这是最高优先级安全约束。
- 2026-10-10 全量复盘：93%→80%（-6.1G），9 案退役、8 项保留零误伤（别 bot 活跃 56+12 进程、借用资产宿主、2 个自有未完结案全在）。
