---
name: case-review
description: >-
  案卷只读复核。用户提到交差、证据链、STATUS 能不能结案、
  对象矩阵缺格、handoff、case-review、证据闸、口头结论、NO_PATH 时使用。
  不探测、不打点、不改目标。进攻面仍走原专卡。
---

# 案卷证据复核（Cursor Skill）

## 真源

1. `docs/playbooks/逆向技能缺口与路由手法.md`
2. `python3 tools/ops/case_review.py --case exports/bot-recovery/<案卷>`
3. 对象矩阵：`docs/playbooks/对象矩阵与身份错位手法.md`
4. 字面量闸：`docs/playbooks/编解码对照与证据闸手法.md` · `evidence_gate.py`
5. 恢复成功后闭环：`docs/playbooks/恢复后固化与备份.md`

## 强制

1. 只读案卷目录。发现缺格就补文档，不要借复核继续打点。
2. STATUS 里已有身份线索但没有 `测绘/object_matrix.md` → 直接 FAIL。
3. 矩阵仍有「未测」→ 警告，禁止写复工结案。
4. 声称的 L 级 / CVE / flag 必须能被 `evidence_gate` 逐字符对上；高信号未耗尽禁止 NO_PATH。

```bash
python3 tools/ops/case_review.py --case exports/bot-recovery/<案卷>
python3 tools/ops/case_review.py --case exports/bot-recovery/<案卷> --strict --json
python3 tools/ops/evidence_gate.py --case <案卷> --from-status
# 若有 证据/ledger.jsonl：
python3 tools/ops/case_ledger.py verify --report <案卷>
```

## 过线标准

- [ ] 有 `STATUS.md` 且不是空壳
- [ ] 有 `测绘/` `接管/` `支付/` `证据/` 之一
- [ ] 有身份则矩阵已填
- [ ] Finding 能指回命令或文件，不是口头结论
- [ ] `evidence_gate --from-status` 无 misses / 无 NO_PATH 拦截
