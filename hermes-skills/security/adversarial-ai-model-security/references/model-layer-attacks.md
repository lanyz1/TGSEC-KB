# 模型层对抗参考(对抗样本 / 后门投毒 / 模型窃取 / 成员推断 / 多模态 / 联邦)

标注约定:未标注 = 本次本机实测,或经官方文档/官方仓库核实;【未验证】= 本次无法复现或来源存疑,禁止照抄。
上游 = HiFullHouse/CyberSecurity-Skills 第 16 模块(仅取事实与工具名,其自编 Python class「引擎」一律不抄)。

## 0 边界:本卡只做「模型层」

| 本库已有卡 | 它覆盖的 | 与本卡边界 |
|---|---|---|
| llm-ai-security-pentest | AI/LLM 应用攻击面路由 | 应用入口;本卡处理模型/权重/训练数据 |
| ai-ml-security | 对抗/投毒/窃取的分类总览(概念) | 概念索引;本卡给可执行代码与命令 |
| ai-agent-jailbreak / fable5-jailbreak-fusion | 提示词层越狱、破甲 | 不改模型不改权重,属提示层 |
| ai-agent-runtime-pentest | Agent 运行时(Host 伪造/RPC) | 运行时;本卡管模型产物 |
| ai-customer-service-attack-surface / trade-ideas-ai-rag-pentest | 客服 bot、RAG 应用 | 应用;本卡只取「RAG 语料投毒→回答偏移」 |
| mcp-builder | MCP server 构建 | 工具侧;本卡把 MCP 只当供应链入口 |

一句话判据:**「不发提示词也能影响模型行为」的攻击归本卡。**

## 1 对抗样本

### 1.1 PyTorch 手写 FGSM / PGD(ast 语法校验通过;本机未装 torch,未实跑)

```python
import torch, torch.nn.functional as F

def fgsm(model, x, y, eps, clip_min=0.0, clip_max=1.0):
    x_adv = x.clone().detach().requires_grad_(True)
    loss = F.cross_entropy(model(x_adv), y)
    grad, = torch.autograd.grad(loss, x_adv)
    return torch.clamp(x + eps * grad.sign(), clip_min, clip_max).detach()

def pgd(model, x, y, eps, alpha, steps=20, clip_min=0.0, clip_max=1.0):
    x_adv = x.clone().detach()
    for _ in range(steps):
        x_adv.requires_grad_(True)
        loss = F.cross_entropy(model(x_adv), y)
        grad, = torch.autograd.grad(loss, x_adv)
        x_adv = x_adv.detach() + alpha * grad.sign()
        x_adv = torch.min(torch.max(x_adv, x - eps), x + eps)   # 投影回 eps 球
        x_adv = torch.clamp(x_adv, clip_min, clip_max).detach()
    return x_adv
```

### 1.2 C&W L2(同上:语法通过,未实跑)

```python
def cw_l2(model, x, y, c=1.0, kappa=0.0, steps=200, lr=0.01, clip_min=0.0, clip_max=1.0):
    w = torch.zeros_like(x, requires_grad=True)
    opt = torch.optim.Adam([w], lr=lr)
    for _ in range(steps):
        x_adv = 0.5 * (torch.tanh(w) + 1.0) * (clip_max - clip_min) + clip_min
        d = (x_adv - x).flatten(1).norm(dim=1)
        logits = model(x_adv)
        real = logits.gather(1, y.view(-1, 1)).squeeze(1)
        other = logits.masked_fill(F.one_hot(y, logits.size(1)).bool(), -1e9).max(1).values
        f = torch.clamp(real - other + kappa, min=0.0)
        loss = d.sum() + c * f.sum()
        opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        return 0.5 * (torch.tanh(w) + 1.0) * (clip_max - clip_min) + clip_min
```

本机用 numpy 复刻同一数学(2 维特征逻辑回归,clean acc 0.959):

| eps | FGSM ASR | PGD ASR | 实测 L∞ |
|---|---|---|---|
| 0.05 | 5.1% | 5.1% | 0.050 |
| 0.10 | 6.6% | 6.6% | 0.100 |
| 0.20 | 9.4% | 9.4% | 0.200 |
| 0.40 | 18.4% | 18.4% | 0.400 |

