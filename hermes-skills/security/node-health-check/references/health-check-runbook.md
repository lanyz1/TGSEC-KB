# 节点健康自检 Runbook — 完整命令清单

## 1. 系统层
```bash
date; uptime; df -h /; free -h
systemctl --failed --no-pager | head -5
pgrep -af hermes        # 网关进程存活与启动时长
```
- failed unit 先分类：装饰性服务（fwupd / networkd-wait-online 类）报一句即可；关键服务 failed 才升级为故障。

## 2. Hermes 内核
```bash
hermes doctor                       # 只看 tail；⚠ 与可选 key 缺失 = 观察项
ls -lt ~/.hermes/logs/ | head -6
tail -30 ~/.hermes/logs/gateway.log # 收发链路：inbound/response/Sending 成对出现
tail -25 ~/.hermes/logs/errors.log
sqlite3 ~/.hermes/state.db "PRAGMA integrity_check; SELECT COUNT(*) FROM sessions;"
ls ~/.hermes/plugins/
cat ~/.hermes/cron/jobs.json        # 队列是否符合预期（空队列 + 有任务预期 = 异常）
cat ~/.hermes/cron/ticker_heartbeat # 心跳新鲜 = 调度器活着
ls -lt ~/.hermes/sessions/ | head -8
wc -c ~/.hermes/memories/*.md
```
- 网关健康判据：进程在 + gateway.log 近期收/发日志对 + ticker 心跳新鲜，三者齐备。
- 崩溃史诊断：`tail -40 ~/.hermes/logs/gateway-exit-diag.log`——看 exit 75/SystemExit 循环后最后一次 `gateway.start` 的时间戳是否延续至今；延续 = 自愈。

## 3. 模型链路
```bash
grep -A4 '^model:' ~/.hermes/config.yaml
grep -oE '^[A-Z_]+=' ~/.hermes/.env   # 只看 key 名，不输出值
grep -c AuthenticationError ~/.hermes/logs/errors.log
grep -n AuthenticationError ~/.hermes/logs/errors.log | cut -c1-120   # 定位时间窗
```
- 401 判据：全部落在单会话时间窗且之后零复发 = 上游中转瞬时抖动；分散出现 = 凭据/配置病。

## 4. 装备链（实测，不凭档案）
```bash
for t in nmap sqlmap nuclei subfinder httpx gobuster ffuf ammo spray rotate_proxy.sh; do
  printf "%-16s %s\n" "$t" "$(command -v $t 2>/dev/null || echo MISSING)"; done
timeout 30 rotate_proxy.sh curl -s --max-time 20 https://api.ipify.org   # 出口 live probe
```
- 装备清单按当前部署增删（postex 目录、/opt 工具、字典库路径可按需追加 `ls` 核验）。
- 脚本形式部署的工具（asset_search.sh/.py 类）报实体路径，不算 MISSING。

## 5. 就地修复与复验
- 修什么验什么：修复动作完成后，对原故障面重新执行触发该判定的检查，确认转为健康，再进报告。
- 技能重名：比对两份 SKILL.md，保留正式版（版本 frontmatter + references/templates 结构），旧快照 `mv ~/.hermes/skills/<name> ~/.hermes/backup/<name>-stale-<date>/`，然后 `skill_view <name>` 确认不再 ambiguous。
- npm 依赖漏洞类：给 `hermes doctor --fix` 作为观察项修复命令，不在自检中现场升级（改动面大，属独立维护动作）。

## 自检期间的已知拦截
- 装备盘点命令命中 skill-enforcer 域签名（recon/sqli 类）→ 点名 `skill_view` 装载拦截消息列出的任一域技能，**原样重试同一条命令**。
- 段头 echo 含括号必须引号包裹：`echo "=== xxx ==="`，否则 compound 命令中途语法中止。
