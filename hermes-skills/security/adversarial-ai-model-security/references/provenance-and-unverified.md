# REPORT — adversarial-ai-model-security 抽取报告

## 1 读了哪些文件

上游根:`D:/skills4redteam/HiFullHouse-CyberSecurity-Skills/`

| # | 文件(模块 16 大模型安全) | 行数 | 处置 |
|---|---|---|---|
| 1 | 模型对抗攻击与防御-AdversarialAttackDefense.md | 302 | 吸收(重写代码) |
| 2 | LLM提示注入与安全防护-PromptInjectionDefense.md | 279 | 部分吸收 |
| 3 | LLM数据泄露与隐私保护-DataLeakagePrivacy.md | 290 | 部分吸收 |
| 4 | AI供应链安全-AISupplyChainSecurity.md | 313 | 吸收(修正命令) |
| 5 | 大模型红队测试-LLMRedTeaming.md | 353 | 部分吸收(丢弃伪 ID) |
| 6 | AI Agent权限与访问控制-AgentAuthorization.md | 370 | 概念吸收,代码丢弃 |
| 7 | 模型输出安全与幻觉检测-OutputSafetyHallucination.md | 303 | 部分吸收(丢弃伪包) |
| 8 | AI应用安全配置审计-AIAppSecurityConfig.md | 304 | 吸收 |
| 9 | 联邦学习安全-FederatedLearningSecurity.md | 283 | 部分吸收(丢弃伪包) |
| 10 | 多模态AI安全-MultimodalAISecurity.md | 231 | 部分吸收(丢弃死链) |
| 11 | 模块 14:`14-安全审计-SecurityAudit/skills/AI Agent安全审计-AIAgentSecurityAudit.md` | 275 | 清单吸收(治理/合规项) |

行数为本次实测(10 个模块 16 文件合计 3028 行,加模块 14 的 275 行);表中「丢弃」栏的每条原始行号见 §2 的引用。

## 2 逐条处置

### 吸收(改写为可执行内容)
- 对抗样本:上游的 FGSM/PGD 伪代码 → 重写为 PyTorch 版(本机 ast 语法校验通过,本机无 torch 未实跑),另有 ART 类名清单(官方文档核实)、上游的 L1–L4 威胁分级与 ASR/ACA/Lp 指标。
- 数据投毒检测:上游的 IsolationForest(特征+标签拼接)→ 保留并标注局限(抓不到干净标签投毒),补触发词 ASR 差分与激活聚类。
- 供应链:上游的哈希校验、SBOM 四要素、safetensors 优先、`trust_remote_code` 风险场景、镜像依赖扫描 → 全部吸收,命令按官方口径修正。
- 配置审计:上游 1–5 节(API 端点、推理服务基线、向量库、清单、自动化脚本)重整为「凭据 / 日志 / 向量库 / 工具白名单与预算 / 暴露面」五组,加入工具清单 hash、embedding 鉴权、不可逆工具人工确认等可验证项。
- 输出安全:上游的 NeMo Guardrails、Guardrails AI、LLM Guard、SelfCheckGPT、结构化输出 → 吸收并给出**核实过的**包名、类名与函数签名。
- 隐私:Presidio、Opacus、成员推断、训练数据记忆 → 吸收(Presidio/Opacus 经 PyPI 核实,Opacus 归入缓解手段)。
- 治理合规:模块 14 的审计清单(GDPR / 个保法 / EU AI Act / NIST AI RMF / DPIA)→ 精简为成本最低的几条落进目录审计。
- 映射:OWASP LLM Top 10 2025 名称取自 OWASP 官方页;ATLAS 技术与案例 ID 取自官方数据仓 mitre-atlas/atlas-data。

