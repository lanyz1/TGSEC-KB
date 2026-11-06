# 替换范围审计与遗留定时任务归属

用户问「已经把手搓版代码完全替换原来的了吗」/「crontab 这个任务是干嘛的、新代码里有它吗」时的标准动作:
**逐层取证 → 分层结论 → 遗留项给证据 + 待批**。不许用部署工具的成功输出、单层验收、或「我记得换过了」作答。

## 一、两层替换面(取证真值)

| 层 | 载体 | 判「换没换」 | 判「跑没跑」 |
|---|---|---|---|
| 采集端 ×12 | 入口 `/opt/v6/collector.py`(launcher) + 代码树 `/opt/v6/lib/<rel>` + `current` 软链 + `v6collector` 单元 | `tree_hash` 全台一致、入口 2286B=launcher、`current -> lib/<rel>` | `journalctl -u v6collector \| grep boot` 的 `[boot] tree=… tree_hash=…`、`NRestarts=0` |
| 主控侧 | `/opt/v6/*.py` + 常驻进程 + cron | `ps` / `crontab -l` / 与新树逐文件 md5 对照 | 同上 |

**「从未割接」的硬判据**:主控没有 `/opt/v6/current`、也没有 `/opt/v6/lib` —— 这两个是割接工装的副产物,有=已割接,无=一个字没换。

## 二、只读取证命令(两条够答完)

```bash
# 主控:跑的是哪套(ps + cron + 单元 + 目录 + md5,一次拿全)
ssh -i <key> -p <port> root@<master> '
  ps -eo pid,etimes,args | grep -E "python3? .*\.py" | grep -v grep
  crontab -l
  systemctl list-units --type=service --state=running --no-pager --no-legend | grep -vE "systemd|dbus|ssh|network|cron|rsyslog"
  ls -la /opt/v6/ | head -40
  md5sum /opt/v6/*.py | head -40'
```

判读纪律:
- `/opt/v6/` 是**几十代历史脚本的堆放场** ⇒ 目录列表不等于「在跑什么」,唯一权威 = 活进程 + crontab + md5。
- 每个 cron 任务**读头 4 行/docstring 定归属**(`head -4 /opt/v6/<job>.py`)—— 本项目 / 别的项目一眼分。
- 输出会被截断:先 `head`/分段取,别把整屏一次性拉回(会丢段落,导致只看到半张表)。

## 三、遗留定时任务三问

1. **它干什么** → 先读它**自己的日志**(`/tmp/*_cron.log`)的计数行(比源码快且是真值),再读脚本前 40 行确认机制。
2. **它的产出还有人读吗** → **全库 grep 产物文件名**(手搓版 + 主控 + 老采集器),全部为空 = 孤儿任务。
3. **新代码里有它吗** → grep 新树里「它产物的名字」与「它依赖的池名」,再找新树里的**等价模块**(比"有没有抄它"更重要)。

**产出无人消费 = 可停,但停 = 动生产,必须单独批准**。报告口径:给三条 —— ①它已空转的证据(计数行)②停了少什么(边界)③建议(如先留观 24h 再停),执行权交回用户。

## 四、机队 crontab 归属表(全台枚举一次,长期有效)

| 台 | 任务 | 归属 |
|---|---|---|
| 上海0 | `*/10 audit_harvest_cn.py`(flock;令牌池淘金器,`new_jwt` 恒 0,池无消费者) | 95306 遗留,可停待批 |
| 上海4 | `17 */4 ttl_probe.py` | **我方探针**(票 TTL 实测结论来源),保留 |
| 乌兰察布 | `*/25 /root/.local/share/misc/syncd.py` | **另一个项目**(优智采 `zb.lyc.cn` OSS-STS 同步,`~/tokens.txt` → `getOssSecurityTokenBySts`),**一律不碰** |
| 其余 9 台 | 无 crontab | — |

**纪律**:必须**全台**枚举 —— 只查一台既会漏本项目的任务,又可能把别的项目的活任务误认成自家遗留。命中非本项目脚本时**只登记不处置**。

## 五、别踩的坑

- 把「单层验收全绿」讲成「完全替换」(用户下一句就会问到你没查的那一层)。
- 拿 `/opt/v6/` 的 `ls` 当「在跑什么」。
- 拿部署/安装脚本的成功输出当运行证据 —— 运行证据只有:活进程、单元状态、`[boot]` 日志、产物 mtime。
- 自己判出「某任务已空转」就顺手停 —— 判定无用 ≠ 有权执行。
