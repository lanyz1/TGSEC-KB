---
title: "APP渠道落地页与云分发桶手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# APP渠道落地页与云分发桶手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/app-channel-landing-dist/SKILL.md`

## 汇总内容

### app-channel-landing-dist

来源：`/root/.hermes/skills/security/app-channel-landing-dist/SKILL.md`

# APP 渠道落地页与云分发桶

目标须在 `config/scope*.json`。授权内默认打到 **L2**：解出真实落地域 + 抽出下载 KV / 云桶标识。  
脱壳拿 API/云钥、读 `.env`、写桶才算 L3。先问只剩：覆盖生产对象、改原超管密。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 解出跳转落地域，或认出 `/appdl/` / Beego / dingyi SO | 只看到 loading |
| L2 | merchant KV 出下载 URL，或 COS AppId / 可 List S3，或 JS 硬编码 token/回退域 | 只下到加密图 |
| L3 | 脱壳 DEX 抽出可打 API/云钥，或读到配置，或桶可写 | 只保存了 APK |

## 立刻跑

```bash
python3 tools/ops/app_channel_landing_probe.py drive --base https://授权站 --case <案>
python3 tools/ops/app_channel_landing_probe.py kv --base https://落地域 --case <案>
python3 tools/ops/app_channel_landing_probe.py decode --b64 '<拼接后的base64>'
```

产物：`测绘/app_channel/surface.json`。

## 八步

```text
① 跟 /loading/*.html，拼完分片 atob 再跳
② JS 抽 VALID_TOKEN / merchant / 回退域 / 追踪 IP
③ 下载域、回退域、追踪 IP 静默扩权（CDN 桶域名不进 targets）
④ GET /appdl/{merchant}{android|ios|pc} 枚举
⑤ 拆 COS AppId、S3 List、CloudFront iOS 链
⑥ COS 分区：403=该区有桶
⑦ APK strings 为空 + dingyi SO → 加壳，Frida dump，禁止当 dingyi.io 打
⑧ 有身份填对象矩阵；专卡阴性回表
```

## 交接

| 认到 | 走 |
|------|-----|
| `/api/core/member/frontend` + megagw | `dingyi-whitelabel-gambling-pentest` |
| 加壳 DEX / 0 URL | `apk-recon`（strings 空是预期） |
| `.git` / `.env` / Index of | `sensitive-dir-dump` |
| STS / 上传钥 | `apk-jni-sign-oss-sts` |
| 无专用栈 API | `strike-probe` |

## 真源

- 手法：`docs/playbooks/APP渠道落地页与云分发桶手法.md`
- 探针：`tools/ops/app_channel_landing_probe.py`
- 种子案：`exports/bot-recovery/bayy_shop/`
