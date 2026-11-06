# AI 应用配置审计与输出护栏参考

标注约定:未标注 = 本机实测或官方文档/官方仓库核实;【未验证】= 本次无法复现,照抄前先自测。
命令里的主机名/仓库名/模型名是占位,替换为目标值。

## 1 配置审计清单(每项给检查动作)

### 1.1 API key 与凭据存放
- [ ] key 不在前端 bundle/URL/日志里:`rg -n "(sk-|Bearer |api[_-]?key)" dist/ --hidden`(grep 类工具自选)
- [ ] 仓库/镜像层无硬编码密钥:gitleaks、Yelp/detect-secrets、trufflesecurity/trufflehog(三个官方仓库本次核实存在;具体子命令以各自 `--help` 为准【未验证】)
- [ ] 服务端代理模式:前端只访问自家后端,上游 key 只存后端环境变量;确认后端不把 key 回显进错误页
- [ ] 多租户:同一 key 是否跨租户共用;模型侧凭据与业务身份是否绑定(不绑 = 一把钥匙开所有账)
- [ ] key 轮换与配额:配额是按 key 还是按用户;AML.CS0030 LLM Jacking 的入口就是"拿到 key 后无限制用"

### 1.2 日志留存与最小化
- [ ] prompt/response 是否全量落盘、落多久、谁能读(越权读日志 = 直接读走用户隐私与系统 Prompt)
- [ ] 日志里排除:密钥、身份证/手机号等 PII、系统 Prompt 原文(上游做法:PII 正则+关键字过滤,可跑)
- [ ] 日志注入:用户输入里的换行/控制字符是否被转义后再写日志(否则可伪造日志行)
- [ ] 检索面:日志平台是否对 LLM 应用开放了无鉴权查询接口

### 1.3 向量库 / 检索层权限
- [ ] 是否存在"能列 collection 就能读"的未授权面(先抓服务端版本,再按官方 API 路径逐条验证;具体 REST 路径本次未复验【未验证】)
- [ ] 默认口令/无口令、以及 bind 0.0.0.0 的公网暴露
- [ ] collection 与租户是否一一隔离(共享 collection + 元数据过滤 = 典型越权读)
- [ ] embedding 服务是否也要鉴权(能调 embedding 就能做相似度枚举,绕过应用层过滤)
- [ ] 写入权限:谁能 upsert/delete;能写 = 可做 RAG 语料投毒(见 model-layer-attacks.md §2.3)

### 1.4 工具白名单与调用预算
- [ ] 工具清单是**白名单**枚举,不是黑名单过滤;新增工具要过审
- [ ] 每个工具声明:是否可逆、是否触外网、最大影响面
- [ ] 最大调用深度/次数/超时/单次返回体积全部有上限(无上限 = 一次注入可循环外带)
- [ ] 高风险工具(发信、付款、写库、执行命令)强制人工确认或双人复核
- [ ] 工具入参校验在**服务端**,不依赖模型自觉(模型生成的 URL/路径必须再校验)
- [ ] 工具清单与描述做 hash 留档,变更即告警(对应 AML.T0110 工具投毒)

### 1.5 服务暴露面
- [ ] 网关限流(按用户+按 IP)、请求体大小上限(防大 Prompt 打爆)、超时
- [ ] 推理服务不直连公网;管理面(如面板/metrics)不外露
- [ ] 错误信息不回显上游栈、不回显 key、不回显系统 Prompt

## 2 红队自动化:Garak / PyRIT / ART 真实命令

```bash
pip install garak                      # PyPI 0.17.0 核实;仓库 NVIDIA/garak(leondz/garak 已重定向到此)
garak --list_probes                    # 参数名取自 cli.py(官方源码)
garak --target_type <类型> --target_name <模型> --spec probes.encoding --report_prefix run1
garak --target_type <类型> --target_name <模型> --spec probes.encoding --generations 5
```
- **上游给的 `garak --model_name gpt-3.5-turbo --probes all` 是过时写法**:`-m/--model_name/--model_type` 自 0.13.1.pre1 起弃用,`--probes/--probe_tags/--buffs` 自 0.15.1.pre1 起弃用改为 `--spec`(依据官方 cli.py 中的弃用注释)。报告参数是 `--report_prefix`,不是上游写的 `--report_format/--report_file`。
- `--target_type` 可选值、probe 完整清单未逐项复验【未验证】,以 `garak --help` / `--list_probes` 输出为准。

