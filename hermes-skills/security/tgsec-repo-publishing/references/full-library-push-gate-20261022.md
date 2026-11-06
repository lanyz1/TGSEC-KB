# 全量库入仓闸 + 蒸馏覆盖率实数（2026-10-22 实测）

## 1. 触发场景

用户问「为什么不能把完整技能库提交到仓库」/「是不是已经蒸馏吸收了」。两句都必须先量后答，
否则就会用「按设计不入仓」搪塞，被当场怼「瞎鸡巴搞」。

## 2. 可见性与凭据（先量这个）

```bash
curl -s https://api.github.com/repos/lanyz1/TGSEC-Qtzuu | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["visibility"], d["size"],"KB")'
# → public 123456 KB
```

安装库凭据面（`~/.hermes/skills`，2146 张 / 201MB / 12660 文件，含 41MB `.curator_backups`）：

| 模式 | 命中文件数 |
|---|---|
| `BEGIN … PRIVATE KEY` | 46 |
| `AKIA[0-9A-Z]{16}` | 8 |
| `ghp_[A-Za-z0-9]{20,}` | 1 |
| `sk-[A-Za-z0-9]{20,}` | 1 |
| `password[:=]'…'` 明文口令 | 114 |
| `references/legacy/*.md`（真实目标案卷） | 1858 |

仓库 tracked 内容里**已经有**：`BEGIN … PRIVATE KEY` 60 文件、AKIA 16、ghp 3。抽样 8 处全部是
CVE 靶场自签测试密钥（`domains/0day-exploits/cloud-foundry-uaa/CVE-2026-59358/lab/uaa.yml`）、
扫描器正则（`re.compile(r"(?i)-----BEGIN [A-Z ]+PRIVATE KEY-----")`）、`AKIAIO...MPLE` 占位、
`ghp_xx...xxxx` 占位。结论：公开仓长期在漏 lab 密钥，再加 150MB 实战卡就是主动开闸。

## 3. 蒸馏覆盖率（2146 vs 987）

```bash
python3 scripts/measure_repo_coverage.py /root/TGSEC-Qtzuu ~/.hermes/skills
```

实测：

| 指标 | 数 | 占比 |
|---|---|---|
| 本机安装卡 | 2146 | — |
| 仓库卡名（domains 973 + 伞形 15） | 987 | — |
| 同名交集 | 837 | 39.0% |
| 仅本机有 | 1309 | 61.0% |
| 仅本机的 1309 里名字在仓正文出现过 | 525 | 40.1%（多是 eval_core.json / docs/updates 的路径引用，不是内容） |
| 本机 legacy 归档 | 1856 份 | — |
| legacy 名字在仓正文出现过 | 931 | 50.2%（**925 份完全没影**） |

口径纪律：**「仓库能给的都一致了」= 索引卡数 == 磁盘 SKILL.md 数、`ok=true`，只证明账对得上**，
不代表卡齐了。报覆盖率就报上面四个数，别用「已吸收」含糊过去。

## 4. 三条出路（依次说清，别只给结论）

1. **转 private（推荐）**：GitHub → Settings → Danger Zone → Change visibility → Private；
   然后 `bash scripts/sync-full-library.sh --push`（仓库版脚本，第 1 步就是可见性闸，
   `rsync -a --delete` 排除 `.curator_backups/`、`.curator_ledger.jsonl`、`*.pkl`、`__pycache__/`，
   提交前过 `/root/tgsec-guard/scan_push.py`）。同步量：2146 张 / ≈150MB / 12656 文件。
   转私有需要 admin token —— SSH deploy key 只能推代码，改不了可见性；本机无 gh CLI 时明确说「你点一下或给 token」。
2. **坚持 public**：只推脱敏子集，私钥/口令替 `[REDACTED]`，代价是 payload 段变占位。
3. **保持现状**：`export-arsenal-library.sh` 搬 82MB 包 + md5 清单，离线核对。

## 5. 验证清单（转私有后）

```bash
git -C /root/TGSEC-Qtzuu status --porcelain | wc -l        # 0
find /root/TGSEC-Qtzuu/hermes-skills -name SKILL.md | wc -l  # 2146
git clone -q --depth 1 git@github.com:lanyz1/TGSEC-Qtzuu.git /tmp/v && find /tmp/v/hermes-skills -name SKILL.md | wc -l  # 2146
```

clone 出来的卡数不等于 2146 就是没推全（rsync 的 `--delete` 会按本机为准，私有卡多的机器先在
`hermes-skills/` 里确认没有别人的卡）。

## 6. 相关实测（同批）

- 重建：2146 卡 / 342,605,824 B / **70.75s**（说明写 65–80s，对得上）
- 门禁 full：`selftest 30/30`、`core96 TOP1 94/96 TOP3 96/96 MISS 0`、三 phase TOP3 16/16、标题 7/7、正文 7/8
- 可达：TOP1 1899（88.49%）/ TOP3 2067（96.32%）/ TOP10 2122（98.88%），MISS 24（about-security、web-sec、hunt-idor、hunt-oauth、http-parameter-pollution、windows-ad…）
- 查询延迟 0.40–0.42s；「宝塔 面板 密码 忘了」TOP1 = `bt-panel-pentest`
- 仓库卡数三种口径：`git ls-files | grep -c 'SKILL.md$'` = 1160（含 50 个 `upstream-*-SKILL.md` 转储）、
  真名 SKILL.md 的 tracked = 1110（15 伞形 + 1095 domains）、`docs/learning` 283 个符号链接里 90 个叫 SKILL.md 且**本机 0 悬空**
