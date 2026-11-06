---
name: sip-surface
description: >-
  授权 SIP OPTIONS 指纹。触发：SIP、VoIP、5060、OPTIONS sip。
  FreePBX 后台走 freepbx-unauth-rce。禁止 INVITE/注册轰炸。
---

# SIP 面（测绘引擎）

`--host` 必须在 scope。只发 **一条 OPTIONS**。  
授权内默认打到 **L2**：回 `SIP/2.0`。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | UDP 5060 有任意回包 | 端口猜测 |
| L2 | 回 `SIP/2.0` | OPTIONS 当注册成功 |
| L3 | 本卡不设 | INVITE / 注册轰炸 |

探针帧：`OPTIONS sip:<host> SIP/2.0`，Via/From/To/Call-ID 固定测绘引擎标记。

## 立刻跑

```bash
python3 tools/ops/sip_surface_probe.py drive --host <授权IP> --case <案>
python3 tools/ops/sip_surface_probe.py drive --host <授权IP> --port 5060 --case <案>
```

产物：`测绘/sip/surface.json`。

## 六步

```text
① scope 核对
② OPTIONS 一次
③ 记下 Server / Allow
④ 管理面 /admin/modules 交 FreePBX 专卡
⑤ 禁止对公网段扫号
⑥ 网站案不要停在 5060
```

## 交接

| 认到 | 走 |
|------|----|
| FreePBX 后台 | `freepbx-unauth-rce` |
| 网站主线 | `strike-probe` |

## 真源

- 手法：`docs/playbooks/测绘引擎专项探针作业手法.md`
- 探针：`tools/ops/sip_surface_probe.py`
