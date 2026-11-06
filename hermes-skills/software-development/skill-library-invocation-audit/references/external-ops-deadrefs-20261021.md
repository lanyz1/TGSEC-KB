# 外部 ops 套件死引用审计（2026-10-21）

> **历史首轮快照**：以下 226/0、114/114 是修复前基线，不是当前状态。
> 首轮修复后的 38/190、60.3% 覆盖率与 `coverage_gate.py` 见
> `references/ops-coverage-closure-20261021.md`。

## 背景

TGSEC 知识卡大量使用 `tools/ops/<script>.py` 作为执行入口；2026-10-21 审计发现本机根本没有 `tools/ops/` 目录。检索层（`skill_find`/`vuln_find`/`repo_find`）正常，导致“卡能查到、命令跑不了”的假闭环。

## 实测数字

- 全库（含归档）唯一 `tools/ops/*.py` 引用：**226 个，0 存在**
- 启用卡唯一 `tools/ops/*.py` 引用：**114 个，114 缺失**
- 启用卡 `docs/playbooks/*.md` 引用：**88 个唯一路径，87 缺失**
- 真实可执行层：`/root/TGSEC-Qtzuu/.claude/skills/pentest-redteam/scripts/tools/` — 29 个纯标准库脚本
- 案卷账本：同目录上一级 `case_ledger.py`

高频缺失入口（括号内为引用文件数）：

- `case_report.py` (151)
- `core_web_surface_probe.py` (144)
- `shizhan_pack_route.py` (164)
- `object_matrix.py` (34)
- `kit_run.py` (30)
- `case_triage.py` (30)
- `nday_route.py` (31)
- `auto_campaign.py` (19)
- `case_facts.py` (21)
- `evidence_gate.py` (5)

## 审计脚本

```python
import glob, os, re, yaml
cfg = yaml.safe_load(open('/root/.hermes/config.yaml'))
dis = set(cfg.get('skills', {}).get('disabled', []))
pat = re.compile(r'(?:tools/ops|docs/playbooks)/[A-Za-z0-9_.\-/]+\.(?:py|md)')
refs = set()
for p in glob.glob('/root/.hermes/skills/**/SKILL.md', recursive=True):
    if os.path.basename(os.path.dirname(p)) in dis:
        continue
    refs.update(pat.findall(open(p, encoding='utf-8', errors='ignore').read()))
missing = []
for r in sorted(refs):
    if not any(os.path.exists(os.path.join(base, r)) for base in ('/root/TGSEC-Qtzuu', '/root')):
        missing.append(r)
print('active refs', len(refs), 'missing', len(missing))
for r in missing:
    print('MISS', r)
```

## 本机可执行替代

```bash
# 子域/端口/目录/注入/SSRF/JWT/IDOR/CMS 等
python3 /root/TGSEC-Qtzuu/.claude/skills/pentest-redteam/scripts/tools/subdomain_enum.py example.com
python3 /root/TGSEC-Qtzuu/.claude/skills/pentest-redteam/scripts/tools/port_scanner.py -t example.com
python3 /root/TGSEC-Qtzuu/.claude/skills/pentest-redteam/scripts/tools/dir_brute.py -u https://example.com

# 已装二进制
nuclei -u https://example.com -ni -duc -tags cve -severity critical,high
ffuf -u https://example.com/FUZZ -w wordlist.txt
sqlmap -u 'https://example.com/item?id=1' --batch
```

## 本机冒烟结果

- `whatweb` 对本地 HTTP 服务返回 200，识别 Python SimpleHTTP
- `ffuf` 命中 `index.html`
- `port_scanner.py` 正确报告 18080 开放
- `nuclei` 默认参数会等 interactsh/更新检查而挂住；加 `-ni -duc` 后正常退出
- `case_ledger.py` 的 `hypothesis/evidence/verdict/verify/render` 全链跑通，`verify --report` 输出 PASS，`render` 生成 `evidence-validation.md`

## 结论口径

- 知识层闭环 ≠ 作战层闭环。
- 不要把“226 个脚本都能用”写进报告；它们全不在本机。
- 不要为补引用重写 226 个历史脚本；优先修路由真话 + 用现有 29 个脚本/二进制替代 + 补高频适配层。
