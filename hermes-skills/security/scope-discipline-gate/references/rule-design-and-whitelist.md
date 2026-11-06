# 规则设计、误报白名单与报告话术

## 规则设计（防假阳性的四条教训）

1. 中文判据：`(授权|权限|范围)\s*(无限|不设限|不受限|无边界)`；或「无需授权 + 攻击动作（测试/攻击/渗透/利用/开打）」同现。
2. 英文判据**必须加 `\b` 词边界**：`any\s+scope` 命中 `company scope`（comp-**any**）——栽过的坑。
3. 「无限」+「目标/资产」弱共现不得判 DANGER：`无限消耗(重放攻击打爆配额)`、`免费无限域名` 都会被误伤。
4. 真误报固化成 `selftest` 反例（6 条）：验证「规则改宽后不会假阴」。

扫描深度要覆盖到类别目录三层 + 4 层嵌套（`*/*/SKILL.md` 会漏掉嵌套包里的卡）；默认跳过 `.archive/`。

## SMELL 白名单（实测全是技术名词/方法论，不必处理）

`ptrace_scope=0`（内核参数）、`-ResultSize Unlimited`（PowerShell 参数）、Golden Ticket「无限制访问域内资源」（Kerberos 事实）、「无限 approve/permit」（合约授权滥用）、`max_bandwidth: 0`（配置样例）、证书透明度「全网扫描」（OSINT 方法）、工具帮助里的 `-m 0 = unlimited`、「登录无限流」（加固建议里描述缺陷）。

## 报告话术（三个必须）

- **必须带口径**：`DANGER 0 张（扫描口径 N 张：哪几层目录、是否含 .archive）`，并同时给出「需人工判读 M 张」；只报一个 0 是不可核的结论。
- **必须给全量证据**：扫描器是规则的、可重跑的，给出「哪条规则命中哪句原句」（`--json` 里有），不要用抽样代替。
- **定性错了就地改**：卡名/描述不足以定性，子系统名也不等于语义；报告里那句错话直接改写，不留「UPDATE」尾巴，引用过旧结论的位置一并更正。

## 全流程（写入报告前）

```bash
cd /d/测绘引擎 && export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
python tools/ops/scope_lint.py selftest
python tools/ops/scope_lint.py scan --root <外部库>/skills
python tools/ops/scope_lint.py scan --orch          # warn 必须为 0
```

收尾同步：`skill_index.py build` → `skill_catalog.py validate`（fail=0）→ `hermes_skill_sentinel.py sync --apply`。

## 配套：本库张数口径（报数与收编对账时）

同一批工具会给出三个不同的「张数」，都要带口径才不会像自相矛盾：真源活跃卡（`find … -name SKILL.md` 减去 `.archive/`） / 分发副本（store 扁平） / 索引 JSON。报数写「活跃卡 N（索引口径 M）」。

**判「新增了哪些卡」别用 `find -newermt`**：分发用 `cp -p` 保留 mtime，新落进真源的卡不会出现在「新文件」里；以 `sentinel_report.md` 的 `ingest=…copied=N` 与前后的 owned 增量为准。
