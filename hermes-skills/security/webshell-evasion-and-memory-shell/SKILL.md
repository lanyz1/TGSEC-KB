---
name: webshell-evasion-and-memory-shell
description: Webshell 免杀与 Java 内存马时用：混淆/流量/注入/查杀四段。
---

# Webshell 免杀与 Java 内存马

服务端权限维持的载荷面：**静态免杀 + 流量免杀 + 内存驻留 + 检测查杀**。
触发词：webshell 免杀、内存马、冰蝎、哥斯拉、蚁剑、PHPFuck、Agent 内存马、D盾/河马、无文件落地。

| 档 | 成立 | 不算 |
|----|------|------|
| primitive | 载荷生成并可执行 | 只混淆没跑通 |
| L2 | 落地被杀软/云查杀判为干净且功能完整 | 只过 D盾 单引擎 |
| L3 | 内存马注入成功且重启存活/无文件 | “理论上可注入” |

## 四段结构

```text
① 静态免杀：字符串变换 → 函数特性 → 类特性 → 混合（去工具格式特征最关键）
② 流量免杀：编码器自定义（蚁剑）/ 自写加密器（哥斯拉）/ 协义伪装（冰蝎）
③ 内存驻留：Servlet/Filter/Listener/Spring Interceptor/Valve/Java Agent（无文件）
④ 查杀验证：本地扫描器 + 流量侧特征 + 内存侧比对，两边都要过
```

| 段 | 详细手法 | 参考 |
|----|----------|------|
| ① | 逆序/注释/变量函数/二进制定位特征码 | `references/webshell-evasion.md` |
| ② | 蚁剑编码器、哥斯拉 AES/XOR、冰蝎密钥=密码 MD5 前 16 位 | `references/webshell-evasion.md` |
| ③ | 六类内存马注册点 + 注入方式 | `references/memory-shell.md` |
| ④ | 静态扫描、流量特征、内存取类名 | `references/detect-and-kill.md` |

## 立刻跑

```bash
python3 scripts/webshell_static_scan.py --path /var/www/html --ext php,jsp,aspx
python3 scripts/webshell_static_scan.py --path ./upload --json out.json --show
```

判定：脚本给的是**线索分**（0-100），分数高 ≠ 确认木马；必须人工看上下文（`--show` 打印命中行）。

## 交接

| 认到 | 走 |
|------|-----|
| 上传点还没拿下 | `file-upload-webshell` · `path-traversal-pentest` |
| 反序列化入口打内存马 | `java-framework-deserialization-family` |
| 内存马落到 Tomcat（含 Valve） | `middleware-parser-and-legacy-cve-family` |
| 样本是别人放的 | `attacker-tracing-and-counterstrike` |
| 免杀面向 EDR/RAT 而非 webshell | `evasion` · `edr-bypass-re` |

## 铁律

- 静态免杀**先去工具格式特征**（变量名/函数顺序/空行风格），再谈混淆；直接套 base64 早入库了。
- 内存马必须验证 **重启后是否存活 / 无文件落地**，否则只是 webshell。
- 免杀只对授权目标与授权样本用；查杀/取证均留哈希与样本。

## 真源

- `references/webshell-evasion.md` · `references/memory-shell.md` · `references/detect-and-kill.md`
- 探针：`scripts/webshell_static_scan.py`（已实测）
