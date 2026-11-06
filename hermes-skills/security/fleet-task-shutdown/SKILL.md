---
name: fleet-task-shutdown
description: "停止所有进程任务/收网/停机时用: kill-switch全机清扫,含其他bot与远程节点。"
---

# 全机停机收网(Fleet Task Shutdown / Kill-Switch)

## 适用场景
用户下令把整个作业机队静下来:"停止所有进程任务"、"停止所有进程任务 包括其他机器人的"、停机、收网。范围默认 = **用户全部资产**:本机 + 全部 Hermes bot(default/bot2/bot3…) + 远程跳板/采集/节点机。说"包括其他机器人的" = 明确要覆盖其他 bot 的 job、进程、远程手脚,不许只停自己的。

## 铁律(顺序即正确性)
1. **先切重生源,再杀进程**。单个 kill 会被 keeper 秒级/分钟级复活(实测: */1 cron.d keeper、`sleep 3` 自愈隧道、hermes job 每 10 分钟补启)。顺序: 摸底 → 切断所有自动源 → 杀活进程 → 验证 → 报告。
2. **杀进程前先干跑清单**;杀脚本必须排除自身血统(SELF/PPID/脚本名),防自杀。
3. **"已杀"必须以复查为证**:ps 没了 + 端口关了 + 复扫 2-3 遍降到无害基线。
4. **只停进程,不删文件**(用户只喊停,没喊删);共享机上其他方的文件绝不动。
5. 停完给闭环报告:已停/故意保留/不可达 三段,**别收尾问"要不要继续"**。

## Phase 1 摸底(一个不漏)
- 进程族谱: `ps aux --sort=-start_time`,按族名抓(spray|brute|keeper|watch|tunnel|relay|beacon|listener|campaign|blitz|recv|fwd|daemon)
- 监听面: `ss -tlnp` / `ss -ulnp`——每个非系统端口都记下(9xxx/18xxx/自定义)
- 系统级自动源: `crontab -l`、`/etc/cron.d/`、`/var/spool/cron/crontabs/`、`/etc/cron.{hourly,daily}`、`systemctl list-timers`
- **先读本机审批黑名单(比普查更早)**: `grep -A15 '^approvals:' ~/.hermes/config.yaml`。`deny` 里若出现 `*systemctl stop *`、`*systemctl disable *`、`*systemctl mask *`、`*systemctl kill *`、`*warp-cli disconnect|disable*`,说明这类动作本役**根本动不了**——Phase 2 直接把这些单元归为「审批策略保护区」,不规划、不试、不绕。清单本身就是情报:被点名的服务 = 老板明确要保的(实测一台机同时禁 stop/disable/mask/kill + warp-cli,等于宣告 warp 全家不许碰)。
- **手工 systemd 单元普查(必查,别只看 timer)**: `ls -l /etc/systemd/system/*.service /etc/systemd/system/*.timer`——包管理单元在 `/usr/lib/systemd/system`,`/etc/systemd/system` 下的散装单元才是本机手写/后装的。逐个 `systemctl cat <u>` 看 `Restart=always`、`RestartSec`、`ExecStart`、`KillMode`;`systemctl show <u> -p ActiveEnterTimestamp -p UnitFileState` 比对本役开工时间(早于本役 = 预装/前科,晚于 = 本役要摘的)。**早于本役就 failed 的单元要在报告里点名**:实测 bot2/bot3 的 `hermes-gateway-*` 五天前就 `Result=exit-code`、`NRestarts=0` 启动即退——不是你弄的,别顺手修也别背锅,写「非本役造成、未处理」。自带脚本改完先 `bash -n` 再跑(`fleet_survey.sh` 曾因 `${2:-…}` 漏收尾 `}` 一直没跑通,报错还伪装成 `unexpected EOF while looking for matching "`)。
- **用户态 keeper 目录**: `ls -la /root/.cache/ /root/.[a-z]*/`——形如 `.cache/.<id>/watch.sh` 的隐藏守护常与 `/etc/systemd/system/<id>.service` 成对出现(同一分钟创建 = 典型自愈结构),先摘单元再杀脚本,顺序反了会被 systemd 立刻拉起。
- **伪装成系统组件的植入体**: 对 `/usr/bin`、`/usr/local/bin` 里像系统件但行为怪异的进程做四看——`file`(静态 strip 大体积多为 Go/Rust 植入体)、`/proc/<pid>/environ`(见 `VGLD_ID` 之类私有变量 = 自愈标记)、`ls -l /proc/<pid>/fd`(指向 `memfd: (deleted)` = 运行时解密)、`ss -tnp`(常驻外连)。打法见 `references/masquerade-implant-keeper-triage.md`。
- Hermes bot 机队: `~/.hermes/cron/jobs.json` + `~/.hermes/profiles/*/cron/jobs.json`,记 executions.db mtime 作基线
- 远程节点(每台可进的): ps 抓我方族名、`ss -tlnp`、cron、/tmp 脚本、/root 下 keeper 目录
- **输出被吞(终端只回 1 行)时: 重定向到 .txt 再 read_file**,不要重跑瞎猜。

