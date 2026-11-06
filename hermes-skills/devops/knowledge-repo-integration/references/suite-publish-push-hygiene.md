# Suite 发布推送卫生（2026-09-17 实录）

适用：把 `security-suite` 大融合提交推到 GitHub 时被 **secret scanning / push protection** 拒绝，或提交里夹带超大 lab 二进制。

## 推送前必做（防拦）

在 `git commit` 前对**新入库的 case-reports / case-lessons** 扫云厂商密钥形态：

```bash
rg -n -g'*.md' \
  'LTAI[A-Za-z0-9]{8,}|AKID[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}' \
  domains/*/case-reports domains/*/case-lessons
```

命中 → **打码后再提交**（手法/结论保留，明文密钥改 `[REDACTED]`）。不要指望「仓库没开 Secret Scanning 就不会拦」——GitHub 对有资格的仓仍可在 push 时做 push protection。

### 常见命中与替换

| 形态 | 例 | 替换 |
|---|---|---|
| 阿里云 AccessKey ID | `LTAI…` | `LTAI[REDACTED]` |
| 阿里云 AccessKey Secret | 长随机串旁注「完整已获取」 | `[REDACTED]（完整已获取，入库已脱敏）` |
| 腾讯云 SecretId | `AKID…` | `AKID[REDACTED]` |
| 腾讯云 SecretKey | 表里配对的第二列 | `[REDACTED]` |

支付商户密钥、JWT、平台 token 等同理：报告里保留「已获取/已验证」叙述即可，**明文不出库**。

## 全形态凭据闸（2026-10-08 补课，血泪教训）

实测事故：2026-09 三批吸收（09-17 / 09-28 / 10-06）只按上表扫了**云 AK 形态**（`LTAI/AKID/AKIA/ghp_`——恰好≈“会被 GitHub 拦”的子集），**TG bot token、`sk-` LLM key、`tga_/tgb_`、URL 内嵌凭据、2FA 种子、明文口令值、真实手机号**全部裸奔入库，直到 10-08 全量审计才补刀（160 文件扫出：bot token ×6 全量 46 字符、sk ×3、tga/tgb ×8、URL 凭据 ×3、手机号 ×17、口令/2FA ×50+）。

教训：**“能过 GitHub 拦截” ≠ “脱敏完成”**。规则是「明文不出库」（私有仓亦然），与 GitHub 扫不扫无关。执行完一批吸收后必须对 `domains/*/case-reports` + `case-lessons` 跑**全形态**扫描：

```bash
rg -n -g'*.md' -g'*.txt' -g'*.json' -g'*.csv' -g'*.py' -g'*.sh' \
  -e 'LTAI[A-Za-z0-9]{10,}' -e 'AKID[A-Za-z0-9]{13,}' -e 'AKIA[0-9A-Z]{16}' \
  -e 'ghp_[A-Za-z0-9]{30,}' -e '\b[0-9]{6,12}:[A-Za-z0-9_-]{30,45}\b' \
  -e 'sk-[A-Za-z0-9_-]{16,}' -e 'tga_[A-Za-z0-9]{12,}' -e 'tgb_[A-Za-z0-9]{12,}' \
  -e 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}' \
  -e '://[^/\s:@]{1,64}:[^/\s:@]{6,}@' \
  domains/*/case-reports domains/*/case-lessons
```
另跑语境扫描：`密码|口令|SECRET\s*[:=]`、`2FA|TOTP|种子` 邻近的 16-64 位大写字母数字串、`1[3-9]\d{9}` 手机号。

打码口径：凭据值 → `[REDACTED]`（保留形态前缀与「已获取/已验证」叙述）；手机号 → `1xx****xxxx`。**纯字母短值必须人工复核**（可能是 `password/approved/tomcat` 等单词或状态值，别乱掩）。脚本参考：`/tmp/scrub1.py`（硬形态）→ `/tmp/scrub3.py`（语境自动）→ `/tmp/peek4.py`（人工复核），任务落盘在 `cases/` 案卷。

## 被拒后的修复（commit 尚未进远程）

1. 读拒绝日志里的 `path:` + 行号，打开文件打码。
2. 再扫一遍确认无残留明文形态。
3. `git add` 脱敏文件 → `git commit --amend`（仅当该 commit **未成功 push** 且是本会话 HEAD）。
4. 用 `git show HEAD:<path> | rg 'LTAI|AKID'` 确认 blob 已脱敏。
5. 再 `git push`。

**不要**为了省事点 GitHub 「allow this secret」把活密钥放进公开仓——知识库要的是手法，不是密钥。

若 commit 已进远程：另开脱敏 commit 覆盖内容，并轮换/作废已泄露密钥（用户侧操作）。

## 超大 lab 二进制（不进 git）

融合 PoC 时常带上演示媒体 / 内核镜像 / 模型权重。提交前：

```text
阈值级（实测曾 >5MB）：
  qemu-system-* / vmlinuz* / *.mov / weights1.bin /
  demo.gif / demo.mp4 / VID_*.mp4
```

处理：

1. `git rm --cached`（或 reset）取消暂存，**磁盘文件可留本地 lab**。
2. 同目录写 `<原名>.NOT_VENDORED.md` 桩：注明体积 + 「分析文档仍在本目录」。
3. `.gitignore` 补对应 glob，避免再次被 `git add -A` 卷进来。

`ysoserial` 等工具链 DLL/EXE 若与 CVE 条目强绑定且体积尚可（数 MB），可保留；纯演示录像/内核镜像一律桩掉。

## ingest 暂存不入库

```gitignore
_ingest_*/
**/_ingest_*/
_probe_*/
**/_probe_*/
*.bak
backup_local_*/
```

融合完成后只留 `_ingest_<batch>/` 里的脚本 + JSON + 日志（百 KB）供审计；克隆本体删掉。

## 提交说明

大融合用一条 `feat(fusion): …`，正文列批次/技能包/报告三块 + 「详见 UPDATE-<date>.md」。
`UPDATE-<date>.md` 写给人看的变更清单，与 commit body 互补。

## 实测（TGSEC-Qtzuu 2026-09-17）

- 首推被拦：`85amz` 报告阿里云短信 `LTAI*` + `完整测绘报告` 腾讯云 `AKID*` 两对。
- 打码 + amend 后 `ece52a45` 推送成功。
- 另桩掉 qemu-system（~60MB）、vmlinuz、demo 媒体、ANE weights 等 8 个大文件。