读法:投影实现正确(L∞ 严格等于 eps);**线性/浅层模型上 FGSM 与 PGD 等价**,两者拉开差距需要深度非线性模型(Madry et al. 2017, arXiv:1706.06083)。别把 toy 上的低 ASR 当成"模型免疫"。

### 1.3 ART 封装(类名取自官方文档 1.20;本机未装 ART,未实跑)

```python
import numpy as np, torch, torch.nn as nn
from art.estimators.classification import PyTorchClassifier
from art.attacks.evasion import FastGradientMethod, ProjectedGradientDescent
classifier = PyTorchClassifier(model=net, loss=nn.CrossEntropyLoss(),
                               optimizer=torch.optim.Adam(net.parameters(), lr=1e-3),
                               input_shape=(3, 32, 32), nb_classes=10, clip_values=(0.0, 1.0))
adv = ProjectedGradientDescent(classifier, eps=0.03, eps_step=0.007, max_iter=40).generate(x, y)
```

- 安装:`pip install adversarial-robustness-toolbox`(PyPI 1.20.1 核实)
- 可用 evasion 类(文档核实):FastGradientMethod、ProjectedGradientDescent、AutoProjectedGradientDescent、CarliniL2Method、CarliniLInfMethod、AutoAttack、SquareAttack、BoundaryAttack、HopSkipJump、ZooAttack、SimBA、Wasserstein、AdversarialPatchPyTorch
- 防御类(文档核实):preprocessor FeatureSqueezing/JpegCompression/Mp3Compression/SpatialSmoothing/TotalVarMin/PixelDefend/VideoCompression;trainer AdversarialTrainer/AdversarialTrainerMadryPGD/AdversarialTrainerTRADESPyTorch/AdversarialTrainerFBFPyTorch

### 1.4 威胁分级与指标

L1 纯黑盒查询(ZOO/SimBA)→ L2 黑盒+概率输出(Boundary)→ L3 白盒梯度(FGSM/PGD)→ L4 白盒+架构(C&W/AutoAttack)(上游分级,与 ART 类名一致)。指标:ASR、ACA、Lp 失真(上游);CLEVER 分数可直接用 `art.metrics.clever_u` / `art.metrics.clever_t`(官方文档核实,ART metrics 另有 empirical_robustness、loss_sensitivity、PDTP、SHAPr、wasserstein_distance)。

### 1.5 文本 / LLM 侧对抗

- `pip install textattack`(PyPI 0.3.11 核实),`textattack attack --help`(仓库 README 核实);TextFooler 等词替换类。
- 提示级优化攻击 GCG:仓库 llm-attacks/llm-attacks、GraySwanAI/nanoGCG;评测集 HarmBench、JailbreakBench(均为官方仓库,本次核实存在)。
- 与越狱卡的边界:GCG 产出的是**优化得到的 token 后缀**,可跨模型迁移,属模型层鲁棒性;一次性话术改写归 ai-agent-jailbreak。

## 2 后门与投毒

### 2.1 形态(ATLAS 官方 ID,取自 atlas-data 官方数据)

- 触发器后门:AML.T0018 Manipulate AI Model、AML.T0043.004 Insert Backdoor Trigger;案例 AML.CS0019 PoisonGPT、AML.CS0013 移动 App 深度学习后门
- 数据投毒:AML.T0020 Poison Training Data、AML.T0019 Publish Poisoned Datasets
- 大规模语料投毒:AML.CS0025 Web-Scale Data Poisoning: Split-View Attack
- 供应链投毒:AML.T0010 AI Supply Chain Compromise、AML.CS0031 Malicious Models on Hugging Face、AML.CS0028 AI Model Tampering via Supply Chain Attack
- 编码助手规则文件后门:AML.CS0041 Rules File Backdoor

### 2.2 检测要点

- 数据侧:近重复簇、异常短样本、候选触发词 n-gram 频次、标签翻转比例。上游给了 IsolationForest(特征+标签拼接)抓离群样本——能跑,但只抓明显离群,对干净标签投毒基本无效。
- 模型侧:候选触发词 ASR 差分(同一批输入 ± 触发词,看预测/输出翻转率)、内部激活聚类与异常神经元、微调前后权重差分(diff 集中在少数层 = 可疑)。
- 防御侧:ART defences 检测器类名本次未逐条核验【未验证】;可用的是上文 1.3 的 preprocessor/trainer 列表。