### 丢弃(理由)
| 上游内容 | 丢弃理由 |
|---|---|
| 全部自编 Python class「引擎」(Agent 权限枚举、工具调用框架、脱敏类、审计脚本类等) | 作业指示明确不抄;且是演示桩,无法直接跑 |
| 提示注入整卡主体(直接/间接注入话术、越狱技巧、双模型验证架构) | 与本库 ai-agent-jailbreak / fable5-jailbreak-fusion / llm-ai-security-pentest 重复,只保留"注入→工具提权"那一段并写清边界 |
| 大模型红队卡里的 ATLAS ID(T1501/T1502/T1503/T1510/T1511/T1512/T1520/T1521) | **伪 ID**:ATLAS 用 `AML.T00xx`,不存在 T15xx 编号;已换成官方 ID |
| `huggingface-cli verify-repo-signatures <repo>` | **伪命令**:本机 hf CLI 无此子命令(实测);HF 的签名面是 commit 签名 + Hub 徽标,本地核验用 gpg |
| `pip install halu-eval` + `python -m halueval.evaluate` | **包不存在**(PyPI 404,实测);HaluEval 是数据集仓库 |
| `from krum import KrumAggregator`(联邦学习安全 第 258 行) | **包不存在**(PyPI 404,实测);该卡第 128 行另有自写 `def krum(...)` 实现,属算法演示,不抄 |
| `lm_eval --tasks truthfulqa_mc` | 任务名不存在;官方仓库目录为 truthfulqa_mc1 / truthfulqa_mc2 / truthfulqa_gen |
| 上游多模态卡的工具链接:ethz-privsec/mllm-attack、ggg0912/MM-Safety、linzhiqiu/vgascore | **全部 404**(实测);已换成本次核实的替代仓库 |
| 上游隐私卡提到的 Greenery(`ethz-privsec/greenery`) | 404(实测),未采用 |
| 上游"事实核查"里用 hashlib 决定验证结论的示例 | 演示桩,不是检测手段 |
| 上游的输出过滤关键词表、越狱 payload 模板、PII 正则长表 | 与本卡定位无关或已在越狱卡;仅在需要处保留最小正则示例 |
| 上游每卡末尾的"参考资源/常用工具"整表 | 只保留可核实且本卡真的会用的;其余随死链丢弃 |

### 修正(上游写法过时/不准确)
- Garak:`--model_name/--probes` → 现行 `--target_type/--target_name/--spec --report_prefix`(依据官方 cli.py 的弃用注释)。
- Trivy:上游用的是 `trivy fs --severity HIGH,CRITICAL --exit-code 1 /path`,未限定扫描类目(默认 vuln+secret,漏 misconfig);已补 `--scanners vuln,secret,misconfig`(官方文档)。
- Safety:上游 `safety check -r requirements.txt --full-report` 是旧式,官方 README 现为 `safety scan`。
- 联邦学习框架:上游 FL 卡只列了仓库链接(adap/flower 等),没给安装命令;照名字 `pip install flower` 会装到 Celery 的监控工具,**联邦学习框架的 PyPI 名是 `flwr`**(PyPI 核实)。
- PyRIT 仓库 `Azure/PyRIT` 已归档 → `microsoft/PyRIT`;`leondz/garak` 重定向至 `NVIDIA/garak`;llm-guard 仓库已归档(2026-07)。
- CLEVER 分数:上游只列为指标,未给实现;经查 ART 官方提供 `art.metrics.clever_u` / `clever_t`,已在参考文件中补上。
- ATLAS ID:红队卡第 29 行起用 T1501/T1502… 这一套编号(伪),但同卡第 298 行又引了正确的 `atlas.mitre.org/techniques/AML.T0043` 链接——说明伪 ID 出自该卡自制对照表,已整体替换为官方 ID。

## 3 哪些来自上游 / 哪些是补充

- **来自上游**:章节骨架(对抗样本→投毒→窃取→隐私→供应链→护栏)、威胁分级与指标清单、供应链检查清单与攻击场景、AI 应用配置检查清单、幻觉检测工具选型、联邦/多模态风险点条目、Agent 权限设计原则(最小权限/纵深/人工确认/可审计)。
- **本次补充**:全部可跑代码(FGSM/PGD/C&W、safetensors 头解析、采集脚本)、ART/Garak/PyRIT/LLM Guard/SelfCheckGPT 的核实命令与签名、模型提取七步流程与查询预算、shadow model 步骤、MCP 与 LoRA 投毒入口表、OWASP×ATLAS 映射表、ATLAS 案例表(CS0019/CS0025/CS0030/CS0031/CS0035/CS0037/CS0038/CS0039/CS0040/CS0041/CS0046/CS0049/CS0051/CS0052/CS0053/CS0054/CS0056)、与库内已有卡的边界表。

## 4 本次核实方式与遗留缺口

**核实方式**:PyPI JSON(包名/版本)、GitHub API(仓库是否存在、是否归档)、官方文档与源码(cli.py、`hf --help`、README、函数签名)、atlas-data 官方 YAML(ID 与案例名)、本机实测(numpy 对抗实验、safetensors 头解析、11 个上游文件读取)。

**仍有标注【未验证】的点**(写入文件时已逐条标注):torch/C&W 与 ART 未在本机安装,相关代码只过语法校验;Garak `--target_type` 取值与 probe 全清单、PyRIT scenario/target 全清单、向量库 REST 具体路径、`pip install lm-eval`、gitleaks/detect-secrets/trufflehog 子命令、Counterfit/Giskard/LLMFuzzer、llama.cpp GBNF 命令行。

## 5 产出

- `references/model-layer-attacks.md`
- `references/ai-app-audit-guardrails.md`
- `DRAFT-SKILL.md`(frontmatter 仅 name/description;description 首段即触发)
