## 真源

- 手法：`docs/playbooks/业务API未授权与越权手法.md`
- 作业手法：`docs/playbooks/测绘引擎越权IDOR作业手法.md`
- 换号：`python3 tools/ops/idor_swap_probe.py --url 'https://授权/api/order?id=1' --ids 1,2 --case <案>`
- 面探：`python3 tools/ops/core_web_surface_probe.py --help`

---

<!-- 补充视角: api-authz-idor-testing (兄弟技能库 2026-09-12) -->

---
name: api-authz-idor-testing
description: "IDOR越权系统测试:中间件分类→伪造owner→多机全库拉取。触发:idor,越权,伪造uid,全库拉取。"
version: 1.0.0
author: SurveyEngine Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
    category: security
---

# API 越权(IDOR)系统化测试与全库数据获取

目标"用户信息/资金数据"时**别逐接口瞎撞**。流程:接口全集(见 `spa-api-discovery`)→ 合法测试账号 → 按本节分类测越权 → 多机编排全量拉取。全部方法论经抖啦咪(doumvips.com,69 万用户)实战验证。

