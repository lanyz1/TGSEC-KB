# 三层检索与路径漂移（2026-10-21）

本机落地：技能卡、漏洞库、整仓文档分三层索引，目标是「吸收过的手法实战中查得到、加载得了、执行得动」。

## 三层职责

- `skill_find` → `arsenal.db`：2,173 张技能卡（374 启用 + 1,799 归档），返回 `load:`。
- `vuln_find` → `vuln.db`：8,055 条 CVE/产品/PoC/情报入口；TGSEC `domains/0day-exploits` 是第一来源，返回 `read:` + `run:`。
- `repo_find` → `repo.db`：6,265 条整仓路由/25 域文档/案例，返回 `read_file` 路径；不替代 TGSEC 自身 `AGENTS.md → ROUTING.md → MASTER.md`。

## 构建与验收

```bash
python3 /root/.hermes/arsenal/arsenal_build.py
python3 /root/.hermes/arsenal/selftest.py       # 30 条路由回归
python3 /root/.hermes/arsenal/vuln_build.py
python3 /root/.hermes/arsenal/repo_build.py
python3 /root/.hermes/skills/software-development/skill-library-invocation-audit/scripts/audit_skill_paths.py
```

- 技能检索回归：30/30。
- CVE 检索抽测：20/20（含 `CVE-2026-87902`、`CVE-2026-61628`、`CVE-2026-109618`）。
- 0day 真身：13,686 文件 / 960 个产品-CVE 目录 / 1,189 个 py / 814 张 by-cve 卡。

## vuln_find 排序规则

- 精确 CVE 命中时只保留该 CVE 的行，避免同产品/同年其他 CVE 污染。
- `poc-dir` +25；年份新近加权；同 CVE 多来源默认去重，`--all` 展开。
- 无 CVE 编号的产品包以 `product-poc` 入索引（如 pfSense/abraxas），只搜编号会漏。
- 标签：`POC`/`CARD`/`DOC`/`IDX`/`LOCAL`/`INTEL`。`[POC]` 不等于可直接打，先读 `read:` 的 README/analysis。

## 本次路径故障

- `0day-exploit-library` 整卡引用旧仓 `/root/security-suite`，本机不存在；实际为 `/root/TGSEC-Qtzuu/domains/0day-exploits`。修改 19 个技能文件；旧概览 76 产品/90 漏洞改为实测 13,686 文件/960 目录/1,189 py/814 卡。
- `1day-nuclei-kit` 的 `tools/1day-kit/od_kit.py`、`docs/playbooks/*` 在本机不存在，已在卡内加“本机核验”警告，避免按空路径作业。
- 教训：**索引命中 ≠ 执行路径存在**；合并/迁移后必须先做路径存在性审计，再重建三个库。

## 回答方式

用户问「怎么调用」时，直接给命令 + 真实路径 + `read:`/`run:`，不要只讲架构或只报索引大小。
