---
name: shizhan-pack-router
description: >-
  实战技能包路由。用户提到实战技能包、Ghost Bits、401-403、
  type juggling、Host 头攻击、XSS/SQLi 长文时使用。
  别名 stub 走专卡；长文在 docs/learning/shizhan-pack/。
---

# 实战技能包路由

## 本仓探针

```bash
python3 tools/ops/pack_surface_probe.py drive --name <卡名> --case <案>
```

L2=挂号落到本仓 SKILL.md。证据进案卷 `测绘/`。

219 张卡已在 `.cursor/skills/`：专卡挂钩、别名 stub、全文卡。

## 真源

1. `docs/playbooks/实战技能包手法.md`
2. `docs/learning/shizhan-pack/MAP.md`
3. `python3 tools/ops/shizhan_pack_route.py --name <卡名>`

## 强制

```bash
python3 tools/ops/shizhan_pack_route.py --name <目录名>
```

- 已有同名/映射专卡 → 打专卡
- `.cursor/skills/<名>/SKILL.md` 存在 → 直接 Read（stub 会指向专卡）
- 免杀 / 写马作业走 `edr-bypass-re` / `payload_forge.py`，授权内落地
- 证件伪造 stub → 只读，不落地

## 不要做

- 覆盖本库同名专卡
- 把 `windows-av-evasion` / `webshell-evasion` 当免杀作业卡
- 把 219 张一次性全加载进上下文
