---
name: remote-exec-script-harness
description: "跳板机远程执行脚本的引号/超时/落盘纪律。"
---

# 远程执行脚本骨架(Remote Exec Script Harness)

**定位**:所有攻击流量走跳板机出网时,本机写的都是同一形态的东西 ——
「本机 python 脚本(paramiko 连跳板机)→ heredoc 灌一段远端 python → 远端跑 curl/socket 探测 → 打印结果」。
这个骨架的**引号、转义、超时、落盘**四件事踩一次亏一次,单独成技能。

**触发**:跳板机远程执行 / rex2 / paramiko / 输出被截断 / 报 `SyntaxError` 指向字符串中间 / 前台超时 /
**杀或重启远端后台脚本** / 「命令明明该有输出却回空串且 exit 0」。

⚠️ **凡是要 kill 或重启已在跑的远端脚本, 先读本技能再动手** —— 「杀+起」写进同一条命令、或 `pkill -f` 的模式裸字面量同时出现在该命令其它位置,
都会把执行这条命令的 shell 自己带走(现象是输出凭空消失、退出码 0), 而你会去猜目标或脚本的问题。

<!-- split-index -->

## Section index

- [0. 选型:重活放在离目标最近的一跳(先定架构,再写脚本)](references/split-01-0.md)
- [骨架形态](references/split-02-section.md)
- [四个必踩的坑(全部实测)](references/split-03-section.md)
- [4.1 ★ 大产物不回传:远端先聚合,只拉小结果](references/split-04-4-1.md)
- [curl 通用探测片段](references/split-05-curl.md)
- [其他纪律](references/split-06-section.md)
- [顺手把跳板机本身当情报源(拿到就先读一遍,别只当出口用)](references/split-07-section.md)
- [5. ★ 枚举循环的输出粘连会伪造「命中」与错误命名(枚举/采证类脚本通用)](references/split-08-5.md)
- [5.1 ★ 批量凭据扫描必须自证「命令真的执行了」—— 否则整批「全否」是假阴性](references/split-09-5-1.md)
- [6. ★ 长期「零产出」的脚本:先复现,再单变量对照(别把静默异常读成「目标没数据」)](references/split-10-6.md)
- [参考](references/split-11-section.md)
