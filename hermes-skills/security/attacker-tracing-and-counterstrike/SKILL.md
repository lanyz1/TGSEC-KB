---
name: attacker-tracing-and-counterstrike
description: 溯源/反制攻击者时用：日志指纹→画像→反打其工具链。
---

# 溯源与反制（测绘引擎）

进攻链的镜像：把「侦察→定位→打点→验证」用在攻击者身上。
两段式：**先溯源**（锁身份/资产）→ **再反制**（拿攻击者机器或客户端）。

触发词：溯源、反制、蓝队、攻防演练防守、攻击者画像、CS/蚁剑/sqlmap/Goby/AWVS 反制、蜜罐。

| 档 | 成立 | 不算 |
|----|------|------|
| primitive | 捕获攻击源（IP/样本/流量） | 只看了一眼 WAF 告警 |
| L2 | 攻击者画像（工具+归属+身份关联） | 单条 IP 无归属 |
| L3 | 反制落地：拿到攻击者 VPS/客户端权限 | 「理论上可反制」 |

## 溯源五步

```text
① 捕获攻击源：WAF/态势感知/全流量/EDR/堡垒机/蜜罐/Web 日志/邮件网关
② 样本特征提取：webshell→编码器+密钥+密码参数；木马→config+C2+证书
③ IP 定位：ASN/WHOIS/反查/威胁情报/端口反扫/被控机日志关联
④ 社交定位：蜜标投递 + JSONP/XSS 前端漏洞取网络身份
⑤ 时间线：把 ①-④ 按时间对齐，出攻击者画像报告
```

## 反制矩阵

| 目标 | 切入点 | 前置 | 证据 |
|------|--------|------|------|
| AntSword | 改后门返回内容，客户端侧 XSS→RCE | ≤2.0.7 | 攻击者机回连 |
| CS 客户端 | beacon 元数据注入 SVG/HTML = CVE-2022-39197 | CS ≤4.7 | 客户端执行命令 |
| CS TeamServer | checksum8 指纹定位 + 登录爆破 | 样本已暴露 C2 | 弱口命中 |
| Goby / AWVS | 目标页返回 exp 打扫描器内置浏览器 | 老版本 | 扫描机回连 |
| sqlmap | 构造注入页固定参数 + 管道符回注；rogue MySQL 读客户端文件 | `--os-shell` / local_infile | 文件内容落地 |
| 蜜罐 | 蜜标投递 + JSONP/XSS 取画像；虚假备份/OVPN 诱饵 | 有蜜罐产品 | 画像数据 |

细节、版本约束与失败记录见 `references/counterstrike-playbook.md`。

## 立刻跑

```bash
python3 scripts/scan_log_fingerprint.py --log access.log --json out.json
python3 scripts/scan_log_fingerprint.py --log /var/log/nginx/access.log --top 20
```

指纹字典：`references/attacker-fingerprint-dict.md`（可扩充）。

## 交接

| 认到 | 走 |
|------|-----|
| 已拿攻击者 shell | `host-ir-check` 先取证后动手 |
| 样本是 webshell | `webshell-evasion-and-memory-shell` 查杀段 |
| 需要事件定级/处置 | `incident-response` |
| 流量还原 | `traffic-analysis-pcap` · `protocol-reverse` |
| 攻击者用扫描器 | `recon-discriminators` 防误判 |

## 真源

- 溯源模型与设备清单：`references/tracing-model.md`
- 反制细节（客户端侧）：`references/counterstrike-playbook.md`
- 反制细节（服务端/蜜罐/rogue MySQL）：`references/counterstrike-server-side.md`
- 指纹字典：`references/attacker-fingerprint-dict.md`
- 探针：`scripts/scan_log_fingerprint.py`（日志→IP 聚合+指纹，已实测）
