<!-- archived from /root/.hermes/skills/security/ssi-esi-injection/SKILL.md on 2026-10-21 -->

---
name: ssi-esi-injection
description: >-
  SSI / ESI 注入。触发：Server-Side Include、.shtml、<!--#echo、<!--#exec、
  Edge Side Include、esi:include、Surrogate-Control、Akamai ESI。
  模板引擎走 ssti-exploit；Java EL 走 expression-language-injection。
---

> 归档卡：原目录 `/root/.hermes/skills/security/ssi-esi-injection`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ssi-esi-injection/…')`，不要相对 `references/legacy/` 解析。

# SSI / ESI 注入

目标须在 `config/scope*.json`。

## 真源

- 手法：`docs/playbooks/测绘引擎SSI-ESI作业手法.md`
- 工具：`python3 tools/ops/ssi_esi_probe.py --base https://授权站 --case <案>`
- 对照：`docs/playbooks/公开仓对照补强手法.md`

```bash
python3 tools/ops/ssi_esi_probe.py --base https://授权站 --case <案>
python3 tools/ops/ssi_esi_probe.py --base https://授权站 --case <案> --deep
```

## 何时用

路径带 `.shtml`，或响应头有 `Surrogate-Control` / `Edge-Control`，或参数回显 HTML 注释。  
`${7*7}` 走 SSTI，不要用本卡。

## 失败

原样回 `<!--#echo` = 没解析。换 `.shtml` / 另参，禁止当 SSTI 阴性结案。