```bash
pip install pyrit                      # PyPI 1.1.0;仓库 microsoft/PyRIT(Azure/PyRIT 已归档)
pyrit_scan --help                      # console script 取自官方 pyproject.toml
pyrit_scan run airt.rapid_response --target openai_chat   # 官方源码 docstring 中的示例
```
scenario/target 的完整取值未复验【未验证】,以 `pyrit_scan --help` 为准。

```bash
pip install adversarial-robustness-toolbox   # PyPI 1.20.1
# ART 是库不是 CLI,按 model-layer-attacks.md §1.3 的 PyTorchClassifier + 攻击类调用
```

上游另外列的 Counterfit / Giskard / LLMFuzzer 本次未核实版本与可用性【未验证】。

## 3 输出安全

### 3.1 护栏(输入侧 + 输出侧)
```python
# LLM Guard:PyPI llm-guard 0.3.16;注意官方 GitHub 仓库已归档(archived),2026-07 后无新提交
from llm_guard import scan_prompt, scan_output                 # 包根导出,官方源码核实
from llm_guard.input_scanners import PromptInjection, Secrets, TokenLimit, BanTopics, InvisibleText, Anonymize
from llm_guard.output_scanners import JSON, Sensitive, FactualConsistency, NoRefusal, Deanonymize, Relevance, Bias
clean, valid, score = scan_prompt([PromptInjection()], user_input, fail_fast=False)
# 官方签名:scan_prompt(scanners, prompt, fail_fast=False) -> (str, dict[str,bool], dict[str,float])
#           scan_output(scanners, prompt, output, fail_fast=False) -> (str, dict[str,bool], dict[str,float])
```
`PromptInjection` 默认模型为 `protectai/deberta-v3-base-prompt-injection`(源码核实)。
- NeMo Guardrails:`pip install nemoguardrails`(PyPI 0.24.1),Python 入口 `LLMRails`(README 核实);官方文档另提供 LLM 漏洞扫描(garak 集成)章节。
- Guardrails AI:`pip install guardrails-ai`(PyPI 0.11.0),验证器以独立包安装(`guardrails-ai-regex-match` 等),用法 `Guard().use(...)`(README 核实)。
- 审计要点:护栏是**旁路目标**——先测"护栏发现不了的那一半"(编码、跨语言、分段注入、多模态输入),再测"护栏被绕过后的兜底"(工具白名单、配额)。

### 3.2 幻觉检测
```bash
# lm-evaluation-harness:任务名 truthfulqa_mc1 / truthfulqa_mc2 / truthfulqa_gen(官方仓库目录核实)
lm_eval --model hf --model_args pretrained=<model> --tasks truthfulqa_mc1,truthfulqa_mc2
```
- **上游写的 `truthfulqa_mc` 任务名不存在**,已改为上面三个;`pip install lm-eval` 本次 PyPI 查询超时【未验证】,可用 `git clone` 后 `pip install -e .`。
- **上游写的 `pip install halu-eval` + `python -m halueval.evaluate` 不存在**(PyPI 404,本次实测),丢弃;HaluEval 是数据集仓库 RUCAIBox/HaluEval,不是可 pip 安装的 CLI。
- SelfCheckGPT:`pip install selfcheckgpt`(PyPI 0.1.7),类 `SelfCheckNLI / SelfCheckBERTScore / SelfCheckNgram / SelfCheckMQAG / SelfCheckLLMPrompt`(README 核实)——零资源黑盒检测,采样多次比一致性,适合做回归门禁。
- 上游的"事实核查"示例用 `hashlib` 决定验证结果,是**演示桩代码,直接丢弃**。

### 3.3 结构化输出约束(比"让模型输出 JSON"可靠)
- [ ] 用服务端语法约束:JSON Schema / 文法约束解码(OpenAI `response_format`、vLLM 的 guided decoding、llama.cpp GBNF 文法);库侧可用 outlines(dottxt-ai/outlines,仓库核实)。具体命令行本次未复验【未验证】。
- [ ] 解析失败要有降级路径(重试一次 → 拒答),不要"解析失败就整段透传"
- [ ] 输出再校验:PII/密钥/URL 白名单/长度/枚举值,校验失败即拦;PII 脱敏用 Presidio(`pip install presidio-analyzer presidio-anonymizer`,PyPI 2.2.364 核实)或 LLM Guard 的 Anonymize/Deanonymize 扫描器
- LLM Guard 的 `JSON` 输出扫描器就是这个位置(见 3.1)。

