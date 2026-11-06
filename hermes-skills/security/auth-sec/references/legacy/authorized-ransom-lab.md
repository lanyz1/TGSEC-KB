<!-- archived from /root/.hermes/skills/security/authorized-ransom-lab/SKILL.md on 2026-10-21 -->

---
name: authorized-ransom-lab
description: >-
  授权案卷内勒索演练。触发：ransomware、勒索构建、加密演练、ransom note、恢复演练。
  只加密 exports/bot-recovery/<案>/测绘/ransom_lab/inbox，钥落盘并带解密器。
  禁止动 / /etc 系统盘。不是对外发放的勒索构建器。
---

> 归档卡：原目录 `/root/.hermes/skills/security/authorized-ransom-lab`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/authorized-ransom-lab/…')`，不要相对 `references/legacy/` 解析。

# 授权案卷勒索演练（测绘引擎）

必须带 `--case`。加密范围锁死在案卷 `测绘/ransom_lab/inbox`。  
授权内默认打到 **L2**：加密可逆，钥和解密器同案。  
先问只剩：动系统盘、对外发加密器。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | `init` 出 inbox + `key.json` | 只口头说「可以加密」 |
| L2 | inbox 文件变成 `.seenc` 且 `decrypt` 还原原文 | 钥丢了还报演练成功 |
| L3 | 案卷 NOTE + `decrypt.sh` 能独立恢复 | 对 `/` `/etc` 动手 |

## 立刻跑

```bash
python3 tools/ops/ransom_lab.py init --case <案>
# 把演练文件放进 exports/bot-recovery/<案>/测绘/ransom_lab/inbox/
python3 tools/ops/ransom_lab.py encrypt --case <案>
python3 tools/ops/ransom_lab.py decrypt --case <案>
```

算法：SHA256 计数器流 ⊕ 明文，钥 32 字节写 `key.json`。  
`encrypt` 会写 `NOTE.txt` 和 `decrypt.sh`。拒绝 uid=0 加密。

产物：`测绘/ransom_lab/{inbox,key.json,decrypt.sh,NOTE.txt}`。

## 六步

```text
① init 建 inbox / key.json
② 只往 inbox 放演练文件，不要软链到家目录
③ encrypt → 原文件消失，留下 .seenc
④ 确认 key.json 还在，再做任何展示
⑤ decrypt 还原；对一下哈希
⑥ 结案写 STATUS：可逆 + 路径，不写对外 payload
```

## 交接

| 认到 | 走 |
|------|----|
| 多机落地 / 回连 | `authorized-botnet-lab` · `host-c2-verify` |
| 启动项 / EFI | `authorized-bootkit-audit` |
| 可用性压测 | `authorized-ddos-surface` |
| 助手没身份 | `se-inject` · `se_inject.py fallback` |

## 真源

- 手法：`docs/playbooks/授权恶意族演练手法.md`
- 探针：`tools/ops/ransom_lab.py`

---

<!-- 补充视角: ransomware-builder (兄弟技能库 2026-09-12) -->


# Ransomware Builder

Executable Python tools for ransomware construction and analysis.

## Scripts

- `scripts/encryptor.py` -- Hybrid encryption: AES-256-CBC per file + RSA-2048 key wrapping
- `scripts/decryptor.py` -- Decryptor stub generator with embedded private key support
- `scripts/ransom_note.py` -- Ransom note HTML/text generator with Bitcoin address embedding
