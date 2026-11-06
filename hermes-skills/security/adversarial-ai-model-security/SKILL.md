---
name: adversarial-ai-model-security
description: "Use when 打对抗ML/模型层:对抗样本、投毒、模型窃取、AI供应链。"
---

# 模型层安全(对抗样本 / 投毒 / 窃取 / 推断 / 护栏)

## 什么时候用

- 目标给了**模型产物或训练链路**:模型文件、LoRA/adapter、数据集、推理镜像、联邦学习节点
- 要评估"**不发提示词也能影响模型行为**"的问题:对抗样本、后门/投毒、模型窃取、成员推断、训练数据提取
- 要审 AI 应用的**护栏与配置**:key 存放、日志、向量库权限、工具白名单、调用深度、输出结构化
- 要做红队自动化与合规映射:Garak/PyRIT 跑批、OWASP LLM Top 10 2025 → MITRE ATLAS 对照

**边界(别在这里做)**:提示词层越狱/破甲 → ai-agent-jailbreak、fable5-jailbreak-fusion;Agent 运行时(Host 伪造、特权 RPC)→ ai-agent-runtime-pentest;客服/在线客服 bot → ai-customer-service-attack-surface;RAG 应用面 → trade-ideas-ai-rag-pentest;AI/ML 概念总览 → ai-ml-security;应用入口路由 → llm-ai-security-pentest。

## 工作流

1. **定位面**:是"模型产物"还是"应用护栏"?前者进 §A,后者进 §B。两件都做时先 A 后 B(A 的结论决定 B 的测法)。
2. **A. 模型层**
   - 白盒(有模型+权重):算对抗样本 ASR(见 references/model-layer-attacks.md §1),再测后门(候选触发词 ASR 差分)与模型提取上限(是否给 logits)。
   - 黑盒(只有 API):先测输出面信息量(logits/top-k/概率),再估查询预算做蒸馏提取,最后测成员推断基线(规则版)。
   - 训练链路:数据集近重复/标签翻转抽样、adapter 与基座分别做权重差分、MCP/工具描述变更审计。
3. **B. 应用护栏**
   - 先跑配置清单(§1),逐项留证据;护栏永远是"旁路优先"——先测护栏抓不到的那一半(编码、跨语言、分段、多模态输入)。
   - 输出侧:结构化约束 + 再校验 + 解析失败降级路径,三条缺一即记问题。
4. **回归与留证**:每个发现都要能复跑(固定 seed、固定 revision、固定查询集),报告里带命令与原始输出。
5. **映射**:发现落到 OWASP LLM Top 10 2025 与 ATLAS ID(model-layer-attacks.md §6),便于横向对齐。

## 命令速查

```bash
# --- 模型层 ---
pip install adversarial-robustness-toolbox     # ART 1.20.1:对抗样本/提取/成员推断(库,不是 CLI)
pip install textattack                         # 文本对抗(2 选 1:textattack attack --help)
pip install opacus                             # 差分隐私训练(缓解训练数据记忆)

# --- 红队自动化 ---
pip install garak && garak --list_probes
garak --target_type <类型> --target_name <模型> --spec probes.encoding --report_prefix run1
pip install pyrit && pyrit_scan --help         # 示例:pyrit_scan run airt.rapid_response --target openai_chat

# --- 供应链静态扫描(三道防线,先扫后用)---
pip install modelscan picklescan fickling
modelscan -p /path/model.pkl
picklescan --path ./pytorch_model.bin
picklescan --huggingface <owner/repo>
fickling --check-safety -p pickled.data
hf download <owner/repo> --revision <commit-sha> --local-dir ./m
hf cache verify <owner/repo>

# --- 依赖与镜像 ---
trivy fs --scanners vuln,secret,misconfig .
pip install safety && safety scan

# --- 护栏与幻觉 ---
pip install llm-guard nemoguardrails guardrails-ai selfcheckgpt
from llm_guard import scan_prompt, scan_output   # 包根导出;scan_prompt(scanners, prompt, fail_fast=False)
lm_eval --model hf --model_args pretrained=<model> --tasks truthfulqa_mc1,truthfulqa_mc2
```

## Pitfalls

- **别信"限速能防提取"**:限速只抬成本;真正有效的是收窄输出面(top-1/截断/加噪)+ 水印 + 查询分布漂移检测。
- **toy 实验不等于模型安全**:线性/浅层模型上 FGSM 与 PGD 结果相同(本机实测),ASR 低不代表免疫;要在目标真实结构上测。
- **干净标签投毒骗过离群检测**:基于特征-标签离群(IsolationForest 一类)的检测抓不到它,必须做触发词 ASR 差分或激活聚类。
- **`trust_remote_code=True` = 加载即执行**:任何评测/扫描都必须在无凭证沙箱里做,先扫后加载,优先 safetensors。
- **护栏是旁路目标,不是验收项**:通过护栏≠安全;护栏未覆盖的输入模态与语言要单独枚举测试。
- **幻觉检测要跑基线**:TruthfulQA 类基准给的是分布级信号,不能替代具体业务事实核验。
- **别把 PyPI 名字想当然**:`flwr` 才是联邦学习 Flower(`flower` 是 Celery 监控);`krum`、`halu-eval` 这些上游引用的包不存在。
- **过时命令会白跑**:garak 的 `--model_name/--probes`、`trivy --security-checks`、`safety check -r` 都是旧式;`huggingface-cli verify-repo-signatures` 从来不存在。
- **联邦学习不要只测聚合函数**:客户端梯度裁剪/加噪、参与方旁路通道、投毒剔除缺一即被拜占庭打穿。

## 参考文件

- `references/model-layer-attacks.md` — 对抗样本(FGSM/PGD/C&W + ART)、后门/投毒与检测、模型窃取/提取、成员推断与训练数据提取、投毒入口、注入→工具提权链、OWASP LLM Top 10 2025 × ATLAS 映射。
- `references/ai-app-audit-guardrails.md` — 配置审计清单(凭据/日志/向量库/工具白名单/调用预算)、Garak/PyRIT/ART 真实命令、护栏与幻觉检测、结构化输出、多模态与联邦风险点、AI 供应链审计命令。
- `references/provenance-and-unverified.md`：来源核对（哪些命令搬自上游 / 哪些是补充 / 未验证清单）。