### 2.3 越狱之外的投毒入口(全部为 2025–2026 在野/报告形态)

| 入口 | 手法 | 抽检点 |
|---|---|---|
| 爬取语料 | 自建站/论坛内容进预训练、RAG 索引(AML.CS0025) | 来源白名单、抓取时间戳、近重复 |
| HF dataset 仓库 | 上传带触发器样本,标注正常(AML.T0019) | 抽样人工看、sha256 pin revision |
| 模型卡 trust_remote_code | 加载即执行任意代码(上游场景 3) | 只用 safetensors、禁 trust_remote_code |
| LoRA/adapter 分发 | 基座无毒,后门藏在 adapter 权重 | adapter 权重差分、多 adapter 混合前测 |
| MCP / 工具描述 | AML.T0110 AI Agent Tool Poisoning、AML.T0099 Tool Data Poisoning;案例 AML.CS0053、AML.CS0054 | 工具清单变更审计、描述人工复核 |

## 3 模型窃取 / 提取(API 查询式蒸馏)

### 3.1 流程(纯黑盒,只要有推理 API)

1 圈定任务面与输入分布 → 2 估查询预算(单价×次数) → 3 采集/生成查询集 → 4 拉标签(有 logits 最好,top-1 也可) → 5 训练 substitute 模型 → 6 算一致性(与目标同输入同输出率) → 7 迁移验证(替换进下游任务看效果)。

```python
# 采集端:把 API 当标注机(只需 requests)
import requests, json
rows = []
for q in queries:                      # queries: 你自己的输入集
    r = requests.post(API, json={"input": q}, headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
    rows.append({"input": q, "label": r.json()["output"]})
json.dump(rows, open("steal.jsonl", "w"), ensure_ascii=False)
```

要点:蒸馏损失用 KL(有 logits)优于 CE(仅硬标签);查询集要覆盖目标真实输入分布,否则提取模型只在你采样的区域像。**API 返回 logits 与否直接决定提取上限**,这是评估里的第一个测量项。

### 3.2 ART 提取攻击(官方文档核实签名)

`art.attacks.extraction.CopycatCNN(classifier, batch_size_fit, batch_size_query, nb_epochs, nb_stolen, use_probability)`、`KnockoffNets(classifier, ..., sampling_strategy='random', reward='all')`、`FunctionallyEquivalentExtraction(classifier, num_neurons=None)`。

### 3.3 现实案例(ATLAS 官方数据)

AML.CS0007 GPT-2 Model Replication(复刻)、AML.CS0056 Model Distillation Campaigns Targeting Anthropic Claude(工业化蒸馏)、AML.CS0030 LLM Jacking(盗用 API 凭证再转卖/续用——"窃取"的另一半在凭证,不在算法)。

### 3.4 防御

限速只抬成本、不阻断;真正有效的是输出面收窄(top-1/截断/量化/加噪)、水印与指纹、查询分布漂移检测、凭证级配额+异常告警(对应 AML.CS0030)。

## 4 成员推断与训练数据提取

### 4.1 成员推断(ART,类名与签名核实)

`art.attacks.inference.membership_inference.MembershipInferenceBlackBox(estimator, input_type='prediction', attack_model_type='nn')`、`MembershipInferenceBlackBoxRuleBased(classifier)`(后者按"置信度>阈值即判为成员",零训练成本,先跑它拿基线)。

### 4.2 影子模型自建(黑盒可用)

训练 N 个结构近似的影子模型 → 每个影子模型的训练集标 member、其余标 non-member → 用(影子模型对该样本的输出向量, 标签)训练攻击分类器 → 打目标模型的输出向量。**同分布、样本重复度高的数据集命中率最高。**

### 4.3 LLM 训练数据提取

前缀扰动 + 多次贪婪续写 + 去重排序,是公开论文的标准做法(Extracting Training Data from Large Language Models, arXiv:2012.07805;编号与标题本次按公开论文核对)。上游做法(返回文本跑 PII 正则)可作为落地的最小检测:

