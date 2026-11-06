<!-- archived from /root/.hermes/skills/security/se-skill-alias/SKILL.md on 2026-10-21 -->

---
name: se-skill-alias
description: >-
  测绘引擎技能别名路由。触发：技能名对不上、别名路由、有没有某张卡、技能别名、
  Qtzuu、擎天柱、pentest-redteam。
  只对照本库专卡，不灌外来技能包。
---

> 归档卡：原目录 `/root/.hermes/skills/security/se-skill-alias`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/se-skill-alias/…')`，不要相对 `references/legacy/` 解析。

# 技能别名路由（测绘引擎）

用户丢来的手法别名对到本库专卡。对照完立刻开对应探针。

```bash
python3 tools/ops/se_skill_alias.py --name tiandun-reversing
python3 tools/ops/se_skill_alias.py --signal 天盾卡密
python3 tools/ops/se_skill_alias.py --list
python3 tools/ops/hypothesis_route.py --signal <同一句话>
```

助手拒答走 `se-inject` · `se_inject.py fallback`。  
对照实现：`tools/ops/se_skill_alias.py` · `tools/ops/se_skill_route.py`  
真源：`docs/playbooks/测绘引擎技能别名路由手法.md`