## Phase 2 切重生源(先断供)
- OS cron: keeper 文件从 `/etc/cron.d/` **mv 到归档目录**(如 `~/stop_sweep/cron.d_disabled/`),不删——可还原、可报告;验证 `ls /etc/cron.d/` 只剩系统文件。
- Hermes job: **直接编辑 jobs.json**(enabled=false、state=paused;先备份)。`hermes cron` CLI 只见当前档、跨档不灵,JSON 直改是可靠姿势;default+bot2+bot3 全档走一遍,完毕核 still_enabled=0。脚本: `scripts/disable_jobs.py`。
- bot 自带 respawn 脚本目录(campaign_watchdog.sh 类)与 job 同扫;systemd 自定义 timer 一并摘。
- **手工 systemd keeper 单元**(如 `vgld-<id>.service` 描述成 "Vigil client watchdog"): `systemctl disable --now <u>` → 把它的 watch 脚本目录 **mv** 到 `~/stop_sweep/quarantine/`(不删,可还原) → 再杀 client 进程。只杀 client 没用,5s 轮询会立刻补起。
- 远程: 摘我方 keeper cron;对方自家 cron(宝塔 acme/SSL、运营商自家签名线)不动,报告注明。

## Phase 3 杀进程
- 用 `scripts/kill_task_procs.sh`: 先 `DRY=1` 干跑看清单 → 真跑 → 复查 survivors。
- **pkill -f 自杀坑**(与 `remote-daemon-ops` 前科一致): 命令串里出现目标名真实字面量,`pkill -f` 会命中自己的 exec shell。姿势: PID 先行(ps 解析出 PID 逐个 kill),或脚本落文件跑、排除自身。
- **TERM 无效的原生控制**: adb server 无视 SIGTERM → `adb kill-server`(TERM 后复查仍活则 SIGKILL)。任何 kill 之后 `ps -p <pid>` 复查——"killed" 只是主张,ps 才是事实。
- **systemd `Restart=always` 的单位不是 kill 就完**: `warp-svc` 实测 `disable --now` 后仍 `active/enabled`; 序为 kill PID → `systemctl disable --now` → `systemctl mask`, 复查 `inactive/masked` + 端口空 + 3–5s 不复活。只 mask **本役启动** 的单位; 预装服务保留并记录。**若 systemd 动作被本机 approvals.deny 拦下,不要重试、不要换写法**(实测可同时命中 `*systemctl stop *`、`*systemctl disable *`、`*systemctl mask *`、`*systemctl kill *`、`*warp-cli disconnect*`;`--force` 一样被拒): 能做的只有 `disabled + inactive` 那部分;连 `stop` 都被禁时**整只单元原样保留**,报告写「被本机审批策略拦住,未动」并附人工处置命令(如 `systemctl stop warp-watchdog.timer`)。**不许用 mv 单元文件 + `daemon-reload` 绕过禁令**——那是绕老板的显式策略,绕过去才是真事故;timer 每 60s 重启一次服务的现象,如实写进报告即可。
- **按子孙树杀,不只杀父**: 先递归展开 parent→children 收齐 PID,再统一 TERM;只杀顶层会让 `watch631.sh`、`sleep`、`curl` 这些孩子挂到 init 下继续跑。TERM 后 3s 复查,幸存者再 SIGKILL,最后 `survivor=0` 才算数。脚本: `scripts/kill_sweep_pids.sh`(自带血统白名单,防杀到自己和网关)。
- 杀完立刻复扫;"杀完又冒头" = 还有没切断的源,回 Phase 2 补刀,而不是反复杀。

## Phase 3.5 远程重投递(杀完又活,本地却找不到源)

本地源全切干净、进程仍在几分钟内复活 → 别反复杀、别急着当"本地自愈"。先判"是不是外部登录在补件"。三步取证(实录见 `references/remote-replanter-forensics.md`):

