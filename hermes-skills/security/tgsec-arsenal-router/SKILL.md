---
name: tgsec-arsenal-router
description: "Use to search 2,348 TGSEC skill cards by stack or symptom."
version: 1.0.0
---

# TGSEC 军械库检索 · 2,348 张卡（本机 Windows 版）

## 为什么必须有这张卡

本机 `C:\Users\Administrator\.dsh\tgsec-kb\hermes-skills\` 里躺着 **2,380 个 `SKILL.md` / 2,348 张唯一卡**（security 2,221），
但 DSH 常驻技能目录只注入 **30 张伞形**，其余 **1,774 张归档卡不在目录里**。
**「目录里没有」≠「库里没有」**：不先检索就临时手搓打法 = 把已经写好的链子重写一遍。

磁盘实测（2026-11-05 重建 `arsenal.db` 输出）：
`total 2348 · enabled 574 · disabled 1774 · legacy 1856 · db 354 MB`。

## 一条命令

```
& "C:\Users\Administrator\.dsh\tgsec-kb\tools\cardfind.cmd" "泛微 dubbo 未授权" --top 8
```

`cardfind.cmd` 已内置 python 路径与 `ARSENAL_SKILLS` / `ARSENAL_DB` / `ARSENAL_DIR` / `PYTHONIOENCODING=utf-8`，直接调即可。
等价手工调用：

```
$py='C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$kb='C:\Users\Administrator\.dsh\tgsec-kb'
$env:ARSENAL_SKILLS="$kb\hermes-skills"; $env:ARSENAL_DB="$kb\arsenal\arsenal.db"; $env:ARSENAL_DIR="$kb\tools\arsenal"; $env:PYTHONIOENCODING='utf-8'
& $py "$kb\tools\arsenal\skill_find.py" "<关键词>" --top 8
```

## 阶段扫（开局不知道打哪面）

```
foreach($p in 'recon','auth','injection','file','ad','cloud','mobile','cms','java','php','api','gambling','ai','reverse','cve','tools','report'){
  "===== $p ====="; & "C:\Users\Administrator\.dsh\tgsec-kb\tools\cardfind.cmd" "<目标栈/症状>" --phase $p --top 3
}
```

## 参数

| 参数 | 作用 |
|---|---|
| `--top N` | 返回条数（默认 5） |
| `--phase <p>` | recon / auth / injection / file / ad / cloud / mobile / cms / java / php / api / gambling / ai / reverse / cve / tools / report |
| `--fast` | 只查名称/描述/标题/摘要，最快 |
| `--deep` | 默认已开：扫候选卡正文 |
| `--enabled-only` | 只看启用卡 |
| `--json` | 落结构化结果，含 `body_path`（正文绝对路径） |

## 结果怎么读（照 `load:` 行执行，不要自己拼路径）

- `[E]` 启用卡 → 正文就在 `C:\Users\Administrator\.dsh\tgsec-kb\hermes-skills\security\<卡名>\SKILL.md`
- `[D]` 归档卡 → 全文在 `catalog=...\references\legacy\<卡名>.md`，输出行里给的 `load:` 就是该绝对路径
- DSH 里用 **read 工具**打开上面两种路径；需要脚本/字典按卡内 `原目录` / `Formerly` 回原路径取
- `--json` 的 `body_path` 是权威正文路径，压缩/截断时以它为准

## 已验证命中（2026-11-05 实测，可复跑核对）

| 查询 | Top1 | 分数 | 状态 |
|---|---|---|---|
| `泛微 e-cology dubbo 未授权 RCE` | `weaver-ecology-dubbo-rce` | 2728.7 | [E] |
| `sharepoint _trust SecurityContextToken 反序列化` | `sharepoint-trust-deser-rce` | 1953.3 | [E] |
| `rails activestorage libvips 混淆 读文件` | `rails-activestorage-vips-rce` | 2487.3 | [E] |
| `宝塔 面板 密码 忘了` | `bt-panel-pentest` | 1586.0 | [E] |
| `druid 未授权` | `druid-console-unauth` | 989.5 | [D] |
| `gitlab ci lint 正则 DoS` | `gitlab-ci-lint-regex-rce` | 2632.6 | [E] |

## 检索完还要查什么

- **技能卡** = 怎么打；**产品/版本 PoC** 另查 `domains\0day-exploits\<产品>\`、`EXPLOITARIUM-INDEX.md`、`POC-PLATFORM-INDEX.md`
- **实战课** = 别人怎么打的：`domains\<面>\case-lessons\`，总入口 `domains\CASE-INDEX.md`
- **方法面** = `MASTER.md`（30 域）· 关键词表 `ROUTING.md`

## 加了新卡之后

新卡落盘后旧索引搜不到它 —— 重建（约 95 秒，实测）：

```
& "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" "C:\Users\Administrator\.dsh\tgsec-kb\tools\arsenal\arsenal_build.py"
```

输出 JSON 的 `total` 应 = 原数 + 新增卡数；`enabled/disabled/legacy` 与上一轮差 1~2 属归档增删正常。
落库后检索实测：拿新卡名 + 产品名各查一次，确认进 Top3 再收工。

## 坑

- `find`/`glob` 数 `SKILL.md` 会把 `.archive\` 下的重复归档算进去，比 `arsenal.db` 多几张属正常口径差。
- 摘要字段写太素会被归档老卡压分：产品名/症状/手法名要写进 `description` 与正文首段。
- 卡名全局唯一，重名卡 `arsenal_build.py` 只留一张，检索命中的是正文更长的那张。
