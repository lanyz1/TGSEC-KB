<!-- archived from /root/.hermes/skills/security/hypothesis-ledger/SKILL.md on 2026-10-21 -->

---
name: hypothesis-ledger
description: >-
  测绘引擎假设账本。用户提到假设驱动、ledger.jsonl、观察复现影响、
  证伪、provisional、confirmed、案件黑板、L2 状态机、
  长时多假设、engagement、受限环境标准库工具、
  Qtzuu、pentest-redteam、擎天柱工具包时使用。
  单点单洞仍走专卡；交差闸仍走 case-review。
  旧名 `pentest-redteam` 已并入本卡。公开仓对照见 `公开仓对照补强手法.md` §4。
---

> 归档卡：原目录 `/root/.hermes/skills/security/hypothesis-ledger`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hypothesis-ledger/…')`，不要相对 `references/legacy/` 解析。

# 假设驱动作业账本

长时多假设才建账本。单目标单假设：专卡 + `STATUS.md`。

## 立刻跑

```bash
python3 tools/ops/hypothesis_route.py --signal "若依 actuator"
python3 tools/ops/hypothesis_route.py --signal "claude 拒答"
python3 tools/ops/hypothesis_route.py --doctor
python3 tools/ops/cache_poison_probe.py --url https://授权站/ --case <案卷>
python3 tools/ops/java_web_surface_probe.py -u https://授权站 --case <案卷> --stack cnoa
python3 tools/ops/usdt_attr_hijack.py chain-scan --case <案卷> --pages 15
python3 tools/ops/case_ledger.py init <案卷>
python3 tools/ops/case_ledger.py hypothesis <案卷> \
  --claim "<一句话假设>" --scope "https://授权站" \
  --disprove-if "<什么现象就证伪>"
python3 tools/ops/case_ledger.py evidence <案卷> \
  --role observation --effect supports \
  --artifact STATUS.md --summary "STATUS 里的一手观察"
python3 tools/ops/case_ledger.py evidence <案卷> \
  --role reproduction --effect supports \
  --file 测绘/probe.json --summary "探针 JSON"
python3 tools/ops/case_ledger.py next <案卷>
python3 tools/ops/case_ledger.py verify --report <案卷>
```

不在 scope → `scope_expand.py --grant`。有身份先填 `测绘/object_matrix.md`。

## 强制

1. `confirmed` = 观察 + 复现 + 影响 三条独立证据。缺一只能 `provisional` / `inconclusive`。
2. 证伪写 `killed` + 重访条件，不删假设。
3. Active 3 轮无进展 → `deferred`。
4. 领域信号先 `hypothesis_route.py`（表顺序先命中先赢），再跑表上的探针；长文 22 份后读。
5. 免杀 / C2 / AMSI → `edr-bypass-re`，不按长文落地。

## 真源

- 手法：`docs/playbooks/假设驱动作业账本手法.md`
- 路由：`python3 tools/ops/hypothesis_route.py --signal "<词>"`
- 账本：`python3 tools/ops/case_ledger.py --help`
- 降级：`python3 tools/ops/stdlib_fallback.py --list`
- 地图：`docs/learning/hypothesis-pack/MAP.md`
- 蒸馏：`docs/learning/hypothesis-pack/DISTILL.md`