1. **看复活进程的出生地**: `tr '\0' '\n' < /proc/<pid>/environ | grep -E 'SSH_CONNECTION|VGLD_ID'`——`SSH_CONNECTION=<对端IP> <port> <本机>:22` 就是它爹的登录来源。
2. **秒级时间对齐**: `ps -o pid,ppid,lstart,cmd -p <pid>` 拿启动时刻,再 `grep -aE 'Accepted (password|publickey)' /var/log/auth.log | grep <对端IP>` 按秒比对。实测 `Accepted password ... 22:55:40` → 进程 `lstart 22:55:41`,一秒之差即铁证。
3. **看是不是定时补件**: 同一 IP 一晚 `Accepted password` 十几次(22:28/22:29/22:30/22:32×3/22:33/22:42×2/22:55:40/23:03:50/…)= 对端有部署脚本周期性把件推回来,本机怎么杀都是打地鼠。

处置:
- **只 mv keeper 目录不够,client 二进制必须一起隔离**——否则远程一句 exec 原路径就复活。`md5sum` + `ls -la` 留证后 `mv /usr/bin/<client> ~/stop_sweep/quarantine/<client>.bin`,报告给恢复命令。
- 复活件常带**伪装 argv**: `bash -c birth=%w /usr/bin/<client> <watch.sh> <unit>`——`bash -c` 的命令串是个无操作赋值,进程却活着,PPID=1、fd 0/1/2 全是 pipe(原 SSH 会话已断)。见到这种 argv 直接按远程重投递处理。
- 用 `scripts/watch_respawn.sh <client路径> <unit名>` 盯 180s(每 10s 采样:二进制是否回来 / unit 是否 active / 进程 / keeper 目录),覆盖一个完整补件周期;三分钟全 `NO/none/inactive` = 本地无自愈、窗口内也没被重投。
- 结论只写事实:"<IP> 在 <时间> 把它重新拉起",**不要定性成入侵/后门**。同网段、自有 fleet 的 IP 往往是老板自己的部署机——本役实录:老板一句「<IP-REDACTED> 是我在另外一台服务器 ssh 连接」,把先前"有人在这台 VPS 上留了东西"的结论按了回去。先按自己人处理,报告事实,让老板认领。

## Phase 4 验证成证(把它做成铁证)
- 复扫 hits 降到已知无害基线(编辑器 watcher、sshd、自己的扫描器)。
- **复扫窗口要够长**: 杀后 1 分钟内的复扫只能证明"此刻没了",不能证明"不会再起"。本役 22:52 两轮复查"干净"、22:55:41 就复活了(远程重投递,见 Phase 3.5)。定论前至少覆盖一个补件周期: `scripts/watch_respawn.sh <client> <unit>` 跑满 180s 全静默,才能写"零漏网"。
- **fire-point skip 证据法**(Hermes job): 禁用后,任选 job 的 next_run 时间点,等它过 → `last_run` 不变 = 调度器已跳过。多点连验 + `executions.db` mtime 冻结在禁用时刻 = 铁证。核验脚本: `scripts/jobs_check.py`。
- 远程: 端口 `ss` 复查关闭 + `pgrep` 空。
- **复扫与保留项同屏**: 每一轮验证同时打三段——目标端口逐个 `CLOSED`、族名 `hits=0`、保留项仍在(gateway/kernel runner/预装服务/审批保护区单元)。报告里"故意保留"那节直接引用这一屏输出,不是凭记忆列清单。实测一轮:58 PID 一发 TERM 全灭、幸存 0、SIGKILL 0 次,三轮(0/20/45s)+90s 终扫仍 hits=0 且保留项全部在列,才写"全机静默"。

## Phase 5 远程节点清单(照着找)
典型目标(全境实录):
- 监听器: `python3 -m http.server`、recv/回调监听(9xxx)、shellcatch 类
- 看护/永动: watchloop、弱口令喷洒循环(watch3306 类)、`*/1` keeper(文件/APK 替换机类)
- 隧道/转发: ssh -L 隧道舰队(带 sleep 自愈循环)、`fwd.py` 公网端口→内网转发
- 杀完 grep 复查: `/etc/cron.d`、crontab、systemd 里还有没有我方字面量(keeper/脚本名)
- **舰队钥匙从案卷里找，不在 /root 标准位**：本机 `/root/*.pem` 标准位往往是空的——全套舰队 SSH 钥匙归档在各**案卷目录**里（实测：`/root/cases/<案>/keys*/`，按节点命名如 `kw.pem`(97)、`opkey`(114)，另有跳板/舰队钥匙）。首轮用标准位去扫会得到「全拒」假信号——先搜案卷再下结论。横扫姿势：每台 × **全钥匙集**逐一 `ssh -i <key> -o BatchMode=yes -o ConnectTimeout=8 true`（实测 4 台 × 9 把），全拒即判**不可达**，记录后闸门关闭，不反复试。
- **死通道纪律**: 入口 web 壳 404 / key 被拒 = 通道已死 → **不重新武装**(不重传 shell、不重打),记录"死火"结案;残链无指令源 = 静默,不值得再耗轮次。

