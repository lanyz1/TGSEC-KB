## 九、DevSecOps 审计集成

### 9.1 CI 中 SAST 配置（GitHub Actions）

```yaml
# .github/workflows/sast.yml
name: SAST
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
  security-events: write
jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Semgrep
        run: |
          pip install semgrep
          semgrep scan --config=auto --json > semgrep.json
      - name: 上传 SARIF（GitHub Security tab 展示）
        run: |
          pip install semgrep sarif-tools
          sarif-tools convert semgrep.json -o semgrep.sarif
          # 或直接: semgrep scan --config=auto --sarif > semgrep.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: semgrep.sarif
  codeql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with: { languages: java }
      - uses: github/codeql-action/analyze@v3
```

**CI 工具链安全（2026 重要教训）：**
- Checkmarx ast-github-action 2026 年 3-4 月两轮供应链投毒事件：**必须 SHA pin，不能只 pin tag 版本**
- 示例：`uses: github/codeql-action/analyze@<完整SHA>`（tag 可被覆盖）

### 9.2 质量门禁与增量扫描

```yaml
# 门禁策略：PR 阻断规则
# 1. 新发现的高/严重级漏洞（增量扫描，diff-aware）阻断合并
# 2. 存量漏洞不计入阻断（避免历史噪音卡死开发）
# 3. 供应链：lockfile 变更触发全量 SCA
# 4. 密钥扫描：pre-commit 钩子阻断
semgrep scan --config=auto --baseline-commit HEAD~1   # 只扫本次改动
```

### 9.3 CI 中 SAST 的绕过与盲区（审计者视角）

```
- 构建模型不一致：SAST 用与生产不同的配置解析 → 结果失真
- 符号解析失败：工具静默跳过未解析的 import/类型 → 覆盖缺口
- 语言特性不支持：新语法/动态特性被忽略
- 排除规则滥用：.gitignore/semgrepignore 把敏感目录（routes/controllers）排除
- 扫描超时跳过：大文件 5MB 上限、超时静默跳过（应显式报告 SKIPPED）
- 门禁绕过：--no-error、exit 0 强制通过、baseline 刷新误删告警
- 工具本身被投毒：CI 拉取恶意 Action 版本（见 9.1）
- 审计对策：抽查 SARIF 的 skip/error 条目，检查 CI 日志中工具是否真实运行
```

### 9.4 结果标准化与去噪

```bash
# SARIF 统一格式（跨工具聚合）
semgrep scan --config=auto --sarif > semgrep.sarif
codeql database analyze ./db --format=sarif-latest -o codeql.sarif

# 去噪策略
- 按规则 ID 统计误报率，高误报规则降级/调参
- 结果按"可利用性"排序而非规则严重度
- 自动化 triage：LLM 分类（见第八章）后只留 P0/P1 进工单
- 维护基线：每轮扫描与基线 diff，只处理增量
```