## 4 多模态特有风险点
- 视觉:对抗补丁/贴纸(白盒走 PGD,黑盒走补丁迁移)、图像内**内嵌文字注入**(模型把图里文字当指令)、隐写注入不可见文本
- 音频:Whisper 类 ASR 上的目标对抗(扰动不可听但转写可控;参考仓库 carlini/audio_adversarial_examples,本次核实存在)
- 跨模态一致性:图说一套、文说一套,下游只信文本 = 绕过图像审核
- 审计动作:同一输入的图像版/文本版分别过护栏,对比判定差异;图像 OCR 结果要单独过注入检测
- 上游该文件的工具链接 ethz-privsec/mllm-attack、ggg0912/MM-Safety、linzhiqiu/vgascore 全部 404(本次实测),替代:Unispac/Visual-Adversarial-Examples-Jailbreak-Large-Language-Models、centerforaisafety/HarmBench(含多模态)、carlini/audio_adversarial_examples

## 5 联邦学习特有风险点
- 威胁面:模型投毒(拜占庭)、梯度泄露(能从梯度反推训练样本)、成员推断、自由骑
- 聚合鲁棒性:Mean 聚合对恶意客户端无抵抗力;Krum/Multi-Krum、Trimmed-mean、median 是公开算法。**上游的 `from krum import KrumAggregator` 不存在(PyPI 404,本次实测),丢弃——要自己实现或读论文实现**
- 梯度泄露缓解:梯度压缩/加噪、安全聚合(两两秘密共享掩码)
- 框架(仓库均本次核实):Flower(`pip install flwr`,PyPI 1.38.0;**注意 PyPI 上的 `flower` 是 Celery 监控工具,不是联邦学习**)、tensorflow/federated、FederatedAI/FATE、OpenMined/PySyft(`pip install syft`,PyPI 0.10.0)、facebookresearch/CrypTen(已归档)、pytorch/opacus(差分隐私)
- 审计动作:客户端梯度是否有裁剪+加噪;聚合前是否剔除异常梯度;参与方之间是否真的没有旁路通道

## 6 AI 供应链审计命令(HF 模型 / LoRA / 推理镜像)

```bash
# 1) 序列化文件静态扫描(三道)
pip install modelscan picklescan fickling
modelscan -p /path/model.pkl                      # 官方 README 核实
picklescan --path downloads/pytorch_model.bin     # 官方 README 核实
picklescan --huggingface <owner/repo>             # 直接扫仓库(README 核实)
fickling --check-safety -p pickled.data           # 官方 README 核实
fickling --trace file.pkl                         # 打印 pickle VM 执行轨迹

# 2) 优先 safetensors:头部就是 8 字节小端长度 + JSON(本机用真实模型实测通过)
python - model.safetensors <<'PY'
import json, struct, sys
with open(sys.argv[1], "rb") as f:
    n = struct.unpack("<Q", f.read(8))[0]; hdr = json.loads(f.read(n))
print("header bytes", n, "tensors", len(hdr), "meta", hdr.get("__metadata__"))
PY

# 3) 锁定版本 + 本地校验
hf download <owner/repo> --revision <commit-sha> --local-dir ./m   # 固定 revision 而不是 main
hf models info <owner/repo>
hf cache verify <owner/repo>      # 子命令取自本机 hf CLI 帮助(huggingface_hub 1.24)
```
- **上游的 `huggingface-cli verify-repo-signatures <repo>` 不是真实命令**(本机 hf CLI 无该子命令,本次实测),丢弃。HF 的签名面是 commit 签名:Hub 页面显示 Verified 徽标;本地核对要自己取签名文件用 `gpg --verify`(官方文档 security-gpg)。
- 加载侧硬规则:禁 `trust_remote_code=True`、只用 safetensors;必须在沙箱/无凭证环境首次加载(AML.CS0031 恶意模型、AML.CS0028 供应链篡改模型)。
- 依赖与镜像:
```bash
trivy fs --scanners vuln,secret,misconfig /path/to/project   # 官方文档:--scanners 取值 vuln,misconfig,secret,license
pip install safety && safety scan                            # 官方 README 核实的新式命令
```
  上游的原句是 `trivy fs --severity HIGH,CRITICAL --exit-code 1 /path`(还有 `trivy image --severity ...`),没写扫哪些类目(默认 vuln+secret,漏 misconfig);更早的 `--security-checks` 是旧参数名。上面的 `--scanners vuln,secret,misconfig` 取自官方文档。上游的 `safety check -r requirements.txt --full-report` 是旧式命令,官方 README 现在写的是 `safety scan`。
- LoRA/adapter 单独审:adapter 权重与基座分别做差分扫描,别只看基座;`pip install peft`(huggingface/peft,仓库核实)。
- 上线前清单(吸收上游):safetensors 优先、依赖锁定+SHA、SBOM 留存(训练框架/数据集/基座/Python 依赖四项)、镜像扫 CVE、第三方 AI 服务过安全评估。
