# 目标材料下线清扫清单(实录)

场景: 换目标 / 「停止所有进程任务」后紧跟「删除干净 这些都不需要」。目标 = 让本机对该目标**零残留**,但不动知识库、不动别家案卷。

## 1. 先定范围

- 「这些」= 对话里刚清点过的那一批。**别的旧目标等点名**,不要顺手全删(实录: 先只删新目标,老板下一轮才补旧目标,说明他心里有明确清单)。
- 删除前 `du -sh` + `find | wc -l` + `lsof +D` 清点,报给老板数字(实测 `2.0M / 49 files / 无句柄`)。
- 写脚本落盘跑,不用内联多层引号: `/root/stop_sweep/cleanup_<target>.sh`,每段 `rm -rf <显式路径>` + 回显返回码,日志追加到 `.log`。

## 2. 清扫点(逐类过,漏一类就残留)

| 类别 | 典型路径 |
|---|---|
| 案卷根 | `/root/cases/<target>`(主) |
| 散落工作目录 | `/root/<target>_real`、`_lab`、`/root/realcase`、`/root/eng/<target>` |
| 隔离区 | `/root/range_quarantine*`、`/root/<target>_quarantine`(克隆/实验链脚本常驻这里) |
| /tmp 碎屑 | `nmap_*`、`*_all.txt`、`hosts.txt`、`n_*.html`、`<target>_*.sh`、扫出来的 `*.json` |
| 工具会话 | `~/.local/share/sqlmap/output/<ip>`(target.txt 里带 Host: <域名>)、nuclei/ffuf 输出目录 |
| 工具解包 | `/tmp/katana`、`/tmp/naabu` 之类临时二进制(几十 MB,不删就是留痕) |
| 解析/路由改动 | `/etc/hosts` 里本役加的 pin 行 |

## 3. 绝不删

- 知识库/仓库克隆(`/tmp/tgsec_final`、`/tmp/oldclone`、TGSEC 工作树)
- 词典/工具链(SecLists、rockyou、jadx、go/、venv)
- 共享机别家案卷(`/root/cases/` 下未点名的目录)
- 参考包 `peer_loot/`、`absorb_pkg/` —— 里面出现目标字样是**参考词典**,不是本役产物;保留并在报告里点名

## 4. 有界校验(别写成全盘 grep)

全 `/root` 递归 `grep -ril` 实测 180s 超时(exit 124)。改成:

```bash
timeout 60 grep -rilE '<target>|<target_ip_prefix>' /root \
  --include='*.txt' --include='*.md' --include='*.json' \
  --include='*.sh' --include='*.py' --include='*.html' 2>/dev/null \
  | grep -vE '/root/stop_sweep/|\.hermes/|TGSEC|peer_loot|absorb_pkg'
```

空 = 零残留。再补三条: `ls -d <每个删除路径>` 全 NO、`df -h /` 前后对比、进程/端口复查(接 `fleet-task-shutdown` 的 Phase 4)。

## 5. 报告

分段: 已删(路径 + 体积 + 文件数)/ 释放体积 / 保留项 + 理由 / 终检结论。别问「还要不要继续」。
