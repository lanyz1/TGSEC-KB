## 真源

- `docs/playbooks/TGbot渗透逆向全链手法.md`（A-E 五面全链）
- `docs/playbooks/TG-Bot管理面越权与Webhook劫持手法.md`（§1-§9 BOLA 路径）
- 探针：`tools/ops/tg_bot_token_probe.py`
- 参考：CVE-2026-28454 (GHSA-fhvm-j76f-qmjv)、F-2026-0005 (zealynx)

---

<!-- 补充视角: tg-bot-backend-pentest (兄弟技能库 2026-09-12) -->

---
name: tg-bot-backend-pentest
description: "打TG机器人/小程序后台: 空间测绘语法+弱口令+路径穿越上传。"
---

# TG 机器人/小程序博彩站后台渗透(TGSEC 方法论)

针对 TG Bot 后台、小程序/H5 博彩站的打法。核心:**用搜索代替扫描**(Shodan/Fofa 语法找面板)+ **手动弱口令**(30% 直接进)+ **路径穿越上传 getshell**。

