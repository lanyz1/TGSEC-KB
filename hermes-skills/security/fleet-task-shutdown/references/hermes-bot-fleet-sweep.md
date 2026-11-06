# 全机停机实录: Hermes 多 Bot 机队清扫 (2026-10-12)

## 机队布局
- default 档: `~/.hermes/cron/jobs.json` + `executions.db`
- 其他 bot: `~/.hermes/profiles/<bot>/cron/jobs.json` + `executions.db`(实测有 bot2/bot3)
- 每个 bot 由 systemd 网关拉起(hermes-gateway / -bot2 / -bot3);**网关 = 平台空壳,停任务 ≠ 停网关**;停机报告里明确"网关未动(空转)"。
- 其他 respawn 源: `/etc/cron.d/*`(keeper/watch/campaign/doctor 命名,含 每分钟/3分钟/5分钟 级)、`/etc/crontab`、spool crontabs、systemd timers、bot 自带 `scripts/*_watchdog.sh`(与 job 联动补启)。

## 停法与证据(实测可靠)
1. `/etc/cron.d` 12 个 keeper → **mv 到归档目录**(不删);验证 `ls /etc/cron.d/` 只剩系统文件。
2. 跨档禁 job: `hermes cron` CLI 只见当前档(多档不灵),改 **直接编辑 jobs.json**: enabled=false、state=paused(先备份)。全量走完核 still_enabled=0。
3. **fire-point skip 证据法**: 记录禁用时刻,取各 job 的 next_run 时间点,等它过 → `last_run` 不变 = 调度器跳过。多点连验(16:08:52 / 16:10:39 / 16:12:36 / 16:15:41 四点全跳)+ `executions.db` mtime 冻结在禁用时刻 = 铁证。
4. 杀进程: 先干跑清单 → 杀 → ps+端口复查 → 复扫 2-3 遍降到无害基线(编辑器 watcher / sshd / 自己扫描器)。

## 本次清掉的典型目标(下次照着找)
- 本地: ssh 隧道舰队(带 `sleep 3` 自愈循环)、独立隧道×N、会议 ws 轮询、SSH 爆破器(跑了近 5 小时的 spray)、看护脚本;adb server(TERM 无效 → `adb kill-server` 原生收编)。
- 远程: `python3 -m http.server`(18099)、recv 监听(9999)、shellcatch(9977)、转发器 `fwd.py`(公网 8022-8025 → 内网 10.x)、弱口令永动机 `watch3306.sh`(3306 喷洒)、`*/1` APK 替换 keeper(dfkeeper)。

## 远程节点纪律
- 杀完复查: 端口关 + ps 空 + `grep -r 我方字面量 /etc/cron.d /var/spool/cron /etc/systemd/system` 无残留。
- 分清"我方/对方业务": 运营商自家 cron(宝塔 acme/SSL 续期、自家 APK 签名线)、对方文件 = 不动,报告注明。
- **只停进程不删文件**: 工具/战利品文件默认留存(案卷证据),报告里说明位置。
- **死通道纪律**: 案卷里记的入口会烂——web 壳(zrun72.php / x242x.php 类)事后实测 404、SSH key 被拒 = 通道已死;**不重新武装**(不重传 shell、不重打),记录"死火"(残链无指令源 = 静默)结案,不再耗轮次。
- 输出被吞(终端只回 1 行): 重定向 .txt → read_file,复扫与核验都走这个姿势。
