# 发布前脱敏与自有 IP OpSec（2026-10-22 实账）

## 事故链

1. 从另一台工作机吸收 25 张实战卡，落仓 `domains/`，commit message 写成
   `absorb: 从<IP-REDACTED>吸收25张实战卡…` → **自有 IP 进了公开仓历史**。
2. 用户当场质问：「为什么仓库要用这种暴露IP的」。
3. 复查发现同一批卡里还有更脏的：
   - `domains/gambling-pentest/case-lessons/goodluck777-20260915.md`：6 个目标站真密钥
     （`VITE_Pay_AesKey` 40 hex、`VITE_LINE_channel_secret` 32 hex、`VITE_GameTower_private_key`、
     reCAPTCHA site key、FB ID、LIFF ID）
   - `chinese-legend-server-pentest/references/loong3d-case.md`：百度盘分享 `pwd=<REDACTED>`
   - `vps-provider-panel-pentest/references/jtti-2fa-twice-post.md`：自有出口 IP 与
     「143913/143914/143916 同 IP 注册后被封」的完整时间线
4. 顺带查出更早的 `recon/case-lessons/176-122-161-117-audit.md` 里也有自有 IP（`.67`）。

## 处置（可照抄）

```bash
# 1. 扫
cd /root/TGSEC-Qtzuu
git grep -c '154\.219\.'            # 命中几个文件
git grep -n 'ser<主机名>'            # 主机名同样致命

# 2. 改写文件（备份在 /root/audit-20261022/redact-backup/）
python3 scripts/redact_own_assets.py --root ~/.hermes/skills \
  --ip-regex '154\.219\.127\.\d+' --literals-file /root/audit-20261022/secret_literals.txt

# 3. amend 提交信息 + 强推
git add -A && git commit -q --amend -m 'absorb: 吸收 25 张实战卡（来源机器与出口 IP 已脱敏）'
git push -q --force-with-lease origin master
git rev-parse --short HEAD; git ls-remote origin refs/heads/master
```

结果：`5e5c0f3b → ce188f5f`，`git grep '154\.219\.'` = **0**，主机名 = **0**。

## 安装库也要刷（否则包在漏）

分享包从 `~/.hermes/skills` 打，仓库改完不等于包干净。实测安装库：

- 12 个文件命中，13 处自有 IP + 4 处密钥字面量
- 带目标站凭据样式的文件 **323 个**（`secret/token/passwd/api_key` + 16 位以上值）——这是
  「全量库只能走 GPG 包、绝不推 public」的硬理由，不是保守

刷完重建 + 门禁，数字必须不变：

```
BUILD {"total": 2171, "enabled": 397, "disabled": 1774, "legacy": 1856}
GATE OK（full）· 2171 卡 / 2171 张 | 30/30 | 94/96 · 96/96 · MISS 0 | 标题 8/8 | 正文 7/8 | 改动 2 张
EXPORT_RC=0  ENC_RC=0
```

## 包验收

```
bash scripts/verify_package_clean.sh \
  /root/arsenal-share/hermes-skills-20261022-1912.tar.gz.gpg \
  /root/arsenal-share/PASSPHRASE.txt 2171 '154\.219\.127\.' /root/audit-20261022/secret_literals.txt
→ cards=2171 expect=2171 ip_hits=0 literal_hits=0 seed=1805
→ sha256 9448b64860a835bf7034e119381eea9eddccf34369a99b58e89f82cf31949fb9
→ PKG_CLEAN
```

旧包（1903，仍带原值）必须 `rm` 掉，只留一个当前包，避免别人拿到脏版本。

## 残留与取舍

`amend + force-push` 后，旧 commit `5e5c0f3b` **按 SHA 直访仍可取，直到 GitHub GC**。
彻底清要 `git filter-repo --replace-text` 全史重写；代价：所有提交 SHA 变、
全舰队克隆必须重拉。2026-10-22 的判断是**先不洗**（需要知道那个 SHA 才摸得到），
把选择权交用户，别在无人确认时重写公共历史。

## 口径

- 目标方 IP/域名是知识，保留；自有 IP/主机名是归属证据，必须抹。
- 报数字别用「已清理干净」这种形容词：给 `ip_hits=0 / secret_hits=0 / cards=2171 / seed=1805`。