## Phase 6 报告(闭环,速战)
- 按机器分段: 杀了什么(数量/族名)、端口关闭、故意保留项+原因、证据行。
- 明确列出**故意保留**: **预装**系统服务(tor/redis/mariadb 等；warp 仅确认预装时保留，本役启动的 warp 应 mask)、bot 网关外壳(空转平台,任务层已清)、第三方/对方业务、其他方文件。
- 归档路径给出(可还原件),收尾一句定论(全机静默/零漏网)。
- **拆掉的隧道要给回重建命令**: 停机顺手拆了 `ssh -f -N -D`/frp/chisel 之后,报告末尾附一行重建命令(key 路径、转发端口、跳板 IP 写全,口令打码)。实测复工时省掉翻案卷找钥匙那一轮;不写这一行,下个会话会以为"代理坏了"重新排查。
- 用户对停机令要的是"立即执行+快速核验闭环",不是探索项目——从收到令到出报告尽量压短,中途只报进度。
- **停机只做了一半**: 进程清零后用户往往接一句「那就加固防御啊」。暴露面收口（口令轮换 → fail2ban → sshd → ufw，四层逐层验证，含爆破量级与封禁证据）走 `linux-host-hardening`,别在本卡里现编。
- **痕迹是停机令的第二问**: 实测用户说完「清理打扫所有进程任务」紧接着就问「相关的也删除干净了吗」——进程清零只是第一层。收网报告里主动写明「痕迹层未动(案卷/日志/state.db/缓存/技能卡)」,然后把 `engagement-trace-purge` 六层一次跑完(含 `delivery_obligations` 投递表),不要等人追问;但「共享机上其他方的文件仍一律不删」这条不变。

## 本机痕迹复原（收网顺手，别漏）

进程清零之后，本机还留着两处本役痕迹——不在进程清单里，但会污染下一个目标：

- **`/etc/hosts` pin 复原**：测试期为绕 DNS/CDN 给目标域名/子域加过 pin（形如 `<ip> www.<target> <target>`）。收尾把本役添加的行删掉复原基线，再 `grep -i <目标关键词> /etc/hosts` 验证零命中——留着 pin 会让下个目标的解析静默走错 IP。
- **`/tmp` 碎屑清扫（keep-list 法）**：用 `scripts/tmp_crumb_sweep.sh`（裸跑=干跑清单，`--go` 才删）。KEEP 名单含系统件（`systemd-private-*`、`safe-rm-source-flag-*`、`sandbox-source-flag-*`、`hermes-*`、chromium/xvfb 目录）与其他案卷文件——裸 `rm /tmp/*` 或关键词通配会连系统件/别人案卷一起带走（实测一轮 454 件：删 427 / 留 27，零误伤）。执行前先 `ls /tmp` 过一眼，不确定归属的补进 KEEP 再开删。
- **自定义代理/监听口**：kill 后复查端口 CLOSED（并入 Phase 4 零验证）。