```python
import re
PII = re.compile(r"(\b1[3-9]\d{9}\b)|(\b\d{17}[\dXx]\b)|([\w.+-]+@[\w-]+\.[\w.]+)")
for resp in responses: print(PII.findall(resp))
```

缓解:`pip install opacus`(PyPI 1.6.0 核实,差分隐私训练)+ 数据去重(被记住的几乎都是重复样本)。

## 5 提示注入 → 工具调用提权链(ATLAS 实证;本卡只写"落到模型/数据层"的那一段)

链条:`注入源(网页/文档/邮件/RAG 条目)` → AML.T0051.001 Indirect → 进 Agent 上下文(AML.T0080 AI Agent Context Poisoning)→ 触发工具(AML.T0086 Exfiltration via AI Agent Tool Invocation)→ 外带/破坏;旁路支线:AML.T0092 Manipulate User LLM Chat History、AML.T0094 Delay Execution of LLM Instructions、AML.T0068 LLM Prompt Obfuscation、AML.T0057 LLM Data Leakage、AML.T0056 Extract LLM System Prompt。

| 案例(官方 ID) | 落点 |
|---|---|
| AML.CS0035 Slack AI 外带 / AML.CS0037 Copilot Studio 工具外带 | 间接注入→工具外带 |
| AML.CS0038 延迟自动工具调用 / AML.CS0039 Jira Service Management | 延迟触发、借第三方系统落脚 |
| AML.CS0040 ChatGPT Memories / AML.CS0042 SesameOp | 持久化(记忆、C2 借官方 API) |
| AML.CS0046 Claude Computer-Use 数据破坏 / AML.CS0049 投毒 ClawdBot Skill / AML.CS0051 OpenClaw C2 | 破坏性工具、技能投毒 |
| AML.CS0052 LLMSmith RCE / AML.CS0016 MathGPT 代码执行 | 注入直落 RCE |

判定三问:注入是否改变模型对**自身权限**的认知(T0092)?是否触发**不可逆工具**(T0086)?是否**延迟触发**避开当次人工复核(T0094)?取证要求:prompt 全文 + 工具入参 + 工具清单 hash 一并留存。具体越狱话术见 ai-agent-jailbreak / fable5-jailbreak-fusion。

## 6 OWASP LLM Top 10 2025 × MITRE ATLAS 映射(名称取自 OWASP 官方页,ID 取自 atlas-data)

| OWASP(2025) | 主 ATLAS | 本库落点 |
|---|---|---|
| LLM01 Prompt Injection | T0051(.000/.001/.002)、T0068 | ai-agent-jailbreak + 本卡 §5 |
| LLM02 Sensitive Information Disclosure | T0057、T0056、T0024 | 本卡 §4、数据泄露卡 |
| LLM03 Supply Chain | T0010、T0019、CS0031 | 本卡 §2.3 + references/ai-app-audit-guardrails.md §6 |
| LLM04 Data and Model Poisoning | T0020、T0018、T0043.004 | 本卡 §2 |
| LLM05 Improper Output Handling | T0048 | references/ai-app-audit-guardrails.md §3 |
| LLM06 Excessive Agency | T0086、T0080、T0094 | Agent 权限卡 + 本卡 §5 |
| LLM07 System Prompt Leakage | T0056、T0092 | 越狱卡、审计文件 §1.2 |
| LLM08 Vector and Embedding Weaknesses | T0020、T0080 | 审计文件 §1.3 |
| LLM09 Misinformation | T0031 | 审计文件 §3.2 |
| LLM10 Unbounded Consumption | T0029、T0040 | 审计文件 §1.4 |

## 7 多模态 / 联邦学习

视觉对抗补丁、图像内嵌注入、音频隐蔽指令、梯度泄露与拜占庭聚合的风险点与自查命令见 `references/ai-app-audit-guardrails.md` §4/§5;上游该两个文件的工具链接(ethz-privsec/mllm-attack、ggg0912/MM-Safety、linzhiqiu/vgascore、ethz-privsec/greenery)本次全部 404,**已丢弃**,替代见该文件。
