## 六、供应链代码审计

### 6.1 依赖漏洞（SCA）

```
- 已知 CVE：npm audit / pip audit / trivy / Snyk / OWASP Dependency-Check
- 传递依赖（transitive）漏洞：直接依赖更新 ≠ 修复，需锁定传递链
- 版本过时/EOL：Log4j 1.x、Fastjson 1.x、老 Jackson 均不再出补丁
- 运行期组件：Docker 基础镜像、二进制依赖（go.sum/npm lockfile 校验）
```

### 6.2 恶意包与投毒手法

```
- Typosquatting：拼写相似包名（reacT、requests-lib、pthon）
- Combosquatting：热门包名组合（django-admin-utils）
- Dependency Confusion：私有依赖名被同名公开恶意包抢占（PyPI 优先于私有仓库）
- Repo Confusion / Starjacking：伪造仓库地址借热门项目星标增信
- 维护者账号劫持：合法包推送后门版本（XZ Utils、ua-parser-js、event-stream 前车之鉴）
- 安装钩子攻击：npm install 脚本/preinstall/postinstall 下载执行载荷
- 隐藏代码：Unicode 不可见字符、RTL 覆盖、混淆 eval、熵值高的编码载荷、超大文件跳过扫描
- divide-and-hide：恶意逻辑拆分到多个包，单包分析不可见
```

### 6.3 第三方库源码人工审计要点

```
- 只审安装钩子/构建脚本远不够：恶意代码可能藏于任何模块文件
- 优先审计：入口文件、setup.py/package.json scripts、加密/编码相关函数、网络调用
- 差分分析：比对发布制品与源码仓库差异（恶意代码常只进制品不进源码）
- 高危行为模式：
  - 混淆/编码的字符串、高熵 base64/hex 块
  - 域名硬编码、内网 IP、C2 特征
  - 环境变量/浏览器数据窃取（cookies/passwords/keys）
  - 静默外传（ping 外网、DNS 外带）
  - 自删除/下载执行（curl|sh、wget 到 tmp）
```

### 6.4 供应链检测实战命令

```bash
# npm 恶意包/依赖投毒扫描（2026 活跃恶意活动：GlassWorm、Flooding Dropper 等）
npx supply-chain-guard scan ./package-lock.json
npx supply-chain-guard scan ./          # 递归全仓

# 已知 CVE 检测
npm audit --json
pip audit
trivy fs --scanners vuln,secret,misconfig .
trivy repo https://github.com/org/repo       # 仓库级
grype ./                                      # Anchore 替代品
owasp-dependency-check.sh --scan ./pom.xml

# 密钥/凭据扫描（含 Git 历史）
gitleaks detect --source . --log-opts="--all"
trufflehog git https://github.com/org/repo --results=verified

# 依赖解析与锁定文件审计
pip-audit -r requirements.txt
npm ls --all                                    # 看传递依赖
go list -m all | grep -iE "可疑域名|私有仓库"
```

### 6.5 SBOM 与 SLSA 溯源

```
- SBOM 生成：syft generate ./ → SPDX/CycloneDX 格式
- 工具链构建：cosign 对镜像签名 + SLSA provenance（in-toto/DSSE attestation）
- 审计价值：SBOM 支撑漏洞回溯与投毒影响面评估
- 实战：
  syft dir:./src -o spdx-json > sbom.json
  cosign verify-attestation --type slsaprovenance <image>
```