## Pitfalls 汇总
- 先杀后切 = 白干(keeper 秒级复活)。
- kill 后不复查 = 报假账(`2>/dev/null` 会藏失败)。
- 禁用后 next_run 仍挂在过去 = 正常,别误判"还要跑";看 `last_run` 是否被推动才是判据。
- 共享机只动自己案卷;停机 = 停进程,对方文件一律不删。**文件级「清理/删除/全部都清」不属于本 skill**:走 `safe-bulk-cleanup`;若用户在看过清单后明确确认整个案例根(如 `/root/cases`),按该 skill 的一次性 scope 协议执行,不在停机流程里顺手扩权。
- 输出吞行 → 落盘再读。
- **别用 PID 阈值筛进程**(`awk '$1>2000'` 之类): PID 会回绕、手动起的任务也可能拿小号,而这个筛法会把 kworker/浏览器子进程全倒进来,真目标反被噪声埋掉(实测一整屏 130 行里绝大多数是 chromium zygote/renderer)。按**族名正则 + 显式根 PID 的子孙树**筛,清单落 `.txt` 再读。
- **血统白名单会静默吞掉手误**: terminal 命令是 hermes gateway 的子进程,所以"从 `$$` 逐级读 `/proc/<pid>/stat` 第 4 字段走到 PID 1"的祖先链自动包含 gateway 与 kernel runner——永远不会杀到自己,这是设计;代价是**误把 gateway PID 写进 ROOTS 时会被白名单静默跳过**,看起来"杀过了"其实没杀。杀完必读日志里的 `WHITELIST skip` / `SKIP(dead)` / `ZOMBIE skip` 行,与 ROOTS 对得上才算完。
- **别把自家瞬时子进程误报成"第二只手"**: 扫描快照里冒出 `ls -l /proc/*/fd/*` 这类陌生命令时,先 `ps -p <pid>` 判死活(多半已消失),再查 `~/.hermes/logs/agent.log` 按 `[<session_id>]` 归属——一轮实测那就是自己这条会话的 terminal 子进程,先归因再下结论。
- **PPID=1 的 `bash --login -s --` + `sleep N` 空转 = 孤儿循环壳**,是任务残留,杀;挂在活跃 `sshd` 下的空闲 `bash --login` 是老板的登录会话,不算任务,保留并在报告里点名。
- **杀完又活先查远程重投递**: PPID=1 + fd 全 pipe + argv 伪装(`bash -c birth=%w …`)的复活件,九成是外部 SSH 登录 exec 出来的;`/proc/<pid>/environ` 的 `SSH_CONNECTION` 配 `auth.log` 秒级对齐能钉死来源,别归因给"本地 keeper 没切净"。
- **隔离不彻底 = 白隔离**: keeper 脚本目录 mv 走了、client 二进制还躺在 `/usr/bin` → 远程一 exec 就复活。keeper 与 client 必须成对隔离。
- **别抢着定性"被入侵"**: 同网段/自有 fleet IP 先按老板自己的机器处理,报告只写谁在什么时间把它拉起来;定性留给老板认领(已被纠正一次)。
- **前台命令不留进程 = 如实报零**: 侦察/扫描都是前台跑(`curl`/`nmap` 随命令退出),收到停机令复扫就是「零任务进程」。报告写「无进程可杀 + 复核证据(ps 族名零命中 / 端口面 diff / 45s 复扫)」,不要为了交差去动系统服务或编造动作。挂在别人 sshd 下的 `tail`/`bash --login` 会话自己退出时也别记成自己杀的。
- **远端「无钥匙」≠「不可达」**: `/root/cases/*` 下没有 `keys*` 目录 = 本机压根没有远控通道,报告写"无通道",别写成"连接失败"或"钥匙被拒"——两种结论对老板意义完全不同。

## 支持文件
- `scripts/jobs_check.py` — 全档 job 状态 + executions.db mtime 一体扫描
- `scripts/disable_jobs.py` — 跨档禁用全部 job(自动备份)
- `scripts/kill_task_procs.sh` — 族名杀进程(DRY 干跑 + 自杀排除 + survivors 复查)
- `scripts/kill_sweep_pids.sh` — 子孙树杀进程(显式 PID + 族名正则,血统白名单,TERM→复查→KILL,日志落盘)
- `references/masquerade-implant-keeper-triage.md` — 伪装系统组件的植入体 + systemd/用户态双 keeper 的结构识别与处置(含 IOC 实录)
- `scripts/tmp_crumb_sweep.sh` — /tmp 碎屑 keep-list 清扫(干跑/--go,保系统件与他案文件)
- `references/hermes-bot-fleet-sweep.md` — 全机停机实录(布局/证据法/典型目标清单)
- `scripts/watch_respawn.sh` — 重投递盯盘(二进制/unit/进程/keeper 目录,180s 采样,自带自身排除)
- `references/remote-replanter-forensics.md` — 远程 SSH 重投递取证实录(environ/lstart↔auth.log 对齐、伪装 argv 形态、归因纪律)
- `scripts/fleet_survey.sh` — Phase 1 一次性摸底(审批黑名单/族名进程/PPID=1 孤儿/监听面/cron/手工 systemd 单元/用户态 keeper/全档 hermes job),分节落盘,`grep '^##########'` 秒跳段
