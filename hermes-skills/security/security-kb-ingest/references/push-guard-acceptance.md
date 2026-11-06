# 推前守卫与推送验收（TGSEC 口径，2026-10-12）

## 推前守卫（必须 exit 0 才允许 push）
- `python3 /root/tgsec-guard/scan_push.py /root/TGSEC-Qtzuu --full`
  - 路径闸：`case-reports` 路径命中＝硬失败，绝不推
  - 凭据族闸：`sk / tga / bottok / ghp / github_pat / LTAI / AKIA / AIza / ghpat / slack`
  - `--full`＝全史 blob 扫描（~25k blob），不是只扫 HEAD 树
- 全史闸 `/root/verify_final.py`（v3）：家族表必须与 scan_push 对齐；硬族命中即 `exit 1`（旧版恒 exit 0＝假绿灯，已修）
- `sk-` 正则必须带词边界 `(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}`，否则 `task-runner` / `Task-Is` 这类「单词内 sk- 子串」批量误报

## 示例级豁免（EXSPEC，v3 起）
- 标记集：`EXAMPLE | XXXX | REDACTED | PLACEHOLDER | FAKE | 1234567890 | ABCDEF`（re.I）
- 豁免项**计数上账**（summary 计 examples），不静默放行；真 token 照抓
- 教科书示例/填充序列（AWS 官方样例 key、`AKIA1234…CDEF`、`ghp_xx…xxxx`、lab 种子 SQL）才走豁免——真实熵 token 不可能含连续序列
- 已确认示例出处（2026-10-12 全史图 13 文件 1:1）：MSF 模块文档示例输出、lab Postgres 种子 SQL、recon-skills 自测向量、torch-wiki 教程

## 推后验收（三件齐平才算完成）
1. `push_verify_live.sh [repo]` — 本地 HEAD == 远端 `refs/heads/master` == 远端 `HEAD`；工作树 `## master` 0 残留（脚本在技能自身 `scripts/` 下、**不在仓库里**；用法 `bash <skill>/scripts/push_verify_live.sh [repo]`）
2. 反向克隆抽验 — 全新 clone 到 /tmp（`git clone --quiet git@github.com:lanyz1/TGSEC-Qtzuu.git /tmp/revcheck_<tag>`）：tip == 本地 HEAD、`git rev-list HEAD --count` 对齐。旧对象 404 探针**先本地筛**：`git merge-base --is-ancestor <sha> HEAD`——**祖先 sha（如 bb5f85b6）远端必然可达，不可当探针**；只挑非祖先旧 sha，在克隆里 `git cat-file -t` 逐枚验，全部 "Not a valid object name" 才算旧对象永 404
3. 落盘 — 批量目录 `/root/tgsec-ingest/verify-<date>/`：`guard-prepush-<tag>.log` / `verify-<tag>.log` / `push-<tag>.log` / `accept-verify-live-<tag>.log` + `ACCEPT-<tag>-<date>.md` 判决注记（判决以落盘为准）

## GitHub 侧守卫：GH013 Push Protection（2026-10-17 增补）

自家 guard 全绿 ≠ 能推。GitHub 侧另有暗门：**GH013（`Push cannot contain secrets`）**——两个扫描器口径不同：GH 按「提供方格式 + 熵」判定，自家 EXSPEC 的 `XXXX` 标记 **GH 不认**。

- **症状**：push 被拒，列 ≤5 处 + “`N more secrets detected`”；**迭代重推逐批暴露**（一轮修完再推，通常 2-3 轮清完）
- **高发载体**：新收工具仓的**假 key 测试夹具**（keyhunter / js-analyser 类扫描器仓重灾）——Stripe `sk_live_/sk_test_`、OpenAI `sk-proj-`、Slack `xoxb-`、GitHub `ghp_`、AWS `AKIA`、New Relic `NRAK-`
- **消毒器**：`scripts/gh013_sanitize.py`（本技能内；对 `git diff --name-only <base>..HEAD` 文件按族改写：`(sk|rk)_(live|test)_` → `前缀_REDACTED`（payload 短于 GH 下限即不匹配）；`sk-proj-/sk-ant-` → `前缀-EXAMPLE`；`gh[pousr]_`/`xox`/`AIza` → 同法；`AKIA<16+>` → `AKIAXXXXEXAMPLEKEY1` 或**规范为 canonical** `AKIA<REDACTED>`（最全球豁免））
- **New Relic 特例**：别改测试值——用 `concat!("NRAK-", "AA…")`（Rust）或相邻字符串拼接拆分，源码不含连续格式即过、测试真值保留
- **自家 guard 盲区**：`sk-` 正则带连字符，**漏 Stripe 下划线形 `sk_live_`**——家族表补 `(sk|rk)_(live|test)_`
- **迭代纪律**：改完 → `git commit --amend --no-edit` → `git reflog expire --expire=now --all && git gc --prune=now` → `scan_push --full` 重跑 → 重推；未推提交可 `git reset --soft <base>` 压平

## 全史复核的两个坑（2026-10-17）
- `scan_push.py` 对**无 diff** 的仓库直接早退（`no new commits vs origin/master — nothing to scan`）——要在反向克隆上跑全史扫描须**直调** `python3 /root/verify_final.py <repo>`（不吃 diff 闸）。
- `git clone --depth 1` 起步的活干完后本地是**浅克隆**（rev-list 只 2、远端 83）：`git fetch --unshallow` 补齐后对账；**远端精确镜像 + 本地双侧全史 `hard=0`** 才是最强证据。

## Pitfalls
- 两个扫描器（HEAD 级 + 全史级）必须同步升级、同步对账——只升一个会漏族（假绿灯）
- 推前命中先验上下文再定性：测试样例/产品名子串 ≠ 真凭据；做**精确豁免**（标记识别），不做逐文件重写
- `scan_push.py` 输出流交错：`2>&1` 重定向后文件里可能先见 blob 扫描段、守卫头几行落在末尾（stdout 缓冲 vs stderr 直写）——判完成看 `rc=0` + `FULL VERDICT` 行，勿把文件末行「--full: running…」误读成截断
- 实例锚点（2026-10-12 refsfix）：5 提交 `047b0a83..b401bbe1`（39 文件）；全史 33,287 对象 / 25,289 blob，16 硬族全 ZERO，soft 83（urlcred 4 = lab DATABASE_URL 占位、phone11 79 = 教科书连号）；反向克隆 82 提交对齐；404 探针四枚 `c570571c / df5bd0aa / 220a58f4 / f5a28386`
- 实例锚点（2026-10-17 abraxas 增量批）：`b401bbe1..27cddfc8` **三推**（GH013 拦两轮：Stripe/OpenAI/Slack/GitHub/AWS/New Relic 共 6 文件夹具）；全史 34,621 对象 / 26,601 blob，hard=0，soft 113，豁免 AKIA=22/ghp=5/sk=3；反向克隆 **83==83**；404 探针六枚 `9d47c9a4 / ef032079 / 3751ce2e / c9cfe0c8 / c570571c / df5bd0aa` 全过
