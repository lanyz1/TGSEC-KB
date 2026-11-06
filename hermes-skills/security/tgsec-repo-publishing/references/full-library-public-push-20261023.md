# 全量库推公开仓（2026-10-23）— 时间线、扫描口径、真/假命中

## 1. 案发：本地领先 1 个 commit，远端整棵子树为空

| 时间(UTC) | 事件 |
|---|---|
| 10-22 20:18 | 远端 `4a6e3a25`（最后一次真正推上去的） |
| 10-23 01:04 | 本地 `4f3ab31a`：全量入仓 12,872 文件 / 2,490,000 行 / 153MB |
| 10-23 01:22 | `--amend`（脱敏补丁后再提交） |
| 之后 | **从未 push**（脱敏做到一半会话被中断） |
| 10-23 01:34Z | 本轮推上去；01:5x 又推 `884811f1`（补 `arsenal/`） |

用户原话：「那前面让你优化的 全部都没提交到仓库吗 本地和仓库差距那么多？」

判定三连（10 秒出结论）：

```bash
git status -sb                                   # ## master...origin/master [ahead 1]
git rev-list --left-right --count origin/master...HEAD   # 0	1
git ls-tree -r --name-only origin/master | grep -c '^hermes-skills/.*SKILL.md$'   # 0
find ~/.hermes/skills -name SKILL.md | wc -l      # 2206
```

远端 0 / 本地 2,217 → **整棵子树没上去**，不是「部分文件漏了」。`git push --dry-run` 当时就是通的（`4a6e3a25..4f3ab31a master -> master`），所以不是权限/网络问题。

## 2. 第一轮：自写正则（宽 → 收）

- 宽版：`(?:口令|密码)\s*[：:=]?\s*(\w{6,})` + `-p` + `password=` → **1,771 文件 / 3,601 命中**，逐个看全是 `--proxy-user`、`root/.bash_history`、`https://...` 这类噪声。
- 收紧：`(?<![\w-])-p`、要求「含数字或符号」、排除 `root/*.session` 等路径形状 → **54 文件**，其中真口令 10 个。

## 3. 第二轮：gitleaks 8.28（全树 4.3 秒）

`gitleaks detect --source hermes-skills --no-git --report-format json --report-path /tmp/gl.json --exit-code 0` → 775 findings：

| 规则 | 条数 | 真伪 |
|---|---|---|
| curl-auth-user | 364 | 全是文档示例（`admin:PASS`、`Harbor12345`） |
| curl-auth-header | 195 | 同上 |
| generic-api-key | 184 | 真货 3 个，其余 `YOUR_API_KEY` 类 |
| jwt | 21 | 全部 `eyJhbG...` 截断示例 |
| private-key | 6 | **全是 `secret_scan.py` / `secret-patterns.md` 的检测正则** |
| stripe | 2 | `sk_liv...xxxx` 掩码示例 |
| linkedin-client-id | 3 | 命中的是英文单词 `organizational` |

真货：`[REDACTED]`（客户 apifoxToken，6 处）、`[REDACTED]`（kk8 平台 AES 密钥/API secret，8 处）、`m7nrbZ...`（自研证书工具硬编码签名钥匙）。

脱敏后复扫：**775 → 760**，消失的正是这三个。

## 4. 最终替换：23 文件 / 35 处

类别（值不写回本卡）：全舰队主口令（两份卡）、自有跳板机 root 口令 ×2（`mjump.py` + `jump-servers.md`）、目标 root 口令、目标后台口令、目标提现口令、Redis `AUTH`、kk8 AES key、客户 apifoxToken、证书工具签名钥匙。

改完校验：
- `grep -rn '<字面量们>' hermes-skills/ | wc -l` → 0
- `python3 -c "import ast;ast.parse(open('.../mjump.py').read())"` → OK（口令在 dict 字面量里，换成 `[REDACTED]` 仍是合法字符串）
- 提交 `f22dc2ff`，推送成功。

## 5. 补第二批：检索栈 + 记忆脱敏（`884811f1`）

- `arsenal/` 14 个文件入仓：`arsenal_build.py`、`build_termdf.py`、`skill_find.py`、`vuln_build.py`、`vuln_find.py`、`selftest.py`、`trim_scan.py`、`ttp_pairs.json`、`eval_core.json`(96 条基线)、`eval_baseline.json`、`OPTIMIZE-LOG.md`、`ABSORPTION-AUDIT.md`、`CLOSURE-AUDIT.md` + `README.md`（重建命令）。
- 不入仓：`arsenal.db` 367MB、`vuln.db` 15MB（重建即可）。
- `ai-config/hermes/MEMORY.md` 与 `MEMORY.payload.md` 里还留着自有 IP ×3 + 自有域名 ×2 → `[OWN_IP]` / `[OWN_DOMAIN]`（上一版「深度脱敏」只扫了 skills）。

## 6. 复验口径

```bash
git ls-remote origin master                      # 884811f1...
git ls-tree -r --name-only origin/master | grep '^hermes-skills/' | wc -l   # 12,708
git show origin/master:ai-config/hermes/MEMORY.md | grep -c '154\.38\.99\.69\|38\.182\.151\.3\|95\.169\.6\.12'   # 0
curl -s https://api.github.com/repos/<owner>/<repo> | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["size"],d["pushed_at"])'
```

## 7. 事后坑

- 420s 工具超时把 `git push` 判死，其实后台已推完；用户收到的是「push 成功」的延迟通知。**先 `ls-remote` 再下结论**。
- 仓库副本与本机库有 1,453 个文件内容不同 —— 那是脱敏差（邮箱/手机/凭据），不是漏提交。用 `rsync -a --dry-run --itemize-changes` 看差异类型：`>f.st` 是脱敏改写，`>f+++++++` 才是真新增。
