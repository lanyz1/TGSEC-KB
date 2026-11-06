## 真源

- 作业手法：`docs/playbooks/测绘引擎SSRF作业手法.md`
- 云链：`docs/playbooks/云元数据SSRF利用链手法.md`
- 工具：`python3 tools/ops/ssrf_probe.py scan --base https://授权站 --case <案>`
- 面探：`python3 tools/ops/core_web_surface_probe.py --help`

---

<!-- 补充视角: web-ssrf (兄弟技能库 2026-09-12) -->

---
name: web-ssrf
description: 'SSRF attack techniques — internal port scanning, cloud metadata access, gopher/redis exploitation, blind SSRF, DNS rebinding. Trigger: ssrf, server-side request forgery, internal scan, metadata, aws metadata.'
---

# Web Ssrf

SSRF attack techniques — internal port scanning, cloud metadata access, gopher/redis exploitation, blind SSRF, DNS rebinding. Trigger: ssrf, server-side request forgery, internal scan, metadata, aws metadata.

