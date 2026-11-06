---
name: gva-knownkey-local-write
description: >-
  GVA 已知 jwt.signing-key 伪造超管票 → get/setSystemConfig → oss-type=local
  任意路径上传写文件；同机多套密钥隔离与 sysExportTemplate 坑。
  触发：已知签名钥、伪造888、setSystemConfig、local.path 写文件、同机多GVA、
  djboss、Reeloop、Nightplay 旁系超管、exportExcelByToken 获取失败。
  开放注册植入仍走 ginvue-admin-stealth-takeover；领奖走 ginvue-admin-reward。
---

# GVA 已知签名钥伪造 + 本地上传写文件

**前提**：目标在 `config/scope*.json`。

**成功口径**：

- L2：伪造 888 票通过 `getSystemConfig`（拿到 jwt/mysql/oss 等字段名级证据）
- L2+：`setSystemConfig` 写通（noop 或改 `oss-type`/`local.path` 后**必须 restore**）
- L3：本地上传落到绝对路径（url 字段为 `/www/...`）；公网执行另证，**写≠RCE**

## 何时启用

- 已有 `jwt.signing-key` / `jwt-key`（报告、heap、他套泄露、配置备份）
- 需验证同机其他 vhost 是否共用密钥
- 超管后要打 `setSystemConfig` → 本地存储写文件 / 同机目录枚举

不适用：还没有钥、要靠开放注册植入 → `ginvue-admin-stealth-takeover`。

## 强制行为

1. **默认禁止** `resetPassword` / 改原 admin 密。  
2. 改 `system.oss-type` / `local.path` 后**必须 restore** 原配置；案卷留 backup JSON。  
3. 上传只用 marker / 只读探测脚本；破坏性 webshell 与反弹按授权闸，但公网未映射时不要空烧。  
4. `importURL file://` 的 code=0 **不算读文件**（只登记 URL）。  
5. casbin 路径命中 ≠ HTTP 路由存在；以实际 status 为准。  
6. `sysExportTemplate`：无 `templateInfo` 的模板会返回 token 但下载「获取失败」；先导出内置 `api` 或已有完整模板。  
7. 同 IP 多套 GVA：**逐 host 验签**，禁止假设 signing-key 共用。  
8. 用户「暂停」→ 停进攻。

## 最短命令

```bash
# 伪造 + 拉配置 + 跨 host 验签
python3 tools/ops/gva_knownkey_write_probe.py chain \
  --base 'https://授权GVA' \
  --signing-key '<jwt.signing-key>' \
  --cross-bases 'https://同机旁系1,https://同机旁系2' \
  --case <案卷> --insecure

# 可选：本地写 marker 后自动 restore
python3 tools/ops/gva_knownkey_write_probe.py write-marker \
  --base 'https://授权GVA' --signing-key '<key>' \
  --path /tmp/se_gva_marker --case <案卷> --insecure
```

## 真源

- Playbook：`docs/playbooks/GVA已知签名钥与本地上传写文件手法.md`
- 静默注册植入（无钥时）：`ginvue-admin-stealth-takeover`
- 案卷样例：`exports/bot-recovery/coinlist000-nightplay/测绘/PAUSE_REPORT_2026-09-13.md`
