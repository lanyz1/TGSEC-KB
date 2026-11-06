## 十三、CI/CD 攻击测试检查清单（高级版）

- [ ] 平台指纹与版本识别（Jenkins/GitLab/GitHub企业/ArgoCD/Nexus/Harbor/TeamCity）
- [ ] 版本对应 CVE 核对（见第十章速查表 + 官方公告）
- [ ] .git 目录泄露 / Git 历史/reflog/stash/dangling commit 挖掘
- [ ] 公开仓库与代码搜索（dorking）敏感信息
- [ ] Secret 批量扫描（trufflehog/gitleaks 全历史）
- [ ] GitLab: CVE-2023-7028 密码重置 / CI lint SSRF / CI_JOB_TOKEN 权限
- [ ] Jenkins: Script Console / CVE-2024-23897 文件读取 / 凭据库解密
- [ ] GitHub Actions: workflow 注入点审计 / GITHUB_TOKEN 滥用 / 自托管 Runner
- [ ] 流水线配置注入点（PR/issue/branch/tag/webhook 输入）
- [ ] 依赖混淆/typosquatting 候选收集与公共源验证
- [ ] 制品库匿名访问（Nexus/Artifactory/Harbor/Docker Registry）
- [ ] 镜像层内 secrets 提取（docker history/env/层审计）
- [ ] ArgoCD: settings 未认证 / OIDC audience / webhook DoS / CSRF
- [ ] CD 平台弱口令/默认凭据/API 未授权端点
- [ ] 云身份面: OIDC token / kubeconfig / imagePullSecret
- [ ] 开发者终端初始访问面评估（凭据/插件/会话）
- [ ] 供应链影响面评估（仓库→构建→制品→生产全链）

