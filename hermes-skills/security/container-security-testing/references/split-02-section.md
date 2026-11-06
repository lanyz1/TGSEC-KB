## 一、镜像安全深度审计与供应链攻击

### 1.1 镜像层分析与漏洞扫描

```bash
# 镜像解包与逐层分析
docker save target:latest -o image.tar
tar -xf image.tar
# 逐层检查：manifest.json 列出 layer 顺序，逐层解包对比文件系统变更

# 漏洞扫描（多引擎交叉验证）
trivy image --severity HIGH,CRITICAL target:latest
trivy image --ignore-unfixed target:latest       # 只看有修复的
grype target:latest
docker scout cves target:latest                  # Docker 官方

# 敏感信息检测
docker history --no-trunc target:latest           # 查看每一层 RUN 指令（泄露密钥常见来源）
dive target:latest                                # 交互式逐层分析
trivy image --scanners secret,config target:latest  # 内置 secret 扫描

# 软件物料清单（SBOM）——供应链审计基线
syft target:latest -o spdx-json > sbom.json
trivy sbom sbom.json
```

### 1.2 Dockerfile 安全审计要点

```dockerfile
# 高风险模式（逐一核查）：
# 1. FROM 使用 root 基础镜像或 latest 浮动标签（不可复现）
# 2. ADD 远程 URL/自动解压（本地 tar 覆盖风险）
# 3. RUN 链式 && 中间残留密钥（多阶段构建清理）
# 4. 缺少 USER 非 root 指令（容器内 root = 逃逸放大器）
# 5. ENV/ARG 硬编码凭据（AK/SK、DB 密码、token）
# 6. 无 HEALTHCHECK/无 readOnlyRootFilesystem
# 7. .dockerignore 缺失（.env/.git/.ssh 被打进镜像）

# 静态审计工具
hadolint Dockerfile          # Dockerfile lint
dockle target:latest         # 容器镜像 CI 审计（CIS Docker Benchmark）
checkov -d .                 # IaC 安全扫描（含 Dockerfile/K8s Manifest/Helm）
```

### 1.3 镜像供应链攻击深度（联动 ci-cd-attack-testing）

```
攻击面全景：
1. 基础镜像投毒（Docker Hub 恶意/仿冒镜像，冒充 MySQL/Redis/Gradle 等）
2. 依赖包漏洞与依赖混淆（npm/pypi 同形字包名劫持）
3. 构建环境泄露（CI 流水线 secrets、.env、云端凭据被嵌入镜像层）
4. Dockerfile 注入（恶意 RUN 指令，如 cryptominer entrypoint）
5. Registry 未认证 push（获取目标仓库写权限后直接覆盖 tag）
6. 签名绕过（Notary/Cosign 校验缺失或 DCT 层篡改）
7. CI/CD 管道投毒（恶意构建阶段/依赖源替换/上游镜像 tag 漂移）
8. 安全工具自身被投毒（2026-03 aquasec/trivy 镜像事件：0.69.4~0.69.6/latest 被植入 infostealer，
   窃取 ~/.docker/config.json、云凭据、SSH key、CI/CD secrets；扫描器常挂载 docker.sock → 整机沦陷）
```

**镜像层后门——gh0stEdit（2025 披露）：**
利用 Docker 镜像分层/共享层机制，恶意篡改镜像层数据，**不改变镜像 history、层级结构**，且对 DCT 签名镜像**签名不失效**，静态/动态扫描工具均无法检出：

```bash
# 攻击思路（概念，授权测试用）：
# 1. 分析目标镜像 manifest，定位可篡改的共享 layer blob
# 2. 直接改写 layer 内文件（如 /etc/ld.so.preload、bashrc、entrypoint）但不触发重新提交
# 3. 保持 manifest/history 不变 → 签名校验通过 → 扫描器无感
# 防御：镜像准入校验须基于 digest（imagePullPolicy: Always + digest 引用）并做运行时基线对比
```

**供应链投毒检测命令：**
```bash
# 检查本地镜像是否命中已知被投毒 digest（Trivy 事件）
docker images --digests | grep -i trivy
# 已知恶意 digest（示例）：sha256:27f446230c60bbf0b70e008db798bd4f33b7826f9f76f756606f5417100beef3

# 校验镜像摘要而不是 tag（防 tag 漂移）
docker pull target:0.69.3@sha256:<digest>

# 检查镜像内是否有可疑的 entrypoint / 自动启动脚本
docker inspect target:latest --format '{{json .Config.Entrypoint}}'
docker run --rm --entrypoint cat target:latest /entrypoint.sh
```

### 1.4 签名验证与绕过

```bash
# Cosign 签名/验证
cosign sign --key cosign.key target:latest
cosign verify --key cosign.pub target:latest

# 绕过场景：
# - 集群未配置 ImagePolicyWebhook / Kyverno 校验 → 签名形同虚设
# - 签名只覆盖 manifest 不覆盖 blob → gh0stEdit 式层篡改
# - 使用 proxy-cache 镜像仓库时签名链断裂被绕过
# 测试：修改镜像层重新 push 同 tag，验证目标集群是否仍拉取

# K8s 侧强制（防御参考）
# Kyverno ClusterPolicy: verifyImageSignatures / ImageValidatingPolicy
```

